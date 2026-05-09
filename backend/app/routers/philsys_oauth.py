"""PhilSys (Philippine Identification System) OAuth Mock (戦略会議 #12 採択 T2)。

`backend/app/routers/myna_oauth.py` (RFC 6749 Authorization Code Grant) と同形に、
フィリピンの PSA (統計庁) PhilSys eID を Mock したプロバイダ。Phase 2 移行用に
本番 PhilSys API と同じフローでフロントが wire-up できるようにする。

【フロー】
    /philsys/v1/authorize?response_type=code&client_id=quezon-city-pbm&...
        → Tagalog/English 切替の同意画面 (HTML) を返す
    POST /philsys/v1/authorize/consent { code, scope, ... }
        → ConsentLog を書き込み (Data Privacy Act of 2012 同等)、code を発行
    POST /philsys/v1/token { grant_type=authorization_code, code, ... }
        → access_token (Bearer) を発行
    GET /philsys/v1/userinfo (Authorization: Bearer)
        → PhilSys claims (PSN HMAC pid / name / city / DoB / dependents) を返す

state / code は exp 60s 制限、token は exp 1h 制限。
本番 PhilSys は OpenID Connect ベース。Mock では同じパス・同じレスポンス形を踏襲。

JP の myna_oauth と PH の philsys_oauth は **HMAC pseudonymization (privacy.py) で同形**。
Provider 抽象化が綺麗に取れる。

【参考】
- PSA PhilSys: https://philsys.gov.ph/
- Data Privacy Act of 2012 (RA 10173)
- 4Ps: Pantawid Pamilyang Pilipino Program
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


router = APIRouter(prefix="/philsys/v1", tags=["philsys-oauth"])


CLIENT_ID = "quezon-city-pbm"
ALLOWED_REDIRECT_URI_PREFIXES = ("http://localhost", "http://127.0.0.1")
CODE_TTL_SEC = 60
TOKEN_TTL_SEC = 3600

# 4Ps デフォルトスコープ
DEFAULT_SCOPE = "psn.hmac household.dependents address.city"


@dataclass
class _AuthCode:
    code: str
    pid: str
    program_id: str
    scope: list[str]
    redirect_uri: str
    state: str
    consent_text_sha256: str
    locale: str  # "tl" or "en"
    issued_at: float = field(default_factory=time.time)
    used: bool = False

    def is_expired(self) -> bool:
        return time.time() - self.issued_at > CODE_TTL_SEC


@dataclass
class _AccessToken:
    token: str
    pid: str
    scope: list[str]
    locale: str
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
    scope: str = Query(DEFAULT_SCOPE),
    state: str = Query(...),
    program_id: str = Query("prog-4ps-2026"),
    locale: str = Query("tl", description="tl (Tagalog) or en (English)"),
):
    if response_type != "code":
        raise HTTPException(400, "only response_type=code supported")
    if client_id != CLIENT_ID:
        raise HTTPException(400, f"unknown client_id (expected {CLIENT_ID})")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "redirect_uri must be localhost (Mock mode)")
    if locale not in ("tl", "en"):
        raise HTTPException(400, "locale must be 'tl' or 'en'")

    consent_text = (
        f"DSWD will retrieve the following PhilSys claims under "
        f"program={program_id}, scope={scope}, "
        f"in compliance with Data Privacy Act of 2012."
    )
    sha = hashlib.sha256(consent_text.encode("utf-8")).hexdigest()

    if locale == "tl":
        title = "PhilSys Pahintulot (Mock)"
        h1 = "PhilSys Pahintulot (Mock)"
        intro = (
            "<b>Ang screen na ito ay Mock.</b> "
            "Sa production, gagana ito sa parehong OAuth flow ng aktwal na PhilSys."
        )
        applicant_label = "Aplikante"
        program_label = "Programa"
        scope_label = "Mga claim na kukuhanin"
        consent_summary = "Pahintulot na text"
        psn_label = "PSN (Mock input)"
        submit_label = "Pumayag at gumawa ng authorization code"
    else:
        title = "PhilSys Consent (Mock)"
        h1 = "PhilSys Consent (Mock)"
        intro = (
            "<b>This screen is a Mock.</b> "
            "Production runs on the same OAuth flow as the actual PhilSys API."
        )
        applicant_label = "Applicant"
        program_label = "Program"
        scope_label = "Claims to be retrieved"
        consent_summary = "Consent text"
        psn_label = "PSN (Mock input)"
        submit_label = "Consent and issue authorization code"

    return HTMLResponse(f"""<!doctype html>
<html lang="{ 'tl' if locale == 'tl' else 'en' }"><head><meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="/ui/styles.css"></head>
<body style="padding:20px;max-width:680px;margin:auto">
<h2>{h1}</h2>
<p class="note">{intro}</p>
<dl style="background:#f7f7f7;padding:12px;border-radius:8px">
  <dt><b>{applicant_label}</b></dt><dd>DSWD / Quezon City LGU (client_id={client_id})</dd>
  <dt><b>{program_label}</b></dt><dd>{program_id}</dd>
  <dt><b>{scope_label}</b> (scope)</dt><dd><code>{scope}</code></dd>
</dl>
<details style="margin:12px 0"><summary>{consent_summary} (sha256={sha[:16]}...)</summary>
<p style="white-space:pre-wrap">{consent_text}</p></details>
<form method="post" action="/philsys/v1/authorize/consent">
  <input type="hidden" name="redirect_uri" value="{redirect_uri}">
  <input type="hidden" name="state" value="{state}">
  <input type="hidden" name="scope" value="{scope}">
  <input type="hidden" name="program_id" value="{program_id}">
  <input type="hidden" name="locale" value="{locale}">
  <input type="hidden" name="consent_text_sha256" value="{sha}">
  <label>{psn_label}<input name="psn" placeholder="e.g. PH-0001" required></label>
  <button type="submit" style="margin-top:12px">{submit_label}</button>
</form>
</body></html>""")


# ----------------------------- /authorize/consent (POST) -----------------------------


@router.post("/authorize/consent")
async def authorize_consent(request: Request, db: Session = Depends(_db)):
    form = await request.form()
    psn = (form.get("psn") or "").strip()
    redirect_uri = form.get("redirect_uri") or ""
    state = form.get("state") or ""
    scope = form.get("scope") or ""
    program_id = form.get("program_id") or ""
    locale = form.get("locale") or "tl"
    consent_text_sha256 = form.get("consent_text_sha256") or ""

    if not psn:
        raise HTTPException(400, "psn required")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "bad redirect_uri")

    # PSN → HMAC pid (privacy.py を流用、JP マイナンバーと同じロジック)
    from app.services.privacy import pseudonymize
    pid = pseudonymize(psn)

    # ConsentLog を確実に書く (Data Privacy Act 2012 監査トレイル)
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
        locale=locale,
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
        locale=record.locale,
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SEC,
        "scope": " ".join(record.scope),
        "pid": record.pid,
        "locale": record.locale,
    }


# ----------------------------- /userinfo -----------------------------


@router.get("/userinfo")
def userinfo(request: Request) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Authorization: Bearer required")
    tok = _tokens.get(auth.removeprefix("Bearer "))
    if tok is None or tok.is_expired():
        raise HTTPException(401, "invalid or expired token")

    return {
        "pid": tok.pid,
        "scope": tok.scope,
        "locale": tok.locale,
        "issued_at": datetime.fromtimestamp(tok.issued_at).isoformat(),
        "_mock": True,
        "_data_privacy_act_compliance": "RA 10173 (PH)",
    }


@router.get("/_/state")
def debug_state() -> dict[str, int]:
    """Mock 用の内部状態カウント。本番では存在しないエンドポイント。"""
    return {
        "codes": len(_codes),
        "tokens": len(_tokens),
    }
