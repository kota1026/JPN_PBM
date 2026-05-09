"""NDRRMC alert receiver ─ 災害宣言で CP-6 自動起動 (CP-6 v2 PH / 戦略会議 #16+#17 採択 PH-4)。

戦略会議 #17 で Engr. Roberto Lim (元 Coins.ph) が「**NDRRMC 公開 API は存在しない**」と
指摘。代替経路:
1. **SMS gateway 受信** (NDRRMC は公式 SMS で発令、SMS gateway 契約 PHP 50K/月)
2. **PRC (Philippine Red Cross) API 連携** (PRC は IT 整備済、災害現場詳細を持つ)

両方を mock。実 SMS gateway / PRC API は R20+。

【インターフェース】
- `NdrrmcBackend.publish_alert(alert)` ─ alert 受信 (mock 注入用)
- `NdrrmcBackend.is_code_red(lgu_code)` ─ 該当 LGU が Code Red 中か
- `NdrrmcBackend.list_active_alerts()` ─ 有効 alert 一覧
- `NdrrmcBackend.subscribe_callback(callback)` ─ alert 受信時のコールバック登録

【factory】
    backend = get_ndrrmc_backend()
       JPN_PBM_NDRRMC_BACKEND=mock         (default)
       JPN_PBM_NDRRMC_BACKEND=sms_gateway  + JPN_PBM_NDRRMC_GATEWAY_URL=...
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Literal, Protocol


AlertLevel = Literal["white", "blue", "green", "yellow", "red"]
AlertSource = Literal["ndrrmc_sms", "prc_api", "manual_override"]


@dataclass(frozen=True)
class NdrrmcConfig:
    backend: str = "mock"
    sms_gateway_url: str | None = None
    sms_gateway_token: str | None = None
    prc_api_url: str | None = None


@dataclass(frozen=True)
class NdrrmcAlert:
    """1 件の災害 alert。"""
    alert_id: str
    level: AlertLevel
    lgu_codes: tuple[str, ...]   # 該当 LGU (e.g., "QC", "MNL", "CAL")
    source: AlertSource
    issued_at: float
    valid_until: float
    description: str = ""

    def is_expired(self, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) > self.valid_until

    def is_code_red(self) -> bool:
        return self.level == "red"


class NdrrmcBackend(Protocol):
    def publish_alert(self, alert: NdrrmcAlert) -> None: ...
    def is_code_red(self, lgu_code: str) -> bool: ...
    def list_active_alerts(self) -> list[NdrrmcAlert]: ...
    def subscribe_callback(self, callback: Callable[[NdrrmcAlert], None]) -> None: ...


class MockNdrrmcBackend:
    """in-process mock。test/手動で publish_alert() で alert を注入する。

    実運用 (R20+) では SMS gateway / PRC API から定期 poll するのを置換。
    """

    def __init__(self) -> None:
        self._alerts: list[NdrrmcAlert] = []
        self._callbacks: list[Callable[[NdrrmcAlert], None]] = []

    def publish_alert(self, alert: NdrrmcAlert) -> None:
        self._alerts.append(alert)
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception:
                pass  # callback failures should not block alert delivery

    def is_code_red(self, lgu_code: str) -> bool:
        now = time.time()
        return any(
            a.is_code_red() and lgu_code in a.lgu_codes and not a.is_expired(now)
            for a in self._alerts
        )

    def list_active_alerts(self) -> list[NdrrmcAlert]:
        now = time.time()
        return [a for a in self._alerts if not a.is_expired(now)]

    def subscribe_callback(self, callback: Callable[[NdrrmcAlert], None]) -> None:
        self._callbacks.append(callback)

    def manual_override(self, *, lgu_code: str, level: AlertLevel = "red",
                        duration_sec: int = 86400, description: str = "manual override"
                        ) -> NdrrmcAlert:
        """手動緊急発令 (PH-4: SMS が来ない場合の fallback)。"""
        alert = NdrrmcAlert(
            alert_id=f"manual-{int(time.time())}",
            level=level, lgu_codes=(lgu_code,),
            source="manual_override",
            issued_at=time.time(),
            valid_until=time.time() + duration_sec,
            description=description,
        )
        self.publish_alert(alert)
        return alert


class SmsGatewayNdrrmcBackend:
    """実 SMS gateway 受信版 (R20+ 実装)。"""

    def __init__(self, cfg: NdrrmcConfig) -> None:
        if not cfg.sms_gateway_url:
            raise ValueError("NdrrmcConfig.sms_gateway_url required")
        if not cfg.sms_gateway_token:
            raise ValueError("NdrrmcConfig.sms_gateway_token required")
        self._cfg = cfg

    def _impl_pending(self):
        raise NotImplementedError(
            "SmsGatewayNdrrmcBackend: pending real SMS gateway contract (R20+)"
        )

    def publish_alert(self, alert): self._impl_pending()
    def is_code_red(self, lgu_code): return False
    def list_active_alerts(self): return []
    def subscribe_callback(self, callback): pass


def ndrrmc_config_from_env() -> NdrrmcConfig:
    return NdrrmcConfig(
        backend=os.environ.get("JPN_PBM_NDRRMC_BACKEND", "mock"),
        sms_gateway_url=os.environ.get("JPN_PBM_NDRRMC_GATEWAY_URL"),
        sms_gateway_token=os.environ.get("JPN_PBM_NDRRMC_GATEWAY_TOKEN"),
        prc_api_url=os.environ.get("JPN_PBM_PRC_API_URL"),
    )


def get_ndrrmc_backend(cfg: NdrrmcConfig | None = None) -> NdrrmcBackend:
    cfg = cfg or ndrrmc_config_from_env()
    if cfg.backend == "mock":
        return MockNdrrmcBackend()
    if cfg.backend in ("sms_gateway", "real"):
        return SmsGatewayNdrrmcBackend(cfg)
    raise ValueError(f"unknown ndrrmc backend: {cfg.backend} (expected: mock|sms_gateway)")
