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
from datetime import date, datetime
from typing import Iterable, Optional

from app.services.sol_compat import (
    SolCoupon,
    address_of,
    privkey_from_hex,
    sign_coupon_eip191,
    verify_coupon_eip191,
)


DEFAULT_GRACE_DAYS = 90
DEFAULT_KEY_MAX_AGE_DAYS = 365  # 戦略会議 #8 採択 C: 1 年でローテーション推奨


@dataclass(frozen=True)
class GovKey:
    privkey_hex: str
    address: str
    is_active: bool
    issued_at: date | None = None  # 鍵発行日 (戦略会議 #8 採択 C)

    @property
    def short(self) -> str:
        return self.address[:10] + "..." + self.address[-6:]

    def age_days(self, *, today: date | None = None) -> int | None:
        if self.issued_at is None:
            return None
        today = today or date.today()
        return (today - self.issued_at).days

    def is_overage(self, *, max_age_days: int = DEFAULT_KEY_MAX_AGE_DAYS, today: date | None = None) -> bool:
        age = self.age_days(today=today)
        if age is None:
            return False  # 不明 → 警告対象外
        return age > max_age_days


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


def _read_issued_dates() -> list[date | None]:
    """JPN_PBM_GOVERNOR_ISSUED_AT="2025-01-15,2024-06-01,..." を読む (戦略会議 #8 採択 C)。

    JPN_PBM_GOVERNOR_PRIVKEYS と同じ並び・同じ要素数。空文字 OR 解釈失敗は None。
    """
    raw = os.environ.get("JPN_PBM_GOVERNOR_ISSUED_AT", "").strip()
    if not raw:
        return []
    out: list[date | None] = []
    for tok in raw.split(","):
        tok = tok.strip()
        try:
            out.append(date.fromisoformat(tok) if tok else None)
        except ValueError:
            out.append(None)
    return out


def load_keys() -> list[GovKey]:
    """env から GovKey のリストを構築。"""
    raw, active_idx, _ = _read_keys_env()
    if not raw:
        return []
    if active_idx < 0 or active_idx >= len(raw):
        active_idx = 0
    issued_dates = _read_issued_dates()
    out: list[GovKey] = []
    for i, hex_str in enumerate(raw):
        sk = privkey_from_hex(hex_str)
        issued = issued_dates[i] if i < len(issued_dates) else None
        out.append(GovKey(
            privkey_hex=hex_str,
            address=address_of(sk),
            is_active=(i == active_idx),
            issued_at=issued,
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


def rotation_status(*, today: date | None = None) -> dict[str, object]:
    """SOC ダッシュボードに出す現在の鍵 rotation 状態。"""
    keys = load_keys()
    _, active_idx, grace_days = _read_keys_env()
    max_age = int(os.environ.get("JPN_PBM_KEY_MAX_AGE_DAYS", str(DEFAULT_KEY_MAX_AGE_DAYS)))
    today = today or date.today()
    addresses: list[dict[str, object]] = []
    overage_count = 0
    for i, k in enumerate(keys):
        age = k.age_days(today=today)
        is_over = k.is_overage(max_age_days=max_age, today=today)
        if is_over:
            overage_count += 1
        addresses.append({
            "index": i,
            "address": k.address,
            "is_active": k.is_active,
            "issued_at": k.issued_at.isoformat() if k.issued_at else None,
            "age_days": age,
            "is_overage": is_over,
        })
    alerts: list[str] = []
    if overage_count > 0:
        alerts.append(
            f"WARNING: {overage_count} key(s) older than {max_age} days. "
            f"Recommend rotation."
        )
    return {
        "configured_keys": len(keys),
        "active_index": active_idx,
        "grace_days": grace_days,
        "max_age_days": max_age,
        "alerts": alerts,
        "addresses": addresses,
    }
