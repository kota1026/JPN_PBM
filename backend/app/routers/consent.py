"""マイナポータル v2 OAuth 同意フロー (戦略会議 #2 採択 #10 完成形)。

Cost Guardian 提案 #6 (申請レス) が実用化される前段で、Legal 提案 #10 の
ConsentLog を「実 API で書き込まれる」状態に持ち上げる。

【フロー (本番のマイナポータル v2 OAuth に揃えてある)】
    POST /consent/grant      — 同意取得 (フロントから取得した consent_text を sha256 化)
    GET  /consent/{pid}      — 当該 pid の同意状況一覧 (取消含む)
    POST /consent/{id}/revoke — 撤回

【セキュリティ】
- pid は HMAC 化済み (生マイナンバー禁止: CP-2)
- consent_text の hash は本人/都の双方が独立に再計算可能 (CP-4 監査可能性)
- IP / UA は sha256 で hash 化して保存 (個情法 ログ要件: 個人識別性ある生 IP は保存しない)
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.consent import ConsentLog
from app.services import purpose_guard


router = APIRouter(prefix="/consent", tags=["consent"])


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _hash_for_log(value: str | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ConsentGrantIn(BaseModel):
    pid: str = Field(..., description="HMAC 化済み citizen pid")
    program_id: str
    consent_text: str = Field(..., min_length=8, description="マイナポータルで提示した文面")
    scope: list[str] = Field(default_factory=list)


class ConsentOut(BaseModel):
    id: str
    pid: str
    program_id: str
    consent_text_sha256: str
    scope: list[str]
    granted_at: datetime
    revoked_at: datetime | None
    revoke_reason: str


class ConsentRevokeIn(BaseModel):
    reason: str = Field(..., min_length=4)


def _to_out(c: ConsentLog) -> ConsentOut:
    return ConsentOut(
        id=c.id,
        pid=c.pid,
        program_id=c.program_id,
        consent_text_sha256=c.consent_text_sha256,
        scope=c.scope or [],
        granted_at=c.granted_at,
        revoked_at=c.revoked_at,
        revoke_reason=c.revoke_reason,
    )


@router.post("/grant", response_model=ConsentOut)
def grant(
    payload: ConsentGrantIn,
    request: Request,
    db: Session = Depends(_db),
) -> ConsentOut:
    """住民が「都が JPYC 給付に必要な範囲で 4 情報を取得する」ことに同意する。"""
    # CP-2 ガード: 生 ID 禁止
    d = purpose_guard.cp2_pid_is_pseudonymized(payload.pid)
    if not d.ok:
        raise HTTPException(400, f"{d.code}: {d.why}")

    log = ConsentLog(
        id=str(uuid.uuid4()),
        pid=payload.pid,
        program_id=payload.program_id,
        consent_text_sha256=hashlib.sha256(payload.consent_text.encode("utf-8")).hexdigest(),
        scope=payload.scope,
        source_ip_hash=_hash_for_log(request.client.host if request.client else None),
        user_agent_hash=_hash_for_log(request.headers.get("user-agent")),
    )
    db.add(log)
    db.flush()
    return _to_out(log)


@router.get("/{pid}", response_model=list[ConsentOut])
def list_for_pid(pid: str, db: Session = Depends(_db)) -> list[ConsentOut]:
    rows = db.execute(
        select(ConsentLog).where(ConsentLog.pid == pid).order_by(ConsentLog.granted_at.desc())
    ).scalars().all()
    return [_to_out(c) for c in rows]


@router.post("/{consent_id}/revoke", response_model=ConsentOut)
def revoke(consent_id: str, payload: ConsentRevokeIn, db: Session = Depends(_db)) -> ConsentOut:
    log = db.get(ConsentLog, consent_id)
    if log is None:
        raise HTTPException(404, "consent not found")
    if log.revoked_at is not None:
        raise HTTPException(409, "already revoked")
    log.revoked_at = datetime.utcnow()
    log.revoke_reason = payload.reason
    db.flush()
    return _to_out(log)


@router.get("/_/stats")
def stats(db: Session = Depends(_db)) -> dict[str, Any]:
    rows = db.execute(select(ConsentLog)).scalars().all()
    active = sum(1 for r in rows if r.revoked_at is None)
    revoked = len(rows) - active
    return {"total": len(rows), "active": active, "revoked": revoked}
