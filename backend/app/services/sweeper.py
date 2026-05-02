"""期限切れ PBM トークンの自動返還ジョブ (戦略会議 #2 採択 #6)。

Sol 側 `PBM.revokeProgram` のオフチェーン版。期限超過の `ISSUED` トークンを
`EXPIRED` に遷移させ、program.budget_jpy のうち未消化分を treasury に戻す。

【Red Team 懸念への対応】
"sweeper が走るタイミングを間違えると、まだ使う予定の PBM が刈り取られる"
→ 本実装は **expires_at が現在時刻より厳密に過去** のもののみ刈る (境界 `<=` ではなく `<`)。
   さらに `dry_run` モードで影響範囲を事前確認できる。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pbm import PBMToken
from app.models.program import Program


@dataclass
class SweepReport:
    swept_token_ids: list[str] = field(default_factory=list)
    refunded_jpy_by_program: dict[str, int] = field(default_factory=dict)
    now: datetime | None = None
    dry_run: bool = False

    @property
    def total_refund(self) -> int:
        return sum(self.refunded_jpy_by_program.values())


def sweep_expired_tokens(
    db: Session,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> SweepReport:
    """期限切れの ISSUED トークンを EXPIRED にし、未消化分を集計する。

    Note:
        program.spent_jpy は spend 時に既に減算されているので、ここでは program 本体の
        `budget_jpy` には触らず、SweepReport で「いま time-out で剥がれた未使用枠」を
        報告する。実際の treasury 戻し入れは、本レポートを受けた上位レイヤ
        (jpyc.transfer や Sol revokeProgram 相当) が行う。
    """
    now = now or datetime.utcnow()
    report = SweepReport(now=now, dry_run=dry_run)

    expired = db.execute(
        select(PBMToken).where(
            PBMToken.status == "ISSUED",
            PBMToken.expires_at < now,  # 厳密に過去 (Red Team 懸念対応)
        )
    ).scalars().all()

    for tok in expired:
        report.swept_token_ids.append(tok.id)
        report.refunded_jpy_by_program[tok.program_id] = (
            report.refunded_jpy_by_program.get(tok.program_id, 0) + tok.remaining_jpy
        )
        if not dry_run:
            tok.status = "EXPIRED"

    return report


def sweep_program_revoked(
    db: Session,
    program: Program,
    *,
    dry_run: bool = False,
) -> SweepReport:
    """program が revoked された後の刈り取り (Sol revokeProgram 相当)。"""
    report = SweepReport(dry_run=dry_run)

    tokens = db.execute(
        select(PBMToken).where(
            PBMToken.program_id == program.id,
            PBMToken.status == "ISSUED",
        )
    ).scalars().all()

    for tok in tokens:
        report.swept_token_ids.append(tok.id)
        report.refunded_jpy_by_program[program.id] = (
            report.refunded_jpy_by_program.get(program.id, 0) + tok.remaining_jpy
        )
        if not dry_run:
            tok.status = "REVOKED"

    return report
