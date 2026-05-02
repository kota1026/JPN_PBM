# 戦略会議 #2 — Phase 1 を実際に動かすために何が足りないか

> **作成日**: 2026-05-02
> **議題**: 戦略会議 #1 で採択した「江東区フラッグシップ + CP-6」を **M+3 (Closed alpha 100 世帯×10 店舗) で動かす** ために何を実装すべきか
> **アウトプット**: 6 件の機能実装 + 22 個の追加テスト (合計 43 tests pass)

---

## 1. 提案 → 採択結果

| # | 提案者 | 提案 | 採択 |
|---|--------|------|------|
| 1 | Purpose Guardian | `purpose_guard.py` で CP-1〜CP-6 を runtime 強制 | ✅ Phase 1 |
| 2 | CTO | pbm.py の program 選択を「最も住民有利」に変更 | ✅ Phase 1 |
| 3 | CSO/AML | 加盟店 eKYC モジュール | ⏸ Phase 2 (初期 10 店舗は手動) |
| 4 | CFO | 準備金監査 24h 自動 + アラート | ✅ Phase 1 後半 |
| 5 | CBO | 加盟店認定マーク UI | ⏸ Phase 2 |
| 6 | Cost Guardian | 期限切れ PBM の自動返還 sweeper | ✅ Phase 1 |
| 7 | Engineer | `routers/offline.py` で CP-6 を REST 公開 + EBPM 書き戻し | ✅ Phase 1 |
| 8 | Stablecoin Architect | peg monitor (ハードコード閾値版) | ⏸ Phase 1 後半 |
| 9 | Researcher | EBPM CP-2 保護テスト | ✅ Phase 1 |
| 10 | Legal | `consent.py` モデル (個情法 第27条) | ✅ Phase 1 |
| 11 | Red Team | (PHASE 3 で全提案を批判) | — |

## 2. Red Team が拾った重大欠陥

- **#2 の "最も住民有利" 定義の曖昧さ** → `subsidy_jpy 降順 → remaining_jpy 降順 → program.id 昇順` の 3 段階 tie-break で安定化
- **#6 sweeper が未来 token を刈る危険** → `expires_at < now` の厳密過去のみ対象 + dry_run モード
- **#7 オフライン redemption の EBPM 書き戻し漏れ (CP-4 違反)** → `routers/offline.py:redeem_batch` で accepted item を全て EBPMEvent に書き込み、`guard_offline_redemption` で再検証
- **#9 個票漏れリスク** → `cp2_no_personal_info_in_aggregate` で k-匿名性 (k=5) を明示テスト

## 3. 実装サマリ

| 採択 | ファイル | テスト | 行数 |
|------|----------|--------|------|
| #1 | `backend/app/services/purpose_guard.py` | 11 件 | ~180 |
| #2 | `backend/app/services/pbm.py` (改修) | 1 件 | +20 |
| #6 | `backend/app/services/sweeper.py` | 3 件 | ~75 |
| #7 | `backend/app/routers/offline.py` | 3 件 (E2E) | ~180 |
| #9 | (テストのみ) | 1 件 | — |
| #10 | `backend/app/models/consent.py` | 1 件 | ~30 |

## 4. 検証ハーネス結果

```
$ bash scripts/verify.sh all
[verify:pytest] 43 passed in 1.24s ✓
[verify:seed]   seed ok: citizens=10 stores=5 programs=6 products=30 ✓
[verify:sol]    sol ok: 2 contract file(s) ✓
✓ verify(all) all green
```

ラウンド 1 (21 tests) → ラウンド 2 (43 tests) で **+22 tests** 追加。

## 5. ポイント精算 (ラウンド 2)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| Purpose Guardian | 提案 #1 完全採用 | +20 |
| CTO | 提案 #2 完全採用 | +20 |
| CSO/AML | 提案 #3 Phase 2 へ | +5 |
| CFO | 提案 #4 部分採用 (Phase 1 後半) | +10 |
| CBO | 提案 #5 Phase 2 へ | +5 |
| Cost Guardian | 提案 #6 完全採用 | +20 |
| **Engineer** | **提案 #7 完全採用 + EBPM 書き戻し設計勝利** | **+25** |
| Stablecoin Architect | 提案 #8 Phase 1 後半 | +10 |
| Researcher | 提案 #9 完全採用 | +20 |
| Legal | 提案 #10 完全採用 | +20 |
| **Red Team** | **重大欠陥 4 件指摘 (#2, #6, #7, #9)** | **+20** |

🥇 **MVP**: Engineer (+25) — オフライン redemption の EBPM 書き戻し設計でラウンド 1 の CP-4 漏れを解消。
🥈 次点: Red Team (+20) — 4 件の欠陥指摘で実装を頑健化。

## 6. 残課題 (ラウンド 3 で扱う候補)

- フロントエンド: `prog-koto-kosodate-2026` を tokyo.html に表示
- POS SDK: バーコードスキャナと `/offline/redeem-batch` の実機統合
- マイナポータル v2 OAuth: ConsentLog を実 API で書き込む
- 準備金 24h 監査 cron (#4)
- peg monitor (#8) の閾値とアラート経路
- E2E ブラウザテスト (Playwright)
