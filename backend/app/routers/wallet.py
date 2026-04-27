"""住民・加盟店・東京都トレジャリーの JPYC 残高 + PBM トークン参照。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.models.pbm import PBMToken
from app.services import jpyc

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


class TopupIn(BaseModel):
    amount_jpy: int


@router.get("/citizen/{pid}")
def citizen_wallet(pid: str, db: Session = Depends(_db)):
    c = db.get(Citizen, pid)
    if c is None:
        raise HTTPException(404, "citizen not found")
    pbms = db.execute(
        select(PBMToken).where(
            PBMToken.holder_pid == pid,
            PBMToken.status == "ISSUED",
        )
    ).scalars().all()
    return {
        "pid": pid,
        "jpyc_balance": jpyc.balance_of(db, pid, "citizen"),
        "pbm_tokens": [
            {
                "id": t.id,
                "program_id": t.program_id,
                "remaining_jpy": t.remaining_jpy,
                "status": t.status,
                "expires_at": t.expires_at,
            }
            for t in pbms
        ],
    }


@router.get("/store/{store_id}")
def store_wallet(store_id: str, db: Session = Depends(_db)):
    return {
        "store_id": store_id,
        "jpyc_balance": jpyc.balance_of(db, store_id, "store"),
    }


@router.get("/treasury")
def treasury_wallet(db: Session = Depends(_db)):
    return {"jpyc_balance": jpyc.balance_of(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND)}


@router.post("/citizen/{pid}/topup")
def topup_citizen(pid: str, payload: TopupIn, db: Session = Depends(_db)):
    if db.get(Citizen, pid) is None:
        raise HTTPException(404, "citizen not found")
    bal = jpyc.mint(db, pid, "citizen", payload.amount_jpy)
    return {"jpyc_balance": bal}


@router.post("/treasury/topup")
def topup_treasury(payload: TopupIn, db: Session = Depends(_db)):
    bal = jpyc.mint(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND, payload.amount_jpy)
    return {"jpyc_balance": bal}
