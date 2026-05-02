"""マイナポータル v2 OAuth Mock のテスト (戦略会議 #4 採択 #4)。

Authorization Code Grant の通しフロー (authorize → consent → token → userinfo) と
リプレイ防止・期限切れ・redirect_uri ミスマッチを検証。
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app
from app.routers import myna_oauth as mod


client = TestClient(app)


def setup_function():
    """各テストの前にプロセス内ストアをクリア。"""
    mod._codes.clear()
    mod._tokens.clear()


def test_authorize_html_returned():
    r = client.get("/myna/v2/authorize", params={
        "response_type": "code",
        "client_id": mod.CLIENT_ID,
        "redirect_uri": "http://localhost:8000/cb",
        "scope": "family_register.basic_4",
        "state": "abc123",
    })
    assert r.status_code == 200
    assert "マイナポータル v2 同意" in r.text


def test_authorize_rejects_bad_redirect():
    r = client.get("/myna/v2/authorize", params={
        "client_id": mod.CLIENT_ID, "redirect_uri": "https://evil.example.com/cb",
        "scope": "x", "state": "s",
    })
    assert r.status_code == 400


def test_full_oauth_flow_writes_consent_log_and_returns_userinfo():
    # 1) consent POST → code 取得 + ConsentLog 書き込み
    r = client.post("/myna/v2/authorize/consent", data={
        "maina_id": "MN-OAUTH-1",
        "redirect_uri": "http://localhost:8000/cb",
        "state": "state-abc",
        "scope": "family_register.basic_4 address.ward",
        "program_id": "prog-koto-kosodate-2026",
        "consent_text_sha256": "deadbeef" * 8,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "code=" in body["redirect_to"]
    code = body["redirect_to"].split("code=")[1].split("&")[0]
    consent_id = body["consent_id"]

    # 1.5) ConsentLog が GET /consent/{pid} で見える
    # pid は HMAC で計算済 (privacy.pseudonymize)
    from app.services.privacy import pseudonymize
    pid = pseudonymize("MN-OAUTH-1")
    consent_rows = client.get(f"/consent/{pid}").json()
    assert any(c["id"] == consent_id for c in consent_rows)

    # 2) token 交換
    r = client.post("/myna/v2/token", json={
        "grant_type": "authorization_code",
        "code": code, "redirect_uri": "http://localhost:8000/cb",
        "client_id": mod.CLIENT_ID,
    })
    assert r.status_code == 200, r.text
    tok = r.json()
    assert tok["token_type"] == "Bearer"
    assert tok["pid"] == pid
    access = tok["access_token"]

    # 3) userinfo
    r = client.get("/myna/v2/userinfo", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    info = r.json()
    assert info["pid"] == pid
    assert "family_register.basic_4" in info["scope"]


def test_token_replay_rejected():
    # consent → code 発行
    r = client.post("/myna/v2/authorize/consent", data={
        "maina_id": "MN-REPLAY",
        "redirect_uri": "http://localhost:8000/cb",
        "state": "x", "scope": "s",
        "program_id": "p", "consent_text_sha256": "0" * 64,
    })
    code = r.json()["redirect_to"].split("code=")[1].split("&")[0]

    # 1 回目 OK
    r1 = client.post("/myna/v2/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:8000/cb", "client_id": mod.CLIENT_ID,
    })
    assert r1.status_code == 200

    # 2 回目 (リプレイ) は拒否
    r2 = client.post("/myna/v2/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:8000/cb", "client_id": mod.CLIENT_ID,
    })
    assert r2.status_code == 400
    assert "used" in r2.json()["detail"]


def test_userinfo_requires_bearer():
    r = client.get("/myna/v2/userinfo")
    assert r.status_code == 401


def test_token_redirect_uri_mismatch():
    r = client.post("/myna/v2/authorize/consent", data={
        "maina_id": "MN-X", "redirect_uri": "http://localhost:8000/cb",
        "state": "s", "scope": "x",
        "program_id": "p", "consent_text_sha256": "0" * 64,
    })
    code = r.json()["redirect_to"].split("code=")[1].split("&")[0]
    r2 = client.post("/myna/v2/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://evil.example/cb",  # ミスマッチ → 既に validate_redirect で 400
        "client_id": mod.CLIENT_ID,
    })
    assert r2.status_code == 400


def test_code_expiry(monkeypatch):
    """expired code が 400 を返す。"""
    r = client.post("/myna/v2/authorize/consent", data={
        "maina_id": "MN-EXP", "redirect_uri": "http://localhost:8000/cb",
        "state": "s", "scope": "x",
        "program_id": "p", "consent_text_sha256": "0" * 64,
    })
    code = r.json()["redirect_to"].split("code=")[1].split("&")[0]

    # code の issued_at を強制的に古くする
    rec = mod._codes[code]
    rec.issued_at = time.time() - mod.CODE_TTL_SEC - 10

    r2 = client.post("/myna/v2/token", json={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": "http://localhost:8000/cb", "client_id": mod.CLIENT_ID,
    })
    assert r2.status_code == 400
    assert "expired" in r2.json()["detail"]
