"""マイナポータル OAuth 同意ログ (戦略会議 #2 採択 #10)。

個人情報保護法 第 27 条 (第三者提供の制限) 対応。
住民が「都が JPYC 給付に必要な範囲で 4 情報を取得する」ことを同意した記録を
監査可能な形で永続化する。

【保存項目の決め方】
- 同意取得時点の **同意文面ハッシュ** (sha256) を必ず記録 (改ざん検出)。
- pid は HMAC 化済み (生のマイナンバーは絶対に保存しない、CP-2)。
- scope は最小権限。例: ["family_register.basic_4", "address.ward"]
- revoked_at は同意撤回時に NOT NULL になり、それ以降の照会で参照される。
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pid: Mapped[str] = mapped_column(String(64), index=True)

    # 同意取得時のメタ
    program_id: Mapped[str] = mapped_column(String(32), index=True)
    consent_text_sha256: Mapped[str] = mapped_column(String(64))
    scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    granted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 撤回
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoke_reason: Mapped[str] = mapped_column(String(256), default="")

    # 監査
    source_ip_hash: Mapped[str] = mapped_column(String(64), default="")  # 個情法 ログ要件
    user_agent_hash: Mapped[str] = mapped_column(String(64), default="")
