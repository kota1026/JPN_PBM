"""JAN コードベースの商品マスタ。"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    jan: Mapped[str] = mapped_column(String(13), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32), index=True)
    # 例: "appliance.air_conditioner", "food.baby", "med.supplement"
    price_jpy: Mapped[int] = mapped_column(Integer)
