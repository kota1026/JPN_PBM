"""JPYC 残高ミラー (オンチェーン JPYC が更新するであろう値の MVP 版)。"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Wallet(Base):
    """住民・加盟店・東京都トレジャリーの JPYC 残高。

    owner_kind は "citizen" / "store" / "treasury"。
    """

    __tablename__ = "wallets"

    owner_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    jpyc_balance: Mapped[int] = mapped_column(Integer, default=0)
