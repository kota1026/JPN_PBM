"""EMV QR Code Specification (MPM Mode) parser for QR Ph (戦略会議 #12 採択 T3)。

BSP Circular 2019-859 で標準化された QR Ph (Philippines National QR Code Standard)
は EMV QR Code Specification の MPM (Merchant-Presented Mode) に準拠。

【QR Ph payload format】
    TLV (Tag-Length-Value) sequence、文字列ベース。Tag は 2 桁 ASCII、
    Length は 2 桁 ASCII (10 進、00-99)、Value はその長さの ASCII 文字列。

【標準フィールド (BSP Circular 2019-859 Annex A)】
    Tag    Field                                  Format
    00     Payload Format Indicator               "01" (固定)
    01     Point of Initiation Method             "11"=static, "12"=dynamic
    02-51  Merchant Account Information           PSP 別 (InstaPay / PESONet)
    52     Merchant Category Code (MCC)           4 桁 ISO 18245
    53     Transaction Currency                   "608" = PHP (ISO 4217)
    54     Transaction Amount                     可変 (動的 QR のみ)
    55     Tip / Convenience Indicator            optional
    58     Country Code                           "PH"
    59     Merchant Name                          ASCII printable
    60     Merchant City                          ASCII printable
    61     Postal Code                            optional
    62     Additional Data Field Template         拡張 (txID 等)
    63     CRC-16/CCITT-FALSE checksum            最後の 4 桁、ポリ 0x1021、初期 0xFFFF

【セキュリティ要件】
- CRC-16 検証: payload 全体 (Tag 63 + Length までを含む) の CRC を計算し、Tag 63 の値と比較
- MCC が `ALWAYS_BLOCKED_MCCS` (酒・タバコ・賭博) ならパース成功でも payment side で reject
- 文字列長は 99 まで (ID Length が 2 桁固定なため)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator


# ---- 例外 ----


class QrPhParseError(ValueError):
    """QR Ph payload のパース/検証失敗。"""


# ---- データ ----


@dataclass(frozen=True)
class TLVField:
    tag: str          # "00", "52", "59", "63", ...
    value: str        # parsed value
    raw_length: int   # ASCII length 値


@dataclass
class QrPhInfo:
    """QR Ph から抽出される構造化情報。"""
    payload_format_indicator: str | None = None
    point_of_initiation: str | None = None      # "11"=static, "12"=dynamic
    merchant_category_code: int | None = None    # 4桁
    transaction_currency: str | None = None      # "608" = PHP
    transaction_amount_centavos: int | None = None  # 動的 QR のみ
    country_code: str | None = None              # "PH"
    merchant_name: str | None = None
    merchant_city: str | None = None
    postal_code: str | None = None
    crc_provided: str | None = None
    crc_calculated: str | None = None
    additional_data: dict[str, str] = field(default_factory=dict)
    raw_fields: list[TLVField] = field(default_factory=list)

    @property
    def is_valid_crc(self) -> bool:
        if self.crc_provided is None or self.crc_calculated is None:
            return False
        return self.crc_provided.upper() == self.crc_calculated.upper()


# ---- CRC-16/CCITT-FALSE ----


def crc16_ccitt_false(data: bytes, *, initial: int = 0xFFFF, poly: int = 0x1021) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, no xorout.

    EMV QR Code Specification の Tag 63 はこの実装。
    """
    crc = initial
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc


# ---- TLV iterator ----


def _iter_tlv(text: str, *, depth: int = 0) -> Iterator[TLVField]:
    """文字列を TLV シーケンスとして分解する。

    Tag (2 char ASCII) + Length (2 digit ASCII) + Value (Length chars)。
    """
    if depth > 4:
        raise QrPhParseError("TLV nesting too deep")
    i = 0
    while i < len(text):
        if i + 4 > len(text):
            raise QrPhParseError(f"truncated TLV header at position {i}")
        tag = text[i:i + 2]
        length_str = text[i + 2:i + 4]
        if not length_str.isdigit():
            raise QrPhParseError(f"non-digit length at tag {tag}: {length_str!r}")
        length = int(length_str)
        if i + 4 + length > len(text):
            raise QrPhParseError(
                f"declared length {length} exceeds remaining payload "
                f"at tag {tag} (i={i}, total={len(text)})"
            )
        value = text[i + 4:i + 4 + length]
        yield TLVField(tag=tag, value=value, raw_length=length)
        i += 4 + length


# ---- 公開 API ----


def parse_qr_ph(payload: str, *, verify_crc: bool = True) -> QrPhInfo:
    """QR Ph payload (EMV MPM) をパース。

    `verify_crc=True` で CRC 不一致なら QrPhParseError。
    """
    if not isinstance(payload, str):
        raise QrPhParseError("payload must be str")
    if len(payload) < 8:
        raise QrPhParseError("payload too short to be a valid EMV QR")
    if not payload.startswith("00"):
        raise QrPhParseError("EMV QR must start with tag 00 (Payload Format Indicator)")

    # CRC は payload 末尾 8 byte: tag(2) + length(2)+ 4 hex digits
    # CRC 計算範囲は payload 末尾 8 byte の手前まで (tag '63' と length '04' は含む)
    if len(payload) < 8 or payload[-8:-6] != "63" or payload[-6:-4] != "04":
        if verify_crc:
            raise QrPhParseError("CRC field (tag 63 04 ....) not found at payload tail")

    info = QrPhInfo()
    fields = list(_iter_tlv(payload))
    info.raw_fields = fields

    for f in fields:
        if f.tag == "00":
            info.payload_format_indicator = f.value
        elif f.tag == "01":
            info.point_of_initiation = f.value
        elif f.tag == "52":
            try:
                info.merchant_category_code = int(f.value)
            except ValueError:
                raise QrPhParseError(f"non-numeric MCC: {f.value!r}")
        elif f.tag == "53":
            info.transaction_currency = f.value
        elif f.tag == "54":
            # PHP は小数 2 桁。"42.50" のような文字列を centavos に変換
            try:
                info.transaction_amount_centavos = int(round(float(f.value) * 100))
            except ValueError:
                raise QrPhParseError(f"non-numeric amount: {f.value!r}")
        elif f.tag == "58":
            info.country_code = f.value
        elif f.tag == "59":
            info.merchant_name = f.value
        elif f.tag == "60":
            info.merchant_city = f.value
        elif f.tag == "61":
            info.postal_code = f.value
        elif f.tag == "62":
            # additional data (template, sub-TLV)
            try:
                for sub in _iter_tlv(f.value, depth=1):
                    info.additional_data[sub.tag] = sub.value
            except QrPhParseError:
                pass  # additional data の壊れは fatal にしない
        elif f.tag == "63":
            info.crc_provided = f.value

    # CRC 計算: payload[:-4] (= tag '63' と length '04' を含むまで) を bytes 化
    if info.crc_provided is not None:
        crc_input = payload[: -4].encode("ascii")
        info.crc_calculated = format(crc16_ccitt_false(crc_input), "04X")

    if verify_crc and info.crc_provided and not info.is_valid_crc:
        raise QrPhParseError(
            f"CRC mismatch: provided {info.crc_provided}, "
            f"calculated {info.crc_calculated}"
        )

    return info


def build_qr_ph(
    *,
    merchant_id: str,
    mcc: int,
    merchant_name: str,
    merchant_city: str,
    transaction_amount_php: float | None = None,
    point_of_initiation: str = "11",
) -> str:
    """テスト/デモ用に QR Ph payload を組み立てる。

    本番の QR Ph は GCash / Maya 等 PSP が発行するが、
    本関数は EMV MPM の最小構成を組み立てて、parser のラウンドトリップテストに使う。
    """
    if not (1 <= len(merchant_name) <= 25):
        raise ValueError("merchant_name must be 1..25 chars")
    if not (1 <= len(merchant_city) <= 15):
        raise ValueError("merchant_city must be 1..15 chars")
    if not (1000 <= mcc <= 9999):
        raise ValueError("mcc must be 4 digits")

    def _f(tag: str, value: str) -> str:
        return f"{tag}{len(value):02d}{value}"

    parts: list[str] = []
    parts.append(_f("00", "01"))
    parts.append(_f("01", point_of_initiation))
    # Merchant Account Information (tag 26 = "ph.qr.ph" guid + merchant_id)
    mai = _f("00", "PH.PPMI.QRPH") + _f("01", merchant_id)
    parts.append(_f("26", mai))
    parts.append(_f("52", str(mcc)))
    parts.append(_f("53", "608"))  # PHP
    if transaction_amount_php is not None:
        parts.append(_f("54", f"{transaction_amount_php:.2f}"))
    parts.append(_f("58", "PH"))
    parts.append(_f("59", merchant_name))
    parts.append(_f("60", merchant_city))

    body = "".join(parts) + "6304"  # tag 63 + length 04 を CRC 計算に含める
    crc = format(crc16_ccitt_false(body.encode("ascii")), "04X")
    return body + crc


# ---- 4Ps 適合性のヘルパ ----


# `services.item_eligibility.ALWAYS_BLOCKED_MCCS` と同じ集合を再エクスポート
from app.services.item_eligibility import ALWAYS_BLOCKED_MCCS  # noqa: E402


def is_4ps_acceptable(info: QrPhInfo) -> tuple[bool, str]:
    """QR Ph パース結果が 4Ps 受給で受領可能かを判定。

    早期 reject 用 (PBM contract に到達する前にフロントで弾くため)。
    """
    if not info.is_valid_crc:
        return False, "CRC 不一致 (改ざん or 破損)"
    if info.country_code != "PH":
        return False, f"country_code != PH (got {info.country_code})"
    if info.transaction_currency != "608":
        return False, f"currency != 608/PHP (got {info.transaction_currency})"
    if info.merchant_category_code is None:
        return False, "MCC 欠落"
    if info.merchant_category_code in ALWAYS_BLOCKED_MCCS:
        return False, f"MCC {info.merchant_category_code} は常時ブロック対象"
    return True, "OK"
