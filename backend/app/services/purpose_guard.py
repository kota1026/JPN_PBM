"""CP-1〜CP-6 の runtime 強制レイヤ。

戦略会議 #2 で Purpose Guardian が提起、Red Team が「既存 spend との順序」を懸念
した点を踏まえ、本モジュールは spend / issue / offline_redeem の 3 経路全てから
**最初に呼ばれる単一の関門** として動く。違反したら GuardError を上げて、後段の
副作用 (JPYC 転送, EBPM 書き込み等) を実行させない。

【設計】
- 責務はチェックのみ。状態を持たない。
- spend / issue / offline は同じ Decision を返す: ok=True/False, code, why, ctx
- code は CP 名で固定 (例: "CP-1", "CP-5.double_spend") — 監査ログから機械的に集計可能
- オフラインフォールバック側 (`offline_fallback.py`) は既に同等チェックを内部で持つので、
  本モジュールはオフライン redemption が EBPM/監査側に書き戻されるとき「再検証」する
  ためにも使える (Red Team #7 指摘: CP-4 漏れ防止)。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.models.citizen import Citizen
from app.models.pbm import PBMToken
from app.models.product import Product
from app.models.program import Program
from app.models.store import Store
from app.services.eligibility import check as eligibility_check
from app.services.privacy import age


@dataclass(frozen=True)
class Decision:
    ok: bool
    code: str = ""        # 例: "CP-1.purpose_mismatch"
    why: str = ""

    @classmethod
    def allow(cls) -> "Decision":
        return cls(True)

    @classmethod
    def deny(cls, code: str, why: str) -> "Decision":
        return cls(False, code, why)


class GuardError(RuntimeError):
    def __init__(self, decision: Decision):
        super().__init__(f"{decision.code}: {decision.why}")
        self.decision = decision


# ----------------------------- CP-1 目的整合性 -----------------------------


def cp1_purpose_match(product: Product, program: Program) -> Decision:
    """CP-1: 商品が program の Purpose に合致しているか。

    program.eligible_jans / eligible_categories のいずれかにマッチし、
    excluded_jans に含まれないこと。
    """
    if product.jan in (program.excluded_jans or []):
        return Decision.deny(
            "CP-1.excluded", f"JAN {product.jan} は program {program.id} で除外指定"
        )
    if product.category in (program.eligible_categories or []):
        return Decision.allow()
    if product.jan in (program.eligible_jans or []):
        return Decision.allow()
    return Decision.deny(
        "CP-1.purpose_mismatch",
        f"商品 {product.name} (cat={product.category}) は program {program.id} の Purpose 外",
    )


# ----------------------------- CP-2 プライバシー -----------------------------


def cp2_pid_is_pseudonymized(pid: str) -> Decision:
    """CP-2: holder_pid が HMAC 化済みであることの最低限の形式チェック。

    HMAC-SHA256 の hex は 64 文字、すべて [0-9a-f]。生のマイナンバーや氏名が
    そのまま渡ったら deny。
    """
    if not pid or len(pid) != 64:
        return Decision.deny(
            "CP-2.raw_id", f"pid 長さ ({len(pid) if pid else 0}) が HMAC-SHA256 hex (64) でない"
        )
    if not all(c in "0123456789abcdef" for c in pid):
        return Decision.deny("CP-2.raw_id", "pid に hex 以外の文字が混入")
    return Decision.allow()


def cp2_no_personal_info_in_aggregate(rows: Iterable[dict]) -> Decision:
    """CP-2: EBPM 集計結果に個票が含まれていないことを保証する。

    各行に `count` フィールドがあり、`count >= K_ANONYMITY (5)` であること。
    """
    K_ANON = 5
    for row in rows:
        if "count" not in row:
            return Decision.deny("CP-2.no_count", f"集計行に count が無い: {row}")
        if int(row["count"]) < K_ANON:
            return Decision.deny(
                "CP-2.k_anonymity",
                f"k-匿名性違反: count={row['count']} < {K_ANON}",
            )
    return Decision.allow()


# ----------------------------- CP-3 自動執行 -----------------------------


def cp3_auto_eligibility(citizen: Citizen, program: Program) -> Decision:
    """CP-3: eligibility は人手判断ではなく機械判定のみで決まる。

    実際のチェックは services/eligibility.py に委譲し、ここは入口。
    """
    res = eligibility_check(citizen, program)
    if not res.ok:
        return Decision.deny("CP-3.not_eligible", res.reason)
    return Decision.allow()


# ----------------------------- CP-4 監査可能性 -----------------------------


def cp4_audit_event_complete(event_dict: dict) -> Decision:
    """CP-4: 監査ログが必須フィールドを全て持つこと。

    EBPM/監査の最低キーが欠けていたら deny。
    """
    required = {
        "program_id",
        "jan",
        "total_jpy",
        "subsidy_jpy",
        "citizen_pid",
        "store_id",
    }
    missing = required - set(event_dict.keys())
    if missing:
        return Decision.deny("CP-4.missing", f"監査ログ欠損: {sorted(missing)}")
    return Decision.allow()


# ----------------------------- CP-5 不正三大リスク -----------------------------


def cp5_double_spend(token: PBMToken, requested_jpy: int) -> Decision:
    """CP-5: 二重支給ゼロ。残量を超える spend は deny。"""
    if requested_jpy <= 0:
        return Decision.deny("CP-5.bad_amount", "amount must be positive")
    if requested_jpy > token.remaining_jpy:
        return Decision.deny(
            "CP-5.double_spend",
            f"残量 {token.remaining_jpy} を超える spend {requested_jpy}",
        )
    return Decision.allow()


def cp5_store_authorized(store: Store, program: Program) -> Decision:
    """CP-5: 加盟店認定 (転売・なりすまし対策の入口)。"""
    if store.id not in (program.approved_stores or []):
        return Decision.deny(
            "CP-5.unauthorized_store",
            f"店舗 {store.id} は program {program.id} の approved_stores 外",
        )
    return Decision.allow()


# ----------------------------- CP-6 災害時可用性 -----------------------------


def cp6_offline_signature_required(has_signature: bool) -> Decision:
    """CP-6: オフライン redemption は必ず governor 署名を伴う。"""
    if not has_signature:
        return Decision.deny("CP-6.no_sig", "オフライン redemption に署名が無い")
    return Decision.allow()


# ----------------------------- 統合ゲートウェイ -----------------------------


def guard_spend(
    *,
    citizen: Citizen,
    program: Program,
    token: PBMToken,
    store: Store,
    product: Product,
    requested_subsidy_jpy: int,
    now: datetime | None = None,
) -> Decision:
    """spend 経路の単一関門。CP-1, CP-2, CP-3, CP-5 を順に評価。

    本ガードは services/pbm.py:spend からの呼び出しを想定し、最初の deny で打ち切る。
    """
    now = now or datetime.utcnow()

    if program.revoked:
        return Decision.deny("CP-1.revoked", f"program {program.id} は revoked")
    if not (program.start_at <= now <= program.end_at):
        return Decision.deny("CP-1.out_of_period", f"program {program.id} は期間外")

    for check in (
        lambda: cp2_pid_is_pseudonymized(citizen.pid),
        lambda: cp1_purpose_match(product, program),
        lambda: cp5_store_authorized(store, program),
        lambda: cp3_auto_eligibility(citizen, program),
        lambda: cp5_double_spend(token, requested_subsidy_jpy),
    ):
        d = check()
        if not d.ok:
            return d
    return Decision.allow()


def guard_offline_redemption(
    *,
    pid: str,
    has_signature: bool,
    audit_event: dict,
) -> Decision:
    """オフライン redemption が EBPM に書き戻される直前のガード。

    Red Team #7 指摘 (CP-4 漏れ) を埋めるため、オフライン経路でも CP-2/4/6 を再検証。
    """
    for check in (
        lambda: cp6_offline_signature_required(has_signature),
        lambda: cp2_pid_is_pseudonymized(pid),
        lambda: cp4_audit_event_complete(audit_event),
    ):
        d = check()
        if not d.ok:
            return d
    return Decision.allow()


# ----------------------------- 補助: 年齢/期間ヘルパー -----------------------------


def age_in_program_window(citizen: Citizen, program: Program) -> int:
    """program 開始時点での citizen 年齢 (eligibility と整合させたい場合に使う)。"""
    return age(citizen.dob, today=program.start_at.date())
