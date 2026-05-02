"""多年度予算条例化 (戦略会議 #4 採択 #11)。

CFO 提案 + Red Team 修正案: 既存 `program.budget_jpy` との互換を保つため、
`fiscal_year_budgets` が空のときは budget_jpy を当年度予算として返す。

【設計】
- year は西暦 4 桁文字列 ("2026" 等)
- 「累計予算 = sum(全年度)」の総額が `program.budget_jpy` を超えてはならない
- 当年度を超えた spend は次年度の予算が下りるまで止まる (= 政権交代耐性)
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ebpm import EBPMEvent
from app.models.program import Program


def fiscal_year_of(now: datetime | None = None) -> str:
    """会計年度を西暦 4 桁で返す。日本の年度は 4 月始まり。"""
    now = now or datetime.utcnow()
    if now.month < 4:
        return str(now.year - 1)
    return str(now.year)


def budget_for_year(program: Program, year: str | None = None) -> int:
    """指定年度の予算を返す。multi-year が空なら budget_jpy を返す (後方互換)。"""
    fy = year or fiscal_year_of()
    multi = program.fiscal_year_budgets or {}
    if not multi:
        return program.budget_jpy
    return int(multi.get(fy, 0))


def total_multi_year_budget(program: Program) -> int:
    """全年度の合計予算 (= 多年度ロックすべき総額)。"""
    multi = program.fiscal_year_budgets or {}
    if not multi:
        return program.budget_jpy
    return sum(int(v) for v in multi.values())


def remaining_for_year(program: Program, year: str | None = None) -> int:
    """指定年度の残予算 = 当年度予算 - これまでの spent (近似)。

    厳密には spent_jpy は年度横断の累計なので、年度別 spend を分割管理するなら
    EBPM テーブルから集計する必要がある (Phase 3 課題)。
    """
    fy = year or fiscal_year_of()
    multi = program.fiscal_year_budgets or {}
    if not multi:
        return max(program.budget_jpy - program.spent_jpy, 0)
    # 多年度の場合: 当年度予算は 当年度予算 - (累計 spent から過年度に按分した額)
    # 簡易実装: 過年度予算の合計までは消化済とみなし、残りは当年度予算 - 残り spent
    years_sorted = sorted(multi.keys())
    spent_remaining = program.spent_jpy
    for y in years_sorted:
        b = int(multi[y])
        if y < fy:
            spent_remaining = max(spent_remaining - b, 0)
        elif y == fy:
            return max(b - spent_remaining, 0)
    return 0


def spent_by_year_from_ebpm(db: Session, program: Program) -> dict[str, int]:
    """EBPM テーブルから program の年度別 spent を集計 (戦略会議 #5 採択 B)。

    Round 5 の `remaining_for_year` は spent_jpy を「過年度から順に消化済」と
    みなす近似だったが、本関数は EBPMEvent.ts (= 実際の spend 時刻) を使って
    精度を上げる。マイグレーションは不要 (テーブル既存)。
    """
    rows = db.execute(
        select(
            func.strftime("%Y", EBPMEvent.ts),
            func.coalesce(func.sum(EBPMEvent.subsidy_jpy), 0),
        )
        .where(EBPMEvent.program_id == program.id)
        .group_by(func.strftime("%Y", EBPMEvent.ts))
    ).all()
    out: dict[str, int] = {}
    for year_str, total in rows:
        # event.ts は西暦 (4 月始まりの会計年度ではない)。会計年度に変換。
        # ここでは月情報も必要なので、別 query で月単位に集計し直す。
        pass

    # 月別に集計し、4 月始まりで会計年度を判定する
    rows2 = db.execute(
        select(
            func.strftime("%Y-%m", EBPMEvent.ts),
            func.coalesce(func.sum(EBPMEvent.subsidy_jpy), 0),
        )
        .where(EBPMEvent.program_id == program.id)
        .group_by(func.strftime("%Y-%m", EBPMEvent.ts))
    ).all()
    out = {}
    for ym, total in rows2:
        if not ym:
            continue
        y, m = ym.split("-")
        fy = y if int(m) >= 4 else str(int(y) - 1)
        out[fy] = out.get(fy, 0) + int(total)
    return out


def remaining_for_year_precise(
    db: Session, program: Program, year: str | None = None,
) -> int:
    """EBPM 実績ベースで当年度残予算を算出 (戦略会議 #5 採択 B)。

    `remaining_for_year` (近似版) との違い: spent を年度に分散できる。
    """
    fy = year or fiscal_year_of()
    multi = program.fiscal_year_budgets or {}
    by_year = spent_by_year_from_ebpm(db, program)
    if not multi:
        # 単年度: 当年度予算 = budget_jpy、消化分は spent_jpy
        return max(program.budget_jpy - program.spent_jpy, 0)
    budget = int(multi.get(fy, 0))
    spent = by_year.get(fy, 0)
    return max(budget - spent, 0)


def validate_fiscal_year_budgets(
    *,
    fiscal_year_budgets: dict[str, int],
    fallback_budget_jpy: int,
) -> tuple[bool, str]:
    """ProgramIn 受け入れ時のバリデーション。"""
    if not fiscal_year_budgets:
        return True, ""
    for k, v in fiscal_year_budgets.items():
        if not (k.isdigit() and len(k) == 4):
            return False, f"year key must be YYYY: got {k!r}"
        if int(v) < 0:
            return False, f"year {k}: budget must be >= 0"
    total = sum(int(v) for v in fiscal_year_budgets.values())
    if total <= 0:
        return False, "total of fiscal_year_budgets must be > 0"
    return True, ""
