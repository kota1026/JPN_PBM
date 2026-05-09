"""LandBank ATM bridge — 4Ps 既存配給フローへの bolt-on (戦略会議 #14 採択 T4)。

DSWD 4Ps の現運用は **LandBank cash card** へ毎月入金 → 受給者 ATM 引き出し。
JPN-PBM を導入しても **既存 LandBank 経路を一晩で置換するのは不可能** (政策合意 +
インフラ更新が必要)。代わりに「**並列運用**」 = LandBank 入金 + PBM 入金を同月内
に併存させ、受給者が状況に応じて選べる体制を作る。

【bridge の役割】
1. DSWD が「この世帯は今月 PBM 経由で配る」と決めたら、LandBank 側はその月
   入金しない (or 半額にする) よう同期。
2. LandBank ATM 引き出しと PBM 利用が**同月内に重複しない**よう nonce 管理。
3. 災害時 (CP-6) の オフライン QR 利用は LandBank では追跡できないので、
   復旧後に bridge が補正データを LandBank に流す。

【設計原則】
- LandBank API は政府所管なので外部仕様非公開 → 本モジュールは **interface のみ**
  実装し、実運用時に DSWD 経由で LandBank の正規 API を叩くアダプタに差し替える
- sandbox では完全 mock (in-memory)
- すべての操作は監査ログ可能 (`bridge_audit_log` に記録)

【factory】
    bridge = get_landbank_bridge()
       JPN_PBM_LANDBANK_BACKEND=mock          (default)
       JPN_PBM_LANDBANK_BACKEND=dswd_proxy    + JPN_PBM_LANDBANK_BASE_URL=...
                                              + JPN_PBM_LANDBANK_API_KEY=...
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol


DisbursementMode = Literal["landbank_only", "pbm_only", "split"]


# ============================================================
# データ型
# ============================================================


@dataclass(frozen=True)
class LandBankConfig:
    backend: str = "mock"
    base_url: str | None = None
    api_key: str | None = None
    timeout_sec: float = 5.0


@dataclass
class HouseholdState:
    """4Ps 1 世帯の bridge 状態。"""
    psn_pid: str                        # HMAC PSN
    month_index: int                    # YYYYMM
    mode: DisbursementMode = "landbank_only"
    landbank_amount_centavos: int = 0
    pbm_amount_centavos: int = 0
    landbank_withdrawn_centavos: int = 0
    pbm_redeemed_centavos: int = 0


@dataclass
class BridgeAuditEntry:
    timestamp: float
    op: str
    psn_pid: str
    month_index: int
    detail: str


# ============================================================
# Protocol
# ============================================================


class LandBankBridge(Protocol):
    def get_household_state(self, *, psn_pid: str, month_index: int) -> HouseholdState | None: ...
    def set_disbursement_mode(self, *, psn_pid: str, month_index: int,
                              mode: DisbursementMode,
                              landbank_amount_centavos: int = 0,
                              pbm_amount_centavos: int = 0) -> HouseholdState: ...
    def record_landbank_withdrawal(self, *, psn_pid: str, month_index: int,
                                    amount_centavos: int) -> HouseholdState: ...
    def record_pbm_redemption(self, *, psn_pid: str, month_index: int,
                               amount_centavos: int) -> HouseholdState: ...
    def reconcile_offline_redemptions(self, *, psn_pid: str, month_index: int,
                                       offline_total_centavos: int) -> HouseholdState: ...
    def audit_log(self) -> list[BridgeAuditEntry]: ...


# ============================================================
# Mock 実装
# ============================================================


class MockLandBankBridge:
    """in-process mock。DSWD / LandBank の API 仕様が手元にない間の代用。"""

    def __init__(self) -> None:
        self._states: dict[tuple[str, int], HouseholdState] = {}
        self._audit: list[BridgeAuditEntry] = []

    # -- write ops --

    def set_disbursement_mode(self, *, psn_pid: str, month_index: int,
                              mode: DisbursementMode,
                              landbank_amount_centavos: int = 0,
                              pbm_amount_centavos: int = 0) -> HouseholdState:
        if landbank_amount_centavos < 0 or pbm_amount_centavos < 0:
            raise ValueError("amounts must be >= 0")
        if mode == "landbank_only" and pbm_amount_centavos != 0:
            raise ValueError("landbank_only mode cannot have pbm_amount > 0")
        if mode == "pbm_only" and landbank_amount_centavos != 0:
            raise ValueError("pbm_only mode cannot have landbank_amount > 0")
        key = (psn_pid, month_index)
        self._states[key] = HouseholdState(
            psn_pid=psn_pid, month_index=month_index, mode=mode,
            landbank_amount_centavos=landbank_amount_centavos,
            pbm_amount_centavos=pbm_amount_centavos,
        )
        self._log("set_mode", psn_pid, month_index,
                  f"mode={mode} lb={landbank_amount_centavos} pbm={pbm_amount_centavos}")
        return self._states[key]

    def record_landbank_withdrawal(self, *, psn_pid: str, month_index: int,
                                    amount_centavos: int) -> HouseholdState:
        if amount_centavos <= 0:
            raise ValueError("amount must be > 0")
        st = self._must_get(psn_pid, month_index)
        if st.mode == "pbm_only":
            raise ValueError(
                f"household in pbm_only mode for month {month_index}; "
                "LandBank withdrawal would be CP-5 violation (double-disbursement)"
            )
        new_total = st.landbank_withdrawn_centavos + amount_centavos
        if new_total > st.landbank_amount_centavos:
            raise ValueError(
                f"LandBank cap exceeded ({new_total} > {st.landbank_amount_centavos})"
            )
        st.landbank_withdrawn_centavos = new_total
        self._log("lb_withdraw", psn_pid, month_index, f"+{amount_centavos}")
        return st

    def record_pbm_redemption(self, *, psn_pid: str, month_index: int,
                               amount_centavos: int) -> HouseholdState:
        if amount_centavos <= 0:
            raise ValueError("amount must be > 0")
        st = self._must_get(psn_pid, month_index)
        if st.mode == "landbank_only":
            raise ValueError(
                f"household in landbank_only mode for month {month_index}; "
                "PBM redemption would be CP-5 violation"
            )
        new_total = st.pbm_redeemed_centavos + amount_centavos
        if new_total > st.pbm_amount_centavos:
            raise ValueError(
                f"PBM cap exceeded ({new_total} > {st.pbm_amount_centavos})"
            )
        st.pbm_redeemed_centavos = new_total
        self._log("pbm_redeem", psn_pid, month_index, f"+{amount_centavos}")
        return st

    def reconcile_offline_redemptions(self, *, psn_pid: str, month_index: int,
                                       offline_total_centavos: int) -> HouseholdState:
        """災害時 CP-6 のオフライン redemption を月末に補正する。"""
        if offline_total_centavos <= 0:
            return self._must_get(psn_pid, month_index)
        st = self._must_get(psn_pid, month_index)
        # offline は normal redemption と同じ枠を消費する
        new_total = st.pbm_redeemed_centavos + offline_total_centavos
        if new_total > st.pbm_amount_centavos:
            # 災害時の超過は許容 (CP-6 spec: 30 day grace)、ただし audit log
            self._log("offline_overage", psn_pid, month_index,
                      f"used={new_total} cap={st.pbm_amount_centavos} (CP-6 grace)")
        st.pbm_redeemed_centavos = new_total
        self._log("offline_reconcile", psn_pid, month_index,
                  f"+{offline_total_centavos}")
        return st

    # -- read ops --

    def get_household_state(self, *, psn_pid: str, month_index: int) -> HouseholdState | None:
        return self._states.get((psn_pid, month_index))

    def audit_log(self) -> list[BridgeAuditEntry]:
        return list(self._audit)

    # -- internal --

    def _must_get(self, psn_pid: str, month_index: int) -> HouseholdState:
        st = self._states.get((psn_pid, month_index))
        if st is None:
            raise ValueError(
                f"household state not initialized for "
                f"(psn={psn_pid[:8]}.., month={month_index}). "
                "call set_disbursement_mode() first."
            )
        return st

    def _log(self, op: str, psn_pid: str, month_index: int, detail: str) -> None:
        self._audit.append(BridgeAuditEntry(
            timestamp=time.time(), op=op,
            psn_pid=psn_pid, month_index=month_index, detail=detail,
        ))


# ============================================================
# Real 実装 (DSWD proxy 経由)
# ============================================================


class DswdProxyLandBankBridge:
    """DSWD が提供する LandBank proxy API 経由 (Round 16+ 実装)。

    LandBank の API 仕様は政府所管のため非公開 → DSWD が中継 proxy を提供する想定。
    """

    def __init__(self, cfg: LandBankConfig) -> None:
        if not cfg.api_key:
            raise ValueError("LandBankConfig.api_key required")
        if not cfg.base_url:
            raise ValueError("LandBankConfig.base_url required")
        self._cfg = cfg

    def _impl_pending(self) -> "HouseholdState":
        raise NotImplementedError(
            "DswdProxyLandBankBridge: real proxy spec pending "
            "DSWD agreement (Round 16+)"
        )

    def get_household_state(self, *, psn_pid: str, month_index: int): return self._impl_pending()
    def set_disbursement_mode(self, **kwargs): return self._impl_pending()
    def record_landbank_withdrawal(self, **kwargs): return self._impl_pending()
    def record_pbm_redemption(self, **kwargs): return self._impl_pending()
    def reconcile_offline_redemptions(self, **kwargs): return self._impl_pending()
    def audit_log(self): return []


# ============================================================
# factory
# ============================================================


def landbank_config_from_env() -> LandBankConfig:
    return LandBankConfig(
        backend=os.environ.get("JPN_PBM_LANDBANK_BACKEND", "mock"),
        base_url=os.environ.get("JPN_PBM_LANDBANK_BASE_URL"),
        api_key=os.environ.get("JPN_PBM_LANDBANK_API_KEY"),
        timeout_sec=float(os.environ.get("JPN_PBM_LANDBANK_TIMEOUT", "5.0")),
    )


def get_landbank_bridge(cfg: LandBankConfig | None = None) -> LandBankBridge:
    cfg = cfg or landbank_config_from_env()
    if cfg.backend == "mock":
        return MockLandBankBridge()
    if cfg.backend in ("dswd_proxy", "real"):
        return DswdProxyLandBankBridge(cfg)
    raise ValueError(
        f"unknown landbank backend: {cfg.backend} "
        "(expected: mock|dswd_proxy)"
    )
