"""マイナンバーカード模擬認証。

本番では公的個人認証 (JPKI) で署名された 4 情報の VC/JWT を受け取り検証する。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.services.privacy import pseudonymize


router = APIRouter(prefix="/auth/myna", tags=["auth"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


class MynaLoginIn(BaseModel):
    """マイナンバーカードから取得した 4 情報 + 個人番号 (擬似)。"""

    maina_id: str = Field(..., description="マイナンバー (本番では使用せず JPKI 署名のみ)")
    name: str
    address: str
    ward: str = Field(..., description="区市町村 例: '新宿区'")
    dob: date
    gender: Literal["M", "F", "X"]


class MynaLoginOut(BaseModel):
    pid: str
    issued_at: datetime
    expires_at: datetime


@router.post("/login", response_model=MynaLoginOut)
def login(payload: MynaLoginIn, db: Session = Depends(_db)) -> MynaLoginOut:
    pid = pseudonymize(payload.maina_id)
    citizen = db.get(Citizen, pid)
    if citizen is None:
        citizen = Citizen(
            pid=pid,
            name=payload.name,
            address=payload.address,
            ward=payload.ward,
            dob=payload.dob,
            gender=payload.gender,
        )
        db.add(citizen)
    else:
        # 引っ越し等で住所が更新された場合は反映
        citizen.name = payload.name
        citizen.address = payload.address
        citizen.ward = payload.ward
    db.flush()
    now = datetime.utcnow()
    return MynaLoginOut(pid=pid, issued_at=now, expires_at=now + timedelta(hours=1))


@router.get("/me/{pid}")
def me(pid: str, db: Session = Depends(_db)):
    c = db.get(Citizen, pid)
    if c is None:
        raise HTTPException(404, "citizen not found")
    return {
        "pid": c.pid,
        "name": c.name,
        "ward": c.ward,
        "dob": c.dob,
        "gender": c.gender,
    }
