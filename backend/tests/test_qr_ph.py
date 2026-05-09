"""EMV QR Ph parser テスト (戦略会議 #12 採択 T3)。

CRC-16/CCITT-FALSE 実装と、build_qr_ph / parse_qr_ph のラウンドトリップ、
壊れた payload の reject、4Ps 適合性判定をカバー。
"""

from __future__ import annotations

import pytest

from app.services.qr_ph import (
    ALWAYS_BLOCKED_MCCS,
    QrPhParseError,
    build_qr_ph,
    crc16_ccitt_false,
    is_4ps_acceptable,
    parse_qr_ph,
)


# ============================================================
# CRC-16/CCITT-FALSE 既知ベクトル
# ============================================================


def test_crc16_ccitt_false_known_vector_123456789():
    """RFC 標準ベクトル: '123456789' → 0x29B1 (CCITT-FALSE)"""
    assert crc16_ccitt_false(b"123456789") == 0x29B1


def test_crc16_ccitt_false_empty_input():
    assert crc16_ccitt_false(b"") == 0xFFFF


# ============================================================
# build_qr_ph round-trip
# ============================================================


def test_build_and_parse_static_qr():
    payload = build_qr_ph(
        merchant_id="MERCHANT-MARIA-QC-001",
        mcc=5411,
        merchant_name="ALING MARIA STORE",
        merchant_city="QUEZON CITY",
    )
    info = parse_qr_ph(payload)
    assert info.payload_format_indicator == "01"
    assert info.point_of_initiation == "11"
    assert info.merchant_category_code == 5411
    assert info.transaction_currency == "608"
    assert info.country_code == "PH"
    assert info.merchant_name == "ALING MARIA STORE"
    assert info.merchant_city == "QUEZON CITY"
    assert info.is_valid_crc


def test_build_and_parse_dynamic_qr_with_amount():
    payload = build_qr_ph(
        merchant_id="X-001",
        mcc=5411,
        merchant_name="STORE",
        merchant_city="CITY",
        transaction_amount_php=42.50,
        point_of_initiation="12",
    )
    info = parse_qr_ph(payload)
    assert info.point_of_initiation == "12"
    assert info.transaction_amount_centavos == 4250
    assert info.is_valid_crc


# ============================================================
# CRC 改ざん検知
# ============================================================


def test_crc_tampering_detected():
    payload = build_qr_ph(
        merchant_id="X-001", mcc=5411,
        merchant_name="ORIG", merchant_city="A",
    )
    # MCC を 5921 に書き換える (酒屋に偽装)
    tampered = payload.replace("5240", "5240").replace("5252", "5252")  # noop
    # 実際の改ざん: merchant name 'ORIG' → 'EVIL' (同じ長さ)
    tampered = payload.replace("5904ORIG", "5904EVIL")
    assert tampered != payload
    with pytest.raises(QrPhParseError, match="CRC mismatch"):
        parse_qr_ph(tampered)


def test_crc_tampering_can_skip_with_verify_crc_false():
    payload = build_qr_ph(
        merchant_id="X", mcc=5411,
        merchant_name="ORIG", merchant_city="A",
    )
    tampered = payload.replace("5904ORIG", "5904EVIL")
    info = parse_qr_ph(tampered, verify_crc=False)
    assert info.merchant_name == "EVIL"
    assert not info.is_valid_crc


# ============================================================
# malformed payload
# ============================================================


def test_empty_payload_rejected():
    with pytest.raises(QrPhParseError, match="too short"):
        parse_qr_ph("")


def test_missing_payload_format_indicator_rejected():
    with pytest.raises(QrPhParseError, match="must start with tag 00"):
        parse_qr_ph("99020163041234")  # tag 00 で始まらない


def test_truncated_tlv_rejected():
    with pytest.raises(QrPhParseError, match="exceeds remaining payload"):
        # tag 00 length 99 だけど後ろに 99 文字ない
        parse_qr_ph("0099SHORT" + "63041234")


def test_non_digit_length_rejected():
    with pytest.raises(QrPhParseError, match="non-digit length"):
        parse_qr_ph("00ZZ01" + "63041234")


# ============================================================
# 4Ps 適合性判定
# ============================================================


def test_4ps_grocery_accepted():
    payload = build_qr_ph(
        merchant_id="A", mcc=5411,
        merchant_name="STORE", merchant_city="QC",
    )
    info = parse_qr_ph(payload)
    ok, reason = is_4ps_acceptable(info)
    assert ok
    assert reason == "OK"


def test_4ps_liquor_rejected():
    payload = build_qr_ph(
        merchant_id="A", mcc=5921,  # liquor
        merchant_name="LIQ", merchant_city="QC",
    )
    info = parse_qr_ph(payload)
    ok, reason = is_4ps_acceptable(info)
    assert not ok
    assert "5921" in reason


def test_4ps_tobacco_rejected():
    payload = build_qr_ph(
        merchant_id="A", mcc=5993,
        merchant_name="TOB", merchant_city="QC",
    )
    info = parse_qr_ph(payload)
    ok, reason = is_4ps_acceptable(info)
    assert not ok


def test_always_blocked_mccs_complete():
    """gambling / liquor / tobacco / drinking は必ず含まれる。"""
    assert 5921 in ALWAYS_BLOCKED_MCCS
    assert 5993 in ALWAYS_BLOCKED_MCCS
    assert 5813 in ALWAYS_BLOCKED_MCCS
    assert 7995 in ALWAYS_BLOCKED_MCCS


# ============================================================
# Realistic bench (商業ペイロード相当)
# ============================================================


def test_long_realistic_payload():
    """Mercury Drug 相当のペイロード長 (60+ char)"""
    payload = build_qr_ph(
        merchant_id="MERCURY-DRUG-MAIN-001",
        mcc=5912,
        merchant_name="MERCURY DRUG MAIN",
        merchant_city="QUEZON CITY",
        transaction_amount_php=350.00,
        point_of_initiation="12",
    )
    assert len(payload) >= 60
    info = parse_qr_ph(payload)
    assert info.is_valid_crc
    assert info.merchant_category_code == 5912
    assert info.transaction_amount_centavos == 35000
