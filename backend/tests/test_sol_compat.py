"""Sol PBMOfflineFallback 完全互換テスト (戦略会議 #5 採択 A)。

外部テストベクトル (keccak256, ethereum address) との一致 + 自前 sign→verify
ループで Sol の ecrecover ロジックと等価であることを担保する。
"""

from __future__ import annotations

import pytest

from app.services.sol_compat import (
    SolCoupon,
    address_from_pubkey,
    address_of,
    coupon_abi_encode,
    coupon_hash,
    eth_signed_digest,
    keccak256,
    privkey_from_hex,
    sign_coupon_eip191,
    verify_coupon_eip191,
)


# ----------------------------- 既知ベクトル -----------------------------


def test_keccak256_known_vectors():
    # 空 string
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    # 'abc'
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    # 'hello'
    assert keccak256(b"hello").hex() == "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"


def test_known_ethereum_address_from_privkey():
    # Vitalik 公開鍵テストベクトル (privkey は架空、addr は計算結果一貫性のみ確認)
    # 既知: privkey 0x1 → address 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf
    sk = privkey_from_hex("0000000000000000000000000000000000000000000000000000000000000001")
    addr = address_of(sk).lower()
    assert addr == "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"


# ----------------------------- abi.encode + couponHash -----------------------------


def test_abi_encode_layout_is_5x32():
    """abi.encode(bytes32, bytes32, uint32, uint256, uint64) は 5 word = 160 bytes。"""
    c = SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026",
        pid="a" * 64,  # 64 hex = 32 bytes
        month_index=202604,
        cap_jpy=5000,
        expires_at=9999999999,
    )
    enc = coupon_abi_encode(c)
    assert len(enc) == 32 * 5

    # uint32 monthIndex は word の最下位 4 bytes
    assert enc[64 + 28:64 + 32] == (202604).to_bytes(4, "big")
    # uint256 capJpy は word 全体
    cap_bytes = (5000).to_bytes(32, "big")
    assert enc[96:128] == cap_bytes


def test_coupon_hash_deterministic():
    c1 = SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    c2 = SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    assert coupon_hash(c1) == coupon_hash(c2)


def test_coupon_hash_changes_when_any_field_changes():
    base = SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    h0 = coupon_hash(base)
    # 1 bit でも違えば hash 変化
    assert coupon_hash(SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=1, cap_jpy=101, expires_at=9,
    )) != h0
    assert coupon_hash(SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=2, cap_jpy=100, expires_at=9,
    )) != h0


def test_eth_signed_digest_matches_personal_sign_layout():
    """\\x19Ethereum Signed Message:\\n32 + couponHash の keccak256 になっている。"""
    c = SolCoupon.from_strings(
        program_id="p", pid="a" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    h = coupon_hash(c)
    direct = keccak256(b"\x19Ethereum Signed Message:\n32" + h)
    assert eth_signed_digest(h) == direct


# ----------------------------- sign / verify roundtrip -----------------------------


@pytest.fixture
def gov_privkey():
    return privkey_from_hex("f8b8a8a2c7c4f8c8a8b8e8c8e8b8c8a8d8a8b8c8a8b8c8d8e8a8b8c8d8e8f8a8")


def test_sign_verify_roundtrip(gov_privkey):
    c = SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026",
        pid="b" * 64, month_index=202604, cap_jpy=5000, expires_at=9999999999,
    )
    sig = sign_coupon_eip191(c, gov_privkey)
    assert len(sig) == 65
    addr = address_of(gov_privkey)
    ok, why = verify_coupon_eip191(c, sig, expected_address=addr)
    assert ok, why


def test_signature_low_s_normalization(gov_privkey):
    """low-s normalization が効いている: s < n/2。"""
    from ecdsa import SECP256k1
    c = SolCoupon.from_strings(
        program_id="p", pid="c" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    sig = sign_coupon_eip191(c, gov_privkey)
    s_int = int.from_bytes(sig[32:64], "big")
    assert s_int <= SECP256k1.order // 2


def test_verify_fails_for_wrong_address(gov_privkey):
    c = SolCoupon.from_strings(
        program_id="p", pid="d" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    sig = sign_coupon_eip191(c, gov_privkey)
    ok, why = verify_coupon_eip191(
        c, sig, expected_address="0x0000000000000000000000000000000000000001",
    )
    assert not ok
    assert "address" in why


def test_verify_detects_coupon_tampering(gov_privkey):
    c = SolCoupon.from_strings(
        program_id="p", pid="e" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    sig = sign_coupon_eip191(c, gov_privkey)
    # cap を改ざん
    tampered = SolCoupon.from_strings(
        program_id="p", pid="e" * 64, month_index=1, cap_jpy=999_999, expires_at=9,
    )
    ok, _ = verify_coupon_eip191(tampered, sig, expected_address=address_of(gov_privkey))
    assert not ok


def test_verify_rejects_bad_v_byte(gov_privkey):
    c = SolCoupon.from_strings(
        program_id="p", pid="f" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    sig = bytearray(sign_coupon_eip191(c, gov_privkey))
    sig[64] = 99  # invalid v
    ok, why = verify_coupon_eip191(c, bytes(sig), expected_address=address_of(gov_privkey))
    assert not ok
    assert "v" in why or "bad v" in why


def test_signature_length_validated(gov_privkey):
    c = SolCoupon.from_strings(
        program_id="p", pid="3" * 64, month_index=1, cap_jpy=100, expires_at=9,
    )
    ok, why = verify_coupon_eip191(c, b"\x00" * 60, expected_address=address_of(gov_privkey))
    assert not ok
    assert "65 bytes" in why
