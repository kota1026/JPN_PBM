"""マイナポータル v2 OAuth Mock (戦略会議 #4 採択 #4)。

Phase 2 移行用に、本番マイナポータル v2 と同形 (RFC 6749 Authorization Code Grant)
の OAuth プロバイダを Mock する。実 API は外部サービスなのでサンドボックスでは
動かせないが、本ルータは Phase 1 のフロントが「本番と同じフロー」で wire-up できる
ようにする。

【フロー】
    /myna/v2/authorize?response_type=code&client_id=tokyo-metro&...
        → 同意画面 (HTML) を返す
    POST /myna/v2/authorize/consent { code, scope, ... }
        → ConsentLog を書き込み、code を発行
    POST /myna/v2/token { grant_type=authorization_code, code, ... }
        → access_token (JWT-like) を発行
    GET /myna/v2/userinfo (Authorization: Bearer)
        → 4 情報 (Mock)

state / code は exp 60s 制限、token は exp 1h 制限。
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.consent import ConsentLog


router = APIRouter(prefix="/myna/v2", tags=["myna-oauth"])


CLIENT_ID = "tokyo-metro-pbm"
ALLOWED_REDIRECT_URI_PREFIXES = ("http://localhost", "http://127.0.0.1")
CODE_TTL_SEC = 60
TOKEN_TTL_SEC = 3600


@dataclass
class _AuthCode:
    code: str
    pid: str
    program_id: str
    scope: list[str]
    redirect_uri: str
    state: str
    consent_text_sha256: str
    issued_at: float = field(default_factory=time.time)
    used: bool = False

    def is_expired(self) -> bool:
        return time.time() - self.issued_at > CODE_TTL_SEC


@dataclass
class _AccessToken:
    token: str
    pid: str
    scope: list[str]
    issued_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.issued_at > TOKEN_TTL_SEC


# プロセス内ストア (Phase 2 で Redis/DB へ)
_codes: dict[str, _AuthCode] = {}
_tokens: dict[str, _AccessToken] = {}


def _db():
    db = get_session()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _validate_redirect_uri(uri: str) -> bool:
    return any(uri.startswith(p) for p in ALLOWED_REDIRECT_URI_PREFIXES)


# ----------------------------- /authorize (画面) -----------------------------


@router.get("/authorize", response_class=HTMLResponse)
def authorize(
    response_type: str = Query("code"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query("family_register.basic_4"),
    state: str = Query(...),
    program_id: str = Query("prog-koto-kosodate-2026"),
):
    if response_type != "code":
        raise HTTPException(400, "only response_type=code supported")
    if client_id != CLIENT_ID:
        raise HTTPException(400, f"unknown client_id (expected {CLIENT_ID})")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "redirect_uri must be localhost (Mock mode)")

    consent_text = f"東京都が JPYC 助成 (program={program_id}) のため、以下の情報を取得することに同意します: {scope}"
    sha = hashlib.sha256(consent_text.encode("utf-8")).hexdigest()
    return HTMLResponse(f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>マイナポータル v2 同意 (Mock)</title>
<link rel="stylesheet" href="/ui/styles.css"></head>
<body style="padding:20px;max-width:680px;margin:auto">
<h2>マイナポータル v2 同意 (Mock)</h2>
<p class="note"><b>本画面は Mock です。</b>本番のマイナポータル v2 OAuth と同じフローで動作します。</p>
<dl style="background:#f7f7f7;padding:12px;border-radius:8px">
  <dt><b>申請者</b></dt><dd>東京都 (client_id={client_id})</dd>
  <dt><b>プログラム</b></dt><dd>{program_id}</dd>
  <dt><b>取得情報</b> (scope)</dt><dd><code>{scope}</code></dd>
</dl>
<details style="margin:12px 0"><summary>同意文面 (sha256={sha[:16]}...)</summary>
<p style="white-space:pre-wrap">{consent_text}</p></details>
<form method="post" action="/myna/v2/authorize/consent">
  <input type="hidden" name="redirect_uri" value="{redirect_uri}">
  <input type="hidden" name="state" value="{state}">
  <input type="hidden" name="scope" value="{scope}">
  <input type="hidden" name="program_id" value="{program_id}">
  <input type="hidden" name="consent_text_sha256" value="{sha}">
  <label>マイナンバー (Mock 入力)<input name="maina_id" placeholder="例: MN-0001" required></label>
  <button type="submit" style="margin-top:12px">同意して認可コードを発行</button>
</form>
</body></html>""")


# ----------------------------- /authorize/consent (POST) -----------------------------


@router.post("/authorize/consent")
async def authorize_consent(request: Request, db: Session = Depends(_db)):
    form = await request.form()
    maina_id = (form.get("maina_id") or "").strip()
    redirect_uri = form.get("redirect_uri") or ""
    state = form.get("state") or ""
    scope = form.get("scope") or ""
    program_id = form.get("program_id") or ""
    consent_text_sha256 = form.get("consent_text_sha256") or ""
    if not maina_id:
        raise HTTPException(400, "maina_id required")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "bad redirect_uri")

    # マイナンバー → HMAC pid (privacy.py と同じロジックの簡易再実装)
    from app.services.privacy import pseudonymize
    pid = pseudonymize(maina_id)

    # ConsentLog を確実に書く (#10 と integrate)
    log = ConsentLog(
        id=str(uuid.uuid4()),
        pid=pid,
        program_id=program_id,
        consent_text_sha256=consent_text_sha256,
        scope=scope.split() if scope else [],
        source_ip_hash=hashlib.sha256(
            (request.client.host if request.client else "").encode()
        ).hexdigest(),
        user_agent_hash=hashlib.sha256(
            (request.headers.get("user-agent") or "").encode()
        ).hexdigest(),
    )
    db.add(log)
    db.flush()

    code = secrets.token_urlsafe(24)
    _codes[code] = _AuthCode(
        code=code, pid=pid, program_id=program_id,
        scope=scope.split() if scope else [],
        redirect_uri=redirect_uri, state=state,
        consent_text_sha256=consent_text_sha256,
    )
    sep = "&" if "?" in redirect_uri else "?"
    return JSONResponse({
        "redirect_to": f"{redirect_uri}{sep}code={code}&state={state}",
        "consent_id": log.id,
    })


# ----------------------------- /token -----------------------------


class TokenIn(BaseModel):
    grant_type: str = Field(..., description="must be 'authorization_code'")
    code: str
    redirect_uri: str
    client_id: str


@router.post("/token")
def token(payload: TokenIn) -> dict[str, Any]:
    if payload.grant_type != "authorization_code":
        raise HTTPException(400, "only grant_type=authorization_code supported")
    if payload.client_id != CLIENT_ID:
        raise HTTPException(400, "bad client_id")
    record = _codes.get(payload.code)
    if record is None:
        raise HTTPException(400, "invalid code")
    if record.used:
        raise HTTPException(400, "code already used (replay attack?)")
    if record.is_expired():
        raise HTTPException(400, "code expired")
    if record.redirect_uri != payload.redirect_uri:
        raise HTTPException(400, "redirect_uri mismatch")
    record.used = True

    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = _AccessToken(
        token=access_token, pid=record.pid, scope=record.scope,
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SEC,
        "scope": " ".join(record.scope),
        "pid": record.pid,  # マイナポータルにはない拡張だが Mock の便利のため
    }


# ----------------------------- /userinfo -----------------------------


@router.get("/userinfo")
def userinfo(request: Request, db: Session = Depends(_db)) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Authorization: Bearer required")
    tok = _tokens.get(auth.removeprefix("Bearer "))
    if tok is None or tok.is_expired():
        raise HTTPException(401, "invalid or expired token")

    return {
        "pid": tok.pid,
        "scope": tok.scope,
        "issued_at": datetime.fromtimestamp(tok.issued_at).isoformat(),
        "_mock": True,
    }


@router.get("/_/state")
def debug_state() -> dict[str, int]:
    """Mock 用の内部状態カウント。本番では存在しないエンドポイント。"""
    return {
        "codes": len(_codes),
        "tokens": len(_tokens),
    }
