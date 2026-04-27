"""PBM トークン (= 助成金枠) と消費履歴。"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PBMToken(Base):
    __tablename__ = "pbm_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(32), ForeignKey("programs.id"), index=True)
    holder_pid: Mapped[str] = mapped_column(String(64), ForeignKey("citizens.pid"), index=True)

    # 当該住民が当該プログラムでまだ使える助成金枠 (JPY)
    remaining_jpy: Mapped[int] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(16), default="ISSUED")
    # ISSUED / EXHAUSTED / EXPIRED / REVOKED

    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
