"""Phase 2 ECDSA 署名/検証のテスト (戦略会議 #4 採択 #3)。

Phase 1 (HMAC) と並列で動くこと、改ざん検出が正しく効くことを検証。
"""

from __future__ import annotations

import os

import pytest

from app.services import offline_fallback as of


# テスト用に都の鍵を一時設定
TEST_PRIVKEY = "f8b8a8a2c7c4f8c8a8b8e8c8e8b8c8a8d8a8b8c8a8b8c8d8e8a8b8c8d8e8f8a8"


@pytest.fixture(autouse=True)
def _set_test_privkey(monkeypatch):
    monkeypatch.setattr(of, "GOVERNOR_PRIVKEY_HEX", TEST_PRIVKEY)
    yield


def test_ecdsa_available_when_key_set():
    assert of.is_ecdsa_available()


def test_ecdsa_unavailable_when_key_missing(monkeypatch):
    monkeypatch.setattr(of, "GOVERNOR_PRIVKEY_HEX", "")
    assert not of.is_ecdsa_available()


def test_ecdsa_sign_and_verify_roundtrip():
    signed = of.issue_offline_coupon_ecdsa(
        program_id="prog-koto-kosodate-2026",
        pid="a" * 64,
        month_index=202604,
        cap_jpy=5000,
        expires_at=9999999999,
    )
    assert signed.signature
    ok, why = of.verify_coupon_ecdsa(signed)
    assert ok, why


def test_ecdsa_tampering_detected():
    signed = of.issue_offline_coupon_ecdsa(
        program_id="p", pid="b" * 64, month_index=202604,
        cap_jpy=5000, expires_at=9999999999,
    )
    tampered = of.SignedCoupon(
        coupon=of.OfflineCoupon(
            program_id="p", pid="b" * 64, month_index=202604,
            cap_jpy=999_999,  # cap 改ざん
            expires_at=9999999999,
        ),
        signature=signed.signature,
    )
    ok, why = of.verify_coupon_ecdsa(tampered)
    # ecdsa ライブラリは検証失敗で例外を投げる場合と False を返す場合がある
    assert not ok and ("失敗" in why or "エラー" in why or "Verification" in why or "verification" in why)


def test_ecdsa_invalid_pubkey_rejected():
    signed = of.issue_offline_coupon_ecdsa(
        program_id="p", pid="c" * 64, month_index=202604,
        cap_jpy=5000, expires_at=9999999999,
    )
    # 別の (デタラメな) 公開鍵で検証 → 検証エラーまたは失敗
    other_pk = "04" + "11" * 32 + "22" * 32
    ok, _ = of.verify_coupon_ecdsa(signed, public_key_hex=other_pk)
    assert not ok


def test_ecdsa_signature_length_validated():
    signed = of.issue_offline_coupon_ecdsa(
        program_id="p", pid="d" * 64, month_index=202604,
        cap_jpy=5000, expires_at=9999999999,
    )
    bad = of.SignedCoupon(coupon=signed.coupon, signature="ab" * 30)  # 60 bytes
    ok, why = of.verify_coupon_ecdsa(bad)
    assert not ok and "64 bytes" in why


def test_phase1_hmac_still_works_in_parallel():
    """ECDSA を導入しても Phase 1 HMAC が引き続き動く (並列)。"""
    signed = of.issue_offline_coupon(
        program_id="p", pid="e" * 64, month_index=202604,
        cap_jpy=5000, expires_at=9999999999,
    )
    ok, _ = of.verify_coupon(signed)
    assert ok
