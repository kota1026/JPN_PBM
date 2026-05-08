"""ロードマップ進捗 API のテスト (戦略会議 #7 採択 A)。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.roadmap import (
    MILESTONES,
    auto_metrics,
    evidence_check,
    status_summary,
    to_dict,
)


client = TestClient(app)


def test_milestones_cover_all_three_phases():
    phases = {m.phase for m in MILESTONES}
    assert phases == {1, 2, 3}


def test_status_summary_counts_match_total():
    s = status_summary()
    assert sum(s.values()) == len(MILESTONES)


def test_evidence_files_actually_exist_when_marked():
    """evidence_files に挙げているファイルは実際にリポに存在するべき。"""
    for m in MILESTONES:
        if not m.evidence_files:
            continue
        ev = evidence_check(m)
        for path, exists in ev.items():
            assert exists, f"{m.code} ({m.title}): missing evidence {path}"


def test_to_dict_structure():
    d = to_dict()
    assert "summary" in d
    assert "phases" in d
    assert len(d["phases"]) == 3
    for ph in d["phases"]:
        assert ph["phase"] in (1, 2, 3)
        for m in ph["milestones"]:
            assert m["status"] in {"done", "ready", "partial", "blocked", "pending"}


def test_endpoint_returns_200():
    r = client.get("/treasury/roadmap")
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    # CP-6 マイルストーンが ready で含まれていることを確認 (Phase 2 完了の証)
    cp6 = None
    for ph in body["phases"]:
        if ph["phase"] != 2:
            continue
        for m in ph["milestones"]:
            if m["code"] == "M+11":
                cp6 = m
    assert cp6 is not None
    assert cp6["status"] == "ready"


def test_auto_metrics_returns_real_counts():
    """auto_metrics は repo の実コードから集計される (戦略会議 #10 採択 A4)。"""
    m = auto_metrics()
    # 必須キー
    for k in (
        "tests", "routers", "services", "contracts", "seed_programs",
        "strategy_docs_ja", "strategy_docs_en", "verify_modes", "audit_checks",
    ):
        assert k in m, f"missing key: {k}"
        assert isinstance(m[k], int)
    # ラウンド 11 時点の最低保証値
    assert m["tests"] >= 18, f"tests should be at least 18, got {m['tests']}"
    assert m["contracts"] >= 2
    assert m["seed_programs"] >= 7
    assert m["audit_checks"] >= 20  # 24 checklist
    assert m["verify_modes"] >= 10  # py/seed/sol/cp6/sweep/ready/audit/i18n/e2e/front/load
    # 英訳カバレッジ: ja - en <= 1 (最新 1 本ラグまで許容)
    assert m["strategy_docs_ja"] - m["strategy_docs_en"] <= 1


def test_endpoint_includes_auto_metrics():
    r = client.get("/treasury/roadmap")
    body = r.json()
    assert "auto_metrics" in body
    assert body["auto_metrics"]["contracts"] >= 2


def test_m10_audit_promoted_to_ready():
    """戦略会議 #10 で M+10 (PBM audit) が partial → ready に格上げ。"""
    m10 = next(
        (m for m in MILESTONES if m.phase == 2 and m.code == "M+10"), None
    )
    assert m10 is not None
    assert m10.status == "ready"
    assert "scripts/contract_audit.py" in m10.evidence_files


def test_m18_whitepaper_promoted_to_ready():
    """戦略会議 #10 で M+18 (whitepaper) が partial → ready に格上げ。"""
    m18 = next(
        (m for m in MILESTONES if m.phase == 3 and m.code == "M+18"), None
    )
    assert m18 is not None
    assert m18.status == "ready"
    assert "docs/whitepaper-2026.md" in m18.evidence_files
