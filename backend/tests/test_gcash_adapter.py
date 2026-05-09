"""gcash_adapter テスト (戦略会議 #14 採択 T2)。

Mock backend 挙動 + idempotency + 加盟店の MCC ブロック + factory を検証。
"""

from __future__ import annotations

import pytest

from app.services.gcash_adapter import (
    GCashConfig,
    MerchantInfo,
    MockGCashBackend,
    PaymentRequest,
    RealGCashBackend,
    gcash_config_from_env,
    get_gcash_backend,
)


# ============================================================
# MockGCashBackend
# ============================================================


def test_mock_is_sandbox():
    assert MockGCashBackend().is_sandbox()


def test_mock_seeded_grocery_merchant():
    info = MockGCashBackend().get_merchant_info("ph-store-aling-maria-qc")
    assert info is not None
    assert info.mcc == 5411
    assert info.is_4ps_acceptable


def test_mock_seeded_blocked_liquor_merchant():
    info = MockGCashBackend().get_merchant_info("ph-store-blocked-liquor")
    assert info is not None
    assert info.mcc == 5921
    assert not info.is_4ps_acceptable


def test_mock_payment_succeeded_for_grocery():
    b = MockGCashBackend()
    req = PaymentRequest(
        merchant_id="ph-store-aling-maria-qc",
        citizen_pid_short="abcd1234",
        amount_centavos=1500,
    )
    res = b.create_payment(req)
    assert res.status == "succeeded"
    assert res.amount_centavos == 1500
    assert res.is_mock


def test_mock_payment_failed_for_unknown_merchant():
    b = MockGCashBackend()
    res = b.create_payment(PaymentRequest(
        merchant_id="ph-store-doesnt-exist",
        citizen_pid_short="abcd",
        amount_centavos=100,
    ))
    assert res.status == "failed"
    assert "unknown merchant" in (res.failure_reason or "")


def test_mock_payment_failed_for_blocked_mcc():
    b = MockGCashBackend()
    res = b.create_payment(PaymentRequest(
        merchant_id="ph-store-blocked-liquor",
        citizen_pid_short="abcd",
        amount_centavos=500,
    ))
    assert res.status == "failed"
    assert "5921" in (res.failure_reason or "")


def test_mock_negative_amount_rejected():
    b = MockGCashBackend()
    with pytest.raises(ValueError):
        b.create_payment(PaymentRequest(
            merchant_id="ph-store-aling-maria-qc",
            citizen_pid_short="abcd",
            amount_centavos=-1,
        ))


def test_mock_idempotency_same_reference():
    b = MockGCashBackend()
    req = PaymentRequest(
        merchant_id="ph-store-aling-maria-qc",
        citizen_pid_short="abcd",
        amount_centavos=1500,
        reference="MY-REF-001",
    )
    r1 = b.create_payment(req)
    r2 = b.create_payment(req)
    assert r1.paid_at == r2.paid_at  # 同じ結果オブジェクト


def test_mock_poll_returns_known_payment():
    b = MockGCashBackend()
    req = PaymentRequest(
        merchant_id="ph-store-aling-maria-qc",
        citizen_pid_short="abc",
        amount_centavos=200,
    )
    r = b.create_payment(req)
    polled = b.poll_payment(r.reference)
    assert polled.status == "succeeded"


def test_mock_poll_unknown_returns_expired():
    b = MockGCashBackend()
    polled = b.poll_payment("UNKNOWN-REF")
    assert polled.status == "expired"


def test_mock_only_php_supported():
    b = MockGCashBackend()
    with pytest.raises(ValueError):
        b.create_payment(PaymentRequest(
            merchant_id="ph-store-aling-maria-qc",
            citizen_pid_short="abc", amount_centavos=100, currency="USD",
        ))


def test_mock_add_merchant_dynamically():
    b = MockGCashBackend()
    b.add_merchant(MerchantInfo("ph-store-new", "New store", 5411, True))
    info = b.get_merchant_info("ph-store-new")
    assert info is not None
    assert info.is_4ps_acceptable


# ============================================================
# RealGCashBackend (init reject without env)
# ============================================================


def test_real_gcash_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        RealGCashBackend(GCashConfig(backend="sandbox", base_url="https://x"))


def test_real_gcash_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        RealGCashBackend(GCashConfig(backend="sandbox", api_key="X"))


# ============================================================
# factory
# ============================================================


def test_factory_default_is_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_GCASH_BACKEND", raising=False)
    assert isinstance(get_gcash_backend(), MockGCashBackend)


def test_factory_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_gcash_backend(GCashConfig(backend="paypal"))


def test_config_from_env_timeout(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GCASH_TIMEOUT", "12.5")
    cfg = gcash_config_from_env()
    assert cfg.timeout_sec == 12.5
