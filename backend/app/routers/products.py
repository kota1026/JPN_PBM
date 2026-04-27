"""JAN コードベースの商品マスタ。加盟店登録もここで提供。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
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


@router.get("/products/{jan}", response_model=ProductIn)
def get_product(jan: str, db: Session = Depends(_db)) -> ProductIn:
    p = db.get(Product, jan)
    if p is None:
        raise HTTPException(404, "product not found")
    return ProductIn(jan=p.jan, name=p.name, category=p.category, price_jpy=p.price_jpy)


@router.get("/products")
def list_products(db: Session = Depends(_db)):
    rows = db.execute(select(Product)).scalars().all()
    return [
        {"jan": r.jan, "name": r.name, "category": r.category, "price_jpy": r.price_jpy}
        for r in rows
    ]


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
