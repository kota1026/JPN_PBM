"""UNHCR ProGres federation adapter ─ DP-6 (戦略会議 #19 採択 DPI-1)。

UNHCR ProGres (UN refugee registry, 7,500 万人) を **受益者識別の唯一の信頼源**
として federate する。新規 ID システムは作らない。Imran Khan (UNHCR 元 Identity
Specialist) の council 提言を反映。

【DPI-7 反映】
biometric (iris / fingerprint) は **on-chain には書かない**。
ProGres ID は HMAC で即座に pseudonymize、生 ID は契約レイヤに渡さない。

【factory】
    backend = get_unhcr_progres_backend()
       JPN_PBM_PROGRES_BACKEND=mock      (default)
       JPN_PBM_PROGRES_BACKEND=hcb       + JPN_PBM_PROGRES_API_KEY=...  (R22+)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol


ProGresStatus = Literal["active", "inactive", "deceased", "resettled", "returned"]


PROGRES_SECRET = os.environ.get(
    "JPN_PBM_PROGRES_HMAC_SECRET", "demo-progres-hmac-secret"
).encode()


@dataclass(frozen=True)
class UnhcrProGresConfig:
    backend: str = "mock"
    api_key: str | None = None
    base_url: str | None = None
    timeout_sec: float = 10.0


@dataclass(frozen=True)
class ProGresHouseholdInfo:
    """UNHCR ProGres から取得する世帯情報 (HMAC pid のみ、生 ID 不在)。"""
    household_pid: str           # HMAC(progres_id)
    member_count: int
    children_under_5_count: int
    children_school_age_count: int
    country_of_origin: str       # ISO-2
    country_of_residence: str    # ISO-2
    region: str                  # 例: "Kayes", "Sa'ada"
    status: ProGresStatus
    last_verified_at: float


class UnhcrProGresError(Exception):
    pass


# ============================================================
# Protocol
# ============================================================


class UnhcrProGresBackend(Protocol):
    def resolve_household(self, *, progres_id: str
                           ) -> ProGresHouseholdInfo | None: ...
    def check_active_status(self, *, progres_id: str) -> bool: ...
    def is_sandbox(self) -> bool: ...


# ============================================================
# Mock backend
# ============================================================


def progres_id_to_pid(progres_id: str) -> str:
    """ProGres ID → HMAC pid (生 ID は contract に渡さない)。"""
    return hmac.new(PROGRES_SECRET, progres_id.encode(),
                     hashlib.sha256).hexdigest()


class MockUnhcrProGresBackend:
    """in-process mock。Mali / Yemen / Bangladesh のテスト用 5-10 family。"""

    def __init__(self) -> None:
        # seed: mock 9 household across 3 countries
        self._households: dict[str, ProGresHouseholdInfo] = {}
        self._seed_mock_data()

    def _seed_mock_data(self) -> None:
        now = time.time()
        mock_data = [
            # Mali Kayes
            ("ML-PRG-001", 5, 2, 2, "ML", "ML", "Kayes", "active"),
            ("ML-PRG-002", 4, 1, 2, "ML", "ML", "Kayes", "active"),
            ("ML-PRG-003", 6, 2, 3, "ML", "ML", "Koulikoro", "active"),
            ("ML-PRG-004", 3, 0, 2, "ML", "ML", "Sikasso", "active"),
            # Yemen
            ("YE-PRG-001", 6, 2, 3, "YE", "YE", "Sa'ada", "active"),
            ("YE-PRG-002", 4, 1, 2, "YE", "YE", "Hodeidah", "active"),
            ("YE-PRG-003", 5, 0, 3, "SY", "YE", "Hajjah", "active"),  # シリア籍
            # Bangladesh
            ("BD-PRG-001", 4, 0, 2, "BD", "BD", "Chattogram", "active"),
            ("BD-PRG-002", 3, 0, 1, "BD", "BD", "Dhaka", "active"),
            # inactive (re-settled)
            ("ML-PRG-099", 3, 0, 1, "ML", "ML", "Kayes", "resettled"),
        ]
        for progres_id, mc, c5, csa, coo, cor, reg, status in mock_data:
            pid = progres_id_to_pid(progres_id)
            self._households[progres_id] = ProGresHouseholdInfo(
                household_pid=pid,
                member_count=mc,
                children_under_5_count=c5,
                children_school_age_count=csa,
                country_of_origin=coo,
                country_of_residence=cor,
                region=reg,
                status=status,  # type: ignore
                last_verified_at=now,
            )

    def is_sandbox(self) -> bool:
        return True

    def resolve_household(self, *, progres_id: str
                           ) -> ProGresHouseholdInfo | None:
        return self._households.get(progres_id)

    def check_active_status(self, *, progres_id: str) -> bool:
        info = self._households.get(progres_id)
        return info is not None and info.status == "active"


# ============================================================
# Real backend (R22+)
# ============================================================


class HcbUnhcrProGresBackend:
    """UNHCR HCB (Humanitarian Cash-Based) API 経由 (R22+ 実装)。

    UNHCR との data sharing agreement 締結後に使う。
    """

    def __init__(self, cfg: UnhcrProGresConfig) -> None:
        if not cfg.api_key:
            raise UnhcrProGresError("HcbUnhcrProGresBackend requires api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def _impl_pending(self):
        raise NotImplementedError(
            "HcbUnhcrProGresBackend: pending UNHCR data sharing agreement (R22+)"
        )

    def resolve_household(self, **kwargs): self._impl_pending()
    def check_active_status(self, **kwargs): return False


# ============================================================
# factory
# ============================================================


def unhcr_progres_config_from_env() -> UnhcrProGresConfig:
    return UnhcrProGresConfig(
        backend=os.environ.get("JPN_PBM_PROGRES_BACKEND", "mock"),
        api_key=os.environ.get("JPN_PBM_PROGRES_API_KEY"),
        base_url=os.environ.get("JPN_PBM_PROGRES_BASE_URL"),
        timeout_sec=float(os.environ.get("JPN_PBM_PROGRES_TIMEOUT", "10.0")),
    )


def get_unhcr_progres_backend(cfg: UnhcrProGresConfig | None = None
                                ) -> UnhcrProGresBackend:
    cfg = cfg or unhcr_progres_config_from_env()
    if cfg.backend == "mock":
        return MockUnhcrProGresBackend()
    if cfg.backend in ("hcb", "real"):
        return HcbUnhcrProGresBackend(cfg)
    raise UnhcrProGresError(
        f"unknown UNHCR ProGres backend: {cfg.backend} (expected: mock|hcb)"
    )
