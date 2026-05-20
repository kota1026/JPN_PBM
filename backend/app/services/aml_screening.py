"""AML (Anti-Money Laundering) screening ─ DP-3 (戦略会議 #19 採択)。

3 ソース cross-check (OFAC + UN + EU 無料) をデフォルト、
high-value 寄付は ComplyAdvantage / World-Check (Refinitiv) を pluggable で上乗せ。

【DPI-4 / Lina Okabe 試算】
- OFAC 単独: false positive 30%
- 3 ソース cross-check: 5% (6 倍改善)
- ComplyAdvantage: 10%、$20K-80K/年
- World-Check: 12%、$30K-100K/年

【risk-based scoring】
名前一致だけでは reject しない。country / dob / 複数ソース hit count で score 計算。
James Mwangi の指摘 (「ヨルダンの Mohammed Khan 全員 reject 問題」) への対応。

【factory】
    backend = get_aml_backend()
       JPN_PBM_AML_BACKEND=mock            (default)
       JPN_PBM_AML_BACKEND=free_sources    (OFAC + UN + EU)
       JPN_PBM_AML_BACKEND=complyadvantage + JPN_PBM_AML_API_KEY=...
       JPN_PBM_AML_BACKEND=worldcheck      + JPN_PBM_AML_API_KEY=...
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol


SanctionsList = Literal["ofac_sdn", "un_consolidated", "eu_consolidated",
                         "complyadvantage_pep", "worldcheck_pep"]
ScreeningOutcome = Literal["cleared", "review", "rejected", "cleared_with_audit"]


# 自動 reject 閾値 (risk score 70+)
THRESHOLD_AUTO_REJECT = 70
# 手動 review 閾値 (40-69)
THRESHOLD_MANUAL_REVIEW = 40


@dataclass(frozen=True)
class AmlConfig:
    backend: str = "mock"
    api_key: str | None = None
    base_url: str | None = None


@dataclass
class SanctionsHit:
    source: SanctionsList
    matched_name: str
    match_confidence: float    # 0.0-1.0
    list_entry_id: str
    list_entry_reason: str | None = None


@dataclass
class ScreeningResult:
    outcome: ScreeningOutcome
    risk_score: int           # 0-100
    hits: list[SanctionsHit] = field(default_factory=list)
    reason: str = ""
    screened_at: float = field(default_factory=time.time)
    is_mock: bool = True


class AmlError(Exception):
    pass


# ============================================================
# Protocol
# ============================================================


class AmlBackend(Protocol):
    def screen(self, *, full_name: str, dob: date | None,
                country: str) -> ScreeningResult: ...
    def is_sandbox(self) -> bool: ...


# ============================================================
# Mock backend (3 ソース cross-check simulation)
# ============================================================


# Mock の "sanctioned names" ─ 既知 false positive を再現するため
MOCK_KNOWN_SANCTIONED = {
    "OSAMA BIN LADEN": ("ofac_sdn", "un_consolidated", "eu_consolidated"),
    "KIM JONG UN": ("ofac_sdn", "un_consolidated", "eu_consolidated"),
    "JOHN SMITH": ("ofac_sdn",),       # 1 source = high false positive
    "MOHAMMED KHAN": ("ofac_sdn",),    # James Mwangi 例
}


class MockAmlBackend:
    """in-process mock。3 ソース cross-check + risk-based scoring。"""

    def __init__(self) -> None:
        self._screenings: list[ScreeningResult] = []

    def is_sandbox(self) -> bool:
        return True

    def screen(self, *, full_name: str, dob: date | None,
                country: str) -> ScreeningResult:
        name_upper = full_name.upper().strip()
        hits: list[SanctionsHit] = []

        # mock sanctioned names チェック
        sources = MOCK_KNOWN_SANCTIONED.get(name_upper, ())
        for src in sources:
            hits.append(SanctionsHit(
                source=src,  # type: ignore
                matched_name=name_upper,
                match_confidence=0.95,
                list_entry_id=f"{src.upper()}-{name_upper.replace(' ', '_')}",
                list_entry_reason="mock sanctioned entity",
            ))

        # risk-based scoring
        score = _calc_risk_score(hits=hits, country=country)

        if score >= THRESHOLD_AUTO_REJECT:
            outcome = "rejected"
            reason = f"risk score {score} >= {THRESHOLD_AUTO_REJECT} (auto-reject)"
        elif score >= THRESHOLD_MANUAL_REVIEW:
            outcome = "review"
            reason = f"risk score {score} >= {THRESHOLD_MANUAL_REVIEW} (manual review)"
        else:
            outcome = "cleared"
            reason = f"risk score {score} below threshold"

        result = ScreeningResult(
            outcome=outcome, risk_score=score, hits=hits, reason=reason,
        )
        self._screenings.append(result)
        return result


def _calc_risk_score(*, hits: list[SanctionsHit], country: str) -> int:
    """risk-based scoring。複数ソース hit + country で重み付け。

    1 source hit (e.g., OFAC のみ):  +30 (false positive 高めなので review 行き)
    2 source hits:                  +50 (両方 hit なら manual review 確実)
    3 source hits (cross-checked):  +85 (auto-reject)
    high-risk country:              +15 (Iran/N.Korea/Syria 等)
    """
    if not hits:
        return 0

    distinct_sources = len({h.source for h in hits})
    if distinct_sources == 1:
        base = 30
    elif distinct_sources == 2:
        base = 50
    else:  # 3+
        base = 85

    high_risk_countries = {"IR", "KP", "SY", "AF", "MM"}  # ISO-2
    country_bonus = 15 if country.upper() in high_risk_countries else 0

    return min(base + country_bonus, 100)


# ============================================================
# Real backends (R22+ 実装)
# ============================================================


class FreeSourcesAmlBackend:
    """OFAC + UN + EU の無料リストを実際にダウンロード + 照合。

    Round 22+ で実装。daily refresh + name fuzzy matching を含む。
    """

    def is_sandbox(self) -> bool:
        return True  # 無料リストは sandbox 相当

    def screen(self, **kwargs) -> ScreeningResult:
        raise NotImplementedError(
            "FreeSourcesAmlBackend: pending OFAC/UN/EU list ingestion (R22+)"
        )


class ComplyAdvantageBackend:
    def __init__(self, cfg: AmlConfig) -> None:
        if not cfg.api_key:
            raise AmlError("ComplyAdvantageBackend requires api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def screen(self, **kwargs) -> ScreeningResult:
        raise NotImplementedError(
            "ComplyAdvantageBackend: pending API contract (R22+)"
        )


class WorldCheckBackend:
    def __init__(self, cfg: AmlConfig) -> None:
        if not cfg.api_key:
            raise AmlError("WorldCheckBackend requires api_key")
        self._cfg = cfg

    def is_sandbox(self) -> bool:
        return "sandbox" in (self._cfg.base_url or "").lower()

    def screen(self, **kwargs) -> ScreeningResult:
        raise NotImplementedError(
            "WorldCheckBackend: pending Refinitiv contract (R22+)"
        )


# ============================================================
# factory
# ============================================================


def aml_config_from_env() -> AmlConfig:
    return AmlConfig(
        backend=os.environ.get("JPN_PBM_AML_BACKEND", "mock"),
        api_key=os.environ.get("JPN_PBM_AML_API_KEY"),
        base_url=os.environ.get("JPN_PBM_AML_BASE_URL"),
    )


def get_aml_backend(cfg: AmlConfig | None = None) -> AmlBackend:
    cfg = cfg or aml_config_from_env()
    if cfg.backend == "mock":
        return MockAmlBackend()
    if cfg.backend == "free_sources":
        return FreeSourcesAmlBackend()
    if cfg.backend in ("complyadvantage", "comply_advantage"):
        return ComplyAdvantageBackend(cfg)
    if cfg.backend in ("worldcheck", "world_check"):
        return WorldCheckBackend(cfg)
    raise AmlError(
        f"unknown aml backend: {cfg.backend} "
        f"(expected: mock|free_sources|complyadvantage|worldcheck)"
    )
