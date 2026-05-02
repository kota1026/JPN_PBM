"""CP-6 オフラインフォールバックの REST 公開 (戦略会議 #2 採択 #7)。

平時 (POS 端末への coupon 配布):
    POST /offline/coupons               → SignedCoupon を発行

有事 (POS がオフラインで給付した結果を復旧後に提出):
    POST /offline/redeem-batch          → settlement.redeem_batch +
                                          accepted な item を本体 EBPM に書き戻す

【Red Team #7 指摘への対応】
オフライン redemption が EBPM に書き戻されないと CP-4 違反になる。
本ルータは accepted な item ごとに `purpose_guard.guard_offline_redemption`
を再評価し、guard が allow したものだけ EBPMEvent として永続化する。
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ebpm import EBPMEvent
from app.services import purpose_guard
from app.services.offline_fallback import (
    OfflineCoupon,
    OfflineLedger,
    OfflineRedemption,
    OfflineSettlement,
    SignedCoupon,
    issue_offline_coupon,
)


router = APIRouter(prefix="/offline", tags=["offline"])


# ----------------------------- グローバル状態 -----------------------------
# 本番では HSM + DB に置換。ここではプロセス内で同じ Settlement / POS Ledger を共有して、
# E2E (発行 → POS 給付 → 復旧後精算) を 1 プロセスで再現できるようにしている。
_settlement = OfflineSettlement()
_pos_ledger = OfflineLedger()


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


# ----------------------------- スキーマ -----------------------------


class CouponIssueIn(BaseModel):
    program_id: str
    pid: str = Field(..., description="HMAC 化済み citizen pid")
    month_index: int = Field(..., ge=200001, le=210012)
    cap_jpy: int = Field(..., gt=0)
    expires_at: int = Field(..., description="Unix 秒")


class CouponOut(BaseModel):
    program_id: str
    pid: str
    month_index: int
    cap_jpy: int
    expires_at: int
    signature: str


class StoreApproveIn(BaseModel):
    store_id: str


class RedemptionIn(BaseModel):
    program_id: str
    pid: str
    month_index: int
    cap_jpy: int
    expires_at: int
    signature: str
    store_id: str
    amount_jpy: int = Field(..., gt=0)
    redeemed_at: int


class BatchIn(BaseModel):
    store_id: str
    items: list[RedemptionIn]


class BatchOut(BaseModel):
    accepted_count: int
    rejected_count: int
    total_paid_jpy: int
    accepted_event_ids: list[str]
    rejected: list[dict[str, Any]]


# ----------------------------- 平時 API -----------------------------


@router.post("/coupons", response_model=CouponOut)
def issue_coupon(payload: CouponIssueIn) -> CouponOut:
    """都が住民へ配布する QR を発行する (平時)。"""
    # CP-2: pid が HMAC 化済みでなければ即拒否
    d = purpose_guard.cp2_pid_is_pseudonymized(payload.pid)
    if not d.ok:
        raise HTTPException(400, f"{d.code}: {d.why}")
    signed = issue_offline_coupon(
        program_id=payload.program_id,
        pid=payload.pid,
        month_index=payload.month_index,
        cap_jpy=payload.cap_jpy,
        expires_at=payload.expires_at,
    )
    return CouponOut(
        program_id=signed.coupon.program_id,
        pid=signed.coupon.pid,
        month_index=signed.coupon.month_index,
        cap_jpy=signed.coupon.cap_jpy,
        expires_at=signed.coupon.expires_at,
        signature=signed.signature,
    )


@router.post("/stores/approve")
def approve_store(payload: StoreApproveIn) -> dict[str, str]:
    """都が加盟店を CP-6 用に承認する。POS 側 ledger と settlement の双方に反映。"""
    _pos_ledger.approve_store(payload.store_id)
    _settlement.approve_store(payload.store_id)
    return {"store_id": payload.store_id, "approved": "ok"}


# ----------------------------- 復旧後 API -----------------------------


def _to_redemption(it: RedemptionIn) -> OfflineRedemption:
    return OfflineRedemption(
        coupon=OfflineCoupon(
            program_id=it.program_id,
            pid=it.pid,
            month_index=it.month_index,
            cap_jpy=it.cap_jpy,
            expires_at=it.expires_at,
        ),
        signature=it.signature,
        store_id=it.store_id,
        amount_jpy=it.amount_jpy,
        redeemed_at=it.redeemed_at,
    )


@router.post("/redeem-batch", response_model=BatchOut)
def redeem_batch(payload: BatchIn, db: Session = Depends(_db)) -> BatchOut:
    """POS が復旧後にオフライン redemption をまとめて精算する。

    Settlement で accepted になった item を、本体 EBPM (= EBPMEvent テーブル) に
    書き戻す。これにより CP-4 (監査可能性) がオフライン経路でも担保される。
    """
    items = [_to_redemption(i) for i in payload.items]
    res = _settlement.redeem_batch(payload.store_id, items)

    # accepted のみ EBPM に書き込み (CP-4 漏れ防止 / Red Team #7)
    event_ids: list[str] = []
    for r in res.accepted:
        event_dict = {
            "program_id": r.coupon.program_id,
            "jan": "OFFLINE",  # JAN 不明 (オフライン redemption は商品単位ではない)
            "category": "offline.fallback",
            "qty": 1,
            "total_jpy": r.amount_jpy,
            "subsidy_jpy": r.amount_jpy,
            "citizen_pay_jpy": 0,
            "citizen_pid": r.coupon.pid,
            "age_band": "",
            "gender": "",
            "ward": "",
            "store_id": r.store_id,
            "store_ward": "",
        }
        guard = purpose_guard.guard_offline_redemption(
            pid=r.coupon.pid,
            has_signature=bool(r.signature),
            audit_event=event_dict,
        )
        if not guard.ok:
            # ここに来るのは「PID が pseudonymize されていない」「監査ログが欠損」等。
            # accepted から書き戻しが阻止された場合は rejected 一覧に追加し、
            # 上位レイヤがアラート対象にできるようにする。
            res.rejected.append((r, f"{guard.code}: {guard.why}"))
            res.total_paid_jpy -= r.amount_jpy
            continue

        event = EBPMEvent(id=str(uuid.uuid4()), **event_dict)
        db.add(event)
        event_ids.append(event.id)

    return BatchOut(
        accepted_count=len(event_ids),
        rejected_count=len(res.rejected),
        total_paid_jpy=res.total_paid_jpy,
        accepted_event_ids=event_ids,
        rejected=[{"reason": why, "store_id": r.store_id} for r, why in res.rejected],
    )


@router.get("/consumed")
def consumed(pid: str, month_index: int) -> dict[str, int]:
    """(pid, month_index) の累積消費を返す (POS が事前確認に使う)。"""
    return {
        "pos": _pos_ledger.consumed(pid, month_index),
        "settlement": _settlement.consumed(pid, month_index),
    }
