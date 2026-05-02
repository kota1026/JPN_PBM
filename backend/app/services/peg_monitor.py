"""JPYC ペッグ監視 (戦略会議 #2 採択 #8)。

Stablecoin Architect 提案 + Red Team 修正案: Chainlink は Phase 2 (有料) なので
当面はハードコード閾値 + 手動 override で十分。

【判定】
- spot_jpy_per_jpyc が target = 1.0 から ±DEFAULT_DEVIATION_BPS (= 100bps = 1%)
  以上ズレたら ALERT、ズレ続けたら自動 freeze。
- 都の SOC が手動 override で freeze 解除できる。
- 監査: 全アラートと freeze 操作はメモリリングバッファ + (本番では) DB 保存。

【設計上の注意】
本モジュールは pure Python オブジェクト + プロセス内シングルトンで動く。プロセス
再起動で履歴は消える (本番では PostgreSQL に切り替える)。テストの観点では
PegMonitor を直接 instantiate してアサートする。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Iterable

DEFAULT_TARGET_JPY = 1.0
DEFAULT_DEVIATION_BPS = 100  # ±1% で ALERT
DEFAULT_FREEZE_BPS = 300     # ±3% で AUTO-FREEZE
DEFAULT_HISTORY_LEN = 256


@dataclass
class PegSample:
    ts: datetime
    spot_jpy_per_jpyc: float
    deviation_bps: int  # 負なら下方乖離

    @property
    def deviation_pct(self) -> float:
        return self.deviation_bps / 100.0


@dataclass
class PegStatus:
    healthy: bool
    frozen: bool
    last: PegSample | None
    last_alert_at: datetime | None
    last_freeze_reason: str = ""
    alerts: list[str] = field(default_factory=list)


class PegMonitor:
    """JPYC ペッグ監視のステートマシン。"""

    def __init__(
        self,
        *,
        target: float = DEFAULT_TARGET_JPY,
        alert_bps: int = DEFAULT_DEVIATION_BPS,
        freeze_bps: int = DEFAULT_FREEZE_BPS,
        history_len: int = DEFAULT_HISTORY_LEN,
    ) -> None:
        self.target = target
        self.alert_bps = alert_bps
        self.freeze_bps = freeze_bps
        self._history: Deque[PegSample] = deque(maxlen=history_len)
        self._frozen = False
        self._last_freeze_reason = ""
        self._last_alert_at: datetime | None = None

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def history(self) -> Iterable[PegSample]:
        return tuple(self._history)

    def submit(self, spot_jpy_per_jpyc: float, *, now: datetime | None = None) -> PegStatus:
        """data source から新しいスポット価格を投入し、判定を返す。"""
        now = now or datetime.utcnow()
        deviation_bps = int(round((spot_jpy_per_jpyc - self.target) / self.target * 10_000))
        sample = PegSample(ts=now, spot_jpy_per_jpyc=spot_jpy_per_jpyc, deviation_bps=deviation_bps)
        self._history.append(sample)

        alerts: list[str] = []
        abs_dev = abs(deviation_bps)
        if abs_dev >= self.freeze_bps:
            self._frozen = True
            self._last_freeze_reason = (
                f"AUTO-FREEZE: deviation={deviation_bps}bps "
                f"(>= freeze_bps={self.freeze_bps})"
            )
            alerts.append(self._last_freeze_reason)
            self._last_alert_at = now
        elif abs_dev >= self.alert_bps:
            alerts.append(
                f"ALERT: deviation={deviation_bps}bps (>= alert_bps={self.alert_bps})"
            )
            self._last_alert_at = now

        return PegStatus(
            healthy=(abs_dev < self.alert_bps and not self._frozen),
            frozen=self._frozen,
            last=sample,
            last_alert_at=self._last_alert_at,
            last_freeze_reason=self._last_freeze_reason,
            alerts=alerts,
        )

    def manual_unfreeze(self, *, by: str, reason: str) -> str:
        """都 SOC が手動で freeze 解除する (override)。"""
        if not self._frozen:
            return "noop: not frozen"
        self._frozen = False
        msg = f"MANUAL-UNFREEZE by={by}: {reason}"
        self._last_freeze_reason = msg
        return msg

    def manual_freeze(self, *, by: str, reason: str) -> str:
        """都 SOC が手動で freeze する (例: 法令改正前夜の予防的停止)。"""
        self._frozen = True
        msg = f"MANUAL-FREEZE by={by}: {reason}"
        self._last_freeze_reason = msg
        return msg


# プロセス内シングルトン (REST から共有される)
_singleton: PegMonitor | None = None


def get_monitor() -> PegMonitor:
    global _singleton
    if _singleton is None:
        _singleton = PegMonitor()
    return _singleton


def reset_for_test() -> None:
    """テスト用: シングルトンをリセット。"""
    global _singleton
    _singleton = None
