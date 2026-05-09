"""デモ用シードデータ投入エンドポイント。

`POST /seed/load` を叩くと `seed/*.json` を読み込み、
住民・加盟店・商品・プログラム・トレジャリーへのデモ JPYC ミントまでを一括登録する。

【戦略会議 #13 採択 T1: multi-locale 対応】
`POST /seed/load?locale=ph` で `seed/ph/*.json` を読み込んで PH 4Ps シードを投入する。

- locale='jp' (default): 既存パス (`seed/citizens.json` 等) を読む。互換維持。
- locale='ph': `seed/ph/citizens.json` 等を読む。PSN HMAC pid 化、PHP centavos
  → JPY 整数 互換 (内部単位は「最小単位の整数」で透過)。

JP / PH の seed フィールド差分は本ルータが吸収する。データモデル (Citizen/Store/Program)
は同一スキーマで両国を保持。country 列は持たない (ward / store.id の prefix で区別)。
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.citizen import Citizen
from app.models.product import Product
from app.models.program import Program
from app.models.store import Store
from app.services import jpyc
from app.services.privacy import pseudonymize


router = APIRouter(prefix="/seed", tags=["seed"])

SEED_ROOT = pathlib.Path(__file__).resolve().parents[3] / "seed"


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


# ----------------------------- locale 別 fixture 読込 -----------------------------


def _seed_dir_for(locale: str) -> pathlib.Path:
    if locale == "jp":
        return SEED_ROOT
    if locale == "ph":
        return SEED_ROOT / "ph"
    raise HTTPException(400, f"unknown locale: {locale} (expected jp|ph)")


def _load_jp(db: Session) -> dict:
    """既存 JP seed loader。挙動は Round 13 までと完全互換。"""
    seed_dir = _seed_dir_for("jp")

    jpyc.mint(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND, 100_000_000)

    products = json.loads((seed_dir / "products.json").read_text(encoding="utf-8"))
    product_fields = {"jan", "name", "category", "price_jpy"}
    for pr in products:
        if db.get(Product, pr["jan"]):
            continue
        db.add(Product(**{k: v for k, v in pr.items() if k in product_fields}))

    stores = json.loads((seed_dir / "stores.json").read_text(encoding="utf-8"))
    store_fields = {"id", "name", "ward", "mcc", "qr_ph_id"}
    for s in stores:
        if db.get(Store, s["id"]):
            continue
        db.add(Store(**{k: v for k, v in s.items() if k in store_fields}))

    citizens = json.loads((seed_dir / "citizens.json").read_text(encoding="utf-8"))
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
        jpyc.mint(db, pid, "citizen", 50_000)

    programs = json.loads((seed_dir / "programs.json").read_text(encoding="utf-8"))
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
                eligible_categories=p.get("eligible_categories", []),
                excluded_jans=p.get("excluded_jans", []),
                approved_stores=p.get("approved_stores", []),
            )
        )

    return {"ok": True, "locale": "jp", "pid_map": pid_map,
            "loaded": {"citizens": len(citizens), "products": len(products),
                       "stores": len(stores), "programs": len(programs)}}


def _load_ph(db: Session) -> dict:
    """PH 4Ps seed loader。

    フィールド名のマッピング (PH → DB internal):
    - psn → maina_id (HMAC 元)
    - city → ward (字面違いだが意味は等価; モデルの ward 列に詰める)
    - price_centavos → price_jpy (両者「最小単位の整数」)
    - budget_centavos → budget_jpy
    - per_citizen_cap_centavos → per_citizen_cap_jpy
    """
    seed_dir = _seed_dir_for("ph")

    products = json.loads((seed_dir / "products.json").read_text(encoding="utf-8"))
    for pr in products:
        if db.get(Product, pr["jan"]):
            continue
        db.add(Product(
            jan=pr["jan"],
            name=pr["name"],
            category=pr.get("category", ""),
            price_jpy=pr["price_centavos"],   # 最小単位の整数として保持
        ))

    stores = json.loads((seed_dir / "stores.json").read_text(encoding="utf-8"))
    for s in stores:
        if db.get(Store, s["id"]):
            continue
        db.add(Store(
            id=s["id"],
            name=s["name"],
            ward=s["city"],   # PH では city を ward 列に保持
            mcc=s.get("mcc"),
            qr_ph_id=s.get("qr_ph_id"),
        ))

    # 戦略会議 #17 採択 PH-7 (R19): 世帯単位 voucher 対応
    from app.services.household import derive_household_id  # noqa: WPS433
    citizens = json.loads((seed_dir / "citizens.json").read_text(encoding="utf-8"))
    pid_map: dict[str, str] = {}
    for c in citizens:
        pid = pseudonymize(c["psn"])
        pid_map[c["psn"]] = pid
        # household_psn が seed に含まれていれば world_id を派生
        # (含まれない古い seed との後方互換のため None 許容)
        household_id = None
        if c.get("household_psn"):
            household_id = derive_household_id(primary_psn_or_maina=c["household_psn"])
        if db.get(Citizen, pid):
            continue
        db.add(Citizen(
            pid=pid,
            name=c["name"],
            address=c["address"],
            ward=c["city"],
            dob=datetime.fromisoformat(c["dob"]).date(),
            gender=c["gender"],
            household_id=household_id,
        ))
        jpyc.mint(db, pid, "citizen", 50_000)  # PHPC とラベル分けしないが量は同じ

    programs = json.loads((seed_dir / "programs.json").read_text(encoding="utf-8"))
    for p in programs:
        if db.get(Program, p["id"]):
            continue
        db.add(Program(
            id=p["id"],
            name=p["name"],
            description=p.get("description", ""),
            budget_jpy=p["budget_centavos"],
            subsidy_bps=p["subsidy_bps"],
            per_citizen_cap_jpy=p["per_citizen_cap_centavos"],
            start_at=datetime.fromisoformat(p["start_at"]),
            end_at=datetime.fromisoformat(p["end_at"]),
            eligibility=p.get("eligibility", {}),
            eligible_jans=p.get("eligible_jans", []),
            eligible_categories=p.get("eligible_categories", []),
            excluded_jans=p.get("excluded_jans", []),
            approved_stores=p.get("approved_stores", []),
        ))

    return {"ok": True, "locale": "ph", "pid_map": pid_map,
            "loaded": {"citizens": len(citizens), "products": len(products),
                       "stores": len(stores), "programs": len(programs)}}


@router.post("/load")
def load(
    db: Session = Depends(_db),
    locale: str = Query("jp", description="jp (default, Tokyo) or ph (Manila / 4Ps)"),
):
    if locale == "jp":
        return _load_jp(db)
    if locale == "ph":
        return _load_ph(db)
    raise HTTPException(400, f"unknown locale: {locale}")
