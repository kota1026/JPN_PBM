"""PhilSys OAuth Mock のテスト (戦略会議 #12 採択 T2)。

Authorization Code Grant の通しフロー (authorize → consent → token → userinfo) と
リプレイ防止・期限切れ・redirect_uri ミスマッチ・Tagalog/English 切替を検証。
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app
from app.routers import philsys_oauth as mod


client = TestClient(app)


def setup_function():
    """各テストの前にプロセス内ストアをクリア。"""
    mod._codes.clear()
    mod._tokens.clear()


# ============================================================
# /authorize
# ============================================================


def test_authorize_html_tagalog_default():
    r = client.get("/philsys/v1/authorize", params={
        "response_type": "code",
        "client_id": mod.CLIENT_ID,
        "redirect_uri": "http://localhost:8000/cb",
        "scope": mod.DEFAULT_SCOPE,
        "state": "abc123",
    })
    assert r.status_code == 200
    # Tagalog default
    assert "Pahintulot" in r.text
    assert "Mock" in r.text


def test_authorize_html_english_when_locale_en():
    r = client.get("/philsys/v1/authorize", params={
        "client_id": mod.CLIENT_ID,
        "redirect_uri": "http://localhost:8000/cb",
        "state": "abc123",
        "locale": "en",
    })
    assert r.status_code == 200
    assert "Consent" in r.text
    assert "Pahintulot" not in r.text


def test_authorize_rejects_bad_redirect():
    r = client.get("/philsys/v1/authorize", params={
        "client_id": mod.CLIENT_ID,
        "redirect_uri": "https://evil.example.com/cb",
        "state": "abc",
    })
    assert r.status_code == 400


def test_authorize_rejects_unknown_client():
    r = client.get("/philsys/v1/authorize", params={
        "client_id": "unknown",
        "redirect_uri": "http://localhost:8000/cb",
        "state": "abc",
    })
    assert r.status_code == 400


def test_authorize_rejects_invalid_locale():
    r = client.get("/philsys/v1/authorize", params={
        "client_id": mod.CLIENT_ID,
        "redirect_uri": "http://localhost:8000/cb",
        "state": "abc",
        "locale": "fr",
    })
    assert r.status_code == 400


# ============================================================
# /authorize/consent → /token → /userinfo の通し
# ============================================================


def _consent(redirect_uri="http://localhost:8000/cb",
             psn="PH-0001", program="prog-4ps-2026",
             locale="tl") -> str:
    r = client.post("/philsys/v1/authorize/consent", data={
        "psn": psn,
        "redirect_uri": redirect_uri,
        "state": "stateXYZ",
        "scope": mod.DEFAULT_SCOPE,
        "program_id": program,
        "consent_text_sha256": "deadbeef" * 8,
        "locale": locale,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    return body["redirect_to"].split("code=")[1].split("&")[0]


def test_full_oauth_flow_returns_pid_and_locale():
    code = _consent(locale="tl")
    r = client.post("/philsys/v1/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/cb",
        "client_id": mod.CLIENT_ID,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == mod.TOKEN_TTL_SEC
    assert body["locale"] == "tl"
    pid = body["pid"]
    access_token = body["access_token"]

    # userinfo
    u = client.get("/philsys/v1/userinfo", headers={
        "Authorization": "Bearer " + access_token,
    })
    assert u.status_code == 200
    info = u.json()
    assert info["pid"] == pid
    assert info["locale"] == "tl"
    assert info["_mock"] is True
    assert info["_data_privacy_act_compliance"] == "RA 10173 (PH)"


def test_consent_writes_consent_log():
    """ConsentLog テーブルに行が確実に書かれる (Data Privacy Act 監査)。"""
    from app.db import get_session
    from app.models.consent import ConsentLog
    from sqlalchemy import select

    db = get_session()
    try:
        before = db.execute(select(ConsentLog)).scalars().all()
    finally:
        db.close()

    _consent(psn="PH-0099")

    db = get_session()
    try:
        after = db.execute(select(ConsentLog)).scalars().all()
    finally:
        db.close()
    assert len(after) == len(before) + 1


def test_token_replay_protection():
    code = _consent()
    body = {
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:8000/cb", "client_id": mod.CLIENT_ID,
    }
    r1 = client.post("/philsys/v1/token", json=body)
    assert r1.status_code == 200
    r2 = client.post("/philsys/v1/token", json=body)
    assert r2.status_code == 400  # already used


def test_token_redirect_mismatch_rejected():
    code = _consent(redirect_uri="http://localhost:8000/cb")
    r = client.post("/philsys/v1/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:9999/different", "client_id": mod.CLIENT_ID,
    })
    assert r.status_code == 400


def test_token_expired_code_rejected(monkeypatch):
    code = _consent()
    rec = mod._codes[code]
    # 有効期限を強制的に過去にする
    rec.issued_at = time.time() - mod.CODE_TTL_SEC - 1
    r = client.post("/philsys/v1/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:8000/cb", "client_id": mod.CLIENT_ID,
    })
    assert r.status_code == 400
    assert "expired" in r.text


def test_userinfo_requires_bearer():
    r = client.get("/philsys/v1/userinfo")
    assert r.status_code == 401


def test_jp_and_ph_pid_share_same_hmac_for_same_input():
    """戦略会議 #12: JP / PH provider は privacy.pseudonymize() で同形。"""
    from app.services.privacy import pseudonymize
    p1 = pseudonymize("PH-0001")
    p2 = pseudonymize("PH-0001")
    assert p1 == p2  # idempotent
    p3 = pseudonymize("PH-0002")
    assert p1 != p3
