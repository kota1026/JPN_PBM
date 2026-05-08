# 戦略会議 #11 — スマホスキャン × ハイブリッド eligibility (Tokyo + Manila 両用)

> **作成日**: 2026-05-04 (round 12)
> **議題**: ユーザーから提起された 2 つの設計上の気づきを実装に落とす:
> 1. **「サリサリは POS が無くても、バーコード付き商品 + 受給者スマホで運用できる」**
> 2. **「商品ベース (JAN) と店舗ベース (MCC) のハイブリッドが現実」**
>
> **アウトプット**: 5 件の実装 + 戦略文書 1 本

---

## 0. 状況整理

ラウンド 11 (PR #12 draft) で `docs/expansion-philippines.md` を書いた段階では:

- マニラ展開の商品識別は **「店舗単位 MCC ホワイトリスト」一本** と提案
- これだと **店主の信用に 100% 依存**、4Ps audit 観点で弱い
- 受給者側に検証手段がない

ユーザーからの指摘:

> **「サリサリでも仕入れ商品にはバーコードが付いてる。スマホで読めるのでは?」**

→ これが**サリサリ現実 + 4Ps オーナーシップ**の両方に効く。

| 商品種別 | サリサリ在庫比 | バーコード | 4Ps 適合 | 判定方式 |
|---------|---------------|-----------|----------|---------|
| ブランド袋詰 / 缶詰 | 50-60% | ✅ | ✅ 多い | **JAN/EAN 判定** |
| ティンギ・量り売り | 30-40% | ❌ | △ | **MCC 5411 認定店フォールバック** |
| 酒・タバコ | 5-10% | ✅ or ❌ | ❌ | **両方ブロック** |

→ **ハイブリッド** = JAN ありなら厳格判定、無いなら認定店内で限定額枠。これがフィリピンでも日本でも (個人商店) 動く統一モデル。

## 1. 採択 5 件

| # | エージェント | 提案 | 実装 | 影響 |
|---|--------------|------|------|------|
| **T1** | Engineer | スマホ ZXing.js barcode scanner | `frontend/citizen.html` + `frontend/ph/citizen.html` に WebRTC + ZXing 組込み | **POS ハードウェア不要**、スマホ 1 台で稼働 |
| **T2** | Researcher | Tagalog UI + GCash QR Ph mock | `frontend/ph/index.html` + `citizen.html` (Tagalog/English) | フィリピン pilot UX 完成 |
| **T3** | Stablecoin Architect | ハイブリッド eligibility | `services/eligibility.py` 拡張 + テスト | JAN ありは厳格判定 / 無いなら MCC fallback |
| **T4** | Researcher | QR vs JAN 調査ドキュメント | `docs/qr-vs-jan-research.md` | フィリピン GS1 480 / サリサリ POS 普及率 / QR Ph MCC 仕様 |
| **T5** | Engineer | expansion-philippines.md 修正 | §3 ハイブリッド設計へ書き換え | 設計ドキュメント整合 |

## 2. ハイブリッド eligibility のデータモデル

```python
# 新: 店舗 (Store) に MCC と認定カテゴリを持たせる
class Store:
    id: str
    mcc: int                    # 5411=grocery, 5912=drug, 5921=liquor, ...
    approved_for_programs: list[str]   # 認定 program ID 集合

# 新: Program に「JAN 必須 or 任意」を選べる eligibility_mode
class Program:
    id: str
    eligibility_mode: Literal["jan_strict", "mcc_only", "hybrid"]
    eligible_jans: set[str]       # jan_strict / hybrid で使用
    approved_mccs: set[int]       # mcc_only / hybrid で使用
    cap_no_barcode_jpy: int       # hybrid 時の「JAN 無し購入の月額上限」
```

判定アルゴリズム (Python pseudocode):

```python
def is_eligible(program, store, item):
    if program.eligibility_mode == "jan_strict":
        return item.has_barcode and item.jan in program.eligible_jans
    if program.eligibility_mode == "mcc_only":
        return store.mcc in program.approved_mccs
    if program.eligibility_mode == "hybrid":
        if item.has_barcode:
            return item.jan in program.eligible_jans       # ← 厳格
        return (store.mcc in program.approved_mccs and
                month_no_barcode_used + item.price <= program.cap_no_barcode_jpy)
    raise ValueError(f"unknown mode: {program.eligibility_mode}")
```

## 3. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 165+ passed (R11 154 → R12 +11)
✓ verify(all) all green

$ # ブラウザで /ui/citizen.html を開いて barcode を読む (実機テスト相当)
$ # /ui/ph/citizen.html を開いて Tagalog UI が出る + scanner 起動
```

## 4. ポイント精算 (ラウンド 11)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | A1 audit + A4 auto_metrics + B1 EN landing + B2 pitch + verify mode | **+30** |
| Researcher | A2 whitepaper 600 行 + A3 英訳 #8 #9 | +25 |
| Cost Guardian | C1 audit / C2 i18n verify mode | +15 |
| **CSO/AML** | 自分 (実装にあった honest tone へのプッシュ) | **+15** |
| Red Team | Polygon 未デプロイ問題の指摘 | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Engineer (+30, 3 ラウンド連続)

## 5. ラウンド 13 候補

サンドボックス内で出来ることは Round 12 で **本当に最後の山** (実機 web カメラ依存が始まる)。Round 13 以降は:

1. **Polygon Mumbai 実デプロイ** (RPC URL 要)
2. **GCash sandbox API** との実 mock 連携 (Coins.ph 接触済 を仮定)
3. **JICA フィリピン申請書 v1** ドラフト英訳
4. **Marp PDF 生成 + 提出物パッケージ化** (zip で送れる形に)
5. **動画スクリプト → 実録画 (Loom)** (議員説明用)

## 6. Phase 完了率の更新目標

| Phase | done | ready | partial | blocked | pending | 計 | 完了率 |
|-------|------|-------|---------|---------|---------|-----|--------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | 86% (変化なし) |
| Phase 2 | 1 | 4 | 1 | 1 | 0 | 7 | 71% (変化なし) |
| Phase 3 | 0 | **2** (+1) | 0 | 2 | 1 | 5 | **40%** (+20pt) ← 他自治体 fork が ready 入り |

**Round 12 の効果**: マニラ pilot UX 完成 + ハイブリッド設計確定 → Phase 3 M+16 (他自治体 fork) が partial → ready に。
