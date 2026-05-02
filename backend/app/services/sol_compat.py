"""Sol PBMOfflineFallback 完全互換 ECDSA (戦略会議 #5 採択 A)。

`contracts/PBMOfflineFallback.sol` の `couponHash` / `ethSignedDigest` /
`ecrecover` をオフチェーン Python で完全再現する。これにより、

  1. オフチェーン (Python) で署名した coupon を Sol に投げると検証成功
  2. Sol の `redeemBatch` で reject されないことをローカルでテスト可能
  3. 本番 Polygon Mumbai デプロイ前に互換性が保証される

依存:
- pycryptodome (keccak256)
- ecdsa (secp256k1, 公開鍵復元用に v+r+s → address ロジックを自前)

【Sol 側のハッシュ計算】
    couponHash = keccak256(abi.encode(
        bytes32 programId, bytes32 pid, uint32 monthIndex,
        uint256 capJpy, uint64 expiresAt
    ))
    ethSignedDigest = keccak256("\\x19Ethereum Signed Message:\\n32" || couponHash)
    署名 = ecdsa(privkey, ethSignedDigest)、r||s||v (65 bytes)

【abi.encode の Solidity ルール】
- 各引数は 32 bytes に左ゼロ埋め (左 padding) または右ゼロ埋め (左 padding)
- 動的型 (string, bytes) は別ルールだが、本コントラクトは固定型のみ
- bytes32 はそのまま 32 bytes
- uint8/16/32/64/256 は左ゼロ埋め 32 bytes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

try:
    from Crypto.Hash import keccak as _keccak
    _HAS_KECCAK = True
except Exception:  # pragma: no cover
    _HAS_KECCAK = False

try:
    from ecdsa import SECP256k1, SigningKey, VerifyingKey
    from ecdsa.util import sigdecode_string, sigencode_string
    _HAS_ECDSA = True
except Exception:  # pragma: no cover
    _HAS_ECDSA = False


def keccak256(data: bytes) -> bytes:
    if not _HAS_KECCAK:
        raise RuntimeError("pycryptodome (Crypto.Hash.keccak) 未インストール")
    h = _keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


# ----------------------------- Sol abi.encode 互換 -----------------------------


def _to_bytes32(value: int | bytes | str) -> bytes:
    """Solidity の bytes32 引数 → 32 bytes 表現に揃える。

    - int: 左ゼロ埋め 32 bytes (big endian, unsigned)
    - bytes (≤32): **右ゼロ埋め** で 32 bytes (Solidity の bytes32 と一致)
    - str (hex 0x... or plain): まず bytes に変換した上で右ゼロ埋め
    """
    if isinstance(value, int):
        if value < 0:
            raise ValueError("uint cannot be negative")
        return value.to_bytes(32, "big")
    if isinstance(value, str):
        s = value.removeprefix("0x") if value.startswith("0x") else value
        try:
            value = bytes.fromhex(s)
        except ValueError:
            value = value.encode("utf-8")
    if not isinstance(value, (bytes, bytearray)):
        raise TypeError(f"unsupported {type(value).__name__}")
    if len(value) > 32:
        raise ValueError(f"bytes32 overflow ({len(value)})")
    return value.ljust(32, b"\x00")  # 右ゼロ埋め (Solidity の bytes32 規約)


def _to_uint(value: int, bits: int) -> bytes:
    """Solidity の uintN 引数 → 32 bytes 表現に揃える (左ゼロ埋め)。"""
    if value < 0 or value >= 2 ** bits:
        raise ValueError(f"uint{bits} overflow: {value}")
    return value.to_bytes(32, "big")


# ----------------------------- coupon hash (Sol 互換) -----------------------------


@dataclass(frozen=True)
class SolCoupon:
    """Sol PBMOfflineFallback.OfflineCoupon と同じレイアウト。"""

    program_id: bytes  # bytes32
    pid: bytes         # bytes32
    month_index: int   # uint32
    cap_jpy: int       # uint256
    expires_at: int    # uint64

    @classmethod
    def from_strings(cls, *, program_id: str, pid: str, month_index: int, cap_jpy: int, expires_at: int) -> "SolCoupon":
        """文字列 program_id / pid (hex or plain) を bytes32 に揃える。"""
        return cls(
            program_id=_to_bytes32(program_id),
            pid=_to_bytes32(pid),
            month_index=int(month_index),
            cap_jpy=int(cap_jpy),
            expires_at=int(expires_at),
        )


def coupon_abi_encode(c: SolCoupon) -> bytes:
    """abi.encode(bytes32, bytes32, uint32, uint256, uint64) を再現。

    Solidity では uint32/uint64 も 32 bytes に左ゼロ埋めされる (= 内側 word は常に 32B)。
    """
    if len(c.program_id) != 32 or len(c.pid) != 32:
        raise ValueError("program_id and pid must be 32 bytes (use SolCoupon.from_strings)")
    return (
        c.program_id
        + c.pid
        + _to_uint(c.month_index, 32)
        + _to_uint(c.cap_jpy, 256)
        + _to_uint(c.expires_at, 64)
    )


def coupon_hash(c: SolCoupon) -> bytes:
    """Sol の `couponHash(c)` と完全一致する 32 byte digest。"""
    return keccak256(coupon_abi_encode(c))


def eth_signed_digest(coupon_h: bytes) -> bytes:
    """Sol の `ethSignedDigest(h)` と完全一致 (EIP-191 personal_sign prefix)。"""
    if len(coupon_h) != 32:
        raise ValueError("coupon_h must be 32 bytes")
    return keccak256(b"\x19Ethereum Signed Message:\n32" + coupon_h)


# ----------------------------- 鍵 & 署名 -----------------------------


def _ensure_libs():
    if not _HAS_KECCAK:
        raise RuntimeError("pycryptodome 未インストール")
    if not _HAS_ECDSA:
        raise RuntimeError("ecdsa 未インストール")


def privkey_from_hex(hex_str: str) -> "SigningKey":
    _ensure_libs()
    h = hex_str.removeprefix("0x")
    if len(h) != 64:
        raise ValueError("private key must be 32 bytes hex")
    return SigningKey.from_string(bytes.fromhex(h), curve=SECP256k1)


def address_from_pubkey(pubkey_uncompressed: bytes) -> str:
    """uncompressed (X+Y, 64 bytes; 0x04 prefix なし) → 0x... address。"""
    if len(pubkey_uncompressed) == 65 and pubkey_uncompressed[0] == 0x04:
        pubkey_uncompressed = pubkey_uncompressed[1:]
    if len(pubkey_uncompressed) != 64:
        raise ValueError("public key must be 64 bytes (X||Y)")
    return "0x" + keccak256(pubkey_uncompressed)[-20:].hex()


def address_of(privkey: "SigningKey") -> str:
    return address_from_pubkey(privkey.verifying_key.to_string())


def sign_coupon_eip191(coupon: SolCoupon, privkey: "SigningKey") -> bytes:
    """Sol 互換署名を生成。65 bytes = r(32) || s(32) || v(1)。

    v は 27 or 28。本実装では決定論的に s を low-s 化し、recovery id は試行で確定。
    """
    _ensure_libs()
    digest = eth_signed_digest(coupon_hash(coupon))
    sig = privkey.sign_digest_deterministic(digest, sigencode=sigencode_string)
    r = sig[:32]
    s = sig[32:64]
    # low-s 正規化 (Sol ecrecover の慣習)
    n = SECP256k1.order
    s_int = int.from_bytes(s, "big")
    if s_int > n // 2:
        s_int = n - s_int
        s = s_int.to_bytes(32, "big")

    # recovery id は 0 か 1 を試して、自分の公開鍵に戻る方を採用
    expected_addr = address_of(privkey).lower()
    for rec_id in (0, 1):
        recovered = _recover_pubkey(digest, r, s, rec_id)
        if recovered is None:
            continue
        if address_from_pubkey(recovered).lower() == expected_addr:
            v = (rec_id + 27).to_bytes(1, "big")
            return r + s + v
    raise RuntimeError("failed to determine recovery id")


def _recover_pubkey(digest: bytes, r: bytes, s: bytes, rec_id: int) -> bytes | None:
    """ECDSA 公開鍵復元 (secp256k1, ethereum 互換)。"""
    _ensure_libs()
    from ecdsa.numbertheory import square_root_mod_prime

    curve = SECP256k1.curve
    G = SECP256k1.generator
    order = SECP256k1.order
    p = curve.p()

    r_int = int.from_bytes(r, "big")
    s_int = int.from_bytes(s, "big")
    if not (1 <= r_int < order and 1 <= s_int < order):
        return None

    # x = r (rec_id の上位ビットは省略 — Sol ecrecover はそうなってる)
    x = r_int
    if x >= p:
        return None
    # y² = x³ + 7 (mod p)
    alpha = (pow(x, 3, p) + 7) % p
    try:
        beta = square_root_mod_prime(alpha, p)
    except Exception:
        return None
    y = beta if (beta % 2 == rec_id % 2) else (p - beta)

    # R = (x, y)
    from ecdsa.ellipticcurve import Point
    R = Point(curve, x, y, order)
    e = int.from_bytes(digest, "big") % order
    r_inv = pow(r_int, -1, order)
    Q = r_inv * (s_int * R + (-e) * G)
    pub_x = Q.x().to_bytes(32, "big")
    pub_y = Q.y().to_bytes(32, "big")
    return pub_x + pub_y


def verify_coupon_eip191(coupon: SolCoupon, signature: bytes, expected_address: str) -> Tuple[bool, str]:
    """Sol `redeemBatch` の検証ロジックを Python で再現。"""
    _ensure_libs()
    if len(signature) != 65:
        return False, "signature length must be 65 bytes (r||s||v)"
    r = signature[:32]
    s = signature[32:64]
    v = signature[64]
    if v < 27:
        v += 27
    if v not in (27, 28):
        return False, f"bad v ({v})"
    rec_id = v - 27
    digest = eth_signed_digest(coupon_hash(coupon))
    pub = _recover_pubkey(digest, r, s, rec_id)
    if pub is None:
        return False, "ecrecover returned None"
    addr = address_from_pubkey(pub)
    if addr.lower() != expected_address.lower():
        return False, f"address mismatch: got {addr}, expected {expected_address}"
    return True, "OK"
