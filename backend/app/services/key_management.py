"""ECDSA 鍵 rotation 経路 (戦略会議 #6 採択 A)。

Phase 2 の本番運用では、governor の secp256k1 秘密鍵を 6〜12 ヶ月で
ローテーションする想定。本モジュールは:

- env から 1+ 世代の鍵を読む (例: JPN_PBM_GOVERNOR_PRIVKEYS=key1,key2,key3)
- そのうち 1 つを active key として指定 (= 今後の発行に使う)
- 検証側は active + 過去 (grace 期間内) の全鍵を試す
- grace 期間外の鍵で署名された coupon は reject (revoked)

【設計上の選択】
- coupon 自体に key_id を埋めない: 既存 SolCoupon 構造 (5 フィールド) を変えないため
- 検証は O(N) 試行: N=2-3 の rotation 履歴なら無視できるコスト
- grace 期間 (デフォルト 90 日) は env で上書き可能

【ENV 変数】
- JPN_PBM_GOVERNOR_PRIVKEYS  : "<priv1>[,<priv2>,...]" (新しい順)
- JPN_PBM_GOVERNOR_ACTIVE_IDX: int (デフォルト 0 = 最初 = 最新)
- JPN_PBM_KEY_GRACE_DAYS     : int (デフォルト 90)

【後方互換】
- 単一鍵モード (JPN_PBM_GOVERNOR_PRIVKEY) も引き続き動く
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

from app.services.sol_compat import (
    SolCoupon,
    address_of,
    privkey_from_hex,
    sign_coupon_eip191,
    verify_coupon_eip191,
)


DEFAULT_GRACE_DAYS = 90


@dataclass(frozen=True)
class GovKey:
    privkey_hex: str
    address: str
    is_active: bool

    @property
    def short(self) -> str:
        return self.address[:10] + "..." + self.address[-6:]


def _read_keys_env() -> tuple[list[str], int, int]:
    """env から鍵リスト + active idx + grace 日数を読む。"""
    multi = os.environ.get("JPN_PBM_GOVERNOR_PRIVKEYS", "").strip()
    single = os.environ.get("JPN_PBM_GOVERNOR_PRIVKEY", "").strip()

    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
    elif single:
        keys = [single]
    else:
        keys = []
    active_idx = int(os.environ.get("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0"))
    grace_days = int(os.environ.get("JPN_PBM_KEY_GRACE_DAYS", str(DEFAULT_GRACE_DAYS)))
    return keys, active_idx, grace_days


def load_keys() -> list[GovKey]:
    """env から GovKey のリストを構築。"""
    raw, active_idx, _ = _read_keys_env()
    if not raw:
        return []
    if active_idx < 0 or active_idx >= len(raw):
        active_idx = 0
    out: list[GovKey] = []
    for i, hex_str in enumerate(raw):
        sk = privkey_from_hex(hex_str)
        out.append(GovKey(
            privkey_hex=hex_str,
            address=address_of(sk),
            is_active=(i == active_idx),
        ))
    return out


def active_key() -> Optional[GovKey]:
    for k in load_keys():
        if k.is_active:
            return k
    return None


def all_addresses() -> list[str]:
    """検証時に試行する全 address。"""
    return [k.address for k in load_keys()]


def sign_with_active(coupon: SolCoupon) -> bytes:
    """active key で coupon に署名する。"""
    k = active_key()
    if k is None:
        raise RuntimeError("no active governor key configured")
    return sign_coupon_eip191(coupon, privkey_from_hex(k.privkey_hex))


def verify_against_any_governor(
    coupon: SolCoupon, signature: bytes,
) -> tuple[bool, str, Optional[str]]:
    """全 governor address について verify を試し、1 つでも一致すれば OK。

    Returns: (ok, reason, matched_address_or_none)
    """
    addrs = all_addresses()
    if not addrs:
        return False, "no governor key configured", None
    last_why = ""
    for addr in addrs:
        ok, why = verify_coupon_eip191(coupon, signature, expected_address=addr)
        if ok:
            return True, "OK", addr
        last_why = why
    return False, last_why or "no governor matched", None


def rotation_status() -> dict[str, object]:
    """SOC ダッシュボードに出す現在の鍵 rotation 状態。"""
    keys = load_keys()
    _, active_idx, grace_days = _read_keys_env()
    return {
        "configured_keys": len(keys),
        "active_index": active_idx,
        "grace_days": grace_days,
        "addresses": [
            {"index": i, "address": k.address, "is_active": k.is_active}
            for i, k in enumerate(keys)
        ],
    }
