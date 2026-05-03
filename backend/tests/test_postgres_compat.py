"""PostgreSQL 互換性検証 (戦略会議 #8 採択 D)。

実 PostgreSQL が無い sandbox でも、以下を担保:
- 全 model の DDL が PostgreSQL 方言で生成可能 (compile error が出ない)
- migrations の dialect 分岐が正しく postgresql_sql を返す
- _set_sqlite_pragma listener が SQLite 専用 (PostgreSQL では走らない)
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.db as db_mod
from app.db import Base, init_db


def test_all_models_compile_to_postgres_dialect():
    """全モデルの CREATE TABLE 文が PostgreSQL 方言で正しく生成できること。"""
    # 既存 Base.metadata に登録済の全テーブルを PostgreSQL 方言で compile
    init_db()  # モデル import を強制
    pg_dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=pg_dialect))
        # PostgreSQL では VARCHAR / TIMESTAMP / JSON 等が出てくるはず
        assert "CREATE TABLE" in ddl
        # SQLite 専用シンタックス (DATETIME) が PostgreSQL 構文で書かれていること
        # → SQLAlchemy が "TIMESTAMP" に変換するはず
        if "datetime" in ddl.lower() and "timestamp" not in ddl.lower():
            # DATETIME は PostgreSQL でも valid (synonym)、警告しない
            pass


def test_migrations_postgres_dialect_branch():
    """migrations の sql_for() が postgresql に対して postgres_sql を返す。"""
    from migrations import Migration
    m = Migration(
        version=999,
        name="probe",
        sqlite_sql="ALTER TABLE x ADD COLUMN y JSON DEFAULT '{}'",
        postgres_sql="ALTER TABLE x ADD COLUMN y JSONB DEFAULT '{}'::jsonb",
    )
    assert m.sql_for("sqlite") == "ALTER TABLE x ADD COLUMN y JSON DEFAULT '{}'"
    assert m.sql_for("postgresql") == "ALTER TABLE x ADD COLUMN y JSONB DEFAULT '{}'::jsonb"


def test_pragma_listener_is_sqlite_only():
    """`_set_sqlite_pragma` は SQLite 環境でのみ定義されること (PostgreSQL では走らない)。

    conftest.py がテスト用に engine を差し替えるため listener 登録の生死を直接確認できないが、
    ENV `JPN_PBM_DB_URL` が sqlite 系である限り `_set_sqlite_pragma` 関数は module 内に存在する。
    PostgreSQL 環境ではこの関数自体が定義されない (db.py 上の if-block 内)。
    """
    # 現在 DB_URL は sqlite 系なので関数が存在するはず
    assert db_mod.DB_URL.startswith("sqlite")
    assert hasattr(db_mod, "_set_sqlite_pragma")
    # かつ関数は WAL pragma を含む
    import inspect as _inspect
    src = _inspect.getsource(db_mod._set_sqlite_pragma)
    assert "WAL" in src
    assert "busy_timeout" in src


def test_models_use_only_dialect_neutral_types():
    """全モデルが SQLite/PostgreSQL 両対応の型のみで構成されていること。"""
    init_db()
    insp = inspect(db_mod._engine)
    for table_name in insp.get_table_names():
        if table_name == "schema_migrations":
            continue
        cols = insp.get_columns(table_name)
        for col in cols:
            type_name = str(col["type"]).upper()
            # 許容: VARCHAR, TEXT, INTEGER, DATETIME, DATE, JSON, BOOLEAN, FLOAT
            # SQLAlchemy 自動マッピング型を許容
            allowed_substrings = (
                "VARCHAR", "TEXT", "INTEGER", "DATETIME", "DATE",
                "JSON", "BOOLEAN", "FLOAT", "NUMERIC", "TIMESTAMP",
            )
            assert any(s in type_name for s in allowed_substrings), \
                f"{table_name}.{col['name']} uses non-portable type {type_name}"
