"""ロードマップ進捗 API のテスト (戦略会議 #7 採択 A)。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.roadmap import (
    MILESTONES,
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
