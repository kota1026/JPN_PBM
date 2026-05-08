"""ハイブリッド商品 eligibility のテスト (戦略会議 #11 採択 T3)。"""

from __future__ import annotations

import pytest

from app.services.item_eligibility import (
    ALWAYS_BLOCKED_MCCS,
    ItemContext,
    ProgramRules,
    StoreContext,
    estimate_cart,
    is_item_eligible,
)


# ----------------------------- helpers -----------------------------


def _grocery_store(approved_for: str = "prog-1", mcc: int = 5411) -> StoreContext:
    return StoreContext(id="store-1", mcc=mcc, approved_for_programs={approved_for})


def _diaper(jan: str = "4901301234567") -> ItemContext:
    return ItemContext(has_barcode=True, jan=jan, category="baby", price_jpy=500)


def _tingi() -> ItemContext:
    """バーコードなしのティンギ商品 (はかり売り米 1 カップ等)。"""
    return ItemContext(has_barcode=False, jan=None, category=None, price_jpy=80)


# ============================================================
# jan_strict モード (Tokyo モデル)
# ============================================================


def test_jan_strict_passes_when_jan_listed():
    item = _diaper("4901301234567")
    store = _grocery_store()
    rules = ProgramRules(
        program_id="prog-1", mode="jan_strict",
        eligible_jans={"4901301234567"},
    )
    d = is_item_eligible(item, store, rules)
    assert d.eligible
    assert "jan list match" in d.reason


def test_jan_strict_passes_via_category_when_jan_unknown():
    item = _diaper("9999999999999")  # JAN list に無いが
    store = _grocery_store()
    rules = ProgramRules(
        program_id="prog-1", mode="jan_strict",
        eligible_categories={"baby"},
    )
    d = is_item_eligible(item, store, rules)
    assert d.eligible


def test_jan_strict_rejects_no_barcode():
    item = _tingi()
    store = _grocery_store()
    rules = ProgramRules(program_id="prog-1", mode="jan_strict",
                         eligible_categories={"baby"})
    d = is_item_eligible(item, store, rules)
    assert not d.eligible
    assert "バーコード必須" in d.reason


def test_excluded_jan_blocks_even_when_listed():
    item = _diaper("4901301234567")
    store = _grocery_store()
    rules = ProgramRules(
        program_id="prog-1", mode="jan_strict",
        eligible_jans={"4901301234567"},
        excluded_jans={"4901301234567"},
    )
    d = is_item_eligible(item, store, rules)
    assert not d.eligible
    assert "excluded" in d.reason


# ============================================================
# mcc_only モード (Manila シンプル)
# ============================================================


def test_mcc_only_accepts_grocery():
    item = _tingi()
    store = _grocery_store(mcc=5411)
    rules = ProgramRules(program_id="prog-1", mode="mcc_only",
                         approved_mccs={5411, 5912})
    d = is_item_eligible(item, store, rules)
    assert d.eligible
    assert "approved" in d.reason


def test_mcc_only_rejects_unknown_mcc():
    item = _tingi()
    store = _grocery_store(mcc=5999)
    rules = ProgramRules(program_id="prog-1", mode="mcc_only",
                         approved_mccs={5411})
    d = is_item_eligible(item, store, rules)
    assert not d.eligible


def test_mcc_only_rejects_when_store_not_approved_for_program():
    item = _tingi()
    store = _grocery_store(approved_for="prog-OTHER", mcc=5411)
    rules = ProgramRules(program_id="prog-1", mode="mcc_only",
                         approved_mccs={5411})
    d = is_item_eligible(item, store, rules)
    assert not d.eligible
    assert "未認可" in d.reason


# ============================================================
# hybrid モード (Manila 推奨 / 個人商店共通)
# ============================================================


def test_hybrid_uses_jan_strict_when_barcode_present():
    item = _diaper("4901301234567")
    store = _grocery_store(mcc=5411)
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        eligible_jans={"4901301234567"},
        approved_mccs={5411},
        cap_no_barcode_jpy=2000,
    )
    d = is_item_eligible(item, store, rules)
    assert d.eligible
    # バーコード付きは no_barcode 枠を消費しない
    assert not d.requires_no_barcode_budget


def test_hybrid_falls_back_to_mcc_for_tingi():
    item = _tingi()
    store = _grocery_store(mcc=5411)
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        approved_mccs={5411},
        cap_no_barcode_jpy=2000,
    )
    d = is_item_eligible(item, store, rules)
    assert d.eligible
    assert d.requires_no_barcode_budget
    assert "no-barcode" in d.reason


def test_hybrid_blocks_no_barcode_when_cap_zero():
    item = _tingi()
    store = _grocery_store(mcc=5411)
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        approved_mccs={5411},
        cap_no_barcode_jpy=0,
    )
    d = is_item_eligible(item, store, rules)
    assert not d.eligible


def test_hybrid_rejects_no_barcode_at_unapproved_mcc():
    item = _tingi()
    store = _grocery_store(mcc=5921)  # liquor store (always blocked)
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        approved_mccs={5411},
        cap_no_barcode_jpy=2000,
    )
    d = is_item_eligible(item, store, rules)
    assert not d.eligible
    # ALWAYS_BLOCKED_MCCS check が先に効く
    assert "常時ブロック" in d.reason


def test_always_blocked_mccs_include_liquor_and_tobacco():
    assert 5921 in ALWAYS_BLOCKED_MCCS  # liquor
    assert 5993 in ALWAYS_BLOCKED_MCCS  # tobacco
    assert 5813 in ALWAYS_BLOCKED_MCCS  # drinking places


# ============================================================
# estimate_cart: カート単位の試算
# ============================================================


def test_estimate_cart_mixed_hybrid():
    """ハイブリッドモードで、バーコード付きとティンギを混在させた場合の試算。"""
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        eligible_jans={"4901301234567"},
        approved_mccs={5411},
        cap_no_barcode_jpy=200,  # 月 ¥200 の no-barcode 枠
    )
    store = _grocery_store(mcc=5411)
    cart = [
        _diaper("4901301234567"),                    # JAN match → eligible
        ItemContext(has_barcode=True, jan="9999",    # JAN 不明 → reject
                    category=None, price_jpy=300),
        ItemContext(has_barcode=False, jan=None,     # 80 円 ティンギ → eligible (枠内)
                    category=None, price_jpy=80),
        ItemContext(has_barcode=False, jan=None,     # 80 円 ティンギ → eligible (合計 160)
                    category=None, price_jpy=80),
        ItemContext(has_barcode=False, jan=None,     # 80 円 ティンギ → reject (枠超え 240>200)
                    category=None, price_jpy=80),
    ]
    result = estimate_cart(cart, store, rules)
    assert result["total_price_jpy"] == 500 + 300 + 80 + 80 + 80
    # eligible: diaper 500 + 2 つの ティンギ 160 = 660
    assert result["total_eligible_jpy"] == 500 + 80 + 80
    assert result["no_barcode_used_after"] == 160
    eligibles = [i["eligible"] for i in result["items"]]
    assert eligibles == [True, False, True, True, False]


def test_estimate_cart_resumes_from_prior_no_barcode_used():
    """月の前半で 150 消費済 → 追加 80 が枠内、次の 80 は超過。"""
    rules = ProgramRules(
        program_id="prog-1", mode="hybrid",
        approved_mccs={5411},
        cap_no_barcode_jpy=200,
    )
    store = _grocery_store(mcc=5411)
    cart = [_tingi(), _tingi()]  # 80 + 80
    result = estimate_cart(cart, store, rules, no_barcode_used_jpy=150)
    # 150 + 80 = 230 → 1 個目で枠超過 reject、2 個目はそのまま
    # 実装順序: 1 個目 80 → 230 > 200 で reject、no_barcode_running は 150 のまま
    # 2 個目 80 → 150 + 80 = 230 > 200 で reject
    eligibles = [i["eligible"] for i in result["items"]]
    assert eligibles == [False, False]
    assert result["total_eligible_jpy"] == 0
    assert result["no_barcode_used_after"] == 150
