"""JPYC モック。本番では JPYC v2 (ERC-20) コントラクトをラップする。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.wallet import Wallet


TREASURY_ID = "tokyo-treasury"
TREASURY_KIND = "treasury"


def _wallet(db: Session, owner_id: str, owner_kind: str) -> Wallet:
    w = db.get(Wallet, (owner_id, owner_kind))
    if w is None:
        w = Wallet(owner_id=owner_id, owner_kind=owner_kind, jpyc_balance=0)
        db.add(w)
        db.flush()
    return w


def balance_of(db: Session, owner_id: str, owner_kind: str) -> int:
    return _wallet(db, owner_id, owner_kind).jpyc_balance


def mint(db: Session, owner_id: str, owner_kind: str, amount: int) -> int:
    """JPY 入金 → JPYC 発行 (デモ用)。"""
    if amount <= 0:
        raise ValueError("amount must be positive")
    w = _wallet(db, owner_id, owner_kind)
    w.jpyc_balance += amount
    return w.jpyc_balance


def transfer(
    db: Session,
    src_id: str,
    src_kind: str,
    dst_id: str,
    dst_kind: str,
    amount: int,
) -> None:
    if amount <= 0:
        raise ValueError("amount must be positive")
    src = _wallet(db, src_id, src_kind)
    if src.jpyc_balance < amount:
        raise ValueError(f"insufficient JPYC: need {amount}, have {src.jpyc_balance}")
    dst = _wallet(db, dst_id, dst_kind)
    src.jpyc_balance -= amount
    dst.jpyc_balance += amount
