"""東京都が定義する助成金プログラム。"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(String(1024), default="")

    # 予算 (JPYC = JPY 1:1)
    budget_jpy: Mapped[int] = mapped_column(Integer)
    spent_jpy: Mapped[int] = mapped_column(Integer, default=0)

    # 助成率 (basis points: 3000 = 30%)
    subsidy_bps: Mapped[int] = mapped_column(Integer)

    # 1 住民あたりの累計上限
    per_citizen_cap_jpy: Mapped[int] = mapped_column(Integer)

    # 期間
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)

    # 受給資格条件 (JSON で柔軟に表現)
    # 例: {"wards": ["新宿区","渋谷区",...], "min_age": 65, "max_age": null,
    #      "genders": null, "child_age_max": null}
    eligibility: Mapped[dict] = mapped_column(JSON, default=dict)

    # 対象 JAN リスト (明示的な追加)
    eligible_jans: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 対象カテゴリ (このカテゴリの全 JAN を一括で対象にする)
    eligible_categories: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 非対象 JAN (カテゴリ一括対象から除外したい例外)
    excluded_jans: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 認定加盟店リスト
    approved_stores: Mapped[list[str]] = mapped_column(JSON, default=list)

    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 多年度予算条例化 (戦略会議 #4 採択 #11)。
    # 形式: {"2026": 60000000, "2027": 70000000, "2028": 80000000}
    # 空 dict のときは budget_jpy を当年度予算として扱う (後方互換)。
    fiscal_year_budgets: Mapped[dict] = mapped_column(JSON, default=dict)
