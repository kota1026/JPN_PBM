"""戦略会議 #2 採択分の統合テスト。

カバレッジ:
- #1 purpose_guard: CP-1〜CP-6 を runtime で deny できる
- #2 pbm.py: 複数 program がマッチした際に subsidy 最大の program が選ばれる
- #6 sweeper: 期限切れ token のみが EXPIRED に、未満は ISSUED のまま
- #7 routers/offline: coupon 発行 → POS 給付 → batch 精算 → EBPM 書き戻し
- #9 EBPM CP-2: k-匿名性違反のセルは '-' に丸まる (個票漏れなし)
- #10 consent: ConsentLog モデルが永続化できる
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models.citizen import Citizen
from app.models.consent import ConsentLog
from app.models.pbm import PBMToken
from app.models.product import Product
from app.models.program import Program
from app.models.store import Store
from app.services import purpose_guard
from app.services.purpose_guard import (
    Decision,
    cp1_purpose_match,
    cp2_no_personal_info_in_aggregate,
    cp2_pid_is_pseudonymized,
    cp4_audit_event_complete,
    cp5_double_spend,
    cp5_store_authorized,
    cp6_offline_signature_required,
    guard_offline_redemption,
    guard_spend,
)
from app.services.sweeper import sweep_expired_tokens, sweep_program_revoked


client = TestClient(app)


# ----------------------------- #1 purpose_guard 単体 -----------------------------


def test_cp1_purpose_match_jan_in_eligible():
    prog = _prog(eligible_jans=["4901234567890"], eligible_categories=[])
    prod = _prod(jan="4901234567890", category="appliance.air_conditioner")
    assert cp1_purpose_match(prod, prog).ok


def test_cp1_purpose_match_category():
    prog = _prog(eligible_jans=[], eligible_categories=["appliance.air_conditioner"])
    prod = _prod(category="appliance.air_conditioner")
    assert cp1_purpose_match(prod, prog).ok


def test_cp1_excluded_overrides_category():
    prog = _prog(eligible_categories=["appliance.air_conditioner"], excluded_jans=["4901234567890"])
    prod = _prod(jan="4901234567890", category="appliance.air_conditioner")
    d = cp1_purpose_match(prod, prog)
    assert not d.ok and d.code == "CP-1.excluded"


def test_cp1_purpose_mismatch_denied():
    prog = _prog(eligible_categories=["food.baby"])
    prod = _prod(category="appliance.air_conditioner")
    d = cp1_purpose_match(prod, prog)
    assert not d.ok and d.code == "CP-1.purpose_mismatch"


def test_cp2_pseudonymization_format():
    valid = "a" * 64
    assert cp2_pid_is_pseudonymized(valid).ok
    # 短すぎ
    assert not cp2_pid_is_pseudonymized("MN-0001").ok
    # 長さは合うが非 hex
    assert not cp2_pid_is_pseudonymized("z" * 64).ok


def test_cp2_k_anonymity():
    rows = [{"key": "a", "count": 5}, {"key": "b", "count": 10}]
    assert cp2_no_personal_info_in_aggregate(rows).ok
    bad = [{"key": "a", "count": 3}]
    d = cp2_no_personal_info_in_aggregate(bad)
    assert not d.ok and d.code == "CP-2.k_anonymity"


def test_cp4_audit_event_required_fields():
    full = {
        "program_id": "p", "jan": "4900000000000", "total_jpy": 1, "subsidy_jpy": 0,
        "citizen_pid": "x" * 64, "store_id": "s",
    }
    assert cp4_audit_event_complete(full).ok
    bad = {k: v for k, v in full.items() if k != "store_id"}
    d = cp4_audit_event_complete(bad)
    assert not d.ok and d.code == "CP-4.missing"


def test_cp5_double_spend_bounds():
    tok = _tok(remaining_jpy=1000)
    assert cp5_double_spend(tok, 1000).ok
    assert not cp5_double_spend(tok, 1001).ok
    assert not cp5_double_spend(tok, 0).ok


def test_cp5_store_unauthorized():
    prog = _prog(approved_stores=["store-a"])
    store = _store(id="store-rogue")
    d = cp5_store_authorized(store, prog)
    assert not d.ok and d.code == "CP-5.unauthorized_store"


def test_cp6_signature_required():
    assert cp6_offline_signature_required(True).ok
    d = cp6_offline_signature_required(False)
    assert not d.ok and d.code == "CP-6.no_sig"


def test_guard_spend_full_pipeline_allow():
    prog = _prog(eligible_categories=["food.baby"], approved_stores=["store-a"])
    citizen = _citizen()
    tok = _tok(remaining_jpy=10000)
    store = _store(id="store-a")
    prod = _prod(category="food.baby")
    d = guard_spend(
        citizen=citizen, program=prog, token=tok, store=store, product=prod,
        requested_subsidy_jpy=5000,
    )
    assert d.ok


def test_guard_spend_denies_revoked_program():
    prog = _prog(approved_stores=["store-a"])
    prog.revoked = True
    citizen = _citizen()
    tok = _tok()
    store = _store(id="store-a")
    prod = _prod(category="food.baby")
    d = guard_spend(
        citizen=citizen, program=prog, token=tok, store=store, product=prod,
        requested_subsidy_jpy=1,
    )
    assert not d.ok and "revoked" in d.code.lower()


def test_guard_offline_redemption_blocks_raw_pid():
    """オフライン経路での CP-2 漏れ検出 (Red Team #7 対応)。"""
    audit = {"program_id": "p", "jan": "X", "total_jpy": 1, "subsidy_jpy": 1, "citizen_pid": "MN-0001", "store_id": "s"}
    d = guard_offline_redemption(pid="MN-0001", has_signature=True, audit_event=audit)
    assert not d.ok and d.code == "CP-2.raw_id"


# ----------------------------- #2 pbm.py: 最も住民有利 -----------------------------


def test_pbm_chooses_program_with_largest_subsidy():
    """同じ JAN で 30% プログラムと 50% プログラムが同時に有効な場合、50% が選ばれる。"""
    client.post("/products", json={"jan": "4901111111118", "name": "対象品", "category": "food.daily", "price_jpy": 10_000})
    client.post("/stores", json={"id": "store-best", "name": "ベスト店", "ward": "新宿区"})
    client.post("/wallet/treasury/topup", json={"amount_jpy": 10_000_000})

    base = dict(
        description="x",
        budget_jpy=1_000_000,
        per_citizen_cap_jpy=50_000,
        start_at=(datetime.utcnow() - timedelta(days=1)).isoformat(),
        end_at=(datetime.utcnow() + timedelta(days=30)).isoformat(),
        eligibility={"wards": ["新宿区"]},
        eligible_jans=[],
        eligible_categories=["food.daily"],
        approved_stores=["store-best"],
    )
    client.post("/programs", json={"id": "prog-30", "name": "30%", "subsidy_bps": 3000, **base})
    client.post("/programs", json={"id": "prog-50", "name": "50%", "subsidy_bps": 5000, **base})

    pid = _login("MN-BEST", ward="新宿区")
    client.post(f"/wallet/citizen/{pid}/topup", json={"amount_jpy": 500_000})
    client.post("/programs/prog-30/issue", json={"citizen_pid": pid})
    client.post("/programs/prog-50/issue", json={"citizen_pid": pid})

    r = client.post("/purchase", json={
        "citizen_pid": pid, "store_id": "store-best", "jan": "4901111111118", "qty": 1,
    }).json()
    # 50% プログラムが選ばれて 5,000 助成、3% プログラムは選ばれない
    assert r["subsidy_jpy"] == 5_000


# ----------------------------- #6 sweeper -----------------------------


def test_sweeper_only_expires_past_tokens():
    db = get_session()
    try:
        prog = Program(
            id="prog-sw", name="sw", description="",
            budget_jpy=100_000, subsidy_bps=10_000, per_citizen_cap_jpy=10_000,
            start_at=datetime.utcnow() - timedelta(days=10),
            end_at=datetime.utcnow() + timedelta(days=10),
            eligibility={}, eligible_jans=[], approved_stores=[],
        )
        db.add(prog)
        db.flush()
        # 期限切れ
        db.add(PBMToken(
            id="t-old", program_id="prog-sw", holder_pid="x" * 64,
            remaining_jpy=3_000, status="ISSUED",
            expires_at=datetime.utcnow() - timedelta(seconds=10),
        ))
        # 未来の token (まだ有効)
        db.add(PBMToken(
            id="t-future", program_id="prog-sw", holder_pid="y" * 64,
            remaining_jpy=4_000, status="ISSUED",
            expires_at=datetime.utcnow() + timedelta(days=1),
        ))
        db.commit()

        report = sweep_expired_tokens(db)
        assert report.swept_token_ids == ["t-old"]
        assert report.refunded_jpy_by_program["prog-sw"] == 3_000
        # 未来 token は残る
        live = db.get(PBMToken, "t-future")
        assert live.status == "ISSUED"
    finally:
        db.close()


def test_sweeper_dry_run_does_not_mutate():
    db = get_session()
    try:
        prog = Program(
            id="prog-dry", name="dry", description="",
            budget_jpy=100_000, subsidy_bps=10_000, per_citizen_cap_jpy=10_000,
            start_at=datetime.utcnow() - timedelta(days=1),
            end_at=datetime.utcnow() + timedelta(days=1),
            eligibility={}, eligible_jans=[], approved_stores=[],
        )
        db.add(prog)
        db.flush()
        db.add(PBMToken(
            id="t-old2", program_id="prog-dry", holder_pid="z" * 64,
            remaining_jpy=2_000, status="ISSUED",
            expires_at=datetime.utcnow() - timedelta(seconds=10),
        ))
        db.commit()

        report = sweep_expired_tokens(db, dry_run=True)
        assert "t-old2" in report.swept_token_ids
        # まだ ISSUED のまま
        tok = db.get(PBMToken, "t-old2")
        assert tok.status == "ISSUED"
    finally:
        db.close()


def test_sweep_program_revoked_marks_all_revoked():
    db = get_session()
    try:
        prog = Program(
            id="prog-rev", name="rev", description="",
            budget_jpy=100_000, subsidy_bps=10_000, per_citizen_cap_jpy=10_000,
            start_at=datetime.utcnow() - timedelta(days=1),
            end_at=datetime.utcnow() + timedelta(days=10),
            eligibility={}, eligible_jans=[], approved_stores=[],
        )
        db.add(prog)
        db.flush()
        for i in range(3):
            db.add(PBMToken(
                id=f"t-r{i}", program_id="prog-rev", holder_pid=("p" + str(i)).ljust(64, "0"),
                remaining_jpy=1_000, status="ISSUED",
                expires_at=datetime.utcnow() + timedelta(days=5),
            ))
        db.commit()

        report = sweep_program_revoked(db, prog)
        assert len(report.swept_token_ids) == 3
        assert report.refunded_jpy_by_program["prog-rev"] == 3_000
    finally:
        db.close()


# ----------------------------- #7 routers/offline -----------------------------


def _approve_offline_store(store_id: str = "store-aeon-koto") -> None:
    client.post("/offline/stores/approve", json={"store_id": store_id})


def test_offline_coupon_issuance_rejects_raw_pid():
    """生のマイナンバー風 ID でクーポン発行を試みると CP-2 で deny。"""
    expires = int((datetime.now(tz=timezone.utc) + timedelta(days=30)).timestamp())
    r = client.post("/offline/coupons", json={
        "program_id": "prog-koto-kosodate-2026",
        "pid": "MN-0001",  # 生 ID
        "month_index": 202604,
        "cap_jpy": 5000,
        "expires_at": expires,
    })
    assert r.status_code == 400
    assert "CP-2" in r.json()["detail"]


def test_offline_e2e_issue_redeem_settle_writes_ebpm():
    """coupon 発行 → POS 給付 → batch 精算 → EBPM に書き戻し までの E2E。"""
    pid_hex = hashlib.sha256(b"MN-0001-test").hexdigest()
    expires = int((datetime.now(tz=timezone.utc) + timedelta(days=30)).timestamp())

    # 1) coupon 発行
    r = client.post("/offline/coupons", json={
        "program_id": "prog-koto-kosodate-2026",
        "pid": pid_hex,
        "month_index": 202604,
        "cap_jpy": 5000,
        "expires_at": expires,
    })
    assert r.status_code == 200, r.text
    coupon = r.json()

    # 2) POS 用に store を approve
    _approve_offline_store("store-aeon-koto")

    # 3) batch 精算 (店舗が POS で蓄積した想定の 1 件を提出)
    redemption = {
        **coupon,
        "store_id": "store-aeon-koto",
        "amount_jpy": 3000,
        "redeemed_at": int(datetime.now(tz=timezone.utc).timestamp()),
    }
    r = client.post("/offline/redeem-batch", json={
        "store_id": "store-aeon-koto",
        "items": [redemption],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted_count"] == 1
    assert body["total_paid_jpy"] == 3000

    # 4) EBPM に書き戻し: program_id=prog-koto-kosodate-2026 に対する集計が立つ
    summary = client.get("/ebpm/summary?program_id=prog-koto-kosodate-2026").json()
    assert len(summary) == 1
    assert summary[0]["subsidy_jpy"] == 3000


def test_offline_batch_unapproved_store_rejects():
    pid_hex = hashlib.sha256(b"MN-0099-test").hexdigest()
    expires = int((datetime.now(tz=timezone.utc) + timedelta(days=30)).timestamp())
    coupon = client.post("/offline/coupons", json={
        "program_id": "prog-koto-kosodate-2026",
        "pid": pid_hex, "month_index": 202604, "cap_jpy": 5000, "expires_at": expires,
    }).json()

    redemption = {
        **coupon, "store_id": "store-rogue", "amount_jpy": 1000,
        "redeemed_at": int(datetime.now(tz=timezone.utc).timestamp()),
    }
    body = client.post("/offline/redeem-batch", json={
        "store_id": "store-rogue", "items": [redemption],
    }).json()
    assert body["accepted_count"] == 0
    assert body["rejected_count"] == 1


# ----------------------------- #9 EBPM CP-2 (個票漏れ防止) -----------------------------


def test_ebpm_breakdown_kanonymity_redacts_small_cells():
    """1 人しか購入してない区はセルが '-' に丸められる。"""
    client.post("/products", json={"jan": "4922222222226", "name": "対象", "category": "food.daily", "price_jpy": 1000})
    client.post("/stores", json={"id": "store-koto-k", "name": "K店", "ward": "江東区"})
    client.post("/wallet/treasury/topup", json={"amount_jpy": 1_000_000})

    client.post("/programs", json={
        "id": "prog-kanon",
        "name": "kanon",
        "description": "x",
        "budget_jpy": 1_000_000,
        "subsidy_bps": 5000,
        "per_citizen_cap_jpy": 10_000,
        "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "end_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "eligibility": {"wards": ["江東区"]},
        "eligible_jans": [],
        "eligible_categories": ["food.daily"],
        "approved_stores": ["store-koto-k"],
    })

    # 1 人だけ購入 → unique_citizens=1 < K_ANON=5 → '-' 表示
    pid = _login("MN-KANON-1", ward="江東区", dob="1985-01-01")
    client.post(f"/wallet/citizen/{pid}/topup", json={"amount_jpy": 100_000})
    client.post("/programs/prog-kanon/issue", json={"citizen_pid": pid})
    client.post("/purchase", json={
        "citizen_pid": pid, "store_id": "store-koto-k", "jan": "4922222222226", "qty": 1,
    })

    rows = client.get("/ebpm/breakdown?dim=ward&program_id=prog-kanon").json()
    assert len(rows) == 1
    # CP-2: 1 人しかいないので tx_count, subsidy_jpy 等は全部 '-'
    assert rows[0]["unique_citizens"] == "-"
    assert rows[0]["subsidy_jpy"] == "-"
    assert rows[0]["total_jpy"] == "-"


# ----------------------------- #10 ConsentLog -----------------------------


def test_consent_log_persists_with_text_hash():
    db = get_session()
    try:
        text = "東京都が JPYC 給付に必要な範囲で 4 情報を取得することに同意します"
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        log = ConsentLog(
            id=str(uuid.uuid4()),
            pid="a" * 64,
            program_id="prog-koto-kosodate-2026",
            consent_text_sha256=sha,
            scope=["family_register.basic_4", "address.ward"],
        )
        db.add(log)
        db.commit()

        retrieved = db.query(ConsentLog).filter_by(pid="a" * 64).first()
        assert retrieved is not None
        assert retrieved.consent_text_sha256 == sha
        assert retrieved.scope == ["family_register.basic_4", "address.ward"]
        assert retrieved.revoked_at is None

        # 撤回シミュレーション
        retrieved.revoked_at = datetime.utcnow()
        retrieved.revoke_reason = "本人申し出"
        db.commit()
        again = db.query(ConsentLog).filter_by(pid="a" * 64).first()
        assert again.revoked_at is not None
    finally:
        db.close()


# ----------------------------- ヘルパ -----------------------------


def _login(maina_id: str, ward: str = "新宿区", dob: str = "1985-03-12", gender: str = "M") -> str:
    r = client.post("/auth/myna/login", json={
        "maina_id": maina_id,
        "name": "テスト",
        "address": f"東京都{ward}1-1-1",
        "ward": ward,
        "dob": dob,
        "gender": gender,
    })
    assert r.status_code == 200
    return r.json()["pid"]


def _prog(**kwargs) -> Program:
    base = dict(
        id="p", name="x", description="",
        budget_jpy=100_000, subsidy_bps=5000, per_citizen_cap_jpy=10_000,
        start_at=datetime.utcnow() - timedelta(days=1),
        end_at=datetime.utcnow() + timedelta(days=30),
        eligibility={}, eligible_jans=[], eligible_categories=[],
        excluded_jans=[], approved_stores=[],
    )
    base.update(kwargs)
    return Program(**base)


def _citizen(**kwargs) -> Citizen:
    base = dict(
        pid="a" * 64,
        name="テスト", address="x", ward="新宿区",
        dob=date(1985, 1, 1), gender="M",
    )
    base.update(kwargs)
    return Citizen(**base)


def _tok(**kwargs) -> PBMToken:
    base = dict(
        id="t", program_id="p", holder_pid="a" * 64,
        remaining_jpy=10_000, status="ISSUED",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    base.update(kwargs)
    return PBMToken(**base)


def _store(**kwargs) -> Store:
    base = dict(id="s", name="店", ward="新宿区")
    base.update(kwargs)
    return Store(**base)


def _prod(**kwargs) -> Product:
    base = dict(
        jan="4900000000000", name="商品",
        category="food.daily", price_jpy=1000,
    )
    base.update(kwargs)
    return Product(**base)
