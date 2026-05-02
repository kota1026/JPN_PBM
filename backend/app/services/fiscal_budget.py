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
