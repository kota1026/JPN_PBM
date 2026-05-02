"""多年度予算 (戦略会議 #4 採択 #11) のテスト。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.program import Program
from app.services.fiscal_budget import (
    budget_for_year,
    fiscal_year_of,
    remaining_for_year,
    total_multi_year_budget,
    validate_fiscal_year_budgets,
)


client = TestClient(app)


def _prog(**kwargs) -> Program:
    base = dict(
        id="p", name="x", description="",
        budget_jpy=60_000_000, spent_jpy=0,
        subsidy_bps=10000, per_citizen_cap_jpy=60000,
        start_at=datetime.utcnow(), end_at=datetime.utcnow() + timedelta(days=30),
        eligibility={}, eligible_jans=[], eligible_categories=[],
        excluded_jans=[], approved_stores=[],
        fiscal_year_budgets={},
    )
    base.update(kwargs)
    return Program(**base)


def test_fiscal_year_of_japanese_calendar():
    """4 月始まりの会計年度。"""
    assert fiscal_year_of(datetime(2026, 4, 1)) == "2026"
    assert fiscal_year_of(datetime(2026, 3, 31)) == "2025"
    assert fiscal_year_of(datetime(2027, 1, 15)) == "2026"


def test_budget_for_year_falls_back_to_budget_jpy_when_no_multi_year():
    p = _prog(budget_jpy=10_000_000, fiscal_year_budgets={})
    assert budget_for_year(p, "2026") == 10_000_000


def test_budget_for_year_returns_specific_year():
    p = _prog(fiscal_year_budgets={"2026": 60_000_000, "2027": 70_000_000})
    assert budget_for_year(p, "2026") == 60_000_000
    assert budget_for_year(p, "2027") == 70_000_000
    assert budget_for_year(p, "2099") == 0


def test_total_multi_year_budget():
    p = _prog(fiscal_year_budgets={"2026": 60_000_000, "2027": 70_000_000, "2028": 80_000_000})
    assert total_multi_year_budget(p) == 210_000_000

    legacy = _prog(budget_jpy=50_000_000, fiscal_year_budgets={})
    assert total_multi_year_budget(legacy) == 50_000_000


def test_remaining_consumes_past_years_first():
    """spent_jpy = 80M で fy=2027 を見ると、2026 の 60M を消化済→2027 残=70M-20M=50M。"""
    p = _prog(
        budget_jpy=210_000_000,
        spent_jpy=80_000_000,
        fiscal_year_budgets={"2026": 60_000_000, "2027": 70_000_000, "2028": 80_000_000},
    )
    assert remaining_for_year(p, "2026") == 0  # 全消化
    assert remaining_for_year(p, "2027") == 50_000_000
    assert remaining_for_year(p, "2028") == 80_000_000


def test_validate_rejects_bad_year_keys():
    ok, why = validate_fiscal_year_budgets(
        fiscal_year_budgets={"YYYY": 100}, fallback_budget_jpy=100,
    )
    assert not ok and "YYYY" in why


def test_validate_rejects_negative():
    ok, why = validate_fiscal_year_budgets(
        fiscal_year_budgets={"2026": -1}, fallback_budget_jpy=100,
    )
    assert not ok and ">= 0" in why


def test_validate_accepts_empty():
    ok, _ = validate_fiscal_year_budgets(fiscal_year_budgets={}, fallback_budget_jpy=100)
    assert ok


# ----------------------------- REST 経由 -----------------------------


def test_create_program_with_multi_year_and_query_endpoint():
    client.post("/wallet/treasury/topup", json={"amount_jpy": 250_000_000})
    payload = {
        "id": "prog-multi-year",
        "name": "江東区フラッグシップ 多年度",
        "description": "x",
        "budget_jpy": 210_000_000,
        "subsidy_bps": 10_000,
        "per_citizen_cap_jpy": 60_000,
        "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "end_at": (datetime.utcnow() + timedelta(days=365 * 3)).isoformat(),
        "eligibility": {"wards": ["江東区"]},
        "eligible_jans": [],
        "eligible_categories": ["food.daily"],
        "approved_stores": ["store-a"],
        "fiscal_year_budgets": {"2026": 60_000_000, "2027": 70_000_000, "2028": 80_000_000},
    }
    r = client.post("/programs", json=payload)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["fiscal_year_budgets"] == {"2026": 60_000_000, "2027": 70_000_000, "2028": 80_000_000}

    # /programs/{id}/fiscal-budget
    r = client.get("/programs/prog-multi-year/fiscal-budget?year=2026")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fiscal_year"] == "2026"
    assert body["current_year_budget_jpy"] == 60_000_000
    assert body["total_multi_year_budget_jpy"] == 210_000_000
    assert body["is_multi_year"] is True


def test_create_program_rejects_sum_mismatch():
    client.post("/wallet/treasury/topup", json={"amount_jpy": 1_000_000})
    payload = {
        "id": "prog-mismatch",
        "name": "x", "description": "",
        "budget_jpy": 100,  # 合計と一致しない
        "subsidy_bps": 5000, "per_citizen_cap_jpy": 50,
        "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "end_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "eligibility": {}, "eligible_jans": [], "eligible_categories": [],
        "approved_stores": [],
        "fiscal_year_budgets": {"2026": 50, "2027": 30},  # sum=80 ≠ 100
    }
    r = client.post("/programs", json=payload)
    assert r.status_code == 400
    assert "fiscal_year_budgets" in r.text or "budget_jpy" in r.text
