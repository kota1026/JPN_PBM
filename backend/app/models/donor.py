"""寄付者 (donor) モデル ─ DP-5 (戦略会議 #19 採択)。

KYC tier + AML 状態をモデルに直接保持しないことに注意。
- KYC: kyc_adapter が verification_id を返す → ここに保存
- AML: aml_screening が独立に screen → audit log は別 table (cp8_emergency_bypass)

donor_pid は HMAC(email) or HMAC(legal_entity_id) で生成。raw 情報は保存しない。
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Donor(Base):
    __tablename__ = "donors"

    pid: Mapped[str] = mapped_column(String(64), primary_key=True)  # HMAC PID
    display_name_hash: Mapped[str] = mapped_column(String(64))      # HMAC for display
    country: Mapped[str] = mapped_column(String(2), index=True)     # ISO-2
    current_tier: Mapped[int] = mapped_column(Integer, default=0)    # KycTier
    kyc_verification_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)
    is_legal_entity: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                  server_default=func.now())
    last_donation_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)
    total_donated_centi: Mapped[int] = mapped_column(Integer, default=0)
