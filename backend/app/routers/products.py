"""JAN コードベースの商品マスタ。加盟店登録もここで提供。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.product import Product
from app.models.store import Store


router = APIRouter(tags=["catalog"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


class ProductIn(BaseModel):
    jan: str
    name: str
    category: str
    price_jpy: int


@router.post("/products", response_model=ProductIn, status_code=201)
def upsert_product(payload: ProductIn, db: Session = Depends(_db)) -> ProductIn:
    if len(payload.jan) not in (8, 12, 13):
        raise HTTPException(400, "JAN must be 8/12/13 digits")
    p = db.get(Product, payload.jan)
    if p is None:
        p = Product(**payload.model_dump())
        db.add(p)
    else:
        p.name = payload.name
        p.category = payload.category
        p.price_jpy = payload.price_jpy
    db.flush()
    return payload


# 注意: 静的パス (/products/categories) は動的パス (/products/{jan}) よりも先に
# 登録しないと、{jan} に "categories" が吸われてしまう。

# UI と共有する大分類ラベル。サーバ側でも保持して JSON で返す。
CATEGORY_PARENTS = {
    "appliance": {"label": "家電",     "icon": "🔌"},
    "food":      {"label": "食品",     "icon": "🍙"},
    "goods":     {"label": "日用品",   "icon": "🧴"},
    "med":       {"label": "医薬品",   "icon": "💊"},
    "disaster":  {"label": "防災",     "icon": "🛟"},
    "care":      {"label": "介護",     "icon": "🧓"},
    "school":    {"label": "学用品",   "icon": "🎒"},
}
CATEGORY_LABELS = {
    "appliance.air_conditioner": "エアコン",
    "appliance.refrigerator":    "冷蔵庫",
    "appliance.light":           "照明",
    "appliance.washer":          "洗濯機",
    "appliance.kitchen":         "キッチン家電",
    "food.baby":                 "乳幼児食品",
    "food.daily":                "日常食品",
    "goods.baby":                "育児用品",
    "med.rx":                    "処方薬",
    "med.otc":                   "市販薬",
    "med.supplement":            "サプリ・栄養食品",
    "disaster.water":            "保存水",
    "disaster.food":             "非常食",
    "disaster.gear":             "防災用品",
    "care.adult":                "介護消耗品",
    "care.equipment":            "介護用品",
    "school.stationery":         "文房具",
    "school.bag":                "ランドセル",
}


def _parent_of(category: str) -> str:
    return (category or "").split(".", 1)[0]


@router.get("/products/categories")
def list_categories(db: Session = Depends(_db)):
    """カテゴリ一覧 + 件数 + 日本語ラベル + 大分類。"""
    rows = db.execute(
        select(Product.category, func.count(Product.jan))
        .group_by(Product.category)
        .order_by(Product.category)
    ).all()
    out = []
    for c, n in rows:
        parent = _parent_of(c)
        meta = CATEGORY_PARENTS.get(parent, {"label": parent, "icon": "📦"})
        out.append({
            "category": c,
            "count": n,
            "label": CATEGORY_LABELS.get(c, c.split(".", 1)[-1]),
            "parent": parent,
            "parent_label": meta["label"],
            "parent_icon": meta["icon"],
        })
    return out


@router.get("/products")
def list_products(category: str | None = None, db: Session = Depends(_db)):
    q = select(Product)
    if category:
        q = q.where(Product.category == category)
    rows = db.execute(q).scalars().all()
    return [
        {"jan": r.jan, "name": r.name, "category": r.category, "price_jpy": r.price_jpy}
        for r in rows
    ]


@router.get("/products/{jan}", response_model=ProductIn)
def get_product(jan: str, db: Session = Depends(_db)) -> ProductIn:
    p = db.get(Product, jan)
    if p is None:
        raise HTTPException(404, "product not found")
    return ProductIn(jan=p.jan, name=p.name, category=p.category, price_jpy=p.price_jpy)


class StoreIn(BaseModel):
    id: str
    name: str
    ward: str


@router.post("/stores", response_model=StoreIn, status_code=201)
def upsert_store(payload: StoreIn, db: Session = Depends(_db)) -> StoreIn:
    s = db.get(Store, payload.id)
    if s is None:
        s = Store(**payload.model_dump())
        db.add(s)
    else:
        s.name = payload.name
        s.ward = payload.ward
    db.flush()
    return payload


@router.get("/stores")
def list_stores(db: Session = Depends(_db)):
    rows = db.execute(select(Store)).scalars().all()
    return [{"id": r.id, "name": r.name, "ward": r.ward} for r in rows]
