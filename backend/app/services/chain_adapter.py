"""Polygon (Mumbai testnet / mainnet) chain adapter (戦略会議 #14 採択 T1)。

backend がブロックチェーンに対して持つ唯一の窓口。Phase 1 sandbox では in-process
mock、Phase 2 testnet では web3.py 経由で実 RPC を叩く。env var だけで切替可能。

【インターフェース】
- `ChainBackend.get_program(program_id)` ─ on-chain `programs[id]` 読み取り
- `ChainBackend.coupon_hash(coupon)` ─ Sol couponHash() 等価計算
- `ChainBackend.verify_coupon_signature(coupon, sig)` ─ ECDSA 検証
- `ChainBackend.estimate_redeem_gas(items)` ─ gas 見積 (Phase 2 で重要)
- `ChainBackend.is_connected()` ─ チェーン到達性

【実装】
- `MockChainBackend`: 完全 in-process。`sol_compat.coupon_hash` を再利用。
- `RealChainBackend`: web3.py + RPC URL。`web3` library 未インストール時は
  ImportError が出るが factory が mock にフォールバック。

【factory】
    backend = get_chain_backend()  # env var で自動選択
       JPN_PBM_CHAIN_BACKEND=mock          (default)
       JPN_PBM_CHAIN_BACKEND=mumbai        + JPN_PBM_CHAIN_RPC=https://...
       JPN_PBM_CHAIN_BACKEND=polygon       + JPN_PBM_CHAIN_RPC=https://...

【設計目的】
- production swap が **env var 1 つ** で済む
- CI / sandbox は常に Mock を選び、テストが安定
- `is_connected()` を見せて UI で「接続中」表示できる
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


# ============================================================
# データ型
# ============================================================


@dataclass(frozen=True)
class ChainProgram:
    """on-chain `Program` struct と等価な Python 表現。"""
    program_id: bytes        # bytes32
    issuer: str              # 0x...
    budget: int              # JPYC (=最小単位)
    spent: int
    start_at: int            # unix sec
    end_at: int
    subsidy_bps: int
    per_citizen_cap: int
    revoked: bool


@dataclass(frozen=True)
class ChainConfig:
    backend: str = "mock"                    # mock / mumbai / polygon
    rpc_url: str | None = None
    chain_id: int = 80001                    # Mumbai default
    pbm_contract: str | None = None          # 0x...
    offline_contract: str | None = None      # 0x...
    jpyc_contract: str | None = None         # 0x...
    governor_address: str | None = None      # 0x... (read only; signing uses HSM/key_management)


# ============================================================
# Protocol
# ============================================================


class ChainBackend(Protocol):
    """すべての chain 実装が満たすインターフェース。"""

    def is_connected(self) -> bool: ...
    def chain_id(self) -> int: ...
    def get_program(self, program_id: bytes) -> ChainProgram | None: ...
    def coupon_hash(self, *, program_id: bytes, pid: bytes,
                    month_index: int, cap_jpy: int, expires_at: int) -> bytes: ...
    def verify_coupon_signature(self, *, program_id: bytes, pid: bytes,
                                 month_index: int, cap_jpy: int,
                                 expires_at: int, signature: bytes,
                                 expected_signer: str) -> bool: ...
    def estimate_redeem_gas(self, batch_size: int) -> int: ...


# ============================================================
# Mock 実装 (sandbox / CI 用)
# ============================================================


class MockChainBackend:
    """Polygon RPC を叩かず in-process で動く chain 模倣。

    `services/sol_compat` を再利用し、本物と byte 互換な hash / verify を返す。
    `programs` は内部 dict 状態として保持し、テスト都度 set_program() で投入する。
    """

    def __init__(self, *, chain_id: int = 80001) -> None:
        self._chain_id = chain_id
        self._programs: dict[bytes, ChainProgram] = {}

    # -- diagnostics --

    def is_connected(self) -> bool:
        return True  # mock は常に到達可能

    def chain_id(self) -> int:
        return self._chain_id

    # -- programs --

    def set_program(self, program: ChainProgram) -> None:
        """テスト都度 program を流し込む helper。"""
        self._programs[program.program_id] = program

    def get_program(self, program_id: bytes) -> ChainProgram | None:
        return self._programs.get(program_id)

    # -- hash / signature --

    def coupon_hash(self, *, program_id: bytes, pid: bytes,
                    month_index: int, cap_jpy: int, expires_at: int) -> bytes:
        from app.services.sol_compat import SolCoupon, coupon_hash
        c = SolCoupon(program_id=program_id, pid=pid,
                       month_index=month_index, cap_jpy=cap_jpy,
                       expires_at=expires_at)
        return coupon_hash(c)

    def verify_coupon_signature(self, *, program_id: bytes, pid: bytes,
                                 month_index: int, cap_jpy: int,
                                 expires_at: int, signature: bytes,
                                 expected_signer: str) -> bool:
        from app.services.sol_compat import (
            SolCoupon, verify_coupon_eip191,
        )
        c = SolCoupon(program_id=program_id, pid=pid,
                       month_index=month_index, cap_jpy=cap_jpy,
                       expires_at=expires_at)
        return verify_coupon_eip191(c, signature, expected_signer=expected_signer)

    def estimate_redeem_gas(self, batch_size: int) -> int:
        """1 件あたり ~80,000 gas + 21,000 base (BSP/Polygon mainnet 計測値の目安)。"""
        if batch_size <= 0:
            return 21000
        return 21000 + 80000 * batch_size


# ============================================================
# Real 実装 (web3.py 経由) ─ Phase 2 起動時に使用
# ============================================================


class RealChainBackend:
    """Polygon Mumbai / mainnet 用。web3.py が無いと __init__ で ImportError。"""

    def __init__(self, cfg: ChainConfig) -> None:
        try:
            from web3 import Web3  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "web3 library not installed. install via: "
                "pip install web3 eth-account; or use MockChainBackend for sandbox"
            ) from e
        if not cfg.rpc_url:
            raise ValueError("ChainConfig.rpc_url required for RealChainBackend")
        if not cfg.pbm_contract:
            raise ValueError("ChainConfig.pbm_contract required (deployed PBM address)")
        from web3 import Web3
        self._w3 = Web3(Web3.HTTPProvider(cfg.rpc_url))
        self._cfg = cfg

    def is_connected(self) -> bool:
        try:
            return bool(self._w3.is_connected())
        except Exception:  # pragma: no cover
            return False

    def chain_id(self) -> int:
        return int(self._w3.eth.chain_id)

    def get_program(self, program_id: bytes) -> ChainProgram | None:
        # 実装は contract ABI ロード後に programs(bytes32) を call
        # NOTE: ABI を bundle するのは Round 16 以降。
        raise NotImplementedError(
            "RealChainBackend.get_program: ABI binding pending Round 16"
        )

    def coupon_hash(self, *, program_id: bytes, pid: bytes,
                    month_index: int, cap_jpy: int, expires_at: int) -> bytes:
        # ハッシュは offline 実装と同じなので mock と等価
        from app.services.sol_compat import SolCoupon, coupon_hash
        c = SolCoupon(program_id=program_id, pid=pid,
                       month_index=month_index, cap_jpy=cap_jpy,
                       expires_at=expires_at)
        return coupon_hash(c)

    def verify_coupon_signature(self, *, program_id: bytes, pid: bytes,
                                 month_index: int, cap_jpy: int,
                                 expires_at: int, signature: bytes,
                                 expected_signer: str) -> bool:
        from app.services.sol_compat import (
            SolCoupon, verify_coupon_eip191,
        )
        c = SolCoupon(program_id=program_id, pid=pid,
                       month_index=month_index, cap_jpy=cap_jpy,
                       expires_at=expires_at)
        return verify_coupon_eip191(c, signature, expected_signer=expected_signer)

    def estimate_redeem_gas(self, batch_size: int) -> int:
        # 本物は eth_estimateGas を使う。Round 16+ で実装。
        return 21000 + 80000 * batch_size


# ============================================================
# factory
# ============================================================


def chain_config_from_env() -> ChainConfig:
    return ChainConfig(
        backend=os.environ.get("JPN_PBM_CHAIN_BACKEND", "mock"),
        rpc_url=os.environ.get("JPN_PBM_CHAIN_RPC"),
        chain_id=int(os.environ.get("JPN_PBM_CHAIN_ID", "80001")),
        pbm_contract=os.environ.get("JPN_PBM_PBM_CONTRACT"),
        offline_contract=os.environ.get("JPN_PBM_OFFLINE_CONTRACT"),
        jpyc_contract=os.environ.get("JPN_PBM_JPYC_CONTRACT"),
        governor_address=os.environ.get("JPN_PBM_GOVERNOR_ADDRESS"),
    )


def get_chain_backend(cfg: ChainConfig | None = None) -> ChainBackend:
    """env var (or 引数) で適切な backend を返す。

    `JPN_PBM_CHAIN_BACKEND` が `mumbai`/`polygon` でも、
    web3 未インストール or RPC 未設定なら **暗黙にフォールバック** はしない
    (本番起動時に静かに mock に落ちるバグを避ける)。明示的に
    `JPN_PBM_CHAIN_BACKEND=mock` を指定する必要がある。
    """
    cfg = cfg or chain_config_from_env()

    if cfg.backend == "mock":
        return MockChainBackend(chain_id=cfg.chain_id)
    if cfg.backend in ("mumbai", "polygon", "real"):
        return RealChainBackend(cfg)
    raise ValueError(
        f"unknown chain backend: {cfg.backend} "
        "(expected: mock|mumbai|polygon)"
    )
