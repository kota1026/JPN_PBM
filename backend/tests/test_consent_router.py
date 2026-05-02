"""routers/consent.py の統合テスト。"""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_grant_rejects_raw_pid():
    r = client.post("/consent/grant", json={
        "pid": "MN-0001",  # 生 ID
        "program_id": "prog-koto-kosodate-2026",
        "consent_text": "東京都が JPYC 給付に必要な範囲で 4 情報を取得することに同意します",
        "scope": ["family_register.basic_4"],
    })
    assert r.status_code == 400
    assert "CP-2" in r.json()["detail"]


def test_grant_then_list_then_revoke():
    pid = hashlib.sha256(b"MN-CONSENT-1").hexdigest()
    text = "東京都が JPYC 給付に必要な範囲で 4 情報を取得することに同意します"

    r = client.post("/consent/grant", json={
        "pid": pid,
        "program_id": "prog-koto-kosodate-2026",
        "consent_text": text,
        "scope": ["family_register.basic_4", "address.ward"],
    })
    assert r.status_code == 200
    granted = r.json()
    assert granted["consent_text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert granted["revoked_at"] is None

    # 一覧取得
    rows = client.get(f"/consent/{pid}").json()
    assert len(rows) == 1
    assert rows[0]["program_id"] == "prog-koto-kosodate-2026"

    # 撤回
    r = client.post(f"/consent/{granted['id']}/revoke", json={"reason": "本人申し出"})
    assert r.status_code == 200
    revoked = r.json()
    assert revoked["revoked_at"] is not None
    assert revoked["revoke_reason"] == "本人申し出"

    # 二重撤回は 409
    r = client.post(f"/consent/{granted['id']}/revoke", json={"reason": "二重撤回"})
    assert r.status_code == 409


def test_stats_endpoint_counts_active_and_revoked():
    pid = hashlib.sha256(b"MN-CONSENT-STATS").hexdigest()
    for i in range(3):
        client.post("/consent/grant", json={
            "pid": pid,
            "program_id": f"prog-{i}",
            "consent_text": "AAAAAAAAAA",
            "scope": [],
        })
    # 1 件取消
    rows = client.get(f"/consent/{pid}").json()
    client.post(f"/consent/{rows[0]['id']}/revoke", json={"reason": "test"})

    stats = client.get("/consent/_/stats").json()
    assert stats["total"] >= 3
    assert stats["revoked"] >= 1
    assert stats["active"] >= 2
