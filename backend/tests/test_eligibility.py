"""eligibility 単体テスト。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.citizen import Citizen
from app.models.program import Program
from app.services.eligibility import check


def _prog(**kwargs):
    return Program(
        id="p", name="x", description="",
        budget_jpy=1, subsidy_bps=1, per_citizen_cap_jpy=1,
        start_at=datetime.utcnow(), end_at=datetime.utcnow() + timedelta(days=1),
        eligibility=kwargs.get("eligibility", {}),
        eligible_jans=[], approved_stores=[],
    )


def _citizen(**kwargs):
    base = dict(pid="x", name="n", address="a", ward="新宿区", dob=date(1990, 1, 1), gender="M")
    base.update(kwargs)
    return Citizen(**base)


def test_ward_match():
    assert check(_citizen(ward="新宿区"), _prog(eligibility={"wards": ["新宿区"]})).ok
    assert not check(_citizen(ward="横浜市"), _prog(eligibility={"wards": ["新宿区"]})).ok


def test_age_bounds():
    today = date.today()
    senior = _citizen(dob=date(today.year - 70, 1, 1))
    young = _citizen(dob=date(today.year - 20, 1, 1))
    senior_only = _prog(eligibility={"min_age": 65})
    assert check(senior, senior_only).ok
    assert not check(young, senior_only).ok


def test_gender_filter():
    p = _prog(eligibility={"genders": ["F"]})
    assert not check(_citizen(gender="M"), p).ok
    assert check(_citizen(gender="F"), p).ok
