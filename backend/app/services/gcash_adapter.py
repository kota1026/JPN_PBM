"""GCash QR Ph payment adapter (戦略会議 #14 採択 T2)。

Manila pilot で受給者が QR Ph で決済する時、backend は GCash に対して:
- 加盟店の QR Ph 検証 (mostly client-side, server confirms)
- 決済リクエストの送信 (受給者 → 加盟店、self-pay 部分)
- 決済結果の受領 (webhook or polling)

を行う。本物の GCash Sandbox API は Coins.ph / Globe との契約後に使えるので、
sandbox では in-process mock で同じ shape を再現する。

【インターフェース】
- `GCashBackend.create_payment(...)` ─ 決済要求生成
- `GCashBackend.poll_payment(reference)` ─ 状態確認
- `GCashBackend.get_merchant_info(merchant_id)` ─ 加盟店メタデータ
- `GCashBackend.is_sandbox()` ─ mock / 本物の判別

【factory】
    backend = get_gcash_backend()
       JPN_PBM_GCASH_BACKEND=mock      (default)
       JPN_PBM_GCASH_BACKEND=sandbox   + JPN_PBM_GCASH_API_KEY=...
                                       + JPN_PBM_GCASH_BASE_URL=https://...
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, Protocol


PaymentStatus = Literal["pending", "succeeded", "failed", "expired"]


# ============================================================
# データ型
# ============================================================


@dataclass(frozen=True)
class GCashConfig:
    backend: str = "mock"           # mock / sandbox / production
    api_key: str | None = None
    base_url: str | None = None     # https://sandbox.gcash.com/v1
    timeout_sec: float = 5.0


@dataclass
class PaymentRequest:
    """フロントから受領する決済要求。"""
    merchant_id: str
    citizen_pid_short: str          # privacy: 先頭 8 文字のみ
    amount_centavos: int            # 自己負担額 (subsidy 部分は別ルートで PHPC)
    currency: str = "PHP"
    reference: str = ""             # 外部 idempotency key (なければ自動生成)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class PaymentResult:
    reference: str
    status: PaymentStatus
    merchant_id: str
    amount_centavos: int
    paid_at: float | None = None    # unix sec
    failure_reason: str | None = None
    is_mock: bool = True


@dataclass(frozen=True)
class MerchantInfo:
    merchant_id: str
    display_name: str
    mcc: int
    is_4ps_acceptable: bool


# ============================================================
# Protocol
# ============================================================


class GCashBackend(Protocol):
    def is_sandbox(self) -> bool: ...
    def create_payment(self, req: PaymentRequest) -> PaymentResult: ...
    def poll_payment(self, reference: str) -> PaymentResult: ...
    def get_merchant_info(self, merchant_id: str) -> MerchantInfo | None: ...


# ============================================================
# Mock 実装
# ============================================================


class MockGCashBackend:
    """in-process mock。決済は即時 succeed、merchant info は事前登録から。

    決済結果は `_payments` dict に保存され、`poll_payment` で再取得可能。
    """

    def __init__(self) -> None:
        self._payments: dict[str, PaymentResult] = {}
        self._merchants: dict[str, MerchantInfo] = {}

        # サリサリ + Mercury Drug の seed (R13 の seed/ph/stores.json と一貫)
        for m in [
            MerchantInfo("ph-store-aling-maria-qc", "Aling Maria's Sari-Sari", 5411, True),
            MerchantInfo("ph-store-mang-pedro-mnl", "Mang Pedro's Mini Mart", 5499, True),
            MerchantInfo("ph-store-lola-rosa-cal", "Lola Rosa Convenience", 5411, True),
            MerchantInfo("ph-store-gerry-tag", "Gerry's Tindahan", 5411, True),
            MerchantInfo("ph-store-aling-lina-pas", "Tindahan ni Aling Lina", 5411, True),
            MerchantInfo("ph-store-mercury-qc", "Mercury Drug Quezon Avenue", 5912, True),
            MerchantInfo("ph-store-7eleven-mnl", "7-Eleven Manila Bay", 5499, True),
            MerchantInfo("ph-store-blocked-liquor", "Tatay's Liquor (BLOCKED)", 5921, False),
        ]:
            self._merchants[m.merchant_id] = m

    # -- diagnostics --

    def is_sandbox(self) -> bool:
        return True

    # -- payments --

    def create_payment(self, req: PaymentRequest) -> PaymentResult:
        if req.amount_centavos < 0:
            raise ValueError("amount_centavos must be >= 0")
        if req.currency != "PHP":
            raise ValueError("only PHP supported in mock")

        merchant = self._merchants.get(req.merchant_id)
        if merchant is None:
            return PaymentResult(
                reference=req.reference or _gen_ref(),
                status="failed",
                merchant_id=req.merchant_id,
                amount_centavos=req.amount_centavos,
                failure_reason=f"unknown merchant: {req.merchant_id}",
                is_mock=True,
            )
        if not merchant.is_4ps_acceptable:
            return PaymentResult(
                reference=req.reference or _gen_ref(),
                status="failed",
                merchant_id=req.merchant_id,
                amount_centavos=req.amount_centavos,
                failure_reason=f"merchant MCC {merchant.mcc} blocked",
                is_mock=True,
            )

        ref = req.reference or _gen_ref()
        result = PaymentResult(
            reference=ref,
            status="succeeded",
            merchant_id=req.merchant_id,
            amount_centavos=req.amount_centavos,
            paid_at=time.time(),
            is_mock=True,
        )
        # idempotency: 同じ ref で 2 回目も同じ結果を返す
        if ref in self._payments:
            return self._payments[ref]
        self._payments[ref] = result
        return result

    def poll_payment(self, reference: str) -> PaymentResult:
        if reference not in self._payments:
            return PaymentResult(
                reference=reference, status="expired",
                merchant_id="", amount_centavos=0,
                failure_reason="reference not found", is_mock=True,
            )
        return self._payments[reference]

    def get_merchant_info(self, merchant_id: str) -> MerchantInfo | None:
        return self._merchants.get(merchant_id)

    # -- test helpers --

    def add_merchant(self, info: MerchantInfo) -> None:
        self._merchants[info.merchant_id] = info


# ============================================================
# Real 実装 (Coins.ph + GCash sandbox or production)
# ============================================================


class RealGCashBackend:
    """Coins.ph 仲介 (or 直 GCash) の sandbox/production API を叩く。

    sandbox では `requests` ライブラリで HTTPS 呼び出し。
    現状は実 API 仕様が手元にないので Round 16+ で本実装。
    """

    def __init__(self, cfg: GCashConfig) -> None:
        if not cfg.api_key:
            raise ValueError("GCashConfig.api_key required for RealGCashBackend")
        if not cfg.base_url:
            raise ValueError("GCashConfig.base_url required for RealGCashBackend")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def create_payment(self, req: PaymentRequest) -> PaymentResult:
        raise NotImplementedError(
            "RealGCashBackend.create_payment: pending Round 16 (Coins.ph contact)"
        )

    def poll_payment(self, reference: str) -> PaymentResult:
        raise NotImplementedError(
            "RealGCashBackend.poll_payment: pending Round 16"
        )

    def get_merchant_info(self, merchant_id: str) -> MerchantInfo | None:
        raise NotImplementedError(
            "RealGCashBackend.get_merchant_info: pending Round 16"
        )


# ============================================================
# factory + 補助
# ============================================================


def _gen_ref() -> str:
    return "GCASH-MOCK-" + uuid.uuid4().hex[:12].upper()


def gcash_config_from_env() -> GCashConfig:
    return GCashConfig(
        backend=os.environ.get("JPN_PBM_GCASH_BACKEND", "mock"),
        api_key=os.environ.get("JPN_PBM_GCASH_API_KEY"),
        base_url=os.environ.get("JPN_PBM_GCASH_BASE_URL"),
        timeout_sec=float(os.environ.get("JPN_PBM_GCASH_TIMEOUT", "5.0")),
    )


def get_gcash_backend(cfg: GCashConfig | None = None) -> GCashBackend:
    cfg = cfg or gcash_config_from_env()
    if cfg.backend == "mock":
        return MockGCashBackend()
    if cfg.backend in ("sandbox", "production", "real"):
        return RealGCashBackend(cfg)
    raise ValueError(
        f"unknown gcash backend: {cfg.backend} "
        "(expected: mock|sandbox|production)"
    )
