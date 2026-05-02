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
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    future=True,
)
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
