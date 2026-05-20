"""Donor-PBM 統合テスト ─ DP-2 〜 DP-7 + DP-5 router (Round 21)。

テストカバレッジ:
- kyc_adapter (DP-2): 8 tests
- aml_screening (DP-3): 8 tests
- tier_policy (DP-4): 8 tests
- unhcr_progres_adapter (DP-6): 7 tests
- cp8_emergency_bypass (DP-7): 9 tests
- donor_wallet (DP-5 service): 7 tests
- donor_oauth (DP-5 router): 6 tests
= 53 tests total
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models.donor import Donor
from app.models.donation import Donation
from app.services import aml_screening as aml
from app.services import tier_policy as tp
from app.services.kyc_adapter import (
    DonorIdentity, JumioBackend, KycConfig, KycError,
    MockKycBackend, OnfidoBackend, SumsubBackend, get_kyc_backend,
)
from app.services.aml_screening import (
    AmlError, MockAmlBackend, _calc_risk_score,
    ComplyAdvantageBackend, AmlConfig, WorldCheckBackend,
    THRESHOLD_AUTO_REJECT, THRESHOLD_MANUAL_REVIEW,
    get_aml_backend, SanctionsHit,
)
from app.services.unhcr_progres_adapter import (
    HcbUnhcrProGresBackend, MockUnhcrProGresBackend,
    UnhcrProGresConfig, UnhcrProGresError,
    get_unhcr_progres_backend, progres_id_to_pid,
)
from app.services.cp8_emergency_bypass import (
    Cp8Error, MockCp8AuditStore, clear_default_store,
    get_default_store, maybe_bypass,
)
from app.services.donor_wallet import (
    DonationRequest, donor_pid_from_email, donor_pid_from_entity,
    get_donor_impact, receive_donation,
)


client = TestClient(app)


# ============================================================
# DP-2: kyc_adapter
# ============================================================


def test_kyc_factory_default_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_KYC_BACKEND", raising=False)
    assert isinstance(get_kyc_backend(), MockKycBackend)


def test_kyc_mock_tier0_no_fields_required():
    b = MockKycBackend()
    v = b.verify(
        identity=DonorIdentity(full_name="Anonymous"),
        tier=0, donor_pid="x" * 64,
    )
    assert v.status == "verified"
    assert v.cost_usd_cents == 0


def test_kyc_mock_tier1_requires_email():
    b = MockKycBackend()
    v = b.verify(
        identity=DonorIdentity(full_name="Alice"),  # missing dob/email
        tier=1, donor_pid="x" * 64,
    )
    assert v.status == "rejected"
    assert "Tier 1 requires" in (v.failure_reason or "")


def test_kyc_mock_tier2_requires_photo():
    b = MockKycBackend()
    v = b.verify(
        identity=DonorIdentity(
            full_name="Alice", dob=date(1990, 1, 1),
            email="a@b.com", phone_e164="+81901234567",
        ),  # photo_id_uri 欠落
        tier=2, donor_pid="x" * 64,
    )
    assert v.status == "rejected"
    assert "Tier 2 requires" in (v.failure_reason or "")


def test_kyc_mock_review_branch():
    b = MockKycBackend()
    v = b.verify(
        identity=DonorIdentity(
            full_name="John REVIEW Smith", dob=date(1980, 1, 1),
            email="j@s.com",
        ),
        tier=1, donor_pid="x" * 64,
    )
    assert v.status == "review"


def test_kyc_mock_reject_branch():
    b = MockKycBackend()
    v = b.verify(
        identity=DonorIdentity(
            full_name="REJECT Person", dob=date(1980, 1, 1),
            email="r@p.com",
        ),
        tier=1, donor_pid="x" * 64,
    )
    assert v.status == "rejected"


def test_kyc_jumio_requires_api_key():
    with pytest.raises(KycError, match="api_key"):
        JumioBackend(KycConfig(backend="jumio"))


def test_kyc_estimate_cost_increases_with_tier():
    b = MockKycBackend()
    assert b.estimate_cost(0) == 0
    assert b.estimate_cost(1) < b.estimate_cost(2)
    assert b.estimate_cost(2) < b.estimate_cost(3)


# ============================================================
# DP-3: aml_screening
# ============================================================


def test_aml_factory_default_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_AML_BACKEND", raising=False)
    assert isinstance(get_aml_backend(), MockAmlBackend)


def test_aml_clean_name_cleared():
    b = MockAmlBackend()
    r = b.screen(full_name="Alice Cooper", dob=date(1990, 1, 1), country="JP")
    assert r.outcome == "cleared"
    assert r.risk_score == 0


def test_aml_3_source_hit_auto_rejected():
    b = MockAmlBackend()
    r = b.screen(full_name="Osama Bin Laden", dob=date(1957, 3, 10), country="SA")
    assert r.outcome == "rejected"
    assert r.risk_score >= THRESHOLD_AUTO_REJECT


def test_aml_1_source_hit_review_only():
    """OFAC のみ hit = false positive 高、自動 reject はしない。"""
    b = MockAmlBackend()
    r = b.screen(full_name="John Smith", dob=date(1980, 1, 1), country="US")
    # 1 source → score 30 → manual review threshold (40) 未満 = cleared
    assert r.outcome == "cleared"


def test_aml_high_risk_country_bonus():
    """1 source hit + high-risk country = score 30 + 15 = 45 → review。"""
    b = MockAmlBackend()
    r = b.screen(full_name="Mohammed Khan", dob=date(1985, 1, 1), country="IR")
    assert r.outcome == "review"
    assert r.risk_score >= THRESHOLD_MANUAL_REVIEW


def test_aml_calc_risk_score_no_hits():
    assert _calc_risk_score(hits=[], country="JP") == 0


def test_aml_calc_risk_score_distinct_sources():
    h1 = SanctionsHit("ofac_sdn", "x", 1.0, "id1", None)
    h2 = SanctionsHit("un_consolidated", "x", 1.0, "id2", None)
    h3 = SanctionsHit("eu_consolidated", "x", 1.0, "id3", None)
    s1 = _calc_risk_score(hits=[h1], country="JP")
    s2 = _calc_risk_score(hits=[h1, h2], country="JP")
    s3 = _calc_risk_score(hits=[h1, h2, h3], country="JP")
    assert s1 < s2 < s3


def test_aml_complyadvantage_requires_api_key():
    with pytest.raises(AmlError, match="api_key"):
        ComplyAdvantageBackend(AmlConfig(backend="complyadvantage"))


# ============================================================
# DP-4: tier_policy
# ============================================================


def test_tier_anon_for_small_donation():
    assert tp.determine_required_tier(donation_amount_centi=4000) == 0


def test_tier_1_for_medium_donation():
    assert tp.determine_required_tier(donation_amount_centi=50000) == 1


def test_tier_2_for_fatf_threshold():
    """FATF Travel Rule ($3000) は強制的に Tier 2 以上。"""
    assert tp.determine_required_tier(donation_amount_centi=300000) == 2


def test_tier_3_for_large_donation():
    assert tp.determine_required_tier(donation_amount_centi=5000000) == 3


def test_tier_required_fields_grows_with_tier():
    t0 = tp.required_fields_for_tier(0)
    t1 = tp.required_fields_for_tier(1)
    t2 = tp.required_fields_for_tier(2)
    t3 = tp.required_fields_for_tier(3)
    assert t0 == set()
    assert t0 < t1 < t2 < t3


def test_tier_upgrade_path():
    path = tp.upgrade_path(0, 2)
    assert "photo_id_uri" in path
    assert "selfie_uri" in path
    # 0 → 0 は空
    assert tp.upgrade_path(0, 0) == []
    # current >= target は空
    assert tp.upgrade_path(3, 1) == []


def test_tier_cost_monotonic():
    assert tp.tier_cost_usd_cents(0) < tp.tier_cost_usd_cents(1)
    assert tp.tier_cost_usd_cents(1) < tp.tier_cost_usd_cents(2)
    assert tp.tier_cost_usd_cents(2) < tp.tier_cost_usd_cents(3)


def test_tier_negative_amount_rejected():
    with pytest.raises(tp.TierError):
        tp.determine_required_tier(donation_amount_centi=-1)


# ============================================================
# DP-6: unhcr_progres_adapter
# ============================================================


def test_progres_factory_default_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_PROGRES_BACKEND", raising=False)
    assert isinstance(get_unhcr_progres_backend(), MockUnhcrProGresBackend)


def test_progres_id_to_pid_deterministic():
    p1 = progres_id_to_pid("ML-PRG-001")
    p2 = progres_id_to_pid("ML-PRG-001")
    assert p1 == p2
    assert len(p1) == 64


def test_progres_id_to_pid_distinct():
    p1 = progres_id_to_pid("ML-PRG-001")
    p2 = progres_id_to_pid("ML-PRG-002")
    assert p1 != p2


def test_progres_resolve_household_active():
    b = MockUnhcrProGresBackend()
    info = b.resolve_household(progres_id="ML-PRG-001")
    assert info is not None
    assert info.country_of_residence == "ML"
    assert info.region == "Kayes"
    assert info.status == "active"
    assert len(info.household_pid) == 64


def test_progres_resolve_unknown():
    b = MockUnhcrProGresBackend()
    assert b.resolve_household(progres_id="UNKNOWN") is None


def test_progres_check_active_status():
    b = MockUnhcrProGresBackend()
    assert b.check_active_status(progres_id="ML-PRG-001")
    assert not b.check_active_status(progres_id="ML-PRG-099")  # resettled


def test_progres_hcb_requires_api_key():
    with pytest.raises(UnhcrProGresError, match="api_key"):
        HcbUnhcrProGresBackend(UnhcrProGresConfig(backend="hcb"))


# ============================================================
# DP-7: cp8_emergency_bypass
# ============================================================


def test_cp8_store_count_starts_zero():
    s = MockCp8AuditStore()
    assert s.count() == 0


def test_cp8_bypass_skipped_when_aml_cleared():
    s = MockCp8AuditStore()
    bypassed, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="cleared", aml_hits_count=0, aml_risk_score=0,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s,
    )
    assert not bypassed
    assert entry is None


def test_cp8_bypass_skipped_when_no_emergency():
    s = MockCp8AuditStore()
    bypassed, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=False, emergency_lgu=None,
        store=s,
    )
    assert not bypassed


def test_cp8_bypass_skipped_when_amount_too_large():
    s = MockCp8AuditStore()
    bypassed, _ = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s, max_bypass_centi=500000,
    )
    assert not bypassed


def test_cp8_bypass_applied_with_emergency_and_aml_review():
    s = MockCp8AuditStore()
    bypassed, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s,
    )
    assert bypassed
    assert entry is not None
    assert s.count() == 1
    assert entry.review_due_by > entry.received_at


def test_cp8_overdue_detection():
    s = MockCp8AuditStore()
    _, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s, audit_days=14,
    )
    # 通常時は overdue なし
    assert s.list_overdue() == []
    # 100 日後を見ると overdue
    overdue = s.list_overdue(now=entry.received_at + 100 * 86400)
    assert len(overdue) == 1


def test_cp8_mark_reviewed_cleared():
    s = MockCp8AuditStore()
    _, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s,
    )
    reviewed = s.mark_reviewed(
        entry_id=entry.entry_id, reviewer_pid="y" * 64,
        outcome="cleared",
    )
    assert reviewed.review_outcome == "cleared"
    assert reviewed.reviewer_pid == "y" * 64
    assert s.list_pending_review() == []


def test_cp8_mark_reviewed_clawback():
    s = MockCp8AuditStore()
    _, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s,
    )
    reviewed = s.mark_reviewed(
        entry_id=entry.entry_id, reviewer_pid="y" * 64,
        outcome="clawback", clawback_amount_centi=10000,
    )
    assert reviewed.clawback_amount_centi == 10000


def test_cp8_clawback_amount_must_be_valid():
    s = MockCp8AuditStore()
    _, entry = maybe_bypass(
        donor_pid="x" * 64, amount_centi=10000, program_id="prog-x",
        aml_outcome="review", aml_hits_count=1, aml_risk_score=45,
        ndrrmc_active=True, emergency_lgu="QC",
        store=s,
    )
    with pytest.raises(Cp8Error):
        s.mark_reviewed(entry_id=entry.entry_id, reviewer_pid="y" * 64,
                         outcome="clawback", clawback_amount_centi=20000)


def test_cp8_unknown_entry_id_raises():
    s = MockCp8AuditStore()
    with pytest.raises(Cp8Error, match="not found"):
        s.mark_reviewed(entry_id="bogus", reviewer_pid="x" * 64,
                         outcome="cleared")


# ============================================================
# DP-5: donor_wallet (service)
# ============================================================


def test_donor_pid_from_email_deterministic():
    p1 = donor_pid_from_email("alice@example.com")
    p2 = donor_pid_from_email("Alice@Example.com")  # case-insensitive
    assert p1 == p2


def test_donor_pid_from_entity_distinct():
    p1 = donor_pid_from_entity("foundation-123")
    p2 = donor_pid_from_email("foundation-123@x.com")
    assert p1 != p2


def test_receive_donation_anonymous_succeeds():
    clear_default_store()
    db = get_session()
    try:
        req = DonationRequest(
            donor_email="anon@example.com",
            donor_full_name="Anonymous Donor",
            donor_country="JP",
            amount_centi=1000,  # $10 → Tier 0
            program_id="prog-unicef-mali-llin-2026",
            underlying_token="USDC",
        )
        result = receive_donation(db, req=req)
        assert result.outcome == "received"
        assert result.required_tier == 0
        assert result.aml_outcome == "cleared"
    finally:
        db.rollback()
        db.close()


def test_receive_donation_rejected_for_insufficient_tier():
    """Donor が tier 0、寄付 $1000 = Tier 1 必要 → KYC tier 不足で reject。"""
    clear_default_store()
    db = get_session()
    try:
        req = DonationRequest(
            donor_email="bob@example.com",
            donor_full_name="Bob Donor",
            donor_country="JP",
            amount_centi=100000,  # Tier 1 必要
            program_id="prog-unicef-mali-llin-2026",
            underlying_token="USDC",
        )
        result = receive_donation(db, req=req)
        assert result.outcome == "rejected"
        assert "insufficient" in result.reason or "tier" in result.reason.lower()
    finally:
        db.rollback()
        db.close()


def test_receive_donation_aml_rejected_no_emergency():
    """AML reject 名前、NDRRMC 非 active → そのまま rejected。"""
    clear_default_store()
    db = get_session()
    try:
        req = DonationRequest(
            donor_email="osama@example.com",
            donor_full_name="Osama Bin Laden",
            donor_country="SA",
            amount_centi=1000,
            program_id="prog-unicef-mali-llin-2026",
            underlying_token="USDC",
        )
        result = receive_donation(db, req=req)
        assert result.outcome == "rejected"
        assert result.aml_outcome == "rejected"
    finally:
        db.rollback()
        db.close()


def test_receive_donation_cp8_bypass_when_emergency():
    """AML rejected でも NDRRMC active + emergency_lgu 一致なら CP-8 bypass。"""
    clear_default_store()
    db = get_session()
    try:
        req = DonationRequest(
            donor_email="khan@example.com",
            donor_full_name="Mohammed Khan",  # 1 source hit + IR で review
            donor_country="IR",
            amount_centi=1000,
            program_id="prog-unicef-mali-llin-2026",
            underlying_token="USDC",
            ndrrmc_active=True,
            emergency_lgu="ML-Kayes",
        )
        result = receive_donation(db, req=req)
        assert result.outcome == "cp8_bypass"
        assert result.cp8_bypass_entry_id is not None
    finally:
        db.rollback()
        db.close()


def test_donor_impact_summary():
    clear_default_store()
    db = get_session()
    try:
        for amount in (1000, 2000, 1500):
            req = DonationRequest(
                donor_email="impact@example.com",
                donor_full_name="Impact Donor",
                donor_country="JP",
                amount_centi=amount,
                program_id="prog-unicef-mali-llin-2026",
                underlying_token="USDC",
            )
            receive_donation(db, req=req)

        pid = donor_pid_from_email("impact@example.com")
        summary = get_donor_impact(db, donor_pid=pid)
        assert summary is not None
        assert summary.donation_count == 3
        assert summary.total_donated_centi == 4500
        assert "prog-unicef-mali-llin-2026" in summary.programs
    finally:
        db.rollback()
        db.close()


def test_donor_impact_unknown_donor_returns_none():
    db = get_session()
    try:
        assert get_donor_impact(db, donor_pid="ghost" * 13) is None
    finally:
        db.close()


def test_receive_negative_amount_rejected():
    db = get_session()
    try:
        req = DonationRequest(
            donor_email="x@y.com", donor_full_name="x",
            donor_country="JP", amount_centi=-1,
            program_id="p", underlying_token="USDC",
        )
        with pytest.raises(ValueError):
            receive_donation(db, req=req)
    finally:
        db.close()


# ============================================================
# DP-5: donor_oauth router
# ============================================================


def test_donor_oauth_authorize_html_returned():
    r = client.get("/donor-oauth/v1/authorize", params={
        "response_type": "code",
        "provider": "coinbase",
        "redirect_uri": "http://localhost:8000/cb",
        "amount_centi": 1000,
        "program_id": "prog-unicef-mali-llin-2026",
        "state": "abc",
    })
    assert r.status_code == 200
    assert "coinbase" in r.text.lower() or "Coinbase" in r.text


def test_donor_oauth_unknown_provider_rejected():
    r = client.get("/donor-oauth/v1/authorize", params={
        "provider": "unknown_pay",
        "redirect_uri": "http://localhost:8000/cb",
        "amount_centi": 1000,
        "program_id": "x", "state": "x",
    })
    assert r.status_code == 400


def test_donor_oauth_bad_redirect_rejected():
    r = client.get("/donor-oauth/v1/authorize", params={
        "provider": "coinbase",
        "redirect_uri": "https://evil.example.com/cb",
        "amount_centi": 1000,
        "program_id": "x", "state": "x",
    })
    assert r.status_code == 400


def test_donor_oauth_full_flow_anonymous():
    clear_default_store()
    # consent POST → token POST
    consent = client.post("/donor-oauth/v1/authorize/consent", data={
        "email": "flow@example.com",
        "full_name": "Flow Donor",
        "country": "JP",
        "redirect_uri": "http://localhost:8000/cb",
        "state": "s1",
        "provider": "coinbase",
        "amount_centi": "1000",
        "program_id": "prog-unicef-mali-llin-2026",
        "underlying_token": "USDC",
    })
    assert consent.status_code == 200
    body = consent.json()
    code = body["redirect_to"].split("code=")[1].split("&")[0]

    tok = client.post("/donor-oauth/v1/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/cb",
        "provider": "coinbase",
    })
    assert tok.status_code == 200
    tbody = tok.json()
    assert tbody["donor_pid"] == body["donor_pid"]
    assert tbody["donation_outcome"] in ("received", "cp8_bypass")


def test_donor_oauth_replay_prevented():
    consent = client.post("/donor-oauth/v1/authorize/consent", data={
        "email": "replay@example.com",
        "full_name": "Replay Donor",
        "country": "JP",
        "redirect_uri": "http://localhost:8000/cb",
        "state": "s",
        "provider": "paypal",
        "amount_centi": "1000",
        "program_id": "prog-unicef-mali-llin-2026",
        "underlying_token": "USDC",
    })
    code = consent.json()["redirect_to"].split("code=")[1].split("&")[0]
    body = {"grant_type": "authorization_code", "code": code,
             "redirect_uri": "http://localhost:8000/cb", "provider": "paypal"}
    r1 = client.post("/donor-oauth/v1/token", json=body)
    assert r1.status_code == 200
    r2 = client.post("/donor-oauth/v1/token", json=body)
    assert r2.status_code == 400


def test_donor_oauth_userinfo_requires_bearer():
    r = client.get("/donor-oauth/v1/userinfo")
    assert r.status_code == 401
