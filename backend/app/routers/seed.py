"""デモ用シードデータ投入エンドポイント。

`POST /seed/load` を叩くと `seed/*.json` を読み込み、
住民・加盟店・商品・プログラム・トレジャリーへのデモ JPYC ミントまでを一括登録する。
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.models.product import Product
from app.models.program import Program
from app.models.store import Store
from app.services import jpyc
from app.services.privacy import pseudonymize


router = APIRouter(prefix="/seed", tags=["seed"])

SEED_DIR = pathlib.Path(__file__).resolve().parents[3] / "seed"


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


@router.post("/load")
def load(db: Session = Depends(_db)):
    # トレジャリーへ大きめの JPYC をミント
    jpyc.mint(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND, 100_000_000)

    # 商品
    products = json.loads((SEED_DIR / "products.json").read_text(encoding="utf-8"))
    for pr in products:
        if db.get(Product, pr["jan"]):
            continue
        db.add(Product(**pr))

    # 加盟店
    stores = json.loads((SEED_DIR / "stores.json").read_text(encoding="utf-8"))
    for s in stores:
        if db.get(Store, s["id"]):
            continue
        db.add(Store(**s))

    # 住民 (4 情報) → pid 化
    citizens = json.loads((SEED_DIR / "citizens.json").read_text(encoding="utf-8"))
    pid_map: dict[str, str] = {}
    for c in citizens:
        pid = pseudonymize(c["maina_id"])
        pid_map[c["maina_id"]] = pid
        if db.get(Citizen, pid):
            continue
        db.add(
            Citizen(
                pid=pid,
                name=c["name"],
                address=c["address"],
                ward=c["ward"],
                dob=datetime.fromisoformat(c["dob"]).date(),
                gender=c["gender"],
            )
        )
        # 自己負担用にデモ JPYC を配る
        jpyc.mint(db, pid, "citizen", 50_000)

    # プログラム
    programs = json.loads((SEED_DIR / "programs.json").read_text(encoding="utf-8"))
    for p in programs:
        if db.get(Program, p["id"]):
            continue
        db.add(
            Program(
                id=p["id"],
                name=p["name"],
                description=p.get("description", ""),
                budget_jpy=p["budget_jpy"],
                subsidy_bps=p["subsidy_bps"],
                per_citizen_cap_jpy=p["per_citizen_cap_jpy"],
                start_at=datetime.fromisoformat(p["start_at"]),
                end_at=datetime.fromisoformat(p["end_at"]),
                eligibility=p.get("eligibility", {}),
                eligible_jans=p.get("eligible_jans", []),
                approved_stores=p.get("approved_stores", []),
            )
        )

    return {"ok": True, "pid_map": pid_map}
