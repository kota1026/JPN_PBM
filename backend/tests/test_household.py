"""世帯 (household) サービス + schema テスト (戦略会議 #17 採択 PH-7 / R19)。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models.citizen import Citizen
from app.services.household import (
    assign_household,
    derive_household_id,
    get_household_members,
    get_household_summary,
    household_cap_consumed,
    is_household_member,
    voucher_amount_for_household,
)


client = TestClient(app)


# ============================================================
# household_id 派生
# ============================================================


def test_derive_household_id_deterministic():
    """同じ PSN からは同じ id が出る。"""
    h1 = derive_household_id(primary_psn_or_maina="PH-0001")
    h2 = derive_household_id(primary_psn_or_maina="PH-0001")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_derive_household_id_distinct():
    """異なる PSN からは異なる id。"""
    h1 = derive_household_id(primary_psn_or_maina="PH-0001")
    h2 = derive_household_id(primary_psn_or_maina="PH-0002")
    assert h1 != h2


# ============================================================
# Schema (Citizen.household_id 列存在)
# ============================================================


def test_citizen_household_id_column_present():
    db = get_session()
    try:
        c = Citizen(
            pid="x" * 64, name="Test", address="Addr", ward="QC",
            dob=__import__("datetime").date(2000, 1, 1),
            gender="M", household_id="HH-test-001",
        )
        db.add(c)
        db.flush()
        rt = db.get(Citizen, "x" * 64)
        assert rt is not None
        assert rt.household_id == "HH-test-001"
    finally:
        db.rollback()
        db.close()


def test_citizen_household_id_nullable_for_jp_compat():
    """JP 既存 seed は household_id 未設定でも動く (後方互換)。"""
    db = get_session()
    try:
        c = Citizen(
            pid="y" * 64, name="JP Test", address="Tokyo", ward="新宿区",
            dob=__import__("datetime").date(1990, 1, 1),
            gender="F",
        )
        db.add(c)
        db.flush()
        rt = db.get(Citizen, "y" * 64)
        assert rt is not None
        assert rt.household_id is None
    finally:
        db.rollback()
        db.close()


# ============================================================
# get_household_members / summary
# ============================================================


def _seed_household(db, household_id: str, members: list[tuple[str, str, str]]):
    """テスト用に世帯を seed する。members = [(pid, name, ward), ...]"""
    for pid, name, ward in members:
        db.add(Citizen(
            pid=pid, name=name, address=ward, ward=ward,
            dob=__import__("datetime").date(2000, 1, 1),
            gender="X", household_id=household_id,
        ))
    db.flush()


def test_get_household_members_returns_all():
    db = get_session()
    try:
        _seed_household(db, "HH-A", [
            ("a" * 64, "A", "QC"),
            ("b" * 64, "B", "QC"),
            ("c" * 64, "C", "QC"),
        ])
        members = get_household_members(db, "HH-A")
        assert len(members) == 3
        assert {m.pid for m in members} == {"a" * 64, "b" * 64, "c" * 64}
    finally:
        db.rollback()
        db.close()


def test_get_household_members_empty_for_unknown():
    db = get_session()
    try:
        assert get_household_members(db, "HH-DOES-NOT-EXIST") == []
    finally:
        db.close()


def test_get_household_summary_picks_min_pid_as_primary():
    db = get_session()
    try:
        _seed_household(db, "HH-B", [
            ("z" * 64, "Z", "QC"),
            ("a" * 64, "A", "QC"),
            ("m" * 64, "M", "QC"),
        ])
        s = get_household_summary(db, "HH-B")
        assert s is not None
        assert s.member_count == 3
        assert s.primary_pid == "a" * 64
        assert s.wards == {"QC"}
    finally:
        db.rollback()
        db.close()


def test_get_household_summary_returns_none_for_unknown():
    db = get_session()
    try:
        assert get_household_summary(db, "HH-NULL") is None
    finally:
        db.close()


def test_summary_handles_multi_ward():
    db = get_session()
    try:
        _seed_household(db, "HH-C", [
            ("d" * 64, "D", "QC"),
            ("e" * 64, "E", "MNL"),
        ])
        s = get_household_summary(db, "HH-C")
        assert s is not None
        assert s.wards == {"QC", "MNL"}
    finally:
        db.rollback()
        db.close()


# ============================================================
# is_household_member
# ============================================================


def test_is_household_member_true_for_member():
    db = get_session()
    try:
        _seed_household(db, "HH-D", [("f" * 64, "F", "QC")])
        assert is_household_member(db, pid="f" * 64, household_id="HH-D")
    finally:
        db.rollback()
        db.close()


def test_is_household_member_false_for_other_household():
    db = get_session()
    try:
        _seed_household(db, "HH-E", [("g" * 64, "G", "QC")])
        assert not is_household_member(db, pid="g" * 64, household_id="HH-OTHER")
    finally:
        db.rollback()
        db.close()


def test_is_household_member_false_for_unknown_pid():
    db = get_session()
    try:
        assert not is_household_member(db, pid="ghost" * 13, household_id="HH-X")
    finally:
        db.close()


# ============================================================
# household_cap_consumed
# ============================================================


def test_household_cap_consumed_aggregates():
    db = get_session()
    try:
        _seed_household(db, "HH-F", [
            ("h" * 64, "H", "QC"),
            ("i" * 64, "I", "QC"),
            ("j" * 64, "J", "QC"),
        ])
        per_pid = {
            "h" * 64: 3000,
            "i" * 64: 2500,
            "j" * 64: 1000,
            "k" * 64: 9999,  # 別世帯、加算されないはず
        }
        total = household_cap_consumed(db, household_id="HH-F",
                                        per_pid_consumed=per_pid)
        assert total == 6500
    finally:
        db.rollback()
        db.close()


# ============================================================
# assign_household
# ============================================================


def test_assign_household_bulk_assigns():
    db = get_session()
    try:
        # 既存 citizens (household_id 未設定) を作る
        for pid in ("p" * 64, "q" * 64, "r" * 64):
            db.add(Citizen(
                pid=pid, name="x", address="x", ward="QC",
                dob=__import__("datetime").date(2000, 1, 1), gender="X",
            ))
        db.flush()
        n = assign_household(
            db, pids=("p" * 64, "q" * 64, "missing" * 9),
            household_id="HH-G",
        )
        assert n == 2  # missing は無視される
        assert db.get(Citizen, "p" * 64).household_id == "HH-G"
        assert db.get(Citizen, "q" * 64).household_id == "HH-G"
        assert db.get(Citizen, "r" * 64).household_id is None
    finally:
        db.rollback()
        db.close()


# ============================================================
# voucher_amount_for_household
# ============================================================


def test_voucher_base_only():
    assert voucher_amount_for_household(
        member_count=3, base_amount_per_household=140000,
    ) == 140000


def test_voucher_base_plus_member_bonus():
    """4Ps 風: 世帯 base + 子供 1 人につき bonus。"""
    assert voucher_amount_for_household(
        member_count=3, base_amount_per_household=100000, member_bonus=15000,
    ) == 100000 + 3 * 15000


# ============================================================
# 統合: PH seed load 後の世帯構成
# ============================================================


def test_ph_seed_creates_household_groupings():
    """PH seed をロードすると、PH-0001 系の 3 人が同じ household に属する。"""
    r = client.post("/seed/load?locale=ph")
    assert r.status_code == 200

    from app.services.privacy import pseudonymize
    from app.services.household import derive_household_id

    db = get_session()
    try:
        # PH-0001 系 3 人の household_id が一致
        h_expected = derive_household_id(primary_psn_or_maina="PH-0001")
        santos_pids = [pseudonymize(p) for p in ("PH-0001", "PH-0001-A", "PH-0001-B")]
        for pid in santos_pids:
            c = db.get(Citizen, pid)
            assert c is not None, f"missing citizen {pid[:8]}.."
            assert c.household_id == h_expected

        # PH-0002 (Reyes) は別 world
        h_reyes = derive_household_id(primary_psn_or_maina="PH-0002")
        assert h_reyes != h_expected
        c_reyes = db.get(Citizen, pseudonymize("PH-0002"))
        assert c_reyes is not None
        assert c_reyes.household_id == h_reyes

        # Santos 世帯 summary が 3 人
        s = get_household_summary(db, h_expected)
        assert s is not None
        assert s.member_count == 3
    finally:
        db.close()


def test_jp_seed_does_not_set_household_id():
    """JP seed は household_id 未設定で後方互換。"""
    r = client.post("/seed/load?locale=jp")
    assert r.status_code == 200

    db = get_session()
    try:
        # JP citizens の household_id は全て None
        from sqlalchemy import select
        rows = db.execute(select(Citizen).where(
            Citizen.ward.in_(["新宿区", "渋谷区", "江東区", "世田谷区", "千代田区"])
        )).scalars().all()
        for c in rows:
            assert c.household_id is None
    finally:
        db.close()
