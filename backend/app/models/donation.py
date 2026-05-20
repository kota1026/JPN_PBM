"""寄付 (donation) モデル ─ DP-5 (戦略会議 #19 採択)。

1 件の寄付 transaction を表す。
AML bypass された寄付は cp8_bypass_entry_id にリンク。
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # UUID
    donor_pid: Mapped[str] = mapped_column(String(64), index=True)
    program_id: Mapped[str] = mapped_column(String(64), index=True)
    amount_centi: Mapped[int] = mapped_column(Integer)
    underlying_token: Mapped[str] = mapped_column(String(16))  # JPYC/PHPC/USDC
    tier_at_time: Mapped[int] = mapped_column(Integer)         # KycTier at donation
    aml_outcome: Mapped[str] = mapped_column(String(32))       # cleared/review/rejected
    aml_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    cp8_bypass_entry_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime,
                                                    server_default=func.now())
    status: Mapped[str] = mapped_column(String(16), default="received")
    # received → confirmed → reconciled (impact 集計済) → ... or → clawback
