"""Sol PBMOfflineFallback Python シミュレータのテスト (戦略会議 #6 採択 B)。

Sol コントラクトと Python 実装が同じセマンティクスを持つことを担保する。
"""

from __future__ import annotations

import time

import pytest

from app.services.sol_compat import (
    SolCoupon,
    address_of,
    privkey_from_hex,
    sign_coupon_eip191,
)
from app.services.sol_simulator import (
    GRACE_DAYS_SEC,
    SolRedemption,
    SolRevert,
    SolSimulator,
    cross_check_with_offchain,
)


GOV_KEY = "f8b8a8a2c7c4f8c8a8b8e8c8e8b8c8a8d8a8b8c8a8b8c8d8e8a8b8c8d8e8f8a8"
STORE = "0x0000000000000000000000000000000000005678"


@pytest.fixture
def gov_sk():
    return privkey_from_hex(GOV_KEY)


@pytest.fixture
def sim(gov_sk):
    s = SolSimulator(address_of(gov_sk))
    s.set_approved_store(STORE, True)
    return s


def _coupon(pid="a" * 64, month_index=202604, cap_jpy=5000, expires_at=None):
    if expires_at is None:
        expires_at = int(time.time()) + 30 * 86400
    return SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026", pid=pid,
        month_index=month_index, cap_jpy=cap_jpy, expires_at=expires_at,
    )


def _redemption(coupon, sk, *, amount, store=STORE):
    sig = sign_coupon_eip191(coupon, sk)
    return SolRedemption(
        coupon=coupon, signature=sig,
        store_address=store, amount_jpy=amount,
        redeemed_at=int(time.time()),
    )


# -------------------- 通常系 --------------------


def test_redeem_batch_happy_path(sim, gov_sk):
    c = _coupon(cap_jpy=5000)
    r1 = _redemption(c, gov_sk, amount=2000)
    r2 = _redemption(c, gov_sk, amount=1500)
    res = sim.redeem_batch([r1, r2], msg_sender=STORE)
    assert res.total_paid_jpy == 3500
    assert sim.consumed_of(c.pid, c.month_index) == 3500
    assert sim.store_balances[STORE.lower()] == 3500


def test_redeem_batch_independent_pid_and_months(sim, gov_sk):
    c1 = _coupon(pid="a" * 64, month_index=202604, cap_jpy=3000)
    c2 = _coupon(pid="b" * 64, month_index=202604, cap_jpy=3000)
    c3 = _coupon(pid="a" * 64, month_index=202605, cap_jpy=3000)
    items = [
        _redemption(c1, gov_sk, amount=3000),
        _redemption(c2, gov_sk, amount=3000),
        _redemption(c3, gov_sk, amount=3000),
    ]
    res = sim.redeem_batch(items, msg_sender=STORE)
    assert res.total_paid_jpy == 9000


# -------------------- 失敗系 (Sol revert と等価) --------------------


def test_unapproved_store_reverts(gov_sk):
    sim = SolSimulator(address_of(gov_sk))  # approved_store なし
    c = _coupon()
    r = _redemption(c, gov_sk, amount=100)
    with pytest.raises(SolRevert, match="store not approved"):
        sim.redeem_batch([r], msg_sender=STORE)


def test_store_address_mismatch_reverts(sim, gov_sk):
    c = _coupon()
    r = _redemption(c, gov_sk, amount=100, store="0x0000000000000000000000000000000000009999")
    with pytest.raises(SolRevert, match="store mismatch"):
        sim.redeem_batch([r], msg_sender=STORE)


def test_zero_amount_reverts(sim, gov_sk):
    c = _coupon()
    r = _redemption(c, gov_sk, amount=0)
    with pytest.raises(SolRevert, match="zero amount"):
        sim.redeem_batch([r], msg_sender=STORE)


def test_expiry_grace_boundary(sim, gov_sk):
    """expires_at + 30 days を 1 秒過ぎたら revert、ぴったりは OK。"""
    now = int(time.time())
    expires = now - GRACE_DAYS_SEC  # ちょうど grace 境界
    c = _coupon(expires_at=expires)
    r = _redemption(c, gov_sk, amount=100)
    # ぴったりは OK
    sim.redeem_batch([r], msg_sender=STORE, block_timestamp=expires + GRACE_DAYS_SEC)
    # 1 秒過ぎたら revert
    sim2 = SolSimulator(address_of(gov_sk))
    sim2.set_approved_store(STORE, True)
    with pytest.raises(SolRevert, match="too late"):
        sim2.redeem_batch([r], msg_sender=STORE, block_timestamp=expires + GRACE_DAYS_SEC + 1)


def test_cap_exceeded_within_batch_reverts_all(sim, gov_sk):
    """1 つの batch 内で cap を超えると、それ以前の accept も revert (Sol 等価)。"""
    c = _coupon(cap_jpy=1000)
    items = [
        _redemption(c, gov_sk, amount=600),
        _redemption(c, gov_sk, amount=500),  # 600 + 500 > 1000
    ]
    with pytest.raises(SolRevert, match="cap exceeded"):
        sim.redeem_batch(items, msg_sender=STORE)
    # consumed が 0 のまま (= 全体 revert)
    assert sim.consumed_of(c.pid, c.month_index) == 0


def test_bad_signature_reverts(sim, gov_sk):
    c = _coupon()
    r = _redemption(c, gov_sk, amount=100)
    # 改ざん coupon で署名は元のまま
    tampered_coupon = SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026", pid="a" * 64,
        month_index=202604, cap_jpy=999_999,  # cap 改ざん
        expires_at=c.expires_at,
    )
    bad = SolRedemption(
        coupon=tampered_coupon, signature=r.signature,
        store_address=STORE, amount_jpy=100, redeemed_at=int(time.time()),
    )
    with pytest.raises(SolRevert, match="bad sig"):
        sim.redeem_batch([bad], msg_sender=STORE)


# -------------------- cross-check (シミュレータ同士) --------------------


def test_cross_check_sol_python_results_match(gov_sk):
    """同じ batch を 2 つの SolSimulator に流して結果一致。"""
    c = _coupon(cap_jpy=5000)
    items = [_redemption(c, gov_sk, amount=2000), _redemption(c, gov_sk, amount=2500)]
    r1, r2 = cross_check_with_offchain(
        items=items, governor_privkey_hex=GOV_KEY, msg_sender=STORE,
    )
    assert r1.total_paid_jpy == r2.total_paid_jpy
    assert r1.consumed_after == r2.consumed_after
