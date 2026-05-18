"""世帯 (household) サービス (戦略会議 #17 採択 PH-7 / Round 19)。

PH 4Ps の制度趣旨は「世帯単位」だが、CP-6 v2 PH 設計まで内部モデルは個人単位だった。
R19 で `Citizen.household_id` を追加し、世帯メンバーの集約・eligibility 判定・
voucher 発行を 1 つの単位として扱えるようにする。

【設計原則】
- household_id は HMAC(主たる受給者の PSN/My Number) を推奨
- household_id が NULL なら個人単位 (JP 後方互換)
- voucher の引換上限は世帯単位で集約 (代理使用 OK = 夫が妻の代わりに買い物可)
- audit trail には主たる受給者の HMAC PID と household_id 両方残す

【ユースケース】
- DSWD 4Ps 世帯 ID から household_id 生成
- 世帯メンバー一覧の取得 (給付対象判定)
- 世帯単位 cap の計算 (個人単位の合算)
- voucher 発行時の世帯単位検証
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.citizen import Citizen


# 世帯 ID 派生用シークレット (個人 PID と独立)
HOUSEHOLD_SECRET = os.environ.get(
    "JPN_PBM_HOUSEHOLD_SECRET", "demo-household-secret-change-me"
).encode()


@dataclass
class HouseholdSummary:
    """世帯の集約情報。"""
    household_id: str
    member_pids: list[str]
    primary_pid: str | None  # 主たる受給者 (一般に世帯主)
    member_count: int
    wards: set[str]


def derive_household_id(*, primary_psn_or_maina: str) -> str:
    """主たる受給者の PSN/My Number から household_id を生成。

    HMAC により元 ID は復元不可。同一の主受給者からは決定論的に同じ id を生成。
    """
    return hmac.new(HOUSEHOLD_SECRET,
                     primary_psn_or_maina.encode(),
                     hashlib.sha256).hexdigest()


def get_household_members(db: Session, household_id: str) -> list[Citizen]:
    """同一世帯の全メンバーを返す。"""
    rows = db.execute(
        select(Citizen).where(Citizen.household_id == household_id)
    ).scalars().all()
    return list(rows)


def get_household_summary(db: Session, household_id: str) -> HouseholdSummary | None:
    """世帯の集約情報を返す。"""
    members = get_household_members(db, household_id)
    if not members:
        return None
    # 主たる受給者 = pid が最も若いもの (慣習。本番では 4Ps roster 由来)
    primary = min(members, key=lambda c: c.pid)
    return HouseholdSummary(
        household_id=household_id,
        member_pids=[c.pid for c in members],
        primary_pid=primary.pid,
        member_count=len(members),
        wards={c.ward for c in members if c.ward},
    )


def is_household_member(db: Session, *, pid: str, household_id: str) -> bool:
    """指定 pid が指定世帯のメンバーか。"""
    c = db.get(Citizen, pid)
    return c is not None and c.household_id == household_id


def household_cap_consumed(
    db: Session, *, household_id: str,
    per_pid_consumed: dict[str, int],
) -> int:
    """世帯メンバー全員の累積消費を合算する。

    `per_pid_consumed` は外部 (PBM contract / lista) からの「pid → 消費額」マップ。
    世帯単位 cap の判定に使う。
    """
    members = get_household_members(db, household_id)
    return sum(per_pid_consumed.get(c.pid, 0) for c in members)


def assign_household(
    db: Session, *, pids: Iterable[str], household_id: str,
) -> int:
    """既存 Citizen 群に household_id を一括割当 (migration / seed 用)。"""
    n = 0
    for pid in pids:
        c = db.get(Citizen, pid)
        if c is None:
            continue
        c.household_id = household_id
        n += 1
    return n


def voucher_amount_for_household(
    *, member_count: int, base_amount_per_household: int,
    member_bonus: int = 0,
) -> int:
    """世帯単位 voucher 額の計算 (4Ps 風)。

    base + (member_count × bonus) で世帯員数に応じて増額。
    """
    return base_amount_per_household + member_count * member_bonus
