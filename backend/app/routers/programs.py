"""東京都が助成金プログラムを CRUD し、住民へ PBM を発行するエンドポイント。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.models.pbm import PBMToken
from app.models.program import Program
from app.services import jpyc
from app.services.eligibility import check as eligibility_check
from app.services.fiscal_budget import (
    budget_for_year,
    fiscal_year_of,
    remaining_for_year,
    total_multi_year_budget,
    validate_fiscal_year_budgets,
)
from app.services.pbm import issue as issue_pbm, revoke_program


router = APIRouter(prefix="/programs", tags=["programs"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


class ProgramIn(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    budget_jpy: int
    subsidy_bps: int
    per_citizen_cap_jpy: int
    start_at: datetime
    end_at: datetime
    eligibility: dict[str, Any] = {}
    eligible_jans: list[str] = []
    eligible_categories: list[str] = []
    excluded_jans: list[str] = []
    approved_stores: list[str] = []
    # 多年度予算 (戦略会議 #4 採択 #11)。空 dict なら budget_jpy を当年度予算扱い
    fiscal_year_budgets: dict[str, int] = {}


class ProgramOut(ProgramIn):
    id: str
    spent_jpy: int
    revoked: bool


@router.post("", response_model=ProgramOut, status_code=201)
def create_program(payload: ProgramIn, db: Session = Depends(_db)) -> ProgramOut:
    if payload.end_at <= payload.start_at:
        raise HTTPException(400, "end_at must be after start_at")
    if not (0 < payload.subsidy_bps <= 10_000):
        raise HTTPException(400, "subsidy_bps must be in (0, 10000]")
    if payload.budget_jpy <= 0:
        raise HTTPException(400, "budget_jpy must be positive")

    fyb_ok, fyb_why = validate_fiscal_year_budgets(
        fiscal_year_budgets=payload.fiscal_year_budgets,
        fallback_budget_jpy=payload.budget_jpy,
    )
    if not fyb_ok:
        raise HTTPException(400, f"fiscal_year_budgets: {fyb_why}")
    if payload.fiscal_year_budgets:
        total_fyb = sum(int(v) for v in payload.fiscal_year_budgets.values())
        if total_fyb != payload.budget_jpy:
            raise HTTPException(
                400,
                f"sum(fiscal_year_budgets)={total_fyb} != budget_jpy={payload.budget_jpy}",
            )

    pid = payload.id or f"prog-{uuid.uuid4().hex[:8]}"
    if db.get(Program, pid):
        raise HTTPException(409, "program id exists")

    # 東京都トレジャリーから budget をロック (= 自分自身に保持し、spent が増えるたびに store へ流れる)
    treasury_balance = jpyc.balance_of(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND)
    if treasury_balance < payload.budget_jpy:
        raise HTTPException(
            400,
            f"トレジャリー残高不足: 必要 {payload.budget_jpy} JPYC, 残高 {treasury_balance} JPYC",
        )

    p = Program(
        id=pid,
        name=payload.name,
        description=payload.description,
        budget_jpy=payload.budget_jpy,
        subsidy_bps=payload.subsidy_bps,
        per_citizen_cap_jpy=payload.per_citizen_cap_jpy,
        start_at=payload.start_at,
        end_at=payload.end_at,
        eligibility=payload.eligibility,
        eligible_jans=payload.eligible_jans,
        eligible_categories=payload.eligible_categories,
        excluded_jans=payload.excluded_jans,
        approved_stores=payload.approved_stores,
        fiscal_year_budgets=payload.fiscal_year_budgets or {},
    )
    db.add(p)
    db.flush()
    return _to_out(p)


@router.get("", response_model=list[ProgramOut])
def list_programs(db: Session = Depends(_db)) -> list[ProgramOut]:
    rows = db.execute(select(Program)).scalars().all()
    return [_to_out(p) for p in rows]


@router.get("/{program_id}", response_model=ProgramOut)
def get_program(program_id: str, db: Session = Depends(_db)) -> ProgramOut:
    p = db.get(Program, program_id)
    if p is None:
        raise HTTPException(404, "program not found")
    return _to_out(p)


@router.delete("/{program_id}")
def delete_program(program_id: str, db: Session = Depends(_db)):
    p = db.get(Program, program_id)
    if p is None:
        raise HTTPException(404, "program not found")
    refund = revoke_program(db, p)
    return {"ok": True, "refund_jpy": refund}


@router.get("/{program_id}/fiscal-budget")
def get_fiscal_budget(program_id: str, year: str | None = None, db: Session = Depends(_db)):
    """多年度予算の状況 (戦略会議 #4 採択 #11)。"""
    p = db.get(Program, program_id)
    if p is None:
        raise HTTPException(404, "program not found")
    fy = year or fiscal_year_of()
    return {
        "program_id": program_id,
        "fiscal_year": fy,
        "fiscal_year_budgets": p.fiscal_year_budgets or {},
        "current_year_budget_jpy": budget_for_year(p, fy),
        "current_year_remaining_jpy": remaining_for_year(p, fy),
        "total_multi_year_budget_jpy": total_multi_year_budget(p),
        "spent_jpy": p.spent_jpy,
        "is_multi_year": bool(p.fiscal_year_budgets),
    }


@router.get("/eligible/{pid}", response_model=list[ProgramOut])
def list_eligible(pid: str, db: Session = Depends(_db)) -> list[ProgramOut]:
    citizen = db.get(Citizen, pid)
    if citizen is None:
        raise HTTPException(404, "citizen not found")
    out: list[ProgramOut] = []
    for p in db.execute(select(Program).where(Program.revoked.is_(False))).scalars().all():
        now = datetime.utcnow()
        if not (p.start_at <= now <= p.end_at):
            continue
        if eligibility_check(citizen, p).ok:
            out.append(_to_out(p))
    return out


class IssueIn(BaseModel):
    citizen_pid: str


class IssueOut(BaseModel):
    pbm_id: str
    program_id: str
    holder_pid: str
    remaining_jpy: int
    expires_at: datetime


@router.post("/{program_id}/issue", response_model=IssueOut)
def issue(program_id: str, payload: IssueIn, db: Session = Depends(_db)) -> IssueOut:
    p = db.get(Program, program_id)
    if p is None:
        raise HTTPException(404, "program not found")
    c = db.get(Citizen, payload.citizen_pid)
    if c is None:
        raise HTTPException(404, "citizen not found")
    try:
        token: PBMToken = issue_pbm(db, p, c)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return IssueOut(
        pbm_id=token.id,
        program_id=token.program_id,
        holder_pid=token.holder_pid,
        remaining_jpy=token.remaining_jpy,
        expires_at=token.expires_at,
    )


def _to_out(p: Program) -> ProgramOut:
    return ProgramOut(
        id=p.id,
        name=p.name,
        description=p.description,
        budget_jpy=p.budget_jpy,
        spent_jpy=p.spent_jpy,
        subsidy_bps=p.subsidy_bps,
        per_citizen_cap_jpy=p.per_citizen_cap_jpy,
        start_at=p.start_at,
        end_at=p.end_at,
        eligibility=p.eligibility or {},
        eligible_jans=p.eligible_jans or [],
        eligible_categories=p.eligible_categories or [],
        excluded_jans=p.excluded_jans or [],
        approved_stores=p.approved_stores or [],
        fiscal_year_budgets=p.fiscal_year_budgets or {},
        revoked=p.revoked,
    )
