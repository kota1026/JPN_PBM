"""CP-8 emergency AML bypass + 14-day post-recovery audit ─ DP-7 (戦略会議 #19 採択 DPI-5)。

Lina Okabe (元 Refinitiv) の指摘:
- AML false positive 率は 単独ソースで 30%、3 ソース cross-check でも 5%
- **緊急時 (台風中・地震直後) に AML reject が致命的** (子供が薬を買えない、餓死)

Red Team R-2 への対応:
- NDRRMC Code Red (or 等価宣言) 中は AML bypass を許可
- ただし **必ず audit log に記録、14 日以内に CSO/AML が review**
- review で suspicious と判定されたら 事後返金 (clawback)

【設計原則】
- bypass は **時間 + 地域 + 金額の 3 軸で制限** (無制限 bypass は危険)
- 全件 audit log を永続化、bypass されたものは separately タグ付け
- CP-1 (緊急停止) との連携: governor が CP-8 bypass を即時無効化可
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol


# CP-8 bypass の制約 (env で上書き可)
DEFAULT_BYPASS_MAX_AMOUNT_CENTI = int(
    os.environ.get("JPN_PBM_CP8_MAX_BYPASS_USDC", "500000"))   # $5,000
DEFAULT_AUDIT_DAYS = int(os.environ.get("JPN_PBM_CP8_AUDIT_DAYS", "14"))


@dataclass
class Cp8BypassEntry:
    """CP-8 で AML をすり抜けて受理された 1 件の audit log。"""
    entry_id: str
    donor_pid: str               # HMAC
    amount_centi: int
    program_id: str
    aml_hits_count: int          # bypass された AML hit 数 (raw hits は別 store)
    aml_risk_score: int
    bypass_reason: str
    emergency_lgu: str | None
    received_at: float
    review_due_by: float
    reviewed_at: float | None = None
    reviewer_pid: str | None = None
    review_outcome: str | None = None  # "cleared" | "clawback" | "investigation"
    clawback_amount_centi: int = 0
    is_mock: bool = True


class Cp8Error(Exception):
    pass


# ============================================================
# Protocol
# ============================================================


class Cp8AuditStore(Protocol):
    def add(self, entry: Cp8BypassEntry) -> None: ...
    def list_pending_review(self, *, now: float | None = None) -> list[Cp8BypassEntry]: ...
    def list_overdue(self, *, now: float | None = None) -> list[Cp8BypassEntry]: ...
    def mark_reviewed(self, *, entry_id: str, reviewer_pid: str,
                       outcome: str, clawback_amount_centi: int = 0) -> Cp8BypassEntry: ...
    def get(self, entry_id: str) -> Cp8BypassEntry | None: ...
    def count(self) -> int: ...


# ============================================================
# Mock store
# ============================================================


class MockCp8AuditStore:
    """in-process mock store。本番 (R22+) では DB-backed に置換。"""

    def __init__(self) -> None:
        self._entries: dict[str, Cp8BypassEntry] = {}

    def add(self, entry: Cp8BypassEntry) -> None:
        self._entries[entry.entry_id] = entry

    def list_pending_review(self, *, now: float | None = None
                             ) -> list[Cp8BypassEntry]:
        return [e for e in self._entries.values() if e.reviewed_at is None]

    def list_overdue(self, *, now: float | None = None) -> list[Cp8BypassEntry]:
        t = now if now is not None else time.time()
        return [e for e in self._entries.values()
                if e.reviewed_at is None and t > e.review_due_by]

    def mark_reviewed(self, *, entry_id: str, reviewer_pid: str,
                       outcome: str, clawback_amount_centi: int = 0
                       ) -> Cp8BypassEntry:
        e = self._entries.get(entry_id)
        if e is None:
            raise Cp8Error(f"entry not found: {entry_id}")
        if e.reviewed_at is not None:
            raise Cp8Error(f"entry already reviewed: {entry_id}")
        if outcome not in ("cleared", "clawback", "investigation"):
            raise Cp8Error(f"invalid outcome: {outcome}")
        if outcome == "clawback":
            if clawback_amount_centi <= 0 or clawback_amount_centi > e.amount_centi:
                raise Cp8Error(
                    f"clawback amount {clawback_amount_centi} invalid (0 < x <= {e.amount_centi})"
                )
        e.reviewed_at = time.time()
        e.reviewer_pid = reviewer_pid
        e.review_outcome = outcome
        e.clawback_amount_centi = clawback_amount_centi
        return e

    def get(self, entry_id: str) -> Cp8BypassEntry | None:
        return self._entries.get(entry_id)

    def count(self) -> int:
        return len(self._entries)


# ============================================================
# Core bypass logic
# ============================================================


def maybe_bypass(
    *, donor_pid: str, amount_centi: int, program_id: str,
    aml_outcome: str, aml_hits_count: int, aml_risk_score: int,
    ndrrmc_active: bool, emergency_lgu: str | None,
    store: Cp8AuditStore,
    max_bypass_centi: int | None = None,
    audit_days: int | None = None,
) -> tuple[bool, Cp8BypassEntry | None]:
    """AML が reject/review でも、災害時条件を満たせば受理 + audit log。

    戻り値: (bypassed: bool, audit_entry: Cp8BypassEntry|None)
    bypassed=False は通常フロー (AML cleared か、bypass 条件不適合)。
    """
    # AML が cleared なら bypass 不要
    if aml_outcome == "cleared":
        return False, None

    # 緊急時条件: NDRRMC active + emergency_lgu 指定
    if not (ndrrmc_active and emergency_lgu):
        return False, None

    # 金額制限
    max_amt = (max_bypass_centi if max_bypass_centi is not None
                else DEFAULT_BYPASS_MAX_AMOUNT_CENTI)
    if amount_centi > max_amt:
        return False, None

    # bypass 条件成立 → audit log エントリ作成
    days = audit_days if audit_days is not None else DEFAULT_AUDIT_DAYS
    now = time.time()
    entry = Cp8BypassEntry(
        entry_id="CP8-" + uuid.uuid4().hex[:12].upper(),
        donor_pid=donor_pid,
        amount_centi=amount_centi,
        program_id=program_id,
        aml_hits_count=aml_hits_count,
        aml_risk_score=aml_risk_score,
        bypass_reason=f"CP-8 emergency bypass (NDRRMC Code Red @ {emergency_lgu}, AML risk {aml_risk_score})",
        emergency_lgu=emergency_lgu,
        received_at=now,
        review_due_by=now + days * 86400,
        is_mock=True,
    )
    store.add(entry)
    return True, entry


def get_default_store() -> Cp8AuditStore:
    """singleton-ish。テストでは isolation のため新規 instance を使うこと。"""
    if not hasattr(get_default_store, "_instance"):
        get_default_store._instance = MockCp8AuditStore()  # type: ignore
    return get_default_store._instance  # type: ignore


def clear_default_store() -> None:
    """テスト用 reset。"""
    if hasattr(get_default_store, "_instance"):
        del get_default_store._instance
