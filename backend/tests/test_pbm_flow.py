"""エンドツーエンドの PBM フローを API 経由で検証する。"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _login(maina_id: str, ward: str = "新宿区", dob: str = "1955-03-12", gender: str = "M") -> str:
    r = client.post("/auth/myna/login", json={
        "maina_id": maina_id,
        "name": "テスト 太郎",
        "address": f"東京都{ward}1-1-1",
        "ward": ward,
        "dob": dob,
        "gender": gender,
    })
    assert r.status_code == 200, r.text
    return r.json()["pid"]


def _create_program(**overrides):
    payload = {
        "id": overrides.get("id", "prog-test-eco"),
        "name": "テスト省エネプログラム",
        "description": "test",
        "budget_jpy": 1_000_000,
        "subsidy_bps": 3000,
        "per_citizen_cap_jpy": 50_000,
        "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "end_at":   (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "eligibility": {"wards": ["新宿区"]},
        "eligible_jans": ["4901234567890"],
        "approved_stores": ["store-a"],
    }
    payload.update(overrides)
    r = client.post("/programs", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _setup_catalog():
    client.post("/products", json={"jan": "4901234567890", "name": "省エネエアコン", "category": "appliance.air_conditioner", "price_jpy": 100_000})
    client.post("/products", json={"jan": "4999999999999", "name": "対象外商品", "category": "other", "price_jpy": 5_000})
    client.post("/stores", json={"id": "store-a", "name": "テスト店舗", "ward": "新宿区"})


def test_happy_path_grants_subsidy_and_records_ebpm():
    _setup_catalog()
    client.post("/wallet/treasury/topup", json={"amount_jpy": 5_000_000})
    _create_program()
    pid = _login("MN-T01")
    client.post("/wallet/citizen/" + pid + "/topup", json={"amount_jpy": 200_000})

    # PBM 発行
    r = client.post("/programs/prog-test-eco/issue", json={"citizen_pid": pid})
    assert r.status_code == 200, r.text
    issued = r.json()
    assert issued["remaining_jpy"] == 50_000

    # 購入: 100,000 円 × 30% = 30,000 円が PBM から、残 70,000 円が住民負担
    r = client.post("/purchase", json={
        "citizen_pid": pid,
        "store_id": "store-a",
        "jan": "4901234567890",
        "qty": 1,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_jpy"] == 100_000
    assert body["subsidy_jpy"] == 30_000
    assert body["citizen_pay_jpy"] == 70_000

    # 加盟店残高 = 100_000
    store_bal = client.get("/wallet/store/store-a").json()["jpyc_balance"]
    assert store_bal == 100_000

    # 住民残高 = 200_000 - 70_000
    citizen_bal = client.get("/wallet/citizen/" + pid).json()["jpyc_balance"]
    assert citizen_bal == 130_000

    # EBPM 集計
    summary = client.get("/ebpm/summary").json()
    assert summary[0]["program_id"] == "prog-test-eco"
    assert summary[0]["subsidy_jpy"] == 30_000


def test_subsidy_caps_at_per_citizen_limit():
    _setup_catalog()
    client.post("/wallet/treasury/topup", json={"amount_jpy": 5_000_000})
    _create_program(per_citizen_cap_jpy=20_000)
    pid = _login("MN-T02")
    client.post("/wallet/citizen/" + pid + "/topup", json={"amount_jpy": 500_000})
    client.post("/programs/prog-test-eco/issue", json={"citizen_pid": pid})

    r = client.post("/purchase", json={
        "citizen_pid": pid,
        "store_id": "store-a",
        "jan": "4901234567890",
        "qty": 1,
    }).json()
    # raw 30,000 だが per_citizen_cap=20,000 で抑えられる
    assert r["subsidy_jpy"] == 20_000
    assert r["citizen_pay_jpy"] == 80_000


def test_non_eligible_jan_is_no_subsidy():
    _setup_catalog()
    client.post("/wallet/treasury/topup", json={"amount_jpy": 5_000_000})
    _create_program()
    pid = _login("MN-T03")
    client.post("/wallet/citizen/" + pid + "/topup", json={"amount_jpy": 50_000})
    client.post("/programs/prog-test-eco/issue", json={"citizen_pid": pid})

    # 対象外 JAN
    r = client.post("/purchase", json={
        "citizen_pid": pid,
        "store_id": "store-a",
        "jan": "4999999999999",
        "qty": 1,
    }).json()
    assert r["subsidy_jpy"] == 0
    assert r["citizen_pay_jpy"] == 5_000


def test_non_resident_cannot_get_pbm():
    _setup_catalog()
    client.post("/wallet/treasury/topup", json={"amount_jpy": 5_000_000})
    _create_program()
    pid = _login("MN-T04", ward="横浜市")  # 都外
    r = client.post("/programs/prog-test-eco/issue", json={"citizen_pid": pid})
    assert r.status_code == 400
    assert "対象外" in r.json()["detail"]


def test_revoke_program_blocks_future_purchases():
    _setup_catalog()
    client.post("/wallet/treasury/topup", json={"amount_jpy": 5_000_000})
    _create_program()
    pid = _login("MN-T05")
    client.post("/wallet/citizen/" + pid + "/topup", json={"amount_jpy": 200_000})
    client.post("/programs/prog-test-eco/issue", json={"citizen_pid": pid})

    client.delete("/programs/prog-test-eco")

    r = client.post("/purchase", json={
        "citizen_pid": pid,
        "store_id": "store-a",
        "jan": "4901234567890",
        "qty": 1,
    }).json()
    assert r["subsidy_jpy"] == 0  # プログラム取消で助成なし
    assert r["citizen_pay_jpy"] == 100_000
