"""CP-1〜CP-6 違反検出ログ (戦略会議 #3 採択 #8)。

Purpose Guardian の責務を可視化するため、guard_spend / guard_offline_redemption が
deny した瞬間に「いつ・どの CP コードで・どの program で・どの店舗で」落ちたかを
記録する。EBPM ダッシュボードから集計表示する。

CP-2 観点: 個票は記録しない。pid は短縮 (8 文字 prefix) でのみ保存。
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CPViolation(Base):
    __tablename__ = "cp_violations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), index=True)  # 例: "CP-1.purpose_mismatch"
    why: Mapped[str] = mapped_column(String(256))

    program_id: Mapped[str] = mapped_column(String(32), index=True, default="")
    store_id: Mapped[str] = mapped_column(String(32), index=True, default="")
    pid_prefix: Mapped[str] = mapped_column(String(8), default="")  # CP-2: 8 文字までしか保存

    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
