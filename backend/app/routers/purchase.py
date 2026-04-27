"""加盟店 POS が JAN コードと住民 PID を投げてくる購入エンドポイント。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.models.product import Product
from app.models.store import Store
from app.services.pbm import spend


router = APIRouter(prefix="/purchase", tags=["purchase"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


class PurchaseIn(BaseModel):
    citizen_pid: str
    store_id: str
    jan: str
    qty: int = Field(1, gt=0)


class PurchaseOut(BaseModel):
    ok: bool
    reason: str
    total_jpy: int
    subsidy_jpy: int
    citizen_pay_jpy: int


@router.post("", response_model=PurchaseOut)
def purchase(payload: PurchaseIn, db: Session = Depends(_db)) -> PurchaseOut:
    citizen = db.get(Citizen, payload.citizen_pid)
    if citizen is None:
        raise HTTPException(404, "citizen not found")
    store = db.get(Store, payload.store_id)
    if store is None:
        raise HTTPException(404, "store not found")
    product = db.get(Product, payload.jan)
    if product is None:
        raise HTTPException(404, "product not found")

    res = spend(db, citizen=citizen, store=store, product=product, qty=payload.qty)
    if not res.ok:
        raise HTTPException(400, res.reason)
    return PurchaseOut(
        ok=res.ok,
        reason=res.reason,
        total_jpy=res.total_jpy,
        subsidy_jpy=res.subsidy_jpy,
        citizen_pay_jpy=res.citizen_pay_jpy,
    )
