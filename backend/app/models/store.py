"""加盟店 (リテール) モデル。"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    ward: Mapped[str] = mapped_column(String(32), index=True)
    # 戦略会議 #13 (R14): マニラ展開で MCC (Merchant Category Code, ISO 18245)
    # と QR Ph 加盟店 ID を保持。JP は両方 None 許容で従来通り動く。
    mcc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qr_ph_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
