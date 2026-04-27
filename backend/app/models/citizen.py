"""住民モデル。マイナンバーカード由来 4 情報を擬似 ID 化して保持する。"""

from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Citizen(Base):
    __tablename__ = "citizens"

    pid: Mapped[str] = mapped_column(String(64), primary_key=True)  # HMAC(maina_id)
    # マイナンバー本体は扱わない。本番環境では JPKI 経由で受領した署名のみ検証する。
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str] = mapped_column(String(256))
    ward: Mapped[str] = mapped_column(String(32), index=True)  # 例: "新宿区"
    dob: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(1))  # M/F/X
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
