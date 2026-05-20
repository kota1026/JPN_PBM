"""Donor wallet service ─ DP-5 (戦略会議 #19 採択)。

寄付フローのコア:
1. donor が寄付額を指定
2. tier_policy で必要 KYC tier 算出
3. donor の既存 KYC tier が不足なら upgrade 必要を提示
4. aml_screening で screen
5. AML reject かつ NDRRMC active なら CP-8 bypass 検討
6. donation を記録、program.budget に加算 (= treasury に flow)
7. donor_dashboard 用に impact tracking 開始
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.models.donor import Donor
from app.models.donation import Donation
from app.services import aml_screening as aml
from app.services import tier_policy as tp
from app.services.cp8_emergency_bypass import (
    Cp8AuditStore, get_default_store as get_cp8_store, maybe_bypass,
)


DONOR_HMAC_SECRET = os.environ.get(
    "JPN_PBM_DONOR_HMAC_SECRET", "demo-donor-hmac-secret"
).encode()


def donor_pid_from_email(email: str) -> str:
    return hmac.new(DONOR_HMAC_SECRET, email.lower().encode(),
                     hashlib.sha256).hexdigest()


def donor_pid_from_entity(legal_entity_id: str) -> str:
    return hmac.new(DONOR_HMAC_SECRET,
                     ("entity:" + legal_entity_id).encode(),
                     hashlib.sha256).hexdigest()


# ============================================================
# データクラス (request/response shape)
# ============================================================


DonationOutcome = Literal["received", "rejected", "review", "cp8_bypass"]


@dataclass
class DonationRequest:
    donor_email: str                  # Tier 1+ donors
    donor_full_name: str
    donor_country: str                # ISO-2
    amount_centi: int
    program_id: str
    underlying_token: str             # JPYC/PHPC/USDC
    aml_country_override: str | None = None  # for legal entity
    ndrrmc_active: bool = False
    emergency_lgu: str | None = None


@dataclass
class DonationResult:
    donation_id: str | None
    donor_pid: str
    outcome: DonationOutcome
    required_tier: int
    current_tier: int
    aml_outcome: str
    aml_risk_score: int
    cp8_bypass_entry_id: str | None
    reason: str
    received_at: float


# ============================================================
# Core donation flow
# ============================================================


def receive_donation(
    db: Session,
    *,
    req: DonationRequest,
    cp8_store: Cp8AuditStore | None = None,
) -> DonationResult:
    """donor からの寄付を受理 (or reject)。"""
    if req.amount_centi <= 0:
        raise ValueError("amount_centi must be > 0")
    if not req.donor_email and not req.donor_full_name:
        raise ValueError("either email or full_name required")

    cp8_store = cp8_store or get_cp8_store()

    # tier 決定
    required_tier = tp.determine_required_tier(donation_amount_centi=req.amount_centi)

    # donor lookup or create
    donor_pid = donor_pid_from_email(req.donor_email or req.donor_full_name)
    donor = db.get(Donor, donor_pid)
    if donor is None:
        donor = Donor(
            pid=donor_pid,
            display_name_hash=hmac.new(DONOR_HMAC_SECRET,
                                        req.donor_full_name.encode(),
                                        hashlib.sha256).hexdigest()[:16],
            country=req.donor_country,
            current_tier=0,
        )
        db.add(donor)
        db.flush()

    # tier 不足チェック (実装簡略化: KYC を別 API で済ませる前提、ここでは status 確認のみ)
    if donor.current_tier < required_tier:
        return DonationResult(
            donation_id=None, donor_pid=donor_pid,
            outcome="rejected", required_tier=required_tier,
            current_tier=donor.current_tier,
            aml_outcome="not_screened", aml_risk_score=0,
            cp8_bypass_entry_id=None,
            reason=(f"KYC tier {donor.current_tier} insufficient, "
                    f"need tier {required_tier}"),
            received_at=time.time(),
        )

    # AML 実行
    aml_backend = aml.get_aml_backend()
    aml_result = aml_backend.screen(
        full_name=req.donor_full_name,
        dob=None,
        country=(req.aml_country_override or req.donor_country),
    )

    # AML が rejected/review なら CP-8 bypass 検討
    cp8_entry_id: str | None = None
    if aml_result.outcome in ("rejected", "review"):
        bypassed, entry = maybe_bypass(
            donor_pid=donor_pid,
            amount_centi=req.amount_centi,
            program_id=req.program_id,
            aml_outcome=aml_result.outcome,
            aml_hits_count=len(aml_result.hits),
            aml_risk_score=aml_result.risk_score,
            ndrrmc_active=req.ndrrmc_active,
            emergency_lgu=req.emergency_lgu,
            store=cp8_store,
        )
        if bypassed:
            cp8_entry_id = entry.entry_id  # type: ignore
            # 進行: cp8_bypass として受理
        else:
            return DonationResult(
                donation_id=None, donor_pid=donor_pid,
                outcome="rejected", required_tier=required_tier,
                current_tier=donor.current_tier,
                aml_outcome=aml_result.outcome,
                aml_risk_score=aml_result.risk_score,
                cp8_bypass_entry_id=None,
                reason=aml_result.reason,
                received_at=time.time(),
            )

    # donation 受理
    don = Donation(
        id="DN-" + uuid.uuid4().hex[:16].upper(),
        donor_pid=donor_pid,
        program_id=req.program_id,
        amount_centi=req.amount_centi,
        underlying_token=req.underlying_token,
        tier_at_time=donor.current_tier,
        aml_outcome=aml_result.outcome,
        aml_risk_score=aml_result.risk_score,
        cp8_bypass_entry_id=cp8_entry_id,
        status="received",
    )
    db.add(don)
    donor.last_donation_at = datetime.utcnow()
    donor.total_donated_centi += req.amount_centi
    db.flush()

    return DonationResult(
        donation_id=don.id,
        donor_pid=donor_pid,
        outcome="cp8_bypass" if cp8_entry_id else "received",
        required_tier=required_tier,
        current_tier=donor.current_tier,
        aml_outcome=aml_result.outcome,
        aml_risk_score=aml_result.risk_score,
        cp8_bypass_entry_id=cp8_entry_id,
        reason="ok" if not cp8_entry_id else f"received via CP-8 (entry={cp8_entry_id})",
        received_at=time.time(),
    )


# ============================================================
# 寄付者 dashboard 用集計
# ============================================================


@dataclass
class DonorImpactSummary:
    """donor 視点の集約 (k=50 集約は別途、UI で適用)。"""
    donor_pid: str
    total_donated_centi: int
    donation_count: int
    programs: list[str]                 # 寄付した program_id 一覧
    total_received_status: int          # status="received" の合計
    total_cp8_bypass_status: int        # status="cp8_bypass" の合計


def get_donor_impact(db: Session, *, donor_pid: str
                      ) -> DonorImpactSummary | None:
    from sqlalchemy import select
    donor = db.get(Donor, donor_pid)
    if donor is None:
        return None
    donations = db.execute(
        select(Donation).where(Donation.donor_pid == donor_pid)
    ).scalars().all()
    programs = sorted({d.program_id for d in donations})
    received = sum(d.amount_centi for d in donations
                    if d.cp8_bypass_entry_id is None)
    bypassed = sum(d.amount_centi for d in donations
                    if d.cp8_bypass_entry_id is not None)
    return DonorImpactSummary(
        donor_pid=donor_pid,
        total_donated_centi=donor.total_donated_centi,
        donation_count=len(donations),
        programs=programs,
        total_received_status=received,
        total_cp8_bypass_status=bypassed,
    )
