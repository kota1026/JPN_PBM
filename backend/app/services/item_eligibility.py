"""ハイブリッド商品 eligibility (戦略会議 #11 採択 T3)。

商品レベルの対象判定を 3 つの mode で抽象化:

- **jan_strict** (既存 / Tokyo モデル):
  バーコード必須。`eligible_jans` か `eligible_categories` に含まれることを要求。
  POS スキャナがある前提。

- **mcc_only** (Manila サリサリ単純モデル):
  店舗の MCC (Merchant Category Code) が `approved_mccs` に含まれることのみで判定。
  バーコード不要。店主の事前認定 + audit が信頼アンカー。

- **hybrid** (Manila 推奨 / 個人商店共通):
  バーコードが付いていれば `jan_strict` ロジック。
  付いていなければ店舗の MCC が approved に入っていれば許可、
  ただし「バーコード無し購入」の月次累計が `cap_no_barcode_jpy` を超えない範囲に限定。

```
+----------------------+----------------+----------------+
| eligibility_mode     | item.has_barcode = True         |
|                      |  Yes               No           |
+----------------------+----------------+----------------+
| jan_strict           | JAN list 検査  | reject         |
| mcc_only             | (両方とも) MCC 検査のみ        |
| hybrid               | JAN list 検査  | MCC + cap 検査 |
+----------------------+----------------+----------------+
```

【データクラスとして定義する理由】
SQLAlchemy モデルへの直接の追加を避け、まず純粋関数として実装する。
将来 `models/program.py` に `eligibility_mode` カラムを追加する時に、
そこからこの関数群を呼び出せばよい (Round 13 候補)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal


EligibilityMode = Literal["jan_strict", "mcc_only", "hybrid"]


@dataclass
class ItemContext:
    """購入したい個別商品の最小情報。"""
    has_barcode: bool                # バーコード読取に成功したか
    jan: str | None                  # has_barcode=True 時のみ意味あり
    category: str | None = None      # 商品マスタからの分類 (任意)
    price_jpy: int = 0


@dataclass
class StoreContext:
    """加盟店の情報。"""
    id: str
    mcc: int | None = None           # ISO 18245 MCC (5411=grocery, 5912=drug, ...)
    approved_for_programs: set[str] = field(default_factory=set)


@dataclass
class ProgramRules:
    """eligibility_mode と関連設定。"""
    program_id: str
    mode: EligibilityMode
    eligible_jans: set[str] = field(default_factory=set)
    eligible_categories: set[str] = field(default_factory=set)
    excluded_jans: set[str] = field(default_factory=set)
    approved_mccs: set[int] = field(default_factory=set)
    cap_no_barcode_jpy: int = 0      # hybrid モード時、バーコード無し月額上限


@dataclass
class ItemDecision:
    eligible: bool
    reason: str
    requires_no_barcode_budget: bool = False  # hybrid で "バーコード無し枠" を消費するか


# ---- ブラックリスト系 MCC ----

# 4Ps / 子育て助成等で常に対象外にすべき高リスク MCC。
# Visa / Mastercard / EMV の MCC リストに準拠。
ALWAYS_BLOCKED_MCCS: set[int] = {
    5921,  # Liquor (酒類)
    5993,  # Cigar / tobacco shop
    5813,  # Drinking places (alcohol)
    7995,  # Gambling
    5933,  # Pawn shop
}


# ---- 判定本体 ----


def is_item_eligible(
    item: ItemContext, store: StoreContext, rules: ProgramRules
) -> ItemDecision:
    """1 商品 × 1 店舗 × 1 プログラムの eligibility を判定する。"""

    # 共通: 店舗認可チェック
    if rules.program_id not in store.approved_for_programs:
        return ItemDecision(False, f"store {store.id} は program {rules.program_id} 未認可")

    # 共通: ブラックリスト MCC の店舗は無条件 reject
    if store.mcc in ALWAYS_BLOCKED_MCCS:
        return ItemDecision(False, f"store mcc={store.mcc} は常時ブロック対象")

    # 共通: excluded_jans (ブラックリスト)
    if item.has_barcode and item.jan in rules.excluded_jans:
        return ItemDecision(False, f"jan {item.jan} は excluded")

    if rules.mode == "jan_strict":
        if not item.has_barcode:
            return ItemDecision(False, "jan_strict モードはバーコード必須")
        if item.jan in rules.eligible_jans:
            return ItemDecision(True, "jan list match")
        if item.category and item.category in rules.eligible_categories:
            return ItemDecision(True, f"category {item.category} match")
        return ItemDecision(False, f"jan {item.jan} は対象外")

    if rules.mode == "mcc_only":
        if store.mcc is None:
            return ItemDecision(False, "store.mcc 未設定")
        if store.mcc in rules.approved_mccs:
            return ItemDecision(True, f"store mcc={store.mcc} approved (mcc_only)")
        return ItemDecision(False, f"store mcc={store.mcc} は approved_mccs に含まれない")

    if rules.mode == "hybrid":
        if item.has_barcode:
            # バーコード付きは jan_strict と同じ厳格判定
            if item.jan in rules.eligible_jans:
                return ItemDecision(True, "jan list match (hybrid)")
            if item.category and item.category in rules.eligible_categories:
                return ItemDecision(True, f"category {item.category} match (hybrid)")
            return ItemDecision(False, f"jan {item.jan} は対象外 (hybrid jan path)")
        # バーコード無しは MCC + 月次キャップ枠で許可
        if store.mcc is None:
            return ItemDecision(False, "hybrid no-barcode: store.mcc 未設定")
        if store.mcc not in rules.approved_mccs:
            return ItemDecision(
                False,
                f"hybrid no-barcode: store mcc={store.mcc} not approved",
            )
        if rules.cap_no_barcode_jpy <= 0:
            return ItemDecision(
                False, "hybrid no-barcode: cap_no_barcode_jpy=0 で no-barcode 枠なし"
            )
        return ItemDecision(
            True,
            f"hybrid no-barcode: store mcc={store.mcc} approved, cap 枠を消費",
            requires_no_barcode_budget=True,
        )

    raise ValueError(f"unknown eligibility_mode: {rules.mode}")


def estimate_cart(
    items: Iterable[ItemContext],
    store: StoreContext,
    rules: ProgramRules,
    *,
    no_barcode_used_jpy: int = 0,
) -> dict:
    """カート全体の試算 (フロント表示用)。

    no-barcode 枠を入力時点で `no_barcode_used_jpy` 消費済とし、
    新規にバーコード無し商品を入れた場合、
    cap_no_barcode_jpy を超えないようにクランプする。
    """
    total_price = 0
    total_eligible = 0
    no_barcode_running = no_barcode_used_jpy
    decisions: list[dict] = []

    for it in items:
        d = is_item_eligible(it, store, rules)
        adjusted_eligible = d.eligible
        adjusted_reason = d.reason
        if d.eligible and d.requires_no_barcode_budget:
            if no_barcode_running + it.price_jpy > rules.cap_no_barcode_jpy:
                adjusted_eligible = False
                adjusted_reason = (
                    f"バーコード無し枠 cap 超過 "
                    f"({no_barcode_running}+{it.price_jpy} > {rules.cap_no_barcode_jpy})"
                )
            else:
                no_barcode_running += it.price_jpy

        total_price += it.price_jpy
        if adjusted_eligible:
            total_eligible += it.price_jpy
        decisions.append({
            "jan": it.jan,
            "has_barcode": it.has_barcode,
            "price_jpy": it.price_jpy,
            "eligible": adjusted_eligible,
            "reason": adjusted_reason,
            "no_barcode_budget_consumed": d.requires_no_barcode_budget and adjusted_eligible,
        })

    return {
        "total_price_jpy": total_price,
        "total_eligible_jpy": total_eligible,
        "no_barcode_used_after": no_barcode_running,
        "items": decisions,
    }
