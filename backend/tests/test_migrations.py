"""migrations/ のテスト (戦略会議 #6 採択 C)。

- run_migrations が冪等 (二度走らせても何も追加しない)
- pending → applied の差分が正しく出る
- /treasury/migrations/status エンドポイントが動く
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from migrations import (
    MIGRATIONS,
    Migration,
    applied_versions,
    run_migrations,
    status,
)


client = TestClient(app)


@pytest.fixture
def fresh_engine():
    """インメモリ SQLite を 1 つ用意 (テスト用、本体 DB と独立)。"""
    return create_engine("sqlite:///:memory:", future=True)


def test_status_endpoint_returns_dialect_and_lists():
    r = client.get("/treasury/migrations/status")
    assert r.status_code == 200
    body = r.json()
    assert "dialect" in body
    assert isinstance(body["applied"], list)
    assert isinstance(body["pending"], list)
    assert "total_registered" in body


def test_run_migrations_no_op_when_empty(fresh_engine):
    """MIGRATIONS が空のとき、schema_migrations テーブルだけ作って終わる。"""
    pending = run_migrations(fresh_engine)
    assert pending == []
    # schema_migrations 自体は作られている
    with fresh_engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM schema_migrations")).all()
    assert rows == []


def test_run_migrations_idempotent(fresh_engine):
    """同じ migration を 2 回流しても applied_versions が増えない。"""
    # 一時的に MIGRATIONS に追加 (テスト後に元に戻す)
    test_mig = Migration(
        version=999,
        name="test_only_add_dummy_table",
        sqlite_sql="CREATE TABLE dummy_for_test (id INTEGER)",
        postgres_sql="CREATE TABLE dummy_for_test (id INTEGER)",
    )
    MIGRATIONS.append(test_mig)
    try:
        # 1 回目
        applied1 = run_migrations(fresh_engine)
        assert any(m.version == 999 for m in applied1)
        v1 = applied_versions(fresh_engine)
        assert 999 in v1

        # 2 回目: 同じ engine では何も走らない
        applied2 = run_migrations(fresh_engine)
        assert applied2 == []
        v2 = applied_versions(fresh_engine)
        assert v2 == v1
    finally:
        MIGRATIONS.remove(test_mig)


def test_dry_run_does_not_apply(fresh_engine):
    test_mig = Migration(
        version=998,
        name="test_dry_run",
        sqlite_sql="CREATE TABLE dummy_dry (id INTEGER)",
        postgres_sql="CREATE TABLE dummy_dry (id INTEGER)",
    )
    MIGRATIONS.append(test_mig)
    try:
        pending = run_migrations(fresh_engine, dry_run=True)
        assert any(m.version == 998 for m in pending)
        # まだ applied に入っていない
        assert 998 not in applied_versions(fresh_engine)
    finally:
        MIGRATIONS.remove(test_mig)


def test_status_function_reflects_applied(fresh_engine):
    test_mig = Migration(
        version=997, name="test_status_reflect",
        sqlite_sql="CREATE TABLE x997 (id INTEGER)",
        postgres_sql="CREATE TABLE x997 (id INTEGER)",
    )
    MIGRATIONS.append(test_mig)
    try:
        s_before = status(fresh_engine)
        assert any(p["version"] == 997 for p in s_before["pending"])
        run_migrations(fresh_engine)
        s_after = status(fresh_engine)
        assert 997 in s_after["applied"]
        assert all(p["version"] != 997 for p in s_after["pending"])
    finally:
        MIGRATIONS.remove(test_mig)


def test_postgres_dialect_branch(monkeypatch):
    """dialect が postgres のとき postgres_sql が選ばれる (実際は流さず分岐確認)。"""
    test_mig = Migration(
        version=996, name="test_postgres_branch",
        sqlite_sql="-- sqlite", postgres_sql="-- postgres",
    )
    assert test_mig.sql_for("sqlite") == "-- sqlite"
    assert test_mig.sql_for("postgresql") == "-- postgres"
