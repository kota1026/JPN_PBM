"""EBPM 集計エンドポイント。個票は返さず集計値のみ。k 未満セルは丸める。"""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ebpm import EBPMEvent
from app.models.program import Program

router = APIRouter(prefix="/ebpm", tags=["ebpm"])

K_ANON = 5


def _db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary")
def summary(program_id: str | None = None, db: Session = Depends(_db)):
    q = select(
        EBPMEvent.program_id,
        func.count(EBPMEvent.id),
        func.count(func.distinct(EBPMEvent.citizen_pid)),
        func.coalesce(func.sum(EBPMEvent.total_jpy), 0),
        func.coalesce(func.sum(EBPMEvent.subsidy_jpy), 0),
        func.coalesce(func.sum(EBPMEvent.citizen_pay_jpy), 0),
    ).group_by(EBPMEvent.program_id)
    if program_id:
        q = q.where(EBPMEvent.program_id == program_id)
    rows = db.execute(q).all()
    out = []
    for pid, cnt, uniq, total, subsidy, pay in rows:
        program = db.get(Program, pid) if pid else None
        budget = program.budget_jpy if program else None
        leverage = (pay / subsidy) if subsidy else None
        out.append(
            {
                "program_id": pid or None,
                "program_name": program.name if program else None,
                "tx_count": cnt,
                "unique_citizens": uniq,
                "total_jpy": total,
                "subsidy_jpy": subsidy,
                "citizen_pay_jpy": pay,
                "budget_jpy": budget,
                "budget_remaining_jpy": (budget - subsidy) if budget else None,
                "leverage_pay_per_subsidy": leverage,
            }
        )
    return out


Dim = Literal["age_band", "gender", "ward", "category", "store_ward", "date"]


@router.get("/breakdown")
def breakdown(
    dim: Dim = Query(..., description="集計軸"),
    program_id: str | None = None,
    db: Session = Depends(_db),
):
    """指定軸で集計。k-匿名性 (k=5) を満たさないセルは '-' に丸める。"""
    if dim == "date":
        col = func.strftime("%Y-%m-%d", EBPMEvent.ts)
    else:
        col = getattr(EBPMEvent, dim)

    q = select(
        col,
        func.count(EBPMEvent.id),
        func.count(func.distinct(EBPMEvent.citizen_pid)),
        func.coalesce(func.sum(EBPMEvent.total_jpy), 0),
        func.coalesce(func.sum(EBPMEvent.subsidy_jpy), 0),
    ).group_by(col).order_by(col)
    if program_id:
        q = q.where(EBPMEvent.program_id == program_id)

    rows = db.execute(q).all()
    out = []
    for key, cnt, uniq, total, subsidy in rows:
        if uniq < K_ANON:
            out.append({"key": str(key), "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-"})
        else:
            out.append({"key": str(key), "tx_count": cnt, "unique_citizens": uniq, "total_jpy": total, "subsidy_jpy": subsidy})
    return out


@router.get("/programs/{program_id}/uptake")
def program_uptake(program_id: str, db: Session = Depends(_db)):
    """プログラム単位の利用率指標。"""
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(404, "program not found")
    row = db.execute(
        select(
            func.count(EBPMEvent.id),
            func.count(func.distinct(EBPMEvent.citizen_pid)),
            func.coalesce(func.sum(EBPMEvent.subsidy_jpy), 0),
        ).where(EBPMEvent.program_id == program_id)
    ).one()
    cnt, uniq, subsidy = row
    return {
        "program_id": program_id,
        "name": program.name,
        "budget_jpy": program.budget_jpy,
        "spent_jpy": program.spent_jpy,
        "consumption_rate": (program.spent_jpy / program.budget_jpy) if program.budget_jpy else 0.0,
        "tx_count": cnt,
        "unique_citizens": uniq,
        "subsidy_jpy": subsidy,
    }
