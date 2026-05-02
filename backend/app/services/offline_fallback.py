"""CP-6: 災害時オフラインフォールバック (Phase 1 + Phase 2 移行)。

首都直下地震等でネット/電力が断絶した際でも、加盟店 POS が事前配布された
署名済み QR を用いて住民への助成を継続できるフェイルセーフ。

本モジュールは `contracts/PBMOfflineFallback.sol` のオフチェーン姉妹実装で、
- 平時に都が `issue_offline_coupon` で QR を発行
- 有事に POS が `verify_coupon` でローカル検証 → そのまま給付
- 復旧後に POS が `redeem_batch` で蓄積 redemption をまとめて精算

を再現する。本番では署名は HSM の ECDSA に置き換わる (Sol 側は ECDSA 実装済み)。
ここでは Phase 1 デモ用に HMAC-SHA256 を採用し、ロジック (nonce 二重消費・cap 越え・
期限切れ) を完全検証可能にしている。

CP-5 (二重支給ゼロ) と CP-6 (災害時可用性) を同時に満たすため、
`(pid, month_index)` を nonce 単位に置き、`consumed[pid][month_index]` の
SQLite 永続層 (将来) ないしインメモリ map で一意化する。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable


SIGNING_SECRET = os.environ.get(
    "JPN_PBM_OFFLINE_SECRET", "demo-offline-secret-change-me"
).encode()

# Phase 2: ECDSA secp256k1 (Sol 側 PBMOfflineFallback の ecrecover と互換)
# 戦略会議 #4 採択 #3。Phase 1 HMAC と並列で動かし、Phase 2 移行時に切替える。
# 鍵は環境変数 JPN_PBM_GOVERNOR_PRIVKEY (32 byte hex) で渡す。未設定なら ECDSA 機能は無効。
GOVERNOR_PRIVKEY_HEX = os.environ.get("JPN_PBM_GOVERNOR_PRIVKEY", "")


# ----------------------------- データクラス -----------------------------


@dataclass(frozen=True)
class OfflineCoupon:
    """都が事前署名するオフラインクーポン (QR ペイロード)。"""

    program_id: str
    pid: str          # 住民擬似 ID (HMAC)
    month_index: int  # 例: 2026-04 → 202604
    cap_jpy: int      # この月の上限助成
    expires_at: int   # Unix 秒

    def canonical(self) -> bytes:
        """改ざん検出可能な canonical 形式 (キー順固定の JSON)。"""
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class SignedCoupon:
    """coupon + 署名。これがそのまま QR にエンコードされる。"""

    coupon: OfflineCoupon
    signature: str  # HMAC-SHA256 hex


@dataclass
class OfflineRedemption:
    """加盟店 POS が有事に蓄積する個別 redemption。"""

    coupon: OfflineCoupon
    signature: str
    store_id: str
    amount_jpy: int
    redeemed_at: int  # Unix 秒


@dataclass
class BatchResult:
    accepted: list[OfflineRedemption] = field(default_factory=list)
    rejected: list[tuple[OfflineRedemption, str]] = field(default_factory=list)
    total_paid_jpy: int = 0


# ----------------------------- 署名 -----------------------------


def _sign(payload: bytes) -> str:
    return hmac.new(SIGNING_SECRET, payload, hashlib.sha256).hexdigest()


def issue_offline_coupon(
    *,
    program_id: str,
    pid: str,
    month_index: int,
    cap_jpy: int,
    expires_at: int | datetime,
) -> SignedCoupon:
    """都が住民へ配布するオフライン QR を発行する。

    `expires_at` は Unix 秒もしくは aware datetime を受ける。
    """
    if cap_jpy <= 0:
        raise ValueError("cap_jpy must be positive")
    if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expires_at = int(expires_at.timestamp())
    coupon = OfflineCoupon(
        program_id=program_id,
        pid=pid,
        month_index=month_index,
        cap_jpy=cap_jpy,
        expires_at=int(expires_at),
    )
    return SignedCoupon(coupon=coupon, signature=_sign(coupon.canonical()))


def verify_coupon(signed: SignedCoupon, *, now: int | None = None) -> tuple[bool, str]:
    """POS がローカルで実行する検証。ネット不要。"""
    expected = _sign(signed.coupon.canonical())
    if not hmac.compare_digest(expected, signed.signature):
        return False, "署名不一致 (改ざん or 別鍵で発行された)"
    now = now if now is not None else int(datetime.now(tz=timezone.utc).timestamp())
    if now > signed.coupon.expires_at + 30 * 24 * 3600:
        return False, "QR が失効後 30 日を超過"
    if signed.coupon.cap_jpy <= 0:
        return False, "cap_jpy が不正"
    return True, "OK"


# ----------------------------- POS ローカル消費トラッキング -----------------------------


class OfflineLedger:
    """POS 端末側で nonce (pid, month_index) ごとの累積消費を保持する。

    端末が壊れても復旧時にチェーン側で `consumed` が同じ (pid, month_index) を
    rewind せず累積するため、整合性は保たれる。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consumed: dict[tuple[str, int], int] = {}
        self._approved_stores: set[str] = set()

    # 都が事前同期する加盟店リスト
    def approve_store(self, store_id: str) -> None:
        self._approved_stores.add(store_id)

    def is_store_approved(self, store_id: str) -> bool:
        return store_id in self._approved_stores

    def consumed(self, pid: str, month_index: int) -> int:
        return self._consumed.get((pid, month_index), 0)

    def try_redeem(
        self,
        signed: SignedCoupon,
        *,
        store_id: str,
        amount_jpy: int,
        redeemed_at: int | None = None,
        now: int | None = None,
    ) -> tuple[bool, str, OfflineRedemption | None]:
        """POS が住民の QR を読んでその場で給付する操作。"""
        if amount_jpy <= 0:
            return False, "amount_jpy must be positive", None
        if not self.is_store_approved(store_id):
            return False, "店舗が未承認", None
        ok, why = verify_coupon(signed, now=now)
        if not ok:
            return False, why, None
        with self._lock:
            key = (signed.coupon.pid, signed.coupon.month_index)
            used = self._consumed.get(key, 0)
            if used + amount_jpy > signed.coupon.cap_jpy:
                return False, f"cap 超過 (used={used}, cap={signed.coupon.cap_jpy})", None
            self._consumed[key] = used + amount_jpy
        redemption = OfflineRedemption(
            coupon=signed.coupon,
            signature=signed.signature,
            store_id=store_id,
            amount_jpy=amount_jpy,
            redeemed_at=redeemed_at
            if redeemed_at is not None
            else int(datetime.now(tz=timezone.utc).timestamp()),
        )
        return True, "OK", redemption


# ----------------------------- チェーン (= サーバ) 側 batch redeem -----------------------------


class OfflineSettlement:
    """都サーバ側の集中精算装置。Sol の `redeemBatch` と同等。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (pid, month_index) → 累積消費
        self._chain_consumed: dict[tuple[str, int], int] = {}
        self._approved_stores: set[str] = set()

    def approve_store(self, store_id: str) -> None:
        self._approved_stores.add(store_id)

    def consumed(self, pid: str, month_index: int) -> int:
        return self._chain_consumed.get((pid, month_index), 0)

    def redeem_batch(
        self,
        store_id: str,
        items: Iterable[OfflineRedemption],
        *,
        now: int | None = None,
    ) -> BatchResult:
        """POS が復旧後に提出する redemption バッチを精算する。

        - 1 件ごとに署名検証 + 期限 + cap を再チェック (POS 側が壊れている可能性)。
        - 失敗したアイテムは `rejected` に積み、他は accept する (= ベストエフォート)。
          Sol 版は revert する仕様だが、サーバ版は不正店舗の混入を見つけやすくするため
          partial accept にする。
        """
        result = BatchResult()
        if store_id not in self._approved_stores:
            for it in items:
                result.rejected.append((it, "店舗が未承認"))
            return result

        with self._lock:
            for it in items:
                if it.store_id != store_id:
                    result.rejected.append((it, "store_id mismatch"))
                    continue
                ok, why = verify_coupon(
                    SignedCoupon(coupon=it.coupon, signature=it.signature), now=now
                )
                if not ok:
                    result.rejected.append((it, why))
                    continue
                key = (it.coupon.pid, it.coupon.month_index)
                used = self._chain_consumed.get(key, 0)
                if used + it.amount_jpy > it.coupon.cap_jpy:
                    result.rejected.append((it, f"cap 超過 (used={used}, cap={it.coupon.cap_jpy})"))
                    continue
                self._chain_consumed[key] = used + it.amount_jpy
                result.accepted.append(it)
                result.total_paid_jpy += it.amount_jpy
        return result


# ----------------------------- Phase 2: ECDSA secp256k1 -----------------------------
#
# 戦略会議 #4 採択 #3 (Stablecoin Architect)。HSM/HW 鍵管理は Phase 3 だが、
# Phase 2 で必要な「Sol PBMOfflineFallback.redeemBatch との完全互換」を成立させる。
#
# 設計:
# - メッセージ = couponHash = keccak256(abi.encode(programId32, pid32, monthIndex, capJpy, expiresAt))
#   ただし本実装ではまず標準的な canonical JSON + sha256 で動かし (= Phase 1.5)、
#   Sol 互換 (keccak / abi.encode / personal_sign) のラッパは Phase 2 完成版で追加する。
# - 鍵は env JPN_PBM_GOVERNOR_PRIVKEY (32byte hex, 0x optional)
# - 公開鍵検証は Python 標準の `ecdsa` ライブラリ (secp256k1) を使う

import hashlib as _hashlib

try:  # noqa: SIM105
    from ecdsa import SECP256k1, SigningKey, VerifyingKey
    from ecdsa.util import sigdecode_string, sigencode_string
    _ECDSA_AVAILABLE = True
except Exception:  # pragma: no cover
    _ECDSA_AVAILABLE = False


def is_ecdsa_available() -> bool:
    return _ECDSA_AVAILABLE and bool(GOVERNOR_PRIVKEY_HEX)


def _privkey() -> "SigningKey":
    if not _ECDSA_AVAILABLE:
        raise RuntimeError("ecdsa パッケージが利用不可")
    if not GOVERNOR_PRIVKEY_HEX:
        raise RuntimeError("JPN_PBM_GOVERNOR_PRIVKEY 未設定")
    h = GOVERNOR_PRIVKEY_HEX.removeprefix("0x")
    if len(h) != 64:
        raise ValueError("private key must be 32 bytes hex")
    return SigningKey.from_string(bytes.fromhex(h), curve=SECP256k1)


def _governor_pubkey_hex() -> str:
    """uncompressed (65 byte: 0x04 + X + Y) を hex で返す。"""
    sk = _privkey()
    vk = sk.verifying_key
    return ("04" + vk.to_string().hex())


def coupon_digest(coupon: OfflineCoupon) -> bytes:
    """coupon → 32 byte digest (sha256 over canonical JSON)。

    Sol 版の keccak256(abi.encode(...)) との完全互換は Phase 2 完成版で対応。
    本実装ではオフチェーン同士の互換に集中する。
    """
    return _hashlib.sha256(coupon.canonical()).digest()


def sign_coupon_ecdsa(coupon: OfflineCoupon) -> str:
    """ECDSA で coupon に署名し、64 byte (r||s) を hex で返す。"""
    sk = _privkey()
    digest = coupon_digest(coupon)
    sig = sk.sign_digest_deterministic(digest, sigencode=sigencode_string)
    return sig.hex()


def issue_offline_coupon_ecdsa(
    *,
    program_id: str,
    pid: str,
    month_index: int,
    cap_jpy: int,
    expires_at: int | datetime,
) -> SignedCoupon:
    """ECDSA 版の coupon 発行 (Phase 2)。"""
    if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expires_at = int(expires_at.timestamp())
    coupon = OfflineCoupon(
        program_id=program_id, pid=pid, month_index=month_index,
        cap_jpy=cap_jpy, expires_at=int(expires_at),
    )
    return SignedCoupon(coupon=coupon, signature=sign_coupon_ecdsa(coupon))


def verify_coupon_ecdsa(signed: SignedCoupon, *, public_key_hex: str | None = None) -> tuple[bool, str]:
    """ECDSA 検証。public_key_hex 未指定なら GOVERNOR の公開鍵を使う。"""
    if not _ECDSA_AVAILABLE:
        return False, "ECDSA 利用不可"
    try:
        pk = public_key_hex or _governor_pubkey_hex()
        if pk.startswith("04") and len(pk) == 130:
            pk = pk[2:]
        vk = VerifyingKey.from_string(bytes.fromhex(pk), curve=SECP256k1)
        sig = bytes.fromhex(signed.signature)
        if len(sig) != 64:
            return False, "signature length must be 64 bytes (r||s)"
        digest = coupon_digest(signed.coupon)
        ok = vk.verify_digest(sig, digest, sigdecode=sigdecode_string)
        return (bool(ok), "OK" if ok else "署名検証失敗")
    except Exception as e:
        return False, f"ECDSA 検証エラー: {e}"
