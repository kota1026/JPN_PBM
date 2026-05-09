"""chain_adapter テスト (戦略会議 #14 採択 T1)。

Mock backend の挙動 + factory + Real backend の env 不足 reject を検証。
"""

from __future__ import annotations

import os

import pytest

from app.services.chain_adapter import (
    ChainConfig,
    ChainProgram,
    MockChainBackend,
    RealChainBackend,
    chain_config_from_env,
    get_chain_backend,
)


# ============================================================
# MockChainBackend
# ============================================================


def test_mock_is_connected():
    b = MockChainBackend()
    assert b.is_connected()


def test_mock_chain_id_default():
    assert MockChainBackend().chain_id() == 80001  # Mumbai


def test_mock_chain_id_custom():
    assert MockChainBackend(chain_id=137).chain_id() == 137  # mainnet


def test_mock_get_program_returns_none_for_unknown():
    b = MockChainBackend()
    assert b.get_program(b"\x00" * 32) is None


def test_mock_set_and_get_program():
    b = MockChainBackend()
    pid = b"prog-1".ljust(32, b"\x00")
    p = ChainProgram(
        program_id=pid, issuer="0x" + "1" * 40,
        budget=10_000_000, spent=0,
        start_at=0, end_at=99_999_999_999,
        subsidy_bps=5000, per_citizen_cap=10000, revoked=False,
    )
    b.set_program(p)
    assert b.get_program(pid) == p


def test_mock_estimate_redeem_gas_scales_with_batch():
    b = MockChainBackend()
    g0 = b.estimate_redeem_gas(0)
    g1 = b.estimate_redeem_gas(1)
    g10 = b.estimate_redeem_gas(10)
    assert g0 < g1 < g10


def test_mock_coupon_hash_deterministic():
    b = MockChainBackend()
    pid = b"prog-1".ljust(32, b"\x00")
    h1 = b.coupon_hash(program_id=pid, pid=b"\x01" * 32,
                       month_index=202604, cap_jpy=5000, expires_at=9999999999)
    h2 = b.coupon_hash(program_id=pid, pid=b"\x01" * 32,
                       month_index=202604, cap_jpy=5000, expires_at=9999999999)
    assert h1 == h2
    assert len(h1) == 32


# ============================================================
# RealChainBackend (initialization should reject without env)
# ============================================================


def test_real_chain_backend_requires_rpc_url():
    with pytest.raises((ValueError, ImportError)):
        RealChainBackend(ChainConfig(backend="mumbai"))


def test_real_chain_backend_requires_pbm_contract():
    # web3 が無い環境では先に ImportError、ある環境では ValueError
    with pytest.raises((ValueError, ImportError)):
        RealChainBackend(ChainConfig(
            backend="mumbai", rpc_url="https://example.invalid",
        ))


# ============================================================
# factory
# ============================================================


def test_get_chain_backend_default_is_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_CHAIN_BACKEND", raising=False)
    b = get_chain_backend()
    assert isinstance(b, MockChainBackend)


def test_get_chain_backend_explicit_mock(monkeypatch):
    monkeypatch.setenv("JPN_PBM_CHAIN_BACKEND", "mock")
    b = get_chain_backend()
    assert isinstance(b, MockChainBackend)


def test_get_chain_backend_unknown_raises(monkeypatch):
    cfg = ChainConfig(backend="ethereum-classic")
    with pytest.raises(ValueError, match="unknown chain backend"):
        get_chain_backend(cfg)


def test_chain_config_from_env_picks_up_chain_id(monkeypatch):
    monkeypatch.setenv("JPN_PBM_CHAIN_ID", "137")
    cfg = chain_config_from_env()
    assert cfg.chain_id == 137


def test_no_silent_fallback_from_real_to_mock(monkeypatch):
    """JPN_PBM_CHAIN_BACKEND=mumbai だけ設定して RPC が無い場合、
    暗黙に mock にフォールバック せず、明示的なエラーを出す。"""
    monkeypatch.setenv("JPN_PBM_CHAIN_BACKEND", "mumbai")
    monkeypatch.delenv("JPN_PBM_CHAIN_RPC", raising=False)
    monkeypatch.delenv("JPN_PBM_PBM_CONTRACT", raising=False)
    with pytest.raises((ValueError, ImportError)):
        get_chain_backend()
