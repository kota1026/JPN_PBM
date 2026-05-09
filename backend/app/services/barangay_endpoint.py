"""Barangay endpoint adapter ─ バランガイ + Red Cross 立会給付 (CP-6 v2 PH / 戦略会議 #16+#17 採択 PH-3, PH-9)。

戦略会議 #17 で Dr. Carmela Reyes (人類学) と Red Team が Padrino リスク (政治偏向) を指摘。
緩和策:
- **3 層代理権限**: キャプテン → カガワド (sub-leader) → タノッド (security)
- **PRC (Philippine Red Cross) 立会必須**

【インターフェース】
- `BarangayBackend.register_official(barangay_id, role, ...)` ─ 役職登録
- `BarangayBackend.distribute(barangay_id, household_id, amount, presider, witness)` ─ 給付記録
- `BarangayBackend.door_to_door(...)` ─ 戸別訪問記録 (PRC 主体)
- `BarangayBackend.upload_ledger_scan(barangay_id, scan_uri, entries)` ─ 復旧後の手書き台帳取込
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol


OfficialRole = Literal["captain", "kagawad", "tanod", "prc_volunteer"]


class BarangayError(Exception):
    pass


@dataclass(frozen=True)
class BarangayConfig:
    backend: str = "mock"
    require_prc_witness: bool = True   # PH-9: PRC 立会必須


@dataclass
class Official:
    barangay_id: str
    role: OfficialRole
    name_hash: str           # HMAC of name (PII protection)
    phone_hash: str          # HMAC of phone


@dataclass
class DistributionEvent:
    barangay_id: str
    household_id: str
    amount_centavos: int
    items_summary: str
    presider_role: OfficialRole
    presider_hash: str
    prc_witness_hash: str | None
    is_door_to_door: bool
    recorded_at: float
    photo_uri: str | None = None
    settled: bool = False
    settlement_ref: str | None = None


class BarangayBackend(Protocol):
    def register_official(self, *, barangay_id: str, role: OfficialRole,
                           name_hash: str, phone_hash: str) -> Official: ...
    def list_officials(self, barangay_id: str) -> list[Official]: ...
    def distribute(self, *, barangay_id: str, household_id: str,
                    amount_centavos: int, items_summary: str,
                    presider_hash: str, prc_witness_hash: str | None = None,
                    photo_uri: str | None = None) -> DistributionEvent: ...
    def door_to_door(self, *, barangay_id: str, household_id: str,
                      amount_centavos: int, items_summary: str,
                      prc_volunteer_hash: str, photo_uri: str | None = None
                      ) -> DistributionEvent: ...
    def upload_ledger_scan(self, *, barangay_id: str, scan_uri: str,
                            entry_indices: list[int]) -> int: ...
    def list_distributions(self, *, barangay_id: str | None = None,
                            settled: bool | None = None) -> list[DistributionEvent]: ...


class MockBarangayBackend:
    """in-process mock。3 層代理権限 + PRC 立会の制約を強制。"""

    PRESIDER_ORDER: tuple[OfficialRole, ...] = ("captain", "kagawad", "tanod")

    def __init__(self, cfg: BarangayConfig | None = None) -> None:
        self._cfg = cfg or BarangayConfig()
        self._officials: dict[str, list[Official]] = {}
        self._events: list[DistributionEvent] = []

    # -- officials --

    def register_official(self, *, barangay_id: str, role: OfficialRole,
                           name_hash: str, phone_hash: str) -> Official:
        if role not in ("captain", "kagawad", "tanod", "prc_volunteer"):
            raise BarangayError(f"invalid role: {role}")
        o = Official(
            barangay_id=barangay_id, role=role,
            name_hash=name_hash, phone_hash=phone_hash,
        )
        self._officials.setdefault(barangay_id, []).append(o)
        return o

    def list_officials(self, barangay_id: str) -> list[Official]:
        return list(self._officials.get(barangay_id, []))

    def _find_official(self, barangay_id: str, name_hash: str) -> Official | None:
        for o in self._officials.get(barangay_id, []):
            if o.name_hash == name_hash:
                return o
        return None

    def _find_role_holder(self, barangay_id: str, role: OfficialRole) -> Official | None:
        for o in self._officials.get(barangay_id, []):
            if o.role == role:
                return o
        return None

    # -- distribution (PH-9: 3 層代理 + PRC 立会) --

    def distribute(self, *, barangay_id: str, household_id: str,
                    amount_centavos: int, items_summary: str,
                    presider_hash: str, prc_witness_hash: str | None = None,
                    photo_uri: str | None = None) -> DistributionEvent:
        if amount_centavos <= 0:
            raise BarangayError("amount must be > 0")

        # 立会者は 3 層代理のいずれかに該当する必要がある
        presider = self._find_official(barangay_id, presider_hash)
        if presider is None:
            raise BarangayError("presider not registered as official in this barangay")
        if presider.role not in self.PRESIDER_ORDER:
            raise BarangayError(
                f"presider role {presider.role} is not authorized to distribute"
            )

        # PH-9: 3 層継承の検証 ─ captain がいるなら captain が presider すべき (or 不在)
        # 簡略化: 各 role の "上位者不在" 状況をシステムが追跡しないため
        # 本番運用では「キャプテン不在チェックボックス」を UI で持たせる想定。

        # PRC 立会必須 (cfg で強制)
        if self._cfg.require_prc_witness:
            if prc_witness_hash is None:
                raise BarangayError("PRC witness required (PH-9: Padrino risk mitigation)")
            witness = self._find_official(barangay_id, prc_witness_hash)
            if witness is None or witness.role != "prc_volunteer":
                raise BarangayError("PRC witness must be registered prc_volunteer")

        ev = DistributionEvent(
            barangay_id=barangay_id, household_id=household_id,
            amount_centavos=amount_centavos, items_summary=items_summary,
            presider_role=presider.role, presider_hash=presider_hash,
            prc_witness_hash=prc_witness_hash,
            is_door_to_door=False, recorded_at=time.time(),
            photo_uri=photo_uri,
        )
        self._events.append(ev)
        return ev

    # -- door-to-door (PRC 主体) --

    def door_to_door(self, *, barangay_id: str, household_id: str,
                      amount_centavos: int, items_summary: str,
                      prc_volunteer_hash: str, photo_uri: str | None = None
                      ) -> DistributionEvent:
        if amount_centavos <= 0:
            raise BarangayError("amount must be > 0")
        volunteer = self._find_official(barangay_id, prc_volunteer_hash)
        if volunteer is None or volunteer.role != "prc_volunteer":
            raise BarangayError("door-to-door requires registered PRC volunteer")
        ev = DistributionEvent(
            barangay_id=barangay_id, household_id=household_id,
            amount_centavos=amount_centavos, items_summary=items_summary,
            presider_role="prc_volunteer", presider_hash=prc_volunteer_hash,
            prc_witness_hash=None,  # 自身が PRC なので別 witness 不要
            is_door_to_door=True, recorded_at=time.time(),
            photo_uri=photo_uri,
        )
        self._events.append(ev)
        return ev

    # -- ledger scan upload (復旧後の手書き台帳取込) --

    def upload_ledger_scan(self, *, barangay_id: str, scan_uri: str,
                            entry_indices: list[int]) -> int:
        n = 0
        for i in entry_indices:
            if 0 <= i < len(self._events) and self._events[i].barangay_id == barangay_id:
                self._events[i].photo_uri = scan_uri
                n += 1
        return n

    def list_distributions(self, *, barangay_id: str | None = None,
                            settled: bool | None = None) -> list[DistributionEvent]:
        out = []
        for e in self._events:
            if barangay_id is not None and e.barangay_id != barangay_id:
                continue
            if settled is not None and e.settled != settled:
                continue
            out.append(e)
        return out


def barangay_config_from_env() -> BarangayConfig:
    return BarangayConfig(
        backend=os.environ.get("JPN_PBM_BARANGAY_BACKEND", "mock"),
        require_prc_witness=os.environ.get("JPN_PBM_BARANGAY_REQUIRE_PRC", "1") == "1",
    )


def get_barangay_backend(cfg: BarangayConfig | None = None) -> BarangayBackend:
    cfg = cfg or barangay_config_from_env()
    if cfg.backend == "mock":
        return MockBarangayBackend(cfg)
    raise ValueError(f"unknown barangay backend: {cfg.backend} (only mock for R18)")
