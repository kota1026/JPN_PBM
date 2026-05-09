"""マイナンバーカード Felica SE adapter (CP-6 v2 JP / 戦略会議 #16 採択 JP-2)。

CP-6 v1 の POS 依存設計が破綻したため、新設。SE (Secure Element) に
「今月のオフライン枠」を pre-stage し、災害時に避難所端末で読み取る。

【インターフェース】
- `SeBackend.prefund(pid, month_index, capJpy)` ─ 月初にカードへ書込
- `SeBackend.read_card(card_id)` ─ NFC で SE 読取
- `SeBackend.consume(card_id, amount, ref)` ─ 給付時に SE counter 消費
- `SeBackend.consumed(card_id)` ─ 累積消費額

【factory】
    backend = get_se_backend()
       JPN_PBM_SE_BACKEND=mock           (default, sandbox)
       JPN_PBM_SE_BACKEND=jpki           + JPKI 接続情報 (R20+)

サンドボックスでは完全 in-process mock。本物の Felica/JPKI 接続は R20+。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SeConfig:
    backend: str = "mock"
    jpki_endpoint: str | None = None
    timeout_sec: float = 5.0


@dataclass
class SeCardState:
    """1 枚のマイナンバーカード SE 上の状態。"""
    card_id: str                      # HMAC PID
    month_index: int                  # YYYYMM
    cap_jpy: int                      # 月次オフライン枠
    consumed_jpy: int = 0             # 当月累積消費
    counter: int = 0                  # monotonic counter (anti-replay)
    last_op_at: float = 0.0


class SeReadError(Exception):
    pass


class SeWriteError(Exception):
    pass


class SeBackend(Protocol):
    def prefund(self, *, card_id: str, month_index: int, cap_jpy: int) -> SeCardState: ...
    def read_card(self, card_id: str) -> SeCardState | None: ...
    def consume(self, *, card_id: str, amount_jpy: int, ref: str) -> SeCardState: ...
    def consumed(self, card_id: str) -> int: ...


class MockSeBackend:
    """in-process mock SE backend。

    1 枚の SE = 1 SeCardState。tampering / counter 巻戻し不可を **dict 制約** で表現。
    """

    def __init__(self) -> None:
        self._cards: dict[str, SeCardState] = {}

    def prefund(self, *, card_id: str, month_index: int, cap_jpy: int) -> SeCardState:
        """月初に「今月のオフライン枠」を pre-stage する。"""
        if cap_jpy <= 0:
            raise SeWriteError("cap_jpy must be > 0")
        existing = self._cards.get(card_id)
        if existing is not None and existing.month_index == month_index:
            # 同月の二重 prefund は許さない (idempotent ではない、2 重発行リスク)
            raise SeWriteError(
                f"card {card_id[:8]}.. already prefunded for month {month_index}"
            )
        state = SeCardState(
            card_id=card_id, month_index=month_index, cap_jpy=cap_jpy,
            consumed_jpy=0, counter=0, last_op_at=time.time(),
        )
        self._cards[card_id] = state
        return state

    def read_card(self, card_id: str) -> SeCardState | None:
        return self._cards.get(card_id)

    def consume(self, *, card_id: str, amount_jpy: int, ref: str) -> SeCardState:
        if amount_jpy <= 0:
            raise SeWriteError("amount must be > 0")
        st = self._cards.get(card_id)
        if st is None:
            raise SeReadError(f"card {card_id[:8]}.. not prefunded")
        new_consumed = st.consumed_jpy + amount_jpy
        if new_consumed > st.cap_jpy:
            raise SeWriteError(
                f"cap exceeded ({new_consumed} > {st.cap_jpy})"
            )
        # SE counter は monotonic (タンパー耐性チップで巻き戻し不可)
        st.consumed_jpy = new_consumed
        st.counter += 1
        st.last_op_at = time.time()
        return st

    def consumed(self, card_id: str) -> int:
        st = self._cards.get(card_id)
        return st.consumed_jpy if st else 0


class JpkiSeBackend:
    """本物 JPKI 経由 (R20+ 実装)。"""

    def __init__(self, cfg: SeConfig) -> None:
        if not cfg.jpki_endpoint:
            raise ValueError("SeConfig.jpki_endpoint required")
        self._cfg = cfg

    def _impl_pending(self):
        raise NotImplementedError(
            "JpkiSeBackend: pending JPKI API integration (R20+)"
        )

    def prefund(self, **k): return self._impl_pending()
    def read_card(self, card_id): return self._impl_pending()
    def consume(self, **k): return self._impl_pending()
    def consumed(self, card_id): return 0


def se_config_from_env() -> SeConfig:
    return SeConfig(
        backend=os.environ.get("JPN_PBM_SE_BACKEND", "mock"),
        jpki_endpoint=os.environ.get("JPN_PBM_JPKI_ENDPOINT"),
        timeout_sec=float(os.environ.get("JPN_PBM_SE_TIMEOUT", "5.0")),
    )


def get_se_backend(cfg: SeConfig | None = None) -> SeBackend:
    cfg = cfg or se_config_from_env()
    if cfg.backend == "mock":
        return MockSeBackend()
    if cfg.backend in ("jpki", "real"):
        return JpkiSeBackend(cfg)
    raise ValueError(f"unknown SE backend: {cfg.backend} (expected: mock|jpki)")
