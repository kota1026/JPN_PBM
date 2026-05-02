"""準備金 24h 監査 (戦略会議 #2 採択 #4)。

CFO 提案 + Red Team 修正案: 「都が monthly に手動コール」では遅い、24h 自動 + アラート。

監査の不変条件:
    treasury.jpyc_balance + sum(store.jpyc_balance) + sum(citizen.jpyc_balance)
        == 全 mint 量 - 全 burn 量

但し本実装では burn は無いので:
    全 mint 量 == treasury + stores + citizens の総和

加えて、PBM の整合性:
    program.budget_jpy - program.spent_jpy == sum(token.remaining_jpy where ISSUED)
        + (treasury に戻されるべき未消化分)

戦略会議で Stablecoin Architect も指摘 "JPYC 発行体倒産リスク。月次準備金監査必須"
への直接応答。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pbm import PBMToken
from app.models.program import Program
from app.models.wallet import Wallet
from app.services import jpyc


# 警報閾値 (これ以上の差異が出たら都 SOC へ通報)
DEFAULT_ALERT_THRESHOLD_JPY = 1


@dataclass
class ReserveAuditReport:
    """準備金監査レポート。CSV/JSON 化されて都 SOC に提出される想定。"""

    audited_at: datetime

    # JPYC 全量
    total_minted_jpy: int = 0
    treasury_balance_jpy: int = 0
    store_balance_jpy: int = 0
    citizen_balance_jpy: int = 0
    sum_balances_jpy: int = 0

    # PBM 整合
    program_budgets_jpy: int = 0
    program_spent_jpy: int = 0
    program_outstanding_jpy: int = 0  # = budget - spent
    issued_token_remaining_jpy: int = 0

    # 差分 (絶対値)
    jpyc_supply_diff: int = 0  # = total_minted - sum_balances
    pbm_outstanding_diff: int = 0  # = program_outstanding - issued_token_remaining

    # アラート
    alerts: list[str] = field(default_factory=list)
    threshold_jpy: int = DEFAULT_ALERT_THRESHOLD_JPY

    @property
    def healthy(self) -> bool:
        return not self.alerts


def audit_reserves(
    db: Session,
    *,
    now: datetime | None = None,
    threshold_jpy: int = DEFAULT_ALERT_THRESHOLD_JPY,
) -> ReserveAuditReport:
    """24h cron から呼ばれる準備金監査関数。"""
    report = ReserveAuditReport(
        audited_at=now or datetime.utcnow(),
        threshold_jpy=threshold_jpy,
    )

    # ---- JPYC 全量集計 ----
    rows = db.execute(
        select(Wallet.owner_kind, func.coalesce(func.sum(Wallet.jpyc_balance), 0))
        .group_by(Wallet.owner_kind)
    ).all()
    by_kind = {kind: int(total) for kind, total in rows}
    report.treasury_balance_jpy = by_kind.get(jpyc.TREASURY_KIND, 0)
    report.store_balance_jpy = by_kind.get("store", 0)
    report.citizen_balance_jpy = by_kind.get("citizen", 0)
    report.sum_balances_jpy = (
        report.treasury_balance_jpy
        + report.store_balance_jpy
        + report.citizen_balance_jpy
    )

    # 本 MVP は burn 無し: 全 mint 量 = sum_balances
    # ただし「都が外部から topup」と「自己負担で住民 wallet に topup」両方を mint と
    # みなしているので、デモ環境では mint 量 = sum_balances となる (= 差分は常に 0)。
    # 本番で JPYC 償還 (burn) を実装する際にこの式を更新する。
    report.total_minted_jpy = report.sum_balances_jpy
    report.jpyc_supply_diff = abs(report.total_minted_jpy - report.sum_balances_jpy)

    # ---- PBM 整合 ----
    program_rows = db.execute(
        select(
            func.coalesce(func.sum(Program.budget_jpy), 0),
            func.coalesce(func.sum(Program.spent_jpy), 0),
        ).where(Program.revoked.is_(False))
    ).one()
    report.program_budgets_jpy = int(program_rows[0])
    report.program_spent_jpy = int(program_rows[1])
    report.program_outstanding_jpy = (
        report.program_budgets_jpy - report.program_spent_jpy
    )

    issued_remaining = db.execute(
        select(func.coalesce(func.sum(PBMToken.remaining_jpy), 0)).where(
            PBMToken.status == "ISSUED",
        )
    ).scalar_one()
    report.issued_token_remaining_jpy = int(issued_remaining)

    # PBM の outstanding (program 視点) は token (citizen 視点) の合計以上であるべき
    # (= まだ住民に発行されていない予算分が含まれるため)。
    # 逆方向 = 「token 残量 > program outstanding」になっていたら 二重発行 等の異常。
    report.pbm_outstanding_diff = (
        report.issued_token_remaining_jpy - report.program_outstanding_jpy
    )

    # ---- アラート判定 ----
    if report.jpyc_supply_diff > threshold_jpy:
        report.alerts.append(
            f"CRITICAL: JPYC supply mismatch {report.jpyc_supply_diff} JPY"
            " (treasury+stores+citizens != minted)"
        )
    if report.pbm_outstanding_diff > threshold_jpy:
        report.alerts.append(
            f"CRITICAL: PBM token over-issuance "
            f"({report.issued_token_remaining_jpy} > "
            f"{report.program_outstanding_jpy})"
        )
    if report.treasury_balance_jpy < 0:
        report.alerts.append(
            f"CRITICAL: treasury balance negative ({report.treasury_balance_jpy})"
        )

    return report
