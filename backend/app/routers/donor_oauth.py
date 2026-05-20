"""Donor OAuth mock router ─ DP-5 (戦略会議 #19 採択 DPI-2)。

Coinbase / PayPal / Stripe 等の既存決済プラットフォームから寄付者を取り込む
OAuth + KYC pass-through を mock 実装。これにより我々は VASP/MSB を取得しない。

【flow】
1. /donor-oauth/v1/authorize?provider=coinbase&redirect_uri=...&amount=...
2. (mock 同意画面)
3. /donor-oauth/v1/authorize/consent (POST) → code
4. /donor-oauth/v1/token { code } → access_token + donor_pid
5. /donor-oauth/v1/userinfo (Bearer) → donor_pid + tier + country
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.donor_wallet import (
    donor_pid_from_email, DonationRequest, receive_donation,
)
from app.services import tier_policy as tp


router = APIRouter(prefix="/donor-oauth/v1", tags=["donor-oauth"])


SUPPORTED_PROVIDERS = ("coinbase", "paypal", "stripe")
ALLOWED_REDIRECT_URI_PREFIXES = ("http://localhost", "http://127.0.0.1")
CODE_TTL_SEC = 300
TOKEN_TTL_SEC = 3600


@dataclass
class _AuthCode:
    code: str
    donor_pid: str
    donor_full_name: str
    donor_country: str
    provider: str
    amount_centi: int
    program_id: str
    underlying_token: str
    redirect_uri: str
    state: str
    issued_at: float = field(default_factory=time.time)
    used: bool = False

    def is_expired(self) -> bool:
        return time.time() - self.issued_at > CODE_TTL_SEC


@dataclass
class _AccessToken:
    token: str
    donor_pid: str
    tier: int
    country: str
    issued_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.issued_at > TOKEN_TTL_SEC


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


# ============================================================
# /authorize (mock consent page)
# ============================================================


@router.get("/authorize", response_class=HTMLResponse)
def authorize(
    response_type: str = Query("code"),
    provider: str = Query(...),
    redirect_uri: str = Query(...),
    amount_centi: int = Query(...),
    program_id: str = Query(...),
    underlying_token: str = Query("USDC"),
    state: str = Query(...),
):
    if response_type != "code":
        raise HTTPException(400, "only response_type=code supported")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(400,
                             f"unknown provider; expected one of {SUPPORTED_PROVIDERS}")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "redirect_uri must be localhost (Mock mode)")
    if amount_centi <= 0:
        raise HTTPException(400, "amount_centi must be > 0")

    required_tier = tp.determine_required_tier(donation_amount_centi=amount_centi)

    return HTMLResponse(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{provider} OAuth Consent (Mock)</title>
<link rel="stylesheet" href="/ui/styles.css"></head>
<body style="padding:20px;max-width:680px;margin:auto">
<h2>{provider.title()} Donor OAuth (Mock)</h2>
<p class="note"><b>This is a mock.</b> Production flow integrates with {provider} OAuth.</p>
<dl style="background:#f7f7f7;padding:12px;border-radius:8px">
  <dt><b>Provider</b></dt><dd>{provider}</dd>
  <dt><b>Program</b></dt><dd>{program_id}</dd>
  <dt><b>Amount</b></dt><dd>{amount_centi / 100:.2f} {underlying_token}</dd>
  <dt><b>Required KYC tier</b></dt><dd>Tier {required_tier}</dd>
</dl>
<form method="post" action="/donor-oauth/v1/authorize/consent">
  <input type="hidden" name="redirect_uri" value="{redirect_uri}">
  <input type="hidden" name="state" value="{state}">
  <input type="hidden" name="provider" value="{provider}">
  <input type="hidden" name="amount_centi" value="{amount_centi}">
  <input type="hidden" name="program_id" value="{program_id}">
  <input type="hidden" name="underlying_token" value="{underlying_token}">
  <label>Full name<input name="full_name" required></label>
  <label>Email<input name="email" type="email" required></label>
  <label>Country (ISO-2)<input name="country" value="JP" required></label>
  <button type="submit" style="margin-top:12px">Consent & Donate</button>
</form>
</body></html>""")


# ============================================================
# /authorize/consent (POST)
# ============================================================


@router.post("/authorize/consent")
async def authorize_consent(request: Request, db: Session = Depends(_db)):
    form = await request.form()
    email = (form.get("email") or "").strip()
    full_name = (form.get("full_name") or "").strip()
    country = (form.get("country") or "JP").strip().upper()
    redirect_uri = form.get("redirect_uri") or ""
    state = form.get("state") or ""
    provider = form.get("provider") or ""
    amount_centi = int(form.get("amount_centi") or "0")
    program_id = form.get("program_id") or ""
    underlying_token = form.get("underlying_token") or "USDC"

    if not email or not full_name or amount_centi <= 0:
        raise HTTPException(400, "email + full_name + amount required")
    if not _validate_redirect_uri(redirect_uri):
        raise HTTPException(400, "bad redirect_uri")

    code = secrets.token_urlsafe(24)
    donor_pid = donor_pid_from_email(email)
    _codes[code] = _AuthCode(
        code=code, donor_pid=donor_pid,
        donor_full_name=full_name, donor_country=country,
        provider=provider, amount_centi=amount_centi,
        program_id=program_id, underlying_token=underlying_token,
        redirect_uri=redirect_uri, state=state,
    )
    sep = "&" if "?" in redirect_uri else "?"
    return JSONResponse({
        "redirect_to": f"{redirect_uri}{sep}code={code}&state={state}",
        "donor_pid": donor_pid,
    })


# ============================================================
# /token
# ============================================================


class TokenIn(BaseModel):
    grant_type: str = Field(..., description="must be 'authorization_code'")
    code: str
    redirect_uri: str
    provider: str
    ndrrmc_active: bool = False
    emergency_lgu: str | None = None


@router.post("/token")
def token(payload: TokenIn, db: Session = Depends(_db)) -> dict[str, Any]:
    if payload.grant_type != "authorization_code":
        raise HTTPException(400, "only grant_type=authorization_code supported")
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

    # donation 受理 (mock では tier 0 自動付与、本番では provider 経由で KYC pass-through)
    req = DonationRequest(
        donor_email=record.donor_pid,        # email は既に HMAC 済み
        donor_full_name=record.donor_full_name,
        donor_country=record.donor_country,
        amount_centi=record.amount_centi,
        program_id=record.program_id,
        underlying_token=record.underlying_token,
        ndrrmc_active=payload.ndrrmc_active,
        emergency_lgu=payload.emergency_lgu,
    )

    # tier policy で min tier に donor を upgrade (mock: 自動承認)
    required_tier = tp.determine_required_tier(donation_amount_centi=record.amount_centi)
    from app.models.donor import Donor
    donor = db.get(Donor, record.donor_pid)
    if donor is None:
        donor = Donor(
            pid=record.donor_pid,
            display_name_hash=hmac.new(b"display",
                                        record.donor_full_name.encode(),
                                        hashlib.sha256).hexdigest()[:16],
            country=record.donor_country,
            current_tier=required_tier,  # mock: 自動 upgrade
        )
        db.add(donor)
    else:
        donor.current_tier = max(donor.current_tier, required_tier)
    db.flush()

    result = receive_donation(db, req=req)

    access_token = secrets.token_urlsafe(32)
    _tokens[access_token] = _AccessToken(
        token=access_token, donor_pid=record.donor_pid,
        tier=donor.current_tier, country=record.donor_country,
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SEC,
        "donor_pid": record.donor_pid,
        "tier": donor.current_tier,
        "donation_outcome": result.outcome,
        "donation_id": result.donation_id,
        "cp8_bypass_entry_id": result.cp8_bypass_entry_id,
    }


# ============================================================
# /userinfo
# ============================================================


@router.get("/userinfo")
def userinfo(request: Request) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Authorization: Bearer required")
    tok = _tokens.get(auth.removeprefix("Bearer "))
    if tok is None or tok.is_expired():
        raise HTTPException(401, "invalid or expired token")
    return {
        "donor_pid": tok.donor_pid,
        "tier": tok.tier,
        "country": tok.country,
        "issued_at": tok.issued_at,
        "_mock": True,
    }


@router.get("/_/state")
def debug_state() -> dict[str, int]:
    return {"codes": len(_codes), "tokens": len(_tokens)}
