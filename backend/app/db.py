"""SQLAlchemy 接続セットアップ。MVP は SQLite、本番は PostgreSQL を想定。"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_URL = os.environ.get("JPN_PBM_DB_URL", "sqlite:///./jpn_pbm.db")

_engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # モデル登録のために import (副作用)
    from app.models import (  # noqa: F401
        citizen,
        ebpm,
        pbm,
        product,
        program,
        store,
        wallet,
    )

    Base.metadata.create_all(bind=_engine)


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
