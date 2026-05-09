"""landbank_bridge テスト (戦略会議 #14 採択 T4)。

Mock bridge の状態遷移 + CP-5 二重支給 reject + CP-6 grace + factory を検証。
"""

from __future__ import annotations

import pytest

from app.services.landbank_bridge import (
    DswdProxyLandBankBridge,
    LandBankConfig,
    MockLandBankBridge,
    get_landbank_bridge,
    landbank_config_from_env,
)


PID = "abcd" * 16  # 64 hex chars (HMAC PSN proxy)


# ============================================================
# 基本: モード設定 + read
# ============================================================


def test_set_mode_landbank_only():
    b = MockLandBankBridge()
    s = b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="landbank_only", landbank_amount_centavos=140000,
    )
    assert s.mode == "landbank_only"
    assert s.landbank_amount_centavos == 140000
    assert s.pbm_amount_centavos == 0


def test_set_mode_pbm_only():
    b = MockLandBankBridge()
    s = b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="pbm_only", pbm_amount_centavos=140000,
    )
    assert s.mode == "pbm_only"


def test_set_mode_split():
    b = MockLandBankBridge()
    s = b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="split",
        landbank_amount_centavos=70000, pbm_amount_centavos=70000,
    )
    assert s.mode == "split"
    assert s.landbank_amount_centavos == 70000
    assert s.pbm_amount_centavos == 70000


def test_set_mode_landbank_only_rejects_pbm_amount():
    b = MockLandBankBridge()
    with pytest.raises(ValueError, match="cannot have pbm_amount"):
        b.set_disbursement_mode(
            psn_pid=PID, month_index=202608,
            mode="landbank_only",
            landbank_amount_centavos=140000, pbm_amount_centavos=1,
        )


def test_set_mode_pbm_only_rejects_landbank_amount():
    b = MockLandBankBridge()
    with pytest.raises(ValueError, match="cannot have landbank_amount"):
        b.set_disbursement_mode(
            psn_pid=PID, month_index=202608,
            mode="pbm_only",
            landbank_amount_centavos=1, pbm_amount_centavos=140000,
        )


def test_get_household_state_returns_none_for_unset():
    b = MockLandBankBridge()
    assert b.get_household_state(psn_pid=PID, month_index=999999) is None


# ============================================================
# CP-5: 二重支給 防止
# ============================================================


def test_landbank_withdrawal_rejected_in_pbm_only_mode():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="pbm_only", pbm_amount_centavos=140000,
    )
    with pytest.raises(ValueError, match="CP-5 violation"):
        b.record_landbank_withdrawal(
            psn_pid=PID, month_index=202608, amount_centavos=10000,
        )


def test_pbm_redemption_rejected_in_landbank_only_mode():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="landbank_only", landbank_amount_centavos=140000,
    )
    with pytest.raises(ValueError, match="CP-5 violation"):
        b.record_pbm_redemption(
            psn_pid=PID, month_index=202608, amount_centavos=10000,
        )


def test_split_mode_allows_both_within_limits():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="split",
        landbank_amount_centavos=70000, pbm_amount_centavos=70000,
    )
    s1 = b.record_landbank_withdrawal(
        psn_pid=PID, month_index=202608, amount_centavos=30000,
    )
    s2 = b.record_pbm_redemption(
        psn_pid=PID, month_index=202608, amount_centavos=20000,
    )
    assert s1.landbank_withdrawn_centavos == 30000
    assert s2.pbm_redeemed_centavos == 20000


def test_landbank_cap_exceeded_rejected():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="landbank_only", landbank_amount_centavos=10000,
    )
    with pytest.raises(ValueError, match="cap exceeded"):
        b.record_landbank_withdrawal(
            psn_pid=PID, month_index=202608, amount_centavos=15000,
        )


def test_pbm_cap_exceeded_rejected():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608,
        mode="pbm_only", pbm_amount_centavos=10000,
    )
    with pytest.raises(ValueError, match="cap exceeded"):
        b.record_pbm_redemption(
            psn_pid=PID, month_index=202608, amount_centavos=15000,
        )


def test_uninitialized_household_withdrawal_rejected():
    b = MockLandBankBridge()
    with pytest.raises(ValueError, match="not initialized"):
        b.record_landbank_withdrawal(
            psn_pid=PID, month_index=202608, amount_centavos=100,
        )


def test_zero_or_negative_amount_rejected():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="pbm_only",
        pbm_amount_centavos=10000,
    )
    with pytest.raises(ValueError, match="amount"):
        b.record_pbm_redemption(
            psn_pid=PID, month_index=202608, amount_centavos=0,
        )
    with pytest.raises(ValueError, match="amount"):
        b.record_pbm_redemption(
            psn_pid=PID, month_index=202608, amount_centavos=-1,
        )


# ============================================================
# CP-6: 災害時オフライン補正
# ============================================================


def test_offline_reconcile_within_cap():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="pbm_only",
        pbm_amount_centavos=140000,
    )
    s = b.reconcile_offline_redemptions(
        psn_pid=PID, month_index=202608, offline_total_centavos=50000,
    )
    assert s.pbm_redeemed_centavos == 50000


def test_offline_reconcile_exceeds_cap_logged_but_allowed():
    """CP-6 grace: 災害時オフライン超過は audit log に残るが、reject はしない。"""
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="pbm_only",
        pbm_amount_centavos=10000,
    )
    s = b.reconcile_offline_redemptions(
        psn_pid=PID, month_index=202608, offline_total_centavos=15000,
    )
    assert s.pbm_redeemed_centavos == 15000  # 超過そのまま記録
    log = b.audit_log()
    overage = [e for e in log if e.op == "offline_overage"]
    assert len(overage) == 1


def test_offline_reconcile_zero_is_noop():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="pbm_only",
        pbm_amount_centavos=10000,
    )
    s = b.reconcile_offline_redemptions(
        psn_pid=PID, month_index=202608, offline_total_centavos=0,
    )
    assert s.pbm_redeemed_centavos == 0


# ============================================================
# Audit
# ============================================================


def test_audit_log_records_each_operation():
    b = MockLandBankBridge()
    b.set_disbursement_mode(
        psn_pid=PID, month_index=202608, mode="split",
        landbank_amount_centavos=70000, pbm_amount_centavos=70000,
    )
    b.record_landbank_withdrawal(psn_pid=PID, month_index=202608, amount_centavos=10000)
    b.record_pbm_redemption(psn_pid=PID, month_index=202608, amount_centavos=20000)
    log = b.audit_log()
    ops = [e.op for e in log]
    assert "set_mode" in ops
    assert "lb_withdraw" in ops
    assert "pbm_redeem" in ops


# ============================================================
# Real backend / factory
# ============================================================


def test_dswd_proxy_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        DswdProxyLandBankBridge(LandBankConfig(
            backend="dswd_proxy", base_url="https://x",
        ))


def test_dswd_proxy_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        DswdProxyLandBankBridge(LandBankConfig(
            backend="dswd_proxy", api_key="K",
        ))


def test_factory_default_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_LANDBANK_BACKEND", raising=False)
    assert isinstance(get_landbank_bridge(), MockLandBankBridge)


def test_factory_unknown_raises():
    with pytest.raises(ValueError):
        get_landbank_bridge(LandBankConfig(backend="goldman"))


def test_config_from_env_timeout(monkeypatch):
    monkeypatch.setenv("JPN_PBM_LANDBANK_TIMEOUT", "8.0")
    cfg = landbank_config_from_env()
    assert cfg.timeout_sec == 8.0
