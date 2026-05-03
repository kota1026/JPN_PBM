"""HSM 連携アダプタのテスト (戦略会議 #7 採択 B)。

env backend と mock backend が同じインターフェースを満たすことを担保。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.hsm_adapter import (
    EnvBackend,
    MockBackend,
    get_backend,
    status,
)
from app.services.sol_compat import SolCoupon, address_of, privkey_from_hex, verify_coupon_eip191


client = TestClient(app)


KEY_A = "1111111111111111111111111111111111111111111111111111111111111111"
KEY_B = "2222222222222222222222222222222222222222222222222222222222222222"


def _coupon():
    return SolCoupon.from_strings(
        program_id="prog-koto-kosodate-2026", pid="a" * 64,
        month_index=202604, cap_jpy=5000, expires_at=9999999999,
    )


# ----------------------------- env backend -----------------------------


def test_env_backend_lists_keys(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", f"{KEY_A},{KEY_B}")
    monkeypatch.setenv("JPN_PBM_GOVERNOR_ACTIVE_IDX", "0")
    backend = EnvBackend()
    keys = backend.list_keys()
    assert len(keys) == 2
    assert keys[0].key_id == "env-0"
    assert keys[0].label == "active"
    assert keys[1].label == ""


def test_env_backend_sign_then_verify(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_A)
    backend = EnvBackend()
    addr = backend.get_address("env-0")
    coupon = _coupon()
    sig = backend.sign_coupon("env-0", coupon)
    ok, _ = verify_coupon_eip191(coupon, sig, expected_address=addr)
    assert ok


def test_env_backend_unknown_key_raises(monkeypatch):
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_A)
    backend = EnvBackend()
    with pytest.raises(KeyError):
        backend.get_address("env-99")
    with pytest.raises(KeyError):
        backend.sign_coupon("foo-bar", _coupon())


# ----------------------------- mock backend -----------------------------


def test_mock_backend_parses_label_keys(monkeypatch):
    monkeypatch.setenv(
        "JPN_PBM_HSM_MOCK_KEYS", f"alpha:{KEY_A}, beta:{KEY_B}",
    )
    backend = MockBackend()
    keys = backend.list_keys()
    labels = {k.key_id for k in keys}
    assert labels == {"alpha", "beta"}


def test_mock_backend_sign_and_verify():
    backend = MockBackend(raw=f"hsm-2027:{KEY_A}")
    addr = backend.get_address("hsm-2027")
    coupon = _coupon()
    sig = backend.sign_coupon("hsm-2027", coupon)
    ok, _ = verify_coupon_eip191(coupon, sig, expected_address=addr)
    assert ok
    assert addr == address_of(privkey_from_hex(KEY_A))


def test_mock_backend_unknown_key_raises():
    backend = MockBackend(raw=f"alpha:{KEY_A}")
    with pytest.raises(KeyError):
        backend.get_address("beta")


# ----------------------------- get_backend dispatch -----------------------------


def test_get_backend_default_is_env(monkeypatch):
    monkeypatch.delenv("JPN_PBM_HSM_BACKEND", raising=False)
    monkeypatch.setenv("JPN_PBM_GOVERNOR_PRIVKEYS", KEY_A)
    backend = get_backend()
    assert isinstance(backend, EnvBackend)


def test_get_backend_mock(monkeypatch):
    monkeypatch.setenv("JPN_PBM_HSM_BACKEND", "mock")
    monkeypatch.setenv("JPN_PBM_HSM_MOCK_KEYS", f"x:{KEY_A}")
    backend = get_backend()
    assert isinstance(backend, MockBackend)


def test_get_backend_unknown_raises(monkeypatch):
    monkeypatch.setenv("JPN_PBM_HSM_BACKEND", "unknown_xxx")
    with pytest.raises(NotImplementedError):
        get_backend()


# ----------------------------- pkcs11 backend (Round 9 stub) -----------------------------


def test_pkcs11_backend_falls_back_to_mock_in_sandbox(monkeypatch):
    """sandbox (実 HSM 無し) では Mock にフォールバック。"""
    from app.services.hsm_adapter import Pkcs11Backend
    monkeypatch.delenv("JPN_PBM_HSM_PKCS11_LIBRARY", raising=False)
    monkeypatch.setenv("JPN_PBM_HSM_MOCK_KEYS", f"hsm-1:{KEY_A}")
    backend = Pkcs11Backend()
    assert not backend.is_real_hsm
    keys = backend.list_keys()
    assert len(keys) == 1
    assert keys[0].key_id == "hsm-1"


def test_pkcs11_backend_diagnostic(monkeypatch):
    from app.services.hsm_adapter import Pkcs11Backend
    monkeypatch.delenv("JPN_PBM_HSM_PKCS11_LIBRARY", raising=False)
    backend = Pkcs11Backend()
    diag = backend.diagnostic()
    assert diag["backend"] == "pkcs11"
    assert diag["fallback_in_use"] is True
    assert diag["is_real_hsm"] is False


def test_pkcs11_backend_real_hsm_detected(monkeypatch):
    """library + token 両方が設定されると is_real_hsm=True (実機接続前提)。"""
    from app.services.hsm_adapter import Pkcs11Backend
    monkeypatch.setenv("JPN_PBM_HSM_PKCS11_LIBRARY", "/usr/lib/softhsm/libsofthsm2.so")
    monkeypatch.setenv("JPN_PBM_HSM_PKCS11_TOKEN", "tokyo-pbm-token")
    backend = Pkcs11Backend()
    assert backend.is_real_hsm
    # 実 HSM は無いので NotImplementedError
    with pytest.raises(NotImplementedError):
        backend.list_keys()


def test_get_backend_pkcs11_dispatched(monkeypatch):
    from app.services.hsm_adapter import Pkcs11Backend
    monkeypatch.setenv("JPN_PBM_HSM_BACKEND", "pkcs11")
    monkeypatch.delenv("JPN_PBM_HSM_PKCS11_LIBRARY", raising=False)
    monkeypatch.setenv("JPN_PBM_HSM_MOCK_KEYS", f"x:{KEY_A}")
    backend = get_backend()
    assert isinstance(backend, Pkcs11Backend)


# ----------------------------- /treasury/hsm/status endpoint -----------------------------


def test_hsm_status_endpoint_does_not_leak_privkey(monkeypatch):
    monkeypatch.setenv("JPN_PBM_HSM_BACKEND", "mock")
    monkeypatch.setenv("JPN_PBM_HSM_MOCK_KEYS", f"hsm-1:{KEY_A},hsm-2:{KEY_B}")
    r = client.get("/treasury/hsm/status")
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "mock"
    assert body["key_count"] == 2
    # 秘密鍵が漏れていないこと
    serialized = r.text
    assert KEY_A not in serialized
    assert KEY_B not in serialized
    # address は含まれていること
    assert address_of(privkey_from_hex(KEY_A)).lower() in serialized.lower()
