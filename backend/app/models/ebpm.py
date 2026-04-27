"""EBPM 集計用の取引イベント。匿名化属性のみを保持。"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EBPMEvent(Base):
    __tablename__ = "ebpm_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(32), ForeignKey("programs.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    jan: Mapped[str] = mapped_column(String(13), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    total_jpy: Mapped[int] = mapped_column(Integer)
    subsidy_jpy: Mapped[int] = mapped_column(Integer)
    citizen_pay_jpy: Mapped[int] = mapped_column(Integer)

    # 匿名化属性
    citizen_pid: Mapped[str] = mapped_column(String(64), index=True)
    age_band: Mapped[str] = mapped_column(String(8))  # "60-69" など
    gender: Mapped[str] = mapped_column(String(1))
    ward: Mapped[str] = mapped_column(String(32), index=True)

    store_id: Mapped[str] = mapped_column(String(32), index=True)
    store_ward: Mapped[str] = mapped_column(String(32), index=True)
