"""簡易マイグレーション (戦略会議 #6 採択 C)。

Alembic を入れるほどではないが、`db.py:_PENDING_COLUMNS` のインライン管理は
スケールしない。本パッケージは、`MIGRATIONS` リストに `(version, name, sqlite_sql, postgres_sql)`
を順に登録し、`schema_migrations` テーブルで適用済 version を追跡する。

設計目標:
- SQLite (MVP) と PostgreSQL (本番) の両方で動く
- 1 マイグレーション = 1 文 (DDL)
- 失敗時は記録せず再試行できる
- 既存 _PENDING_COLUMNS 由来の列はマイグレーション対象から除外 (重複適用回避)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sqlite_sql: str
    postgres_sql: str  # PostgreSQL 用の equivalent (ALTER 構文の差を吸収)

    def sql_for(self, dialect: str) -> str:
        if dialect.startswith("postgres"):
            return self.postgres_sql
        return self.sqlite_sql


# ----------------------------- マイグレーション台帳 -----------------------------
# version は単調増加 (再番号禁止)。新しいマイグレーションは末尾に追記する。
MIGRATIONS: list[Migration] = [
    # 既存 _PENDING_COLUMNS は db.py で先に流れるので、ここでは新規追加のみ管理。
    # 例 (将来用):
    # Migration(
    #     version=1,
    #     name="add_consent_extra_field",
    #     sqlite_sql="ALTER TABLE consent_logs ADD COLUMN extra TEXT DEFAULT ''",
    #     postgres_sql="ALTER TABLE consent_logs ADD COLUMN extra VARCHAR(256) DEFAULT ''",
    # ),
]


def _ensure_table(engine: Engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("schema_migrations"):
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE schema_migrations ("
                "version INTEGER PRIMARY KEY, "
                "name VARCHAR(128) NOT NULL, "
                "applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            ))


def applied_versions(engine: Engine) -> set[int]:
    _ensure_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version FROM schema_migrations")).all()
    return {int(r[0]) for r in rows}


def run_migrations(engine: Engine, *, dry_run: bool = False) -> list[Migration]:
    """未適用の MIGRATIONS を順に実行 (戦略会議 #6 採択 C)。

    Returns: 実際に走らせた (or dry_run なら走らせる予定の) Migration 一覧
    """
    _ensure_table(engine)
    applied = applied_versions(engine)
    dialect = engine.dialect.name  # "sqlite" or "postgresql" など
    pending = [m for m in MIGRATIONS if m.version not in applied]
    if dry_run:
        return pending
    for m in pending:
        with engine.begin() as conn:
            conn.execute(text(m.sql_for(dialect)))
            conn.execute(
                text("INSERT INTO schema_migrations (version, name) VALUES (:v, :n)"),
                {"v": m.version, "n": m.name},
            )
    return pending


def status(engine: Engine) -> dict[str, object]:
    """SOC ダッシュボード向けの migration 状態。"""
    applied = applied_versions(engine)
    return {
        "dialect": engine.dialect.name,
        "applied": sorted(applied),
        "pending": [
            {"version": m.version, "name": m.name}
            for m in MIGRATIONS if m.version not in applied
        ],
        "total_registered": len(MIGRATIONS),
    }
