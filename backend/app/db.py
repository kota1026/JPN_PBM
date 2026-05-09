"""SQLAlchemy 接続セットアップ + 簡易スキーママイグレーション。

MVP は SQLite、本番は PostgreSQL を想定。
スキーマ変更を行った場合、既存 DB にカラムを追加する軽量マイグレーションを
起動時に走らせる (Alembic の代用)。
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

log = logging.getLogger(__name__)

DB_URL = os.environ.get("JPN_PBM_DB_URL", "sqlite:///./jpn_pbm.db")

_engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False, "timeout": 10.0} if DB_URL.startswith("sqlite") else {},
    future=True,
)


# SQLite を WAL モードに切替えて読み取り並列性を上げる (戦略会議 #5 採択 E)。
# プロセス起動時に 1 度だけ PRAGMA を投げる。MVP の SQLite が複数 worker の負荷で
# "database is locked" を出す問題を解消する。
if DB_URL.startswith("sqlite"):
    from sqlalchemy import event as _event

    @_event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cur = dbapi_connection.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=10000")
        finally:
            cur.close()
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


# 既存テーブルへ追加すべき (テーブル, カラム, 型, デフォルト) のリスト。
# モデルにフィールドを追加したらここにも一行足す。
# SQLite は ALTER TABLE ... ADD COLUMN しか出来ないので追加のみ対応。
_PENDING_COLUMNS: list[tuple[str, str, str, str]] = [
    ("programs", "eligible_categories", "JSON", "'[]'"),
    ("programs", "excluded_jans",       "JSON", "'[]'"),
    ("programs", "fiscal_year_budgets", "JSON", "'{}'"),
    # 戦略会議 #13 (R14): マニラ展開のため stores に MCC + QR Ph ID 列追加
    ("stores",   "mcc",                 "INTEGER", "NULL"),
    ("stores",   "qr_ph_id",            "VARCHAR(64)", "NULL"),
]


def _migrate(engine) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, col, typ, default in _PENDING_COLUMNS:
            if not insp.has_table(table):
                continue  # create_all がこの後作る
            existing = {c["name"] for c in insp.get_columns(table)}
            if col in existing:
                continue
            log.warning("Migrating: ADD COLUMN %s.%s %s DEFAULT %s", table, col, typ, default)
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {typ} DEFAULT {default}'))


def init_db() -> None:
    # モデル登録のために import (副作用)
    from app.models import (  # noqa: F401
        citizen,
        consent,
        cp_violation,
        ebpm,
        pbm,
        product,
        program,
        store,
        wallet,
    )

    _migrate(_engine)               # 既存テーブルにカラムを追加
    Base.metadata.create_all(bind=_engine)  # 無いテーブルは作る

    # 戦略会議 #6 採択 C: 番号付き migrations (PostgreSQL/SQLite 両対応) を順次適用
    try:
        from migrations import run_migrations  # noqa: WPS433
        run_migrations(_engine)
    except Exception as e:  # pragma: no cover
        log.warning("migrations failed: %s", e)


def get_session() -> Session:
    return SessionLocal()


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
