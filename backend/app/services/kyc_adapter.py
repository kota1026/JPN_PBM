"""KYC (Know Your Customer) adapter ─ DP-2 (戦略会議 #19 採択)。

寄付者の本人確認を Jumio / Onfido / Sumsub 等の SaaS で行うための抽象化。
R15 adapter pattern と同じ Protocol + Mock + Real + factory 構造。

【インターフェース】
- `KycBackend.verify(donor)` ─ KYC 実行
- `KycBackend.get_status(verification_id)` ─ 状態取得
- `KycBackend.estimate_cost(tier)` ─ tier 別コスト見積

【factory】
    backend = get_kyc_backend()
       JPN_PBM_KYC_BACKEND=mock          (default)
       JPN_PBM_KYC_BACKEND=jumio         + JPN_PBM_JUMIO_API_KEY=...
       JPN_PBM_KYC_BACKEND=onfido        + JPN_PBM_ONFIDO_API_KEY=...
       JPN_PBM_KYC_BACKEND=sumsub        + JPN_PBM_SUMSUB_API_KEY=...

【戦略会議 #19 採択】
- DPI-6 (tier-based KYC): Tier 0 anon → Tier 3 enhanced
- DPI-7 (biometric off-chain): face/finger は SaaS 内で完結、PBM contract に書込まない
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Literal, Protocol


KycTier = Literal[0, 1, 2, 3]
KycStatus = Literal["pending", "verified", "rejected", "review", "expired"]


@dataclass(frozen=True)
class KycConfig:
    backend: str = "mock"
    api_key: str | None = None
    base_url: str | None = None
    timeout_sec: float = 30.0


@dataclass
class DonorIdentity:
    """KYC 入力情報。tier に応じて必須項目が変わる。"""
    full_name: str
    dob: date | None = None              # Tier 1+
    country: str = "JP"
    email: str | None = None             # Tier 1+
    phone_e164: str | None = None        # Tier 1+
    photo_id_uri: str | None = None      # Tier 2+
    selfie_uri: str | None = None        # Tier 2+
    source_of_wealth: str | None = None  # Tier 3
    is_legal_entity: bool = False        # 法人


@dataclass
class KycVerification:
    verification_id: str
    donor_pid: str                   # HMAC で擬似 ID 化された donor 識別
    tier: KycTier
    status: KycStatus
    verified_at: float | None = None
    expires_at: float | None = None  # 1 年で expire
    failure_reason: str | None = None
    cost_usd_cents: int = 0
    is_mock: bool = True


class KycError(Exception):
    pass


# ============================================================
# Protocol
# ============================================================


class KycBackend(Protocol):
    def verify(self, *, identity: DonorIdentity, tier: KycTier,
                donor_pid: str) -> KycVerification: ...
    def get_status(self, verification_id: str) -> KycVerification | None: ...
    def estimate_cost(self, tier: KycTier) -> int: ...
    def is_sandbox(self) -> bool: ...


# ============================================================
# Mock 実装
# ============================================================


class MockKycBackend:
    """in-process mock。tier に応じた最小入力検証 + 確率的 review queue。

    Tier 0: 検証なし (anon)
    Tier 1: name + dob + email 必須
    Tier 2: + photo_id + selfie 必須
    Tier 3: + source_of_wealth
    """

    # 各 tier の cost (USD cents)
    COSTS_USD_CENTS: dict[KycTier, int] = {
        0: 0,
        1: 200,
        2: 600,
        3: 2000,
    }

    def __init__(self) -> None:
        self._verifications: dict[str, KycVerification] = {}

    def is_sandbox(self) -> bool:
        return True

    def estimate_cost(self, tier: KycTier) -> int:
        return self.COSTS_USD_CENTS.get(tier, 0)

    def verify(self, *, identity: DonorIdentity, tier: KycTier,
                donor_pid: str) -> KycVerification:
        # Tier 別必須項目チェック
        if tier == 0:
            # anon = 何もチェックしない
            pass
        elif tier >= 1:
            if not identity.full_name or not identity.dob or not identity.email:
                return self._reject(donor_pid, tier,
                                     "Tier 1 requires name + dob + email")
        if tier >= 2:
            if not identity.photo_id_uri or not identity.selfie_uri:
                return self._reject(donor_pid, tier,
                                     "Tier 2 requires photo_id + selfie")
        if tier >= 3:
            if not identity.source_of_wealth:
                return self._reject(donor_pid, tier,
                                     "Tier 3 requires source_of_wealth")

        # mock: 名前が "REJECT" を含むと拒否、"REVIEW" を含むと review queue
        if "REJECT" in identity.full_name.upper():
            return self._reject(donor_pid, tier, "mock: name contains REJECT")
        if "REVIEW" in identity.full_name.upper():
            v = self._build(donor_pid, tier, "review",
                             cost=self.COSTS_USD_CENTS[tier])
            self._verifications[v.verification_id] = v
            return v

        # verified
        v = self._build(donor_pid, tier, "verified",
                         cost=self.COSTS_USD_CENTS[tier])
        self._verifications[v.verification_id] = v
        return v

    def get_status(self, verification_id: str) -> KycVerification | None:
        return self._verifications.get(verification_id)

    # -- helpers --

    def _reject(self, donor_pid: str, tier: KycTier, reason: str) -> KycVerification:
        v = self._build(donor_pid, tier, "rejected",
                         failure_reason=reason)
        self._verifications[v.verification_id] = v
        return v

    def _build(self, donor_pid: str, tier: KycTier, status: KycStatus,
                cost: int = 0, failure_reason: str | None = None
                ) -> KycVerification:
        now = time.time()
        return KycVerification(
            verification_id="KYC-MOCK-" + uuid.uuid4().hex[:12].upper(),
            donor_pid=donor_pid,
            tier=tier,
            status=status,
            verified_at=now if status == "verified" else None,
            expires_at=now + 365 * 86400 if status == "verified" else None,
            failure_reason=failure_reason,
            cost_usd_cents=cost,
            is_mock=True,
        )


# ============================================================
# Real backends (R22+ 実装)
# ============================================================


class JumioBackend:
    def __init__(self, cfg: KycConfig) -> None:
        if not cfg.api_key:
            raise KycError("JumioBackend requires KycConfig.api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def _impl_pending(self):
        raise NotImplementedError(
            "JumioBackend: pending Jumio account + API integration (R22+)"
        )

    def verify(self, **kwargs): self._impl_pending()
    def get_status(self, verification_id): self._impl_pending()
    def estimate_cost(self, tier): return MockKycBackend().estimate_cost(tier)


class OnfidoBackend:
    def __init__(self, cfg: KycConfig) -> None:
        if not cfg.api_key:
            raise KycError("OnfidoBackend requires api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def _impl_pending(self):
        raise NotImplementedError("OnfidoBackend: pending (R22+)")

    def verify(self, **kwargs): self._impl_pending()
    def get_status(self, verification_id): self._impl_pending()
    def estimate_cost(self, tier): return MockKycBackend().estimate_cost(tier)


class SumsubBackend:
    def __init__(self, cfg: KycConfig) -> None:
        if not cfg.api_key:
            raise KycError("SumsubBackend requires api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def _impl_pending(self):
        raise NotImplementedError("SumsubBackend: pending (R22+)")

    def verify(self, **kwargs): self._impl_pending()
    def get_status(self, verification_id): self._impl_pending()
    def estimate_cost(self, tier): return MockKycBackend().estimate_cost(tier)


# ============================================================
# factory
# ============================================================


def kyc_config_from_env() -> KycConfig:
    return KycConfig(
        backend=os.environ.get("JPN_PBM_KYC_BACKEND", "mock"),
        api_key=(os.environ.get("JPN_PBM_JUMIO_API_KEY")
                  or os.environ.get("JPN_PBM_ONFIDO_API_KEY")
                  or os.environ.get("JPN_PBM_SUMSUB_API_KEY")),
        base_url=os.environ.get("JPN_PBM_KYC_BASE_URL"),
        timeout_sec=float(os.environ.get("JPN_PBM_KYC_TIMEOUT", "30.0")),
    )


def get_kyc_backend(cfg: KycConfig | None = None) -> KycBackend:
    cfg = cfg or kyc_config_from_env()
    if cfg.backend == "mock":
        return MockKycBackend()
    if cfg.backend == "jumio":
        return JumioBackend(cfg)
    if cfg.backend == "onfido":
        return OnfidoBackend(cfg)
    if cfg.backend == "sumsub":
        return SumsubBackend(cfg)
    raise KycError(
        f"unknown kyc backend: {cfg.backend} (expected: mock|jumio|onfido|sumsub)"
    )
