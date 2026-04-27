"""PBM (Purpose Bound Money) のドメインロジック。

オンチェーン版 (`contracts/PBM.sol`) と同じステートマシンを再現する。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.citizen import Citizen
from app.models.ebpm import EBPMEvent
from app.models.pbm import PBMToken
from app.models.product import Product
from app.models.program import Program
from app.models.store import Store
from app.services import jpyc
from app.services.eligibility import check as eligibility_check
from app.services.privacy import age_band


@dataclass
class SpendResult:
    ok: bool
    reason: str
    subsidy_jpy: int = 0
    citizen_pay_jpy: int = 0
    total_jpy: int = 0


def issue(db: Session, program: Program, citizen: Citizen) -> PBMToken:
    """住民に PBM トークン (= 助成金枠) を発行する。

    - eligibility を確認
    - プログラム予算からこの住民分の枠 (per_citizen_cap) を仮押さえ
      (実際の JPYC 残高は spend 時にプログラム予算プールから引かれる)
    """
    if program.revoked:
        raise ValueError("program is revoked")
    now = datetime.utcnow()
    if not (program.start_at <= now <= program.end_at):
        raise ValueError("program not active")

    res = eligibility_check(citizen, program)
    if not res.ok:
        raise ValueError(f"not eligible: {res.reason}")

    # 既存の有効トークンがあれば再発行せず返す
    existing = db.execute(
        select(PBMToken).where(
            PBMToken.program_id == program.id,
            PBMToken.holder_pid == citizen.pid,
            PBMToken.status == "ISSUED",
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    token = PBMToken(
        id=str(uuid.uuid4()),
        program_id=program.id,
        holder_pid=citizen.pid,
        remaining_jpy=program.per_citizen_cap_jpy,
        status="ISSUED",
        expires_at=program.end_at,
    )
    db.add(token)
    db.flush()
    return token


def _product_eligible(product: Product, program: Program) -> bool:
    """商品 × プログラムの対象判定。

    対象 = (カテゴリが eligible_categories に含まれる OR
           JAN が eligible_jans に含まれる)
          AND JAN が excluded_jans に含まれない
    """
    if product.jan in (program.excluded_jans or []):
        return False
    if product.category in (program.eligible_categories or []):
        return True
    if product.jan in (program.eligible_jans or []):
        return True
    return False


def _calc_subsidy(price_total: int, program: Program, token: PBMToken) -> int:
    raw = price_total * program.subsidy_bps // 10_000
    capped_by_token = min(raw, token.remaining_jpy)
    capped_by_program = min(capped_by_token, program.budget_jpy - program.spent_jpy)
    return max(capped_by_program, 0)


def spend(
    db: Session,
    *,
    citizen: Citizen,
    store: Store,
    product: Product,
    qty: int,
) -> SpendResult:
    """加盟店 POS からの購入処理。

    1. 商品から適用可能なプログラムを引く
    2. PBM トークン (有効) を取得
    3. eligibility 再チェック (引っ越し・年齢超過対策)
    4. 助成額算出 → JPYC を トレジャリー → 店舗 へ転送 (PBM 部分)
    5. 自己負担分は住民 → 店舗 (通常 JPYC)
    6. EBPM イベント記録
    """
    if qty <= 0:
        return SpendResult(False, "qty must be positive")
    total = product.price_jpy * qty

    # 適用可能なプログラム = JAN を含む & 加盟店認定 & 期間内 & 取消されていない & 当該住民に PBM がある
    now = datetime.utcnow()
    candidate_programs = db.execute(
        select(Program).where(Program.revoked.is_(False))
    ).scalars().all()

    chosen_program: Program | None = None
    chosen_token: PBMToken | None = None
    for p in candidate_programs:
        if not (p.start_at <= now <= p.end_at):
            continue
        if not _product_eligible(product, p):
            continue
        if store.id not in (p.approved_stores or []):
            continue
        token = db.execute(
            select(PBMToken).where(
                PBMToken.program_id == p.id,
                PBMToken.holder_pid == citizen.pid,
                PBMToken.status == "ISSUED",
            )
        ).scalar_one_or_none()
        if not token or token.remaining_jpy <= 0:
            continue
        res = eligibility_check(citizen, p)
        if not res.ok:
            continue
        chosen_program = p
        chosen_token = token
        break  # MVP: 最初にマッチしたプログラムを適用 (本番は最も住民有利なものを選ぶ)

    subsidy = 0
    if chosen_program and chosen_token:
        subsidy = _calc_subsidy(total, chosen_program, chosen_token)

    citizen_pay = total - subsidy

    # JPYC 残高チェック (自己負担分)
    if jpyc.balance_of(db, citizen.pid, "citizen") < citizen_pay:
        return SpendResult(False, "住民の JPYC 残高不足", subsidy, citizen_pay, total)

    # 自己負担転送
    if citizen_pay > 0:
        jpyc.transfer(db, citizen.pid, "citizen", store.id, "store", citizen_pay)

    # 助成金転送 (トレジャリーから)
    if subsidy > 0 and chosen_program and chosen_token:
        jpyc.transfer(db, jpyc.TREASURY_ID, jpyc.TREASURY_KIND, store.id, "store", subsidy)
        chosen_token.remaining_jpy -= subsidy
        if chosen_token.remaining_jpy == 0:
            chosen_token.status = "EXHAUSTED"
        chosen_program.spent_jpy += subsidy

    # EBPM ログ
    event = EBPMEvent(
        id=str(uuid.uuid4()),
        program_id=chosen_program.id if chosen_program else "",
        jan=product.jan,
        category=product.category,
        qty=qty,
        total_jpy=total,
        subsidy_jpy=subsidy,
        citizen_pay_jpy=citizen_pay,
        citizen_pid=citizen.pid,
        age_band=age_band(citizen.dob),
        gender=citizen.gender,
        ward=citizen.ward,
        store_id=store.id,
        store_ward=store.ward,
    )
    db.add(event)
    db.flush()

    return SpendResult(True, "OK", subsidy, citizen_pay, total)


def revoke_program(db: Session, program: Program) -> int:
    """プログラム取消。残予算をトレジャリーへ戻し、PBM トークンを REVOKED に。"""
    if program.revoked:
        return 0
    refund = program.budget_jpy - program.spent_jpy
    program.revoked = True
    tokens = db.execute(
        select(PBMToken).where(
            PBMToken.program_id == program.id,
            PBMToken.status == "ISSUED",
        )
    ).scalars().all()
    for t in tokens:
        t.status = "REVOKED"
    return refund
