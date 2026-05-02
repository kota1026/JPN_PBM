"""都 CFO + SOC 向け: 準備金監査 + JPYC ペッグ監視 (戦略会議 #2 #4 + #8)。

エンドポイント:
    GET  /treasury/audit                  → 24h cron が叩く準備金監査
    POST /treasury/peg/sample             → 外部 oracle がスポット価格を投入
    GET  /treasury/peg/status             → 現在の peg 健康状態
    POST /treasury/peg/freeze             → SOC が手動 freeze
    POST /treasury/peg/unfreeze           → SOC が手動 unfreeze
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.services import key_management, peg_monitor
from app.services.treasury_audit import (
    DEFAULT_ALERT_THRESHOLD_JPY,
    audit_reserves,
)


router = APIRouter(prefix="/treasury", tags=["treasury"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


# ----------------------------- 準備金監査 -----------------------------


@router.get("/audit")
def audit(
    threshold_jpy: int = Query(DEFAULT_ALERT_THRESHOLD_JPY, ge=0),
    db: Session = Depends(_db),
) -> dict[str, Any]:
    rep = audit_reserves(db, threshold_jpy=threshold_jpy)
    return {
        "audited_at": rep.audited_at.isoformat(),
        "healthy": rep.healthy,
        "threshold_jpy": rep.threshold_jpy,
        "totals": {
            "total_minted_jpy": rep.total_minted_jpy,
            "treasury_balance_jpy": rep.treasury_balance_jpy,
            "store_balance_jpy": rep.store_balance_jpy,
            "citizen_balance_jpy": rep.citizen_balance_jpy,
            "sum_balances_jpy": rep.sum_balances_jpy,
        },
        "pbm": {
            "program_budgets_jpy": rep.program_budgets_jpy,
            "program_spent_jpy": rep.program_spent_jpy,
            "program_outstanding_jpy": rep.program_outstanding_jpy,
            "issued_token_remaining_jpy": rep.issued_token_remaining_jpy,
        },
        "diffs": {
            "jpyc_supply_diff": rep.jpyc_supply_diff,
            "pbm_outstanding_diff": rep.pbm_outstanding_diff,
        },
        "alerts": rep.alerts,
    }


# ----------------------------- ペッグ監視 -----------------------------


class PegSampleIn(BaseModel):
    spot_jpy_per_jpyc: float = Field(..., gt=0, description="1 JPYC あたりの JPY スポット")


class PegFreezeIn(BaseModel):
    by: str = Field(..., description="操作者 (例: tokyo-soc-001)")
    reason: str = Field(..., min_length=4)


def _serialize_status(status) -> dict[str, Any]:
    return {
        "healthy": status.healthy,
        "frozen": status.frozen,
        "last_alert_at": status.last_alert_at.isoformat() if status.last_alert_at else None,
        "last_freeze_reason": status.last_freeze_reason,
        "alerts": status.alerts,
        "last_sample": (
            {
                "ts": status.last.ts.isoformat(),
                "spot_jpy_per_jpyc": status.last.spot_jpy_per_jpyc,
                "deviation_bps": status.last.deviation_bps,
                "deviation_pct": status.last.deviation_pct,
            }
            if status.last
            else None
        ),
    }


@router.post("/peg/sample")
def submit_sample(payload: PegSampleIn) -> dict[str, Any]:
    monitor = peg_monitor.get_monitor()
    status = monitor.submit(payload.spot_jpy_per_jpyc)
    return _serialize_status(status)


@router.get("/peg/status")
def peg_status() -> dict[str, Any]:
    monitor = peg_monitor.get_monitor()
    history = list(monitor.history())
    last = history[-1] if history else None
    if last is None:
        return {
            "healthy": True,
            "frozen": monitor.is_frozen,
            "last_alert_at": None,
            "last_freeze_reason": "",
            "alerts": [],
            "last_sample": None,
            "samples_n": 0,
        }
    abs_dev = abs(last.deviation_bps)
    return {
        "healthy": (abs_dev < monitor.alert_bps and not monitor.is_frozen),
        "frozen": monitor.is_frozen,
        "last_alert_at": None,
        "last_freeze_reason": "",
        "alerts": [],
        "last_sample": {
            "ts": last.ts.isoformat(),
            "spot_jpy_per_jpyc": last.spot_jpy_per_jpyc,
            "deviation_bps": last.deviation_bps,
            "deviation_pct": last.deviation_pct,
        },
        "samples_n": len(history),
    }


@router.post("/peg/freeze")
def freeze(payload: PegFreezeIn) -> dict[str, str]:
    monitor = peg_monitor.get_monitor()
    msg = monitor.manual_freeze(by=payload.by, reason=payload.reason)
    return {"result": msg}


@router.get("/keys/rotation")
def keys_rotation() -> dict[str, object]:
    """ECDSA 鍵 rotation 状態 (戦略会議 #6 採択 A)。

    本エンドポイントは公開鍵 (address) しか返さない。秘密鍵は env だけで管理。
    """
    return key_management.rotation_status()


@router.get("/migrations/status")
def migrations_status() -> dict[str, object]:
    """DB マイグレーション状態 (戦略会議 #6 採択 C)。"""
    from app.db import _engine
    from migrations import status as _migration_status
    return _migration_status(_engine)


@router.post("/peg/unfreeze")
def unfreeze(payload: PegFreezeIn) -> dict[str, str]:
    monitor = peg_monitor.get_monitor()
    if not monitor.is_frozen:
        raise HTTPException(409, "monitor is not frozen")
    msg = monitor.manual_unfreeze(by=payload.by, reason=payload.reason)
    return {"result": msg}
