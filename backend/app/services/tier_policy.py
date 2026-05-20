"""KYC tier policy ─ DP-4 (戦略会議 #19 採択 DPI-6)。

寄付額に応じた KYC tier の自動決定 + tier 別必要書類の判定。

【tier 閾値 (default、program 別 override 可)】
- Tier 0 anon:     寄付 $0-50
- Tier 1 light:    $50-1000  (氏名 + DOB + email)
- Tier 2 full:     $1000-10000 (+ photo ID + biometric)
- Tier 3 enhanced: $10000+   (+ source of wealth)

【FATF Travel Rule】
$3,000 (≒ centi 300000) 以上の crypto 送金は travel rule 適用 → Tier 2+
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


KycTier = Literal[0, 1, 2, 3]


@dataclass(frozen=True)
class TierThresholds:
    """寄付額 (smallest unit: cents/centavos/etc, 通貨は context dependent)。"""
    anon_max: int = 5000          # Tier 0 上限: $50
    tier1_max: int = 100000       # Tier 1 上限: $1000
    tier2_max: int = 1000000      # Tier 2 上限: $10000
    fatf_travel_rule_floor: int = 300000   # $3000 ≒ FATF Travel Rule


@dataclass(frozen=True)
class TierPolicyConfig:
    thresholds: TierThresholds = TierThresholds()
    enforce_travel_rule: bool = True


class TierError(Exception):
    pass


def determine_required_tier(
    *, donation_amount_centi: int,
    policy: TierPolicyConfig | None = None,
) -> KycTier:
    """寄付額 → 必要 KYC tier を決定。"""
    if donation_amount_centi < 0:
        raise TierError("donation_amount_centi must be >= 0")

    p = policy or _policy_from_env()
    t = p.thresholds

    # FATF Travel Rule は Tier 2 を強制
    if p.enforce_travel_rule and donation_amount_centi >= t.fatf_travel_rule_floor:
        if donation_amount_centi <= t.tier2_max:
            return 2
        return 3

    if donation_amount_centi <= t.anon_max:
        return 0
    if donation_amount_centi <= t.tier1_max:
        return 1
    if donation_amount_centi <= t.tier2_max:
        return 2
    return 3


def required_fields_for_tier(tier: KycTier) -> set[str]:
    """tier 別の必須入力 field 集合。"""
    if tier == 0:
        return set()
    if tier == 1:
        return {"full_name", "dob", "email"}
    if tier == 2:
        return {"full_name", "dob", "email", "phone_e164",
                "photo_id_uri", "selfie_uri"}
    if tier == 3:
        return {"full_name", "dob", "email", "phone_e164",
                "photo_id_uri", "selfie_uri", "source_of_wealth"}
    raise TierError(f"unknown tier: {tier}")


def tier_cost_usd_cents(tier: KycTier) -> int:
    """tier 別 KYC コスト見積 (USD cents)。"""
    return {0: 0, 1: 200, 2: 600, 3: 2000}[tier]


def upgrade_path(current: KycTier, target: KycTier) -> list[str]:
    """current → target に上げるために必要な追加 field の リスト。"""
    if current >= target:
        return []
    have = required_fields_for_tier(current)
    need = required_fields_for_tier(target)
    return sorted(need - have)


# ============================================================
# config from env
# ============================================================


def _policy_from_env() -> TierPolicyConfig:
    return TierPolicyConfig(
        thresholds=TierThresholds(
            anon_max=int(os.environ.get("JPN_PBM_TIER_ANON_MAX", "5000")),
            tier1_max=int(os.environ.get("JPN_PBM_TIER1_MAX", "100000")),
            tier2_max=int(os.environ.get("JPN_PBM_TIER2_MAX", "1000000")),
            fatf_travel_rule_floor=int(
                os.environ.get("JPN_PBM_FATF_FLOOR", "300000")),
        ),
        enforce_travel_rule=os.environ.get(
            "JPN_PBM_ENFORCE_TRAVEL_RULE", "1") == "1",
    )


def get_tier_policy(cfg: TierPolicyConfig | None = None) -> TierPolicyConfig:
    """factory equivalent。設定なしならenv から。"""
    return cfg or _policy_from_env()
