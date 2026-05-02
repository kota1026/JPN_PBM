"""戦略会議 #2 採択 #4 (準備金監査) + #8 (peg monitor) の統合テスト。

カバレッジ:
- /treasury/audit が JPYC 残高 + PBM outstanding を正しく集計する
- /treasury/audit がトークン過剰発行を検出してアラートする
- peg monitor が ALERT / AUTO-FREEZE 閾値で正しく状態遷移する
- 手動 freeze/unfreeze が REST 経由で動く
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models.pbm import PBMToken
from app.models.program import Program
from app.services import peg_monitor
from app.services.peg_monitor import PegMonitor


client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_peg():
    peg_monitor.reset_for_test()
    yield
    peg_monitor.reset_for_test()


# ----------------------------- 準備金監査 -----------------------------


def _login(maina_id: str, ward: str = "新宿区") -> str:
    r = client.post("/auth/myna/login", json={
        "maina_id": maina_id, "name": "T", "address": "x", "ward": ward,
        "dob": "1985-01-01", "gender": "M",
    })
    assert r.status_code == 200
    return r.json()["pid"]


def test_audit_with_no_activity_is_healthy():
    body = client.get("/treasury/audit").json()
    assert body["healthy"] is True
    assert body["totals"]["sum_balances_jpy"] == 0
    assert body["pbm"]["program_outstanding_jpy"] == 0
    assert body["alerts"] == []


def test_audit_after_topup_and_program_creation():
    client.post("/wallet/treasury/topup", json={"amount_jpy": 1_000_000})
    pid = _login("MN-AUD")
    client.post(f"/wallet/citizen/{pid}/topup", json={"amount_jpy": 50_000})
    client.post("/products", json={
        "jan": "4912345678907", "name": "対象", "category": "food.daily", "price_jpy": 5_000,
    })
    client.post("/stores", json={"id": "store-aud", "name": "A", "ward": "新宿区"})
    client.post("/programs", json={
        "id": "prog-aud", "name": "aud", "description": "x",
        "budget_jpy": 200_000, "subsidy_bps": 5000, "per_citizen_cap_jpy": 10_000,
        "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "end_at": (datetime.utcnow() + timedelta(days=10)).isoformat(),
        "eligibility": {"wards": ["新宿区"]},
        "eligible_jans": [], "eligible_categories": ["food.daily"],
        "approved_stores": ["store-aud"],
    })
    client.post("/programs/prog-aud/issue", json={"citizen_pid": pid})

    body = client.get("/treasury/audit").json()
    assert body["totals"]["treasury_balance_jpy"] == 1_000_000
    assert body["totals"]["citizen_balance_jpy"] == 50_000
    assert body["pbm"]["program_budgets_jpy"] == 200_000
    # token は per_citizen_cap = 10_000 が 1 つ発行された
    assert body["pbm"]["issued_token_remaining_jpy"] == 10_000
    # outstanding (200_000) - issued (10_000) = 余剰 → 異常ではない
    assert body["alerts"] == []
    assert body["healthy"] is True


def test_audit_detects_token_over_issuance():
    """token 残量が program outstanding を超過する状態を仕込み、アラートを確認。"""
    db = get_session()
    try:
        prog = Program(
            id="prog-over", name="over", description="x",
            budget_jpy=10_000, spent_jpy=8_000,  # outstanding = 2_000
            subsidy_bps=10_000, per_citizen_cap_jpy=10_000,
            start_at=datetime.utcnow() - timedelta(days=1),
            end_at=datetime.utcnow() + timedelta(days=10),
            eligibility={}, eligible_jans=[], approved_stores=[],
        )
        db.add(prog)
        db.flush()
        # token 残量合計 = 5_000 > outstanding 2_000 → 異常
        for i in range(2):
            db.add(PBMToken(
                id=f"t-over-{i}", program_id="prog-over", holder_pid=("o" + str(i)).ljust(64, "0"),
                remaining_jpy=2_500, status="ISSUED",
                expires_at=datetime.utcnow() + timedelta(days=5),
            ))
        db.commit()
    finally:
        db.close()

    body = client.get("/treasury/audit").json()
    assert body["healthy"] is False
    assert any("over-issuance" in a for a in body["alerts"])
    assert body["diffs"]["pbm_outstanding_diff"] == 5_000 - 2_000


# ----------------------------- peg monitor -----------------------------


def test_peg_monitor_healthy_within_window():
    m = PegMonitor()
    s = m.submit(1.0)
    assert s.healthy and not s.frozen
    s = m.submit(1.005)  # +50bps
    assert s.healthy


def test_peg_monitor_alert_at_1_percent():
    m = PegMonitor(alert_bps=100, freeze_bps=300)
    s = m.submit(1.012)  # +120bps
    assert not s.healthy
    assert not s.frozen
    assert any("ALERT" in a for a in s.alerts)


def test_peg_monitor_auto_freeze_at_3_percent():
    m = PegMonitor(alert_bps=100, freeze_bps=300)
    s = m.submit(0.965)  # -350bps
    assert s.frozen
    assert any("AUTO-FREEZE" in a for a in s.alerts)
    # 一度 freeze されたら回復スポットでも frozen のまま
    s2 = m.submit(1.0)
    assert s2.frozen


def test_peg_monitor_manual_unfreeze():
    m = PegMonitor()
    m.submit(0.95)  # auto freeze (5%)
    assert m.is_frozen
    msg = m.manual_unfreeze(by="soc-001", reason="JPYC 株式会社が裏付資産を増強")
    assert "MANUAL-UNFREEZE" in msg
    assert not m.is_frozen


def test_peg_rest_e2e():
    """REST 経由でサンプル投入 → ステータス取得 → manual freeze/unfreeze。"""
    r = client.post("/treasury/peg/sample", json={"spot_jpy_per_jpyc": 1.001})
    assert r.status_code == 200
    body = r.json()
    assert body["healthy"] is True
    assert body["last_sample"]["deviation_bps"] == 10

    # アラート閾値を超える
    r = client.post("/treasury/peg/sample", json={"spot_jpy_per_jpyc": 1.02})
    assert r.json()["healthy"] is False  # alert ではあるが auto-freeze ではない
    assert r.json()["frozen"] is False

    # 手動 freeze
    r = client.post("/treasury/peg/freeze", json={
        "by": "tokyo-soc-001", "reason": "予防的停止",
    })
    assert r.status_code == 200

    # 解除
    r = client.post("/treasury/peg/unfreeze", json={
        "by": "tokyo-soc-001", "reason": "状況確認 OK",
    })
    assert r.status_code == 200
    assert "MANUAL-UNFREEZE" in r.json()["result"]

    # frozen でない時に unfreeze は 409
    r = client.post("/treasury/peg/unfreeze", json={
        "by": "tokyo-soc-001", "reason": "noop",
    })
    assert r.status_code == 409
