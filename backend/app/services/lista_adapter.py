"""Disaster Lista (DL) adapter ─ サリサリ informal credit (CP-6 v2 PH / 戦略会議 #17 採択 PH-2)。

Aling Maria (戦略会議 #17 MVP) の現場声を反映:
- **opt-in 店舗のみ** (Lista のデジタル化を強制しない、文化的拒絶リスク)
- **災害時限定 (NDRRMC Code Red 中のみ動作)** (平時の通常運営に介入しない)
- **入金タイミング選択可** (即時 vs 週次 batch、店主の経営事情に合わせる)

【インターフェース】
- `ListaBackend.opt_in_store(store_id, payout_mode)` ─ 店舗参加登録
- `ListaBackend.activate_disaster_mode(active)` ─ NDRRMC alert 受領で起動
- `ListaBackend.add_credit(store_id, household_id, amount, items_summary)` ─ 災害特例与信記入
- `ListaBackend.list_credits(store_id, since)` ─ 復旧後の精算用一覧
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol


PayoutMode = Literal["immediate", "weekly"]


@dataclass(frozen=True)
class ListaConfig:
    backend: str = "mock"
    daily_cap_centavos: int = 20000   # PHP 200/世帯/日 (Aling Maria 推奨)
    monthly_cap_centavos: int = 600000  # PHP 6,000/世帯/月


@dataclass
class StoreOptIn:
    store_id: str
    payout_mode: PayoutMode
    opted_in_at: float = field(default_factory=time.time)


@dataclass
class ListaEntry:
    """1 件の災害特例 lista 記入。"""
    store_id: str
    household_id: str
    amount_centavos: int
    items_summary: str
    recorded_at: float
    photo_attached: bool = False  # AML 対応用 (CP-5 写真貼付 voucher)
    settled: bool = False
    settlement_ref: str | None = None


class ListaError(Exception):
    pass


class ListaBackend(Protocol):
    def opt_in_store(self, *, store_id: str, payout_mode: PayoutMode) -> StoreOptIn: ...
    def is_store_opted_in(self, store_id: str) -> bool: ...
    def activate_disaster_mode(self, active: bool) -> None: ...
    def is_disaster_mode(self) -> bool: ...
    def add_credit(self, *, store_id: str, household_id: str, amount_centavos: int,
                   items_summary: str, photo_attached: bool = False) -> ListaEntry: ...
    def list_credits(self, *, store_id: str | None = None, settled: bool = False
                     ) -> list[ListaEntry]: ...
    def mark_settled(self, entry_indices: list[int], settlement_ref: str) -> int: ...


class MockListaBackend:
    """in-process mock。disaster_mode の bool フラグで動作切替。"""

    def __init__(self, cfg: ListaConfig | None = None) -> None:
        self._cfg = cfg or ListaConfig()
        self._stores: dict[str, StoreOptIn] = {}
        self._disaster_mode = False
        self._entries: list[ListaEntry] = []

    # -- store opt-in --

    def opt_in_store(self, *, store_id: str, payout_mode: PayoutMode) -> StoreOptIn:
        if payout_mode not in ("immediate", "weekly"):
            raise ListaError(f"invalid payout_mode: {payout_mode}")
        si = StoreOptIn(store_id=store_id, payout_mode=payout_mode)
        self._stores[store_id] = si
        return si

    def opt_out_store(self, store_id: str) -> None:
        self._stores.pop(store_id, None)

    def is_store_opted_in(self, store_id: str) -> bool:
        return store_id in self._stores

    # -- disaster mode toggle (NDRRMC alert) --

    def activate_disaster_mode(self, active: bool) -> None:
        self._disaster_mode = active

    def is_disaster_mode(self) -> bool:
        return self._disaster_mode

    # -- credit operations --

    def add_credit(self, *, store_id: str, household_id: str, amount_centavos: int,
                   items_summary: str, photo_attached: bool = False) -> ListaEntry:
        if not self._disaster_mode:
            raise ListaError(
                "disaster mode not active ─ DL Protocol only works during NDRRMC Code Red"
            )
        if not self.is_store_opted_in(store_id):
            raise ListaError(f"store {store_id} not opted in")
        if amount_centavos <= 0:
            raise ListaError("amount must be > 0")

        # 1 日 1 世帯 × 1 サリサリ uniq + 日次 cap
        today_start = int(time.time()) - (int(time.time()) % 86400)
        today_total = sum(
            e.amount_centavos for e in self._entries
            if e.household_id == household_id and e.store_id == store_id
            and e.recorded_at >= today_start
        )
        if today_total + amount_centavos > self._cfg.daily_cap_centavos:
            raise ListaError(
                f"daily cap exceeded ({today_total + amount_centavos} > {self._cfg.daily_cap_centavos})"
            )
        # 月次 cap
        month_start = int(time.time()) - (int(time.time()) % (30 * 86400))
        month_total = sum(
            e.amount_centavos for e in self._entries
            if e.household_id == household_id
            and e.recorded_at >= month_start
        )
        if month_total + amount_centavos > self._cfg.monthly_cap_centavos:
            raise ListaError(
                f"monthly cap exceeded ({month_total + amount_centavos} > {self._cfg.monthly_cap_centavos})"
            )

        entry = ListaEntry(
            store_id=store_id, household_id=household_id,
            amount_centavos=amount_centavos, items_summary=items_summary,
            recorded_at=time.time(), photo_attached=photo_attached,
        )
        self._entries.append(entry)
        return entry

    def list_credits(self, *, store_id: str | None = None, settled: bool = False
                     ) -> list[ListaEntry]:
        result = []
        for e in self._entries:
            if store_id is not None and e.store_id != store_id:
                continue
            if e.settled != settled:
                continue
            result.append(e)
        return result

    def mark_settled(self, entry_indices: list[int], settlement_ref: str) -> int:
        n = 0
        for i in entry_indices:
            if 0 <= i < len(self._entries) and not self._entries[i].settled:
                self._entries[i].settled = True
                self._entries[i].settlement_ref = settlement_ref
                n += 1
        return n


def lista_config_from_env() -> ListaConfig:
    return ListaConfig(
        backend=os.environ.get("JPN_PBM_LISTA_BACKEND", "mock"),
        daily_cap_centavos=int(os.environ.get("JPN_PBM_LISTA_DAILY_CAP", "20000")),
        monthly_cap_centavos=int(os.environ.get("JPN_PBM_LISTA_MONTHLY_CAP", "600000")),
    )


def get_lista_backend(cfg: ListaConfig | None = None) -> ListaBackend:
    cfg = cfg or lista_config_from_env()
    if cfg.backend == "mock":
        return MockListaBackend(cfg)
    raise ValueError(f"unknown lista backend: {cfg.backend} (only mock for R18)")
