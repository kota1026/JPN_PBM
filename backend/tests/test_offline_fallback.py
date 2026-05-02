"""CP-6 オフラインフォールバック (offline_fallback.py) のテスト。

対応する不変性 (= 戦略会議で Red Team が出した懸念):
- 改ざん検出: QR の payload を 1bit でも変えると署名検証 NG
- 期限超過 + 30 日まで OK、それ以降は NG
- 同 (pid, month_index) で cap を超える redeem は不可 (CP-5 二重支給)
- 別の (pid, month_index) は影響を受けない (= シャーディングが正しい)
- 未承認店舗からの redeem_batch は全件 reject
- 部分受理 (一部 OK / 一部 NG) でも accepted のみ精算される
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.offline_fallback import (
    OfflineLedger,
    OfflineSettlement,
    SignedCoupon,
    issue_offline_coupon,
    verify_coupon,
)


def _now() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def _expires_in(days: int) -> int:
    return int((datetime.now(tz=timezone.utc) + timedelta(days=days)).timestamp())


def test_issue_and_verify_roundtrip():
    signed = issue_offline_coupon(
        program_id="prog-koto-kosodate-2026",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(30),
    )
    ok, why = verify_coupon(signed)
    assert ok, why


def test_tampering_detected():
    signed = issue_offline_coupon(
        program_id="p",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(30),
    )
    # 1 円 cap を増やす攻撃
    tampered = SignedCoupon(
        coupon=signed.coupon.__class__(
            program_id=signed.coupon.program_id,
            pid=signed.coupon.pid,
            month_index=signed.coupon.month_index,
            cap_jpy=signed.coupon.cap_jpy + 1,
            expires_at=signed.coupon.expires_at,
        ),
        signature=signed.signature,
    )
    ok, why = verify_coupon(tampered)
    assert not ok and "署名" in why


def test_expiry_grace_period():
    # 既に 31 日前に切れている = 受理不可
    expired = issue_offline_coupon(
        program_id="p",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(-31),
    )
    ok, why = verify_coupon(expired)
    assert not ok and "30 日" in why

    # 25 日前に切れている = まだ grace 内
    grace = issue_offline_coupon(
        program_id="p",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(-25),
    )
    ok, _ = verify_coupon(grace)
    assert ok


def test_pos_local_double_spend_blocked():
    """CP-5 + CP-6: POS 側ローカル ledger で二重消費が止まること。"""
    signed = issue_offline_coupon(
        program_id="p",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(30),
    )
    pos = OfflineLedger()
    pos.approve_store("store-aeon-koto")

    ok, _, r1 = pos.try_redeem(
        signed, store_id="store-aeon-koto", amount_jpy=3000, redeemed_at=_now()
    )
    assert ok and r1 is not None and r1.amount_jpy == 3000

    # cap 5000、既に 3000 消費 → 残 2000
    ok, why, r2 = pos.try_redeem(
        signed, store_id="store-aeon-koto", amount_jpy=2500, redeemed_at=_now()
    )
    assert not ok and "cap 超過" in why and r2 is None

    # 残 2000 ぴったりは OK
    ok, _, r3 = pos.try_redeem(
        signed, store_id="store-aeon-koto", amount_jpy=2000, redeemed_at=_now()
    )
    assert ok and r3 is not None
    assert pos.consumed("pid-001", 202604) == 5000


def test_unapproved_store_blocked():
    signed = issue_offline_coupon(
        program_id="p",
        pid="pid-001",
        month_index=202604,
        cap_jpy=5000,
        expires_at=_expires_in(30),
    )
    pos = OfflineLedger()  # approve しない
    ok, why, _ = pos.try_redeem(
        signed, store_id="store-rogue", amount_jpy=1000, redeemed_at=_now()
    )
    assert not ok and "未承認" in why


def test_batch_settlement_partial_accept():
    """復旧後の集中精算で、不正な item は reject、正しい item は accept される。"""
    settlement = OfflineSettlement()
    settlement.approve_store("store-aeon-koto")

    valid = issue_offline_coupon(
        program_id="p", pid="pid-A", month_index=202604, cap_jpy=5000, expires_at=_expires_in(30)
    )
    other = issue_offline_coupon(
        program_id="p", pid="pid-B", month_index=202604, cap_jpy=5000, expires_at=_expires_in(30)
    )

    pos = OfflineLedger()
    pos.approve_store("store-aeon-koto")

    _, _, r_ok = pos.try_redeem(
        valid, store_id="store-aeon-koto", amount_jpy=4000, redeemed_at=_now()
    )
    _, _, r_other_ok = pos.try_redeem(
        other, store_id="store-aeon-koto", amount_jpy=2000, redeemed_at=_now()
    )

    # 偽造 signature で店舗が混入させた item
    forged = type(r_ok)(
        coupon=valid.coupon,
        signature="00" * 32,
        store_id="store-aeon-koto",
        amount_jpy=1000,
        redeemed_at=_now(),
    )

    res = settlement.redeem_batch(
        "store-aeon-koto", [r_ok, forged, r_other_ok]
    )
    assert res.total_paid_jpy == 4000 + 2000
    assert len(res.accepted) == 2
    assert len(res.rejected) == 1
    assert "署名" in res.rejected[0][1]


def test_batch_unapproved_store_rejects_all():
    settlement = OfflineSettlement()  # 何も approve しない
    valid = issue_offline_coupon(
        program_id="p", pid="pid-A", month_index=202604, cap_jpy=5000, expires_at=_expires_in(30)
    )
    pos = OfflineLedger()
    pos.approve_store("store-aeon-koto")
    _, _, r = pos.try_redeem(
        valid, store_id="store-aeon-koto", amount_jpy=4000, redeemed_at=_now()
    )
    res = settlement.redeem_batch("store-aeon-koto", [r])
    assert res.total_paid_jpy == 0
    assert len(res.accepted) == 0
    assert "未承認" in res.rejected[0][1]


def test_independent_months_isolated():
    """同じ pid でも月が違えば cap は独立。"""
    settlement = OfflineSettlement()
    settlement.approve_store("store-aeon-koto")
    pos = OfflineLedger()
    pos.approve_store("store-aeon-koto")

    apr = issue_offline_coupon(
        program_id="p", pid="pid-A", month_index=202604, cap_jpy=5000, expires_at=_expires_in(30)
    )
    may = issue_offline_coupon(
        program_id="p", pid="pid-A", month_index=202605, cap_jpy=5000, expires_at=_expires_in(30)
    )

    items = []
    for c in (apr, may):
        _, _, r = pos.try_redeem(c, store_id="store-aeon-koto", amount_jpy=5000, redeemed_at=_now())
        items.append(r)

    res = settlement.redeem_batch("store-aeon-koto", items)
    assert res.total_paid_jpy == 10000
    assert len(res.rejected) == 0


@pytest.mark.parametrize("amount", [0, -1])
def test_zero_or_negative_amount_rejected(amount: int):
    pos = OfflineLedger()
    pos.approve_store("store-aeon-koto")
    signed = issue_offline_coupon(
        program_id="p", pid="x", month_index=202604, cap_jpy=5000, expires_at=_expires_in(30)
    )
    ok, why, _ = pos.try_redeem(
        signed, store_id="store-aeon-koto", amount_jpy=amount, redeemed_at=_now()
    )
    assert not ok and "positive" in why
