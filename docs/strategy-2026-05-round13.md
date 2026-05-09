# 戦略会議 #13 — マニラ Phase 1 完成 + 提出物パッケージ (Round 14)

> **作成日**: 2026-05-09 (round 14)
> **議題**: Round 13 でマニラ仕様の "中身" は完成。Round 14 では PH を **動かせる状態** にし (POS SDK + seed loader)、JICA / Coins.ph / DSWD に **送れる状態** にする (提出物 zip + 動画スクリプト)。
> **アウトプット**: 5 件採択 + 戦略文書英訳 1 本

---

## 0. Round 13 完了時点 (PR #14 draft) のギャップ

| アイテム | 状態 |
|---------|------|
| ✅ PH seed (`seed/ph/*.json`) | 完成 |
| ✅ PhilSys OAuth Mock | 完成 |
| ✅ EMV QR Ph parser | 完成 |
| ✅ JICA 申請書 v1 | 完成 |
| ❌ **PH seed が実際に DB にロードされない** (loader が JP しか読まない) | Round 14 |
| ❌ **PH POS SDK** (GCash QR Ph 連携想定) | Round 14 |
| ❌ ホワイトペーパー §6 が JP しか言及していない | Round 14 |
| ❌ JICA / Coins.ph / DSWD に送る zip 提出パッケージ | Round 14 |
| ❌ Round 12 戦略会議英訳 (i18n 11/12 のまま) | Round 14 |

→ Round 14 で **Manila Phase 1 が動く状態 + 提出パッケージ** まで持っていく。

## 1. 採択 5 件

| # | エージェント | 提案 | 実装 | 影響 |
|---|--------------|------|------|------|
| **T1** | Engineer | multi-locale seed loader | `seed/loader.py` + `--locale jp\|ph` | PH 8 世帯 + 25 商品 + 8 店舗 + 2 program が DB に投入可 |
| **T2** | Stablecoin Architect | PH POS SDK + GCash QR Ph 連携 | `sdk/python/jpn_pbm_pos_ph/` (~200 行) + テスト | サリサリ/Mercury Drug 加盟店オンボーディング想定 |
| **T3** | Researcher | Round 12 戦略会議英訳 | `docs/strategy-2026-05-round12-en.md` | i18n full coverage (12/12) |
| **T4** | Researcher | Manila section を whitepaper §6 に統合 | `docs/whitepaper-2026.md` | JICA/MAS/BIS 提出時の整合性 |
| **T5** | Engineer | 提出物 zip パッケージビルダ | `scripts/build_handoff_package.sh` + `docs/handoff-packages/{jica,coins-ph,dswd,quezon-city}/` | 「これを送ればいい」一式 |

## 2. multi-locale seed loader の設計

`backend/migrations/__init__.py` (既存 seed loader) は `seed/*.json` を直接読みに行く。
これを `seed/<locale>/*.json` も読めるように拡張する。

```python
def load_seed(db, *, locale: str = "jp") -> dict:
    """seed/{locale}/*.json (既存 jp はトップレベル維持) をロードして DB に投入。

    locale='jp' は既存パス (seed/citizens.json), 互換のため変更しない。
    locale='ph' は新規パス (seed/ph/citizens.json) を読む。
    """
```

**互換性**: `locale='jp'` がデフォルト = 既存挙動。`/seed/load` API も既存のまま。
`/seed/load?locale=ph` で PH 投入。

CP-1 (緊急停止) との整合: 既存の `dropAndReseed` ロジックを保持、locale の混入禁止。

## 3. PH POS SDK の設計

JP `sdk/python/jpn_pbm_pos/` (R3 で作成) と同形に:

```
sdk/python/jpn_pbm_pos_ph/
├── __init__.py       # public API: PosClient class
├── client.py         # /api/* に対する HTTPS クライアント
├── qr_ph.py          # QR Ph payload 検証 (services/qr_ph を再利用)
└── examples/
    └── sari_sari_simulation.py  # 4Ps 給付シミュレーション
```

主な API:
- `client.scan_merchant_qr(payload)` → MerchantInfo
- `client.scan_product_barcode(jan)` → ProductInfo
- `client.estimate_cart(items, store)` → CartEstimate (subsidy 含む)
- `client.pay(cart_id, payment_method='gcash_qrph')` → PaymentResult

GCash 連携部分は **mock**。実 GCash sandbox API は Coins.ph 接触後 Round 15+。

## 4. 提出物 zip パッケージ

宛先別に必要なドキュメントが違うので、宛先ごとに dir を切る:

```
docs/handoff-packages/
├── jica/
│   ├── README.md  ← 宛先用案内
│   ├── 01-application.md  → docs/jica-application-draft-en.md
│   ├── 02-whitepaper.md   → docs/whitepaper-2026.md
│   ├── 03-pitch.md        → docs/pitch-deck.md (英語版)
│   ├── 04-audit.md        → 自動 audit レポート
│   ├── 05-license.md      → LICENSE
│   └── 06-fork-guide.md   → docs/fork-guide.md
├── coins-ph/
│   ├── README.md
│   ├── 01-letter.md       ← 短文の technical paper
│   ├── 02-architecture.md → docs/architecture.md
│   ├── 03-cp6.md          → docs/cp6-offline-fallback.md
│   └── 04-qr-ph-spec.md   ← QR Ph 互換実装の証明
├── dswd/
│   ├── README.md
│   ├── 01-cover-letter-tagalog.md  ← Tagalog/English 案内
│   ├── 02-4ps-pilot-spec.md        ← prog-4ps-2026 仕様抜粋
│   └── 03-data-privacy.md          ← Data Privacy Act 2012 整合性
└── quezon-city/
    ├── README.md
    ├── 01-cover-letter.md
    ├── 02-pilot-spec-quezon.md
    └── 03-merchant-onboarding.md   ← サリサリ加盟手順
```

`scripts/build_handoff_package.sh <target>` で zip を生成:
```
$ bash scripts/build_handoff_package.sh jica
→ /tmp/jpn-pbm-handoff-jica-2026-05-09.zip (含: 申請書 + whitepaper + audit + ...)
```

## 5. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 200+ passed (R13 195 → R14 +tbd)
✓ verify(all) all green

$ bash scripts/build_handoff_package.sh jica
→ jpn-pbm-handoff-jica-*.zip (6 文書)

$ # /seed/load?locale=ph で PH 8 世帯 + 25 商品 + 2 program が投入される
```

## 6. ポイント精算 (ラウンド 13 = PR #14)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | T2 PhilSys OAuth + T3 EMV QR Ph parser + ロードマップ更新 | **+30** |
| Researcher | T1 PH seed + T4 JICA 申請書 + T5 R11 英訳 | +30 |
| Stablecoin Architect | T2 設計レビュー (myna_oauth との対称性) | +15 |
| Cost Guardian | JICA 予算 ¥65M の内訳精緻化 | +10 |
| Red Team | CRC-16 改ざん検知テストの追加要請 | +10 |
| Purpose Guardian | DPG Standard 9 指標セルフ評価の整理 | +10 |
| Legal | Data Privacy Act 2012 整合性レビュー | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Engineer & Researcher 同点 (+30) ─ 1 ラウンドで 5 件かつ JICA 申請書という対外文書まで仕上げた。

## 7. ラウンド 15 候補 (実外交 / 実機が必要)

サンドボックス内では Round 14 で **本当に最後** になる。Round 15 以降は:

1. **Polygon Mumbai 実デプロイ** (RPC URL)
2. **GCash sandbox API** 実 mock 連携 (Coins.ph 接触済を仮定)
3. **iPhone 実機 scanner テスト** (Web BarcodeDetector iOS 17 動作)
4. **DSWD 4Ps の実 LandBank ATM フローとの統合** (政策合意)
5. **JICA pre-screening conversation** 結果を反映した v2 申請書

## 8. Phase 完了率 (R13 → R14 想定)

| Phase | R13 | R14 (見込) | 差分根拠 |
|-------|-----|-----------|----------|
| Phase 1 | 86% | 86% | 変化なし |
| Phase 2 | 71% | 71% | 変化なし |
| Phase 3 | 40% | **40-60%** | 提出物完成で外交開始準備度が増 |

M+18 (whitepaper) の status は変えない (まだ実外交ゼロのため "ready" のまま)、
ただし evidence_files に Manila section 追記。
