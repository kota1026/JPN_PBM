"""CP-6: 災害時オフラインフォールバック (Phase 1 オフチェーン版)。

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
