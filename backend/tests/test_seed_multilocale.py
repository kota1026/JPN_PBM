"""Multi-locale seed loader テスト (戦略会議 #13 採択 T1)。

JP デフォルト互換 + PH locale 投入を検証。
conftest.py が autouse で各テスト前に DB をリセットするので、テスト間の干渉は無い。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_session
from app.models.store import Store


client = TestClient(app)


# ============================================================
# 既存 JP デフォルトの互換性
# ============================================================


def test_jp_default_load_unchanged():
    r = client.post("/seed/load")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"]
    assert body["locale"] == "jp"
    assert body["loaded"]["citizens"] == 10
    assert body["loaded"]["products"] >= 30
    assert len(body["pid_map"]) == 10


def test_jp_explicit_locale():
    """既存のクライアントが ?locale=jp を渡しても従来通り動く。"""
    r = client.post("/seed/load?locale=jp")
    assert r.status_code == 200
    assert r.json()["locale"] == "jp"


# ============================================================
# PH 投入
# ============================================================


def test_ph_load_creates_8_citizens_25_products():
    r = client.post("/seed/load?locale=ph")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"]
    assert body["locale"] == "ph"
    assert body["loaded"]["citizens"] == 8
    assert body["loaded"]["products"] == 25
    assert body["loaded"]["stores"] == 8
    assert body["loaded"]["programs"] == 2
    assert "PH-0001" in body["pid_map"]
    assert len(body["pid_map"]["PH-0001"]) == 64  # SHA256 hex


def test_ph_store_carries_mcc_and_qr_ph_id():
    client.post("/seed/load?locale=ph")
    db = get_session()
    try:
        s = db.get(Store, "ph-store-aling-maria-qc")
        assert s is not None
        assert s.mcc == 5411
        assert s.qr_ph_id == "MERCHANT-MARIA-QC-001"
        s2 = db.get(Store, "ph-store-blocked-liquor")
        assert s2.mcc == 5921
    finally:
        db.close()


def test_ph_4ps_program_loaded():
    client.post("/seed/load?locale=ph")
    r = client.get("/programs")
    assert r.status_code == 200
    programs = {p["id"]: p for p in r.json()}
    assert "prog-4ps-2026" in programs
    p = programs["prog-4ps-2026"]
    assert p["subsidy_bps"] == 6000   # 60% subsidy
    assert p["per_citizen_cap_jpy"] == 140000  # PHP 1,400 = 140000 centavos


def test_ph_load_idempotent():
    """二度叩いても重複行を作らない。"""
    r1 = client.post("/seed/load?locale=ph")
    r2 = client.post("/seed/load?locale=ph")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # programs エンドポイントが 2 件 (重複なし) を返す
    programs = client.get("/programs").json()
    ph_progs = [p for p in programs if p["id"].startswith("prog-4ps") or p["id"].startswith("prog-disaster-typhoon")]
    assert len(ph_progs) == 2


def test_unknown_locale_rejected():
    r = client.post("/seed/load?locale=xx")
    assert r.status_code == 400
    assert "unknown locale" in r.text


# ============================================================
# JP + PH の coexistence (両方ロードしても衝突しない)
# ============================================================


def test_jp_then_ph_coexist():
    r1 = client.post("/seed/load?locale=jp")
    r2 = client.post("/seed/load?locale=ph")
    assert r1.status_code == 200
    assert r2.status_code == 200
    programs = {p["id"]: p for p in client.get("/programs").json()}
    assert "prog-koto-kosodate-2026" in programs  # JP
    assert "prog-4ps-2026" in programs            # PH
