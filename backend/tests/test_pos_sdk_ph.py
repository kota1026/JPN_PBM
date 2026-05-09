"""PH POS SDK のテスト (戦略会議 #13 採択 T2)。

QR Ph parser proxy + cart 操作 + estimate_cart の eligibility 判定をカバー。
HTTP は backend FastAPI と同 process で動かす (TestClient はサポート外なので
直接 services にあたる経路でテスト)。
"""

from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from fastapi.testclient import TestClient

from app.main import app
from app.services.qr_ph import build_qr_ph
from jpn_pbm_pos_ph import PhPosClient, PhPosConfig


client = TestClient(app)


# ============================================================
# QR Ph parser proxy
# ============================================================


def test_verify_merchant_qr_grocery_accepted():
    payload = build_qr_ph(
        merchant_id="STORE-001", mcc=5411,
        merchant_name="MARIA STORE", merchant_city="QUEZON CITY",
    )
    cfg = PhPosConfig(
        base_url="http://127.0.0.1:0",
        merchant_id="ph-store-aling-maria-qc",
        merchant_qr_ph_payload=payload,
    )
    pos = PhPosClient(cfg)
    info = pos.verify_merchant_qr()
    assert info.is_valid_crc
    assert info.is_4ps_acceptable
    assert info.mcc == 5411
    assert info.merchant_name == "MARIA STORE"


def test_verify_merchant_qr_liquor_rejected():
    payload = build_qr_ph(
        merchant_id="LIQ-001", mcc=5921,
        merchant_name="TATAY LIQUOR", merchant_city="MANILA",
    )
    cfg = PhPosConfig(base_url="http://127.0.0.1:0",
                      merchant_id="ph-store-blocked-liquor",
                      merchant_qr_ph_payload=payload)
    pos = PhPosClient(cfg)
    info = pos.verify_merchant_qr()
    assert not info.is_4ps_acceptable
    assert "5921" in info.reason


def test_verify_merchant_qr_requires_payload():
    cfg = PhPosConfig(base_url="x", merchant_id="x", merchant_qr_ph_payload="")
    pos = PhPosClient(cfg)
    import pytest
    with pytest.raises(ValueError, match="merchant_qr_ph_payload"):
        pos.verify_merchant_qr()


# ============================================================
# Cart 操作
# ============================================================


def _ready_pos() -> PhPosClient:
    payload = build_qr_ph(
        merchant_id="STORE-001", mcc=5411,
        merchant_name="MARIA STORE", merchant_city="QC",
    )
    cfg = PhPosConfig(base_url="http://127.0.0.1:0",
                      merchant_id="ph-store-aling-maria-qc",
                      merchant_qr_ph_payload=payload)
    pos = PhPosClient(cfg)
    pos.verify_merchant_qr()
    return pos


def test_add_tingi_increments_cart():
    pos = _ready_pos()
    pos.add_tingi_item(price_centavos=1500, label="rice cup")
    assert len(pos.cart) == 1
    assert pos.cart[0].is_tingi
    assert pos.cart[0].price_centavos == 1500


def test_add_barcoded_without_master_lookup():
    pos = _ready_pos()
    pos.add_barcoded_item(jan="4806515600015", qty=1, fetch_master=False)
    assert pos.cart[0].has_barcode
    assert pos.cart[0].jan == "4806515600015"


def test_add_tingi_zero_price_rejected():
    pos = _ready_pos()
    import pytest
    with pytest.raises(ValueError, match="price_centavos"):
        pos.add_tingi_item(price_centavos=0)


def test_reset_cart_clears():
    pos = _ready_pos()
    pos.add_tingi_item(price_centavos=1000)
    pos.add_tingi_item(price_centavos=2000)
    assert len(pos.cart) == 2
    pos.reset_cart()
    assert pos.cart == []


# ============================================================
# Estimate (HTTP 経由は別ホストなのでここではモック化)
# ============================================================


def test_estimate_requires_verified_merchant():
    cfg = PhPosConfig(base_url="x", merchant_id="x", merchant_qr_ph_payload="")
    pos = PhPosClient(cfg)
    pos.add_tingi_item(price_centavos=100)
    import pytest
    with pytest.raises(RuntimeError, match="verify_merchant_qr"):
        pos.estimate_cart(citizen_pid="x" * 64, program_id="prog-4ps-2026")


def test_estimate_blocks_when_merchant_not_acceptable():
    payload = build_qr_ph(
        merchant_id="LIQ", mcc=5921,
        merchant_name="LIQ", merchant_city="MNL",
    )
    cfg = PhPosConfig(base_url="x", merchant_id="x", merchant_qr_ph_payload=payload)
    pos = PhPosClient(cfg)
    pos.verify_merchant_qr()
    pos.add_tingi_item(price_centavos=100)
    import pytest
    with pytest.raises(RuntimeError, match="merchant rejected"):
        pos.estimate_cart(citizen_pid="x" * 64, program_id="prog-4ps-2026")


# ============================================================
# GCash mock receipt
# ============================================================


def test_gcash_mock_returns_receipt():
    """estimate_cart を mock 化して charge_via_gcash の receipt フォーマットを確認。"""
    from jpn_pbm_pos_ph import CartEstimate, CartItem  # noqa: E402

    pos = _ready_pos()
    est = CartEstimate(
        items=[CartItem(has_barcode=False, jan=None, name="rice", price_centavos=1500)],
        total_price_centavos=1500,
        total_eligible_centavos=1500,
        total_subsidy_centavos=900,
        self_pay_centavos=600,
        no_barcode_used_centavos=1500,
        no_barcode_cap_centavos=30000,
        program_id="prog-4ps-2026",
        citizen_pid="abc123" * 10 + "ab",
    )
    rcpt = pos.charge_via_gcash(est)
    assert rcpt.is_mock
    assert rcpt.payment_reference.startswith("GCASHQR-")
    assert rcpt.merchant_id == "ph-store-aling-maria-qc"
    assert rcpt.subsidy_paid_phpc_centavos == 900
    assert rcpt.total_paid_centavos == 600


def test_charge_persists_no_barcode_running_total():
    """charge 後、no_barcode_used がクライアント state に書き戻される (月内累計用)。"""
    from jpn_pbm_pos_ph import CartEstimate, CartItem  # noqa: E402

    pos = _ready_pos()
    est = CartEstimate(
        items=[],
        total_price_centavos=0, total_eligible_centavos=0,
        total_subsidy_centavos=0, self_pay_centavos=0,
        no_barcode_used_centavos=12345, no_barcode_cap_centavos=30000,
        program_id="prog-4ps-2026", citizen_pid="x" * 64,
    )
    pos.charge_via_gcash(est)
    assert pos._no_barcode_used_centavos == 12345
