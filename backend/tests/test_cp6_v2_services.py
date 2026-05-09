"""CP-6 v2 4 services の統合テスト (戦略会議 #16+#17 採択)。

JP-2: se_card_adapter
PH-2: lista_adapter
PH-3: barangay_endpoint
PH-4: ndrrmc_alert
"""

from __future__ import annotations

import time

import pytest

from app.services.se_card_adapter import (
    MockSeBackend, SeReadError, SeWriteError,
    get_se_backend, JpkiSeBackend, SeConfig,
)
from app.services.lista_adapter import (
    MockListaBackend, ListaError, ListaConfig,
    get_lista_backend,
)
from app.services.barangay_endpoint import (
    MockBarangayBackend, BarangayError, BarangayConfig,
    get_barangay_backend,
)
from app.services.ndrrmc_alert import (
    MockNdrrmcBackend, NdrrmcAlert,
    get_ndrrmc_backend, NdrrmcConfig, SmsGatewayNdrrmcBackend,
)


# ============================================================
# T1: SE card adapter (JP)
# ============================================================


def test_se_prefund_basic():
    se = MockSeBackend()
    st = se.prefund(card_id="A" * 64, month_index=202608, cap_jpy=10000)
    assert st.cap_jpy == 10000
    assert st.consumed_jpy == 0
    assert st.counter == 0


def test_se_prefund_double_for_same_month_rejected():
    se = MockSeBackend()
    se.prefund(card_id="A" * 64, month_index=202608, cap_jpy=10000)
    with pytest.raises(SeWriteError, match="already prefunded"):
        se.prefund(card_id="A" * 64, month_index=202608, cap_jpy=5000)


def test_se_consume_increments_counter():
    se = MockSeBackend()
    se.prefund(card_id="A" * 64, month_index=202608, cap_jpy=10000)
    st = se.consume(card_id="A" * 64, amount_jpy=3000, ref="r1")
    assert st.consumed_jpy == 3000
    assert st.counter == 1
    st = se.consume(card_id="A" * 64, amount_jpy=2000, ref="r2")
    assert st.consumed_jpy == 5000
    assert st.counter == 2


def test_se_consume_cap_exceeded_rejected():
    se = MockSeBackend()
    se.prefund(card_id="A" * 64, month_index=202608, cap_jpy=5000)
    se.consume(card_id="A" * 64, amount_jpy=4000, ref="r1")
    with pytest.raises(SeWriteError, match="cap exceeded"):
        se.consume(card_id="A" * 64, amount_jpy=2000, ref="r2")


def test_se_consume_unknown_card_rejected():
    se = MockSeBackend()
    with pytest.raises(SeReadError, match="not prefunded"):
        se.consume(card_id="X" * 64, amount_jpy=100, ref="r")


def test_se_factory_default_mock(monkeypatch):
    monkeypatch.delenv("JPN_PBM_SE_BACKEND", raising=False)
    assert isinstance(get_se_backend(), MockSeBackend)


def test_se_jpki_requires_endpoint():
    with pytest.raises(ValueError, match="endpoint"):
        JpkiSeBackend(SeConfig(backend="jpki"))


# ============================================================
# T2: Lista adapter (PH)
# ============================================================


def test_lista_default_disaster_mode_off():
    la = MockListaBackend()
    assert not la.is_disaster_mode()


def test_lista_credit_rejected_when_disaster_inactive():
    la = MockListaBackend()
    la.opt_in_store(store_id="ph-store-aling-maria-qc", payout_mode="immediate")
    with pytest.raises(ListaError, match="disaster mode not active"):
        la.add_credit(
            store_id="ph-store-aling-maria-qc",
            household_id="h" * 64,
            amount_centavos=5000,
            items_summary="rice + canned",
        )


def test_lista_credit_rejected_when_store_not_opted_in():
    la = MockListaBackend()
    la.activate_disaster_mode(True)
    with pytest.raises(ListaError, match="not opted in"):
        la.add_credit(
            store_id="ph-store-not-opted",
            household_id="h" * 64,
            amount_centavos=5000,
            items_summary="x",
        )


def test_lista_normal_credit_succeeds():
    la = MockListaBackend()
    la.opt_in_store(store_id="ph-store-aling-maria-qc", payout_mode="immediate")
    la.activate_disaster_mode(True)
    e = la.add_credit(
        store_id="ph-store-aling-maria-qc",
        household_id="h" * 64,
        amount_centavos=5000,
        items_summary="rice 1kg + canned sardines",
        photo_attached=True,
    )
    assert e.amount_centavos == 5000
    assert e.photo_attached
    assert not e.settled


def test_lista_daily_cap_enforced():
    la = MockListaBackend(ListaConfig(daily_cap_centavos=10000))
    la.opt_in_store(store_id="s1", payout_mode="weekly")
    la.activate_disaster_mode(True)
    la.add_credit(store_id="s1", household_id="h" * 64,
                  amount_centavos=8000, items_summary="x")
    with pytest.raises(ListaError, match="daily cap exceeded"):
        la.add_credit(store_id="s1", household_id="h" * 64,
                      amount_centavos=3000, items_summary="x")


def test_lista_invalid_payout_mode_rejected():
    la = MockListaBackend()
    with pytest.raises(ListaError, match="payout_mode"):
        la.opt_in_store(store_id="s", payout_mode="biweekly")  # type: ignore


def test_lista_settle_marks_entries():
    la = MockListaBackend()
    la.opt_in_store(store_id="s1", payout_mode="weekly")
    la.activate_disaster_mode(True)
    la.add_credit(store_id="s1", household_id="h" * 64,
                  amount_centavos=1000, items_summary="x")
    la.add_credit(store_id="s1", household_id="g" * 64,
                  amount_centavos=2000, items_summary="y")
    n = la.mark_settled([0, 1], settlement_ref="batch-001")
    assert n == 2
    assert la.list_credits(store_id="s1", settled=False) == []
    assert len(la.list_credits(store_id="s1", settled=True)) == 2


# ============================================================
# T3: Barangay endpoint (PH)
# ============================================================


def _setup_barangay(b: MockBarangayBackend, brgy: str = "B1") -> dict:
    """テスト用: captain + kagawad + tanod + prc を登録"""
    return {
        "captain": b.register_official(barangay_id=brgy, role="captain",
                                        name_hash="cap-hash", phone_hash="cap-ph"),
        "kagawad": b.register_official(barangay_id=brgy, role="kagawad",
                                        name_hash="kag-hash", phone_hash="kag-ph"),
        "tanod": b.register_official(barangay_id=brgy, role="tanod",
                                      name_hash="tan-hash", phone_hash="tan-ph"),
        "prc": b.register_official(barangay_id=brgy, role="prc_volunteer",
                                    name_hash="prc-hash", phone_hash="prc-ph"),
    }


def test_barangay_distribute_with_captain_and_prc_witness():
    b = MockBarangayBackend()
    _setup_barangay(b)
    ev = b.distribute(
        barangay_id="B1", household_id="h" * 64,
        amount_centavos=5000, items_summary="rice + water",
        presider_hash="cap-hash", prc_witness_hash="prc-hash",
    )
    assert ev.presider_role == "captain"
    assert ev.prc_witness_hash == "prc-hash"
    assert not ev.is_door_to_door


def test_barangay_distribute_rejects_without_prc_witness():
    b = MockBarangayBackend()
    _setup_barangay(b)
    with pytest.raises(BarangayError, match="PRC witness required"):
        b.distribute(
            barangay_id="B1", household_id="h" * 64,
            amount_centavos=5000, items_summary="x",
            presider_hash="cap-hash", prc_witness_hash=None,
        )


def test_barangay_distribute_rejects_unregistered_presider():
    b = MockBarangayBackend()
    _setup_barangay(b)
    with pytest.raises(BarangayError, match="presider not registered"):
        b.distribute(
            barangay_id="B1", household_id="h" * 64,
            amount_centavos=5000, items_summary="x",
            presider_hash="random-hash", prc_witness_hash="prc-hash",
        )


def test_barangay_distribute_rejects_prc_as_presider():
    """PRC は presider にはなれない (立会専門)。"""
    b = MockBarangayBackend()
    _setup_barangay(b)
    with pytest.raises(BarangayError, match="not authorized to distribute"):
        b.distribute(
            barangay_id="B1", household_id="h" * 64,
            amount_centavos=5000, items_summary="x",
            presider_hash="prc-hash", prc_witness_hash="prc-hash",
        )


def test_barangay_door_to_door_by_prc_volunteer():
    b = MockBarangayBackend()
    _setup_barangay(b)
    ev = b.door_to_door(
        barangay_id="B1", household_id="h" * 64,
        amount_centavos=3000, items_summary="x",
        prc_volunteer_hash="prc-hash",
    )
    assert ev.is_door_to_door
    assert ev.presider_role == "prc_volunteer"


def test_barangay_door_to_door_rejects_non_prc():
    b = MockBarangayBackend()
    _setup_barangay(b)
    with pytest.raises(BarangayError, match="PRC volunteer"):
        b.door_to_door(
            barangay_id="B1", household_id="h" * 64,
            amount_centavos=3000, items_summary="x",
            prc_volunteer_hash="cap-hash",
        )


def test_barangay_can_disable_prc_requirement_via_config():
    b = MockBarangayBackend(BarangayConfig(require_prc_witness=False))
    _setup_barangay(b)
    ev = b.distribute(
        barangay_id="B1", household_id="h" * 64,
        amount_centavos=1000, items_summary="x",
        presider_hash="cap-hash", prc_witness_hash=None,
    )
    assert ev.prc_witness_hash is None


def test_barangay_kagawad_can_distribute_with_prc():
    """PH-9: 3 層継承 (キャプテン → カガワド → タノッド)。"""
    b = MockBarangayBackend()
    _setup_barangay(b)
    ev = b.distribute(
        barangay_id="B1", household_id="h" * 64,
        amount_centavos=2000, items_summary="x",
        presider_hash="kag-hash", prc_witness_hash="prc-hash",
    )
    assert ev.presider_role == "kagawad"


# ============================================================
# T4: NDRRMC alert (PH)
# ============================================================


def test_ndrrmc_no_active_alerts_initially():
    n = MockNdrrmcBackend()
    assert n.list_active_alerts() == []
    assert not n.is_code_red("QC")


def test_ndrrmc_publish_and_query():
    n = MockNdrrmcBackend()
    a = NdrrmcAlert(
        alert_id="a1", level="red", lgu_codes=("QC", "MNL"),
        source="ndrrmc_sms", issued_at=time.time(),
        valid_until=time.time() + 3600, description="Typhoon Yolanda Cat 5",
    )
    n.publish_alert(a)
    assert n.is_code_red("QC")
    assert n.is_code_red("MNL")
    assert not n.is_code_red("CEB")  # not in lgu_codes


def test_ndrrmc_expired_alert_no_longer_active():
    n = MockNdrrmcBackend()
    a = NdrrmcAlert(
        alert_id="old", level="red", lgu_codes=("QC",),
        source="ndrrmc_sms", issued_at=time.time() - 7200,
        valid_until=time.time() - 3600,
    )
    n.publish_alert(a)
    assert not n.is_code_red("QC")
    assert n.list_active_alerts() == []


def test_ndrrmc_callback_fires_on_publish():
    n = MockNdrrmcBackend()
    received: list = []
    n.subscribe_callback(lambda alert: received.append(alert.alert_id))
    a = NdrrmcAlert(
        alert_id="a2", level="red", lgu_codes=("QC",),
        source="prc_api", issued_at=time.time(),
        valid_until=time.time() + 3600,
    )
    n.publish_alert(a)
    assert received == ["a2"]


def test_ndrrmc_callback_failure_does_not_block():
    """callback 失敗が他の callback or alert 発行を止めないこと。"""
    n = MockNdrrmcBackend()
    n.subscribe_callback(lambda a: (_ for _ in ()).throw(RuntimeError("boom")))
    received: list = []
    n.subscribe_callback(lambda a: received.append(a.alert_id))
    a = NdrrmcAlert(
        alert_id="a3", level="red", lgu_codes=("QC",),
        source="manual_override", issued_at=time.time(),
        valid_until=time.time() + 3600,
    )
    n.publish_alert(a)  # should not raise
    assert received == ["a3"]


def test_ndrrmc_manual_override_works():
    """PH-4: SMS が来ない場合の手動 fallback。"""
    n = MockNdrrmcBackend()
    a = n.manual_override(lgu_code="QC", level="red", duration_sec=3600,
                           description="manual storm declaration")
    assert n.is_code_red("QC")
    assert a.source == "manual_override"


def test_ndrrmc_factory_sms_gateway_requires_url():
    with pytest.raises(ValueError, match="sms_gateway_url"):
        SmsGatewayNdrrmcBackend(NdrrmcConfig(backend="sms_gateway", sms_gateway_token="T"))


# ============================================================
# 統合: NDRRMC alert → Lista activate コールバック
# ============================================================


def test_ndrrmc_alert_can_activate_lista_via_callback():
    """PH-2 + PH-4: 災害宣言 → DL Protocol 自動起動の連鎖を mock で再現。"""
    n = MockNdrrmcBackend()
    la = MockListaBackend()
    la.opt_in_store(store_id="s1", payout_mode="immediate")

    def on_alert(alert: NdrrmcAlert):
        if alert.is_code_red():
            la.activate_disaster_mode(True)

    n.subscribe_callback(on_alert)
    assert not la.is_disaster_mode()  # before alert

    a = NdrrmcAlert(
        alert_id="storm-1", level="red", lgu_codes=("QC",),
        source="ndrrmc_sms", issued_at=time.time(),
        valid_until=time.time() + 3600,
    )
    n.publish_alert(a)
    assert la.is_disaster_mode()  # auto-activated

    # Lista add_credit が今度は通る
    la.add_credit(store_id="s1", household_id="h" * 64,
                  amount_centavos=5000, items_summary="emergency rice")
