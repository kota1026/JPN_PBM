"""ECDSA 鍵 rotation のテスト (戦略会議 #6 採択 A)。"""

from __future__ import annotations

import pytest

from app.services import key_management as km
from app.services.sol_compat import SolCoupon, address_of, privkey_from_hex


KEY_A = "1111111111111111111111111111111111111111111111111111111111111111"
KEY_B = "2222222222222222222222222222222222222222222222222222222222222222"
KEY_C = "3333333333333333333333333333333333333333333333333333333333333333"


@pytest.fixture
def coupon():
    return SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026", pid="a" * 64,
        month_index=202604, cap_jpy=5000, expires_at=9999999999,
    )


def test_load_keys_single_key_legacy(monkeypatch):
    monkeypatch.delenv("JPN_PBM_GOVERNOR_PRIVKEYS", raising=False)
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEY", KEY_A)
    keys = km.load_keys()
    assert len(keys) == 1 and keys[0].is_active
    assert keys[0].address == address_of(privkey_from_hex(KEY_A))


def test_load_keys_multi_with_active_idx(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B},{KEY_C}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "1")  # KEY_B が active
    keys = km.load_keys()
    assert len(keys) == 3
    assert keys[1].is_active
    assert not keys[0].is_active
    assert not keys[2].is_active


def test_active_key_returns_indexed(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0")
    assert km.active_key().address == address_of(privkey_from_hex(KEY_A))
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "1")
    assert km.active_key().address == address_of(privkey_from_hex(KEY_B))


def test_sign_with_active_then_verify_against_any(monkeypatch, coupon):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0")
    sig = km.sign_with_active(coupon)
    ok, why, matched = km.verify_against_any_governor(coupon, sig)
    assert ok, why
    # KEY_A の address に一致しているはず
    assert matched == address_of(privkey_from_hex(KEY_A))


def test_old_key_signature_still_verifies_during_grace(monkeypatch, coupon):
    """KEY_A で署名 → KEY_B を active に切替えた後も KEY_A の署名は通る (grace)。"""
    # KEY_A で署名
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0")
    sig = km.sign_with_active(coupon)

    # active を KEY_B に切替
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "1")
    ok, _, matched = km.verify_against_any_governor(coupon, sig)
    assert ok
    assert matched == address_of(privkey_from_hex(KEY_A))


def test_revoked_key_signature_rejected(monkeypatch, coupon):
    """KEY_A で署名 → KEY_A を env から外す → 検証 NG (= revoked)。"""
    # KEY_A で署名
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_A)
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0")
    sig = km.sign_with_active(coupon)

    # KEY_A を完全に外し、KEY_B のみに置換
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_B)
    ok, why, _ = km.verify_against_any_governor(coupon, sig)
    assert not ok and "matched" in why or "address" in why


def test_no_keys_configured(monkeypatch):
    monkeypatch.delenv("JPN_PBM_GOVERNOR_PRIVKEYS", raising=False)
    monkeypatch.delenv("JPN_PBM_GOVERNOR_PRIVKEY", raising=False)
    assert km.load_keys() == []
    assert km.active_key() is None
    ok, why, _ = km.verify_against_any_governor(
        SolCoupon.from_strings(program_id="p", pid="0" * 64, month_index=1, cap_jpy=1, expires_at=9),
        b"\x00" * 65,
    )
    assert not ok


# ----------------------------- 鍵 age tracking (Round 9 採択 C) -----------------------------


def test_key_age_calculation(monkeypatch):
    from datetime import date

    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ISSUED_AT", "2025-01-15,2024-06-01")

    keys = km.load_keys()
    assert keys[0].issued_at == date(2025, 1, 15)
    assert keys[1].issued_at == date(2024, 6, 1)

    # 2026-05-02 から見た age
    today = date(2026, 5, 2)
    assert keys[0].age_days(today=today) == 472
    assert keys[1].age_days(today=today) == 700


def test_key_overage_detection(monkeypatch):
    from datetime import date

    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ISSUED_AT", "2025-01-15,2024-06-01")
    today = date(2026, 5, 2)

    keys = km.load_keys()
    assert keys[0].is_overage(max_age_days=365, today=today)  # 472 > 365
    assert keys[1].is_overage(max_age_days=365, today=today)  # 700 > 365
    # 800 日許容なら 472 はまだ OK
    assert not keys[0].is_overage(max_age_days=800, today=today)


def test_unknown_issued_at_does_not_raise_overage(monkeypatch):
    """issued_at が None なら is_overage=False (=警告対象外)。"""
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_A)
    monkeypatch.delenv("JPN_PBM_GOVERNOR_ISSUED_AT", raising=False)
    keys = km.load_keys()
    assert keys[0].issued_at is None
    assert keys[0].age_days() is None
    assert not keys[0].is_overage()


def test_rotation_status_emits_overage_alert(monkeypatch):
    from datetime import date

    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ISSUED_AT", "2025-01-15,2024-06-01")
    monkeypatch.setenv("JPN_PBM_KEY_MAX_AGE_DAYS", "365")

    status = km.rotation_status(today=date(2026, 5, 2))
    assert status["max_age_days"] == 365
    # 両方 overage
    assert any("WARNING" in a for a in status["alerts"])
    assert all(a["is_overage"] for a in status["addresses"])


def test_rotation_status_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B},{KEY_C}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "1")
    monkeypatch.setenv("JPN_PBM_KEY_GRACE_DAYS", "120")

    client = TestClient(app)
    r = client.get("/treasury/keys/rotation")
    assert r.status_code == 200
    body = r.json()
    assert body["configured_keys"] == 3
    assert body["active_index"] == 1
    assert body["grace_days"] == 120
    addrs = body["addresses"]
    assert len(addrs) == 3
    assert addrs[1]["is_active"] is True
    assert addrs[0]["is_active"] is False
