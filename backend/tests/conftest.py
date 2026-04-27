"""pytest 共通フィクスチャ。

テストではインメモリ SQLite を共有し、テスト間で初期化する。
"""

from __future__ import annotations

import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# app.db が import される前に環境変数を上書きしておく
os.environ["JPN_PBM_DB_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db as _db_module  # noqa: E402

# StaticPool で同一接続を共有 (in-memory DB のため必須)
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
_db_module._engine = _test_engine
_db_module.SessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False, future=True)

from app.db import Base, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=_test_engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=_test_engine)
