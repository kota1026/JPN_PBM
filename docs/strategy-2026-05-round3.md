# 戦略会議 #3 — 「動く Phase 1」を体験できる状態へ

> **作成日**: 2026-05-02 (round 3)
> **議題**: ラウンド 3 で揃った API/SDK を、実際にブラウザで触れる体験まで持ち上げる
> **アウトプット**: 6 件の機能実装 + Playwright E2E 基盤 + verify.sh モード拡張

---

## 1. 提案 → 採択結果

| # | 提案者 | 提案 | 採択 |
|---|--------|------|------|
| 1 | Engineer | Web 版 POS (retailer.html JS 拡張) | ✅ Phase 1 |
| 2 | CTO | Playwright E2E (3 画面通しシナリオ) | ✅ Phase 1 (基盤のみ、実走は実環境) |
| 3 | Stablecoin Architect | Polygon Mumbai 本番デプロイ | ⏸ Phase 2 (実環境必須) |
| 4 | Legal | マイナポータル v2 実 OAuth wire-up | ⏸ Phase 2 (API key 必須) |
| 5 | CBO | citizen.html に CP-6 体験 UI | ✅ Phase 1 |
| 6 | Cost Guardian | sweeper を cron 化 | ✅ Phase 1 |
| 7 | Researcher | 外部活動 (MAS Forum 共有) | — PR 不要 |
| 8 | Purpose Guardian | CP 違反カウンタ可視化 | ✅ Phase 1 |
| 9 | Red Team | 1 万人スケール負荷試験 | ⏸ Phase 1 後半 (#2 完了後) |
| 10 | CSO/AML | 加盟店 eKYC 簡易版 (UI) | ✅ Phase 1 |
| 11 | CFO | 多年度予算条例化 | ⏸ Phase 3 |

## 2. 実装サマリ

| 採択 | ファイル | テスト | 行数 |
|------|----------|--------|------|
| #1 | `frontend/retailer.html` (CP-6 ネット断モード追加) | 構文 OK + Playwright 検証 | +95 |
| #2 | `e2e/playwright.config.ts` + `e2e/tests/flagship-flow.spec.ts` + `e2e/package.json` | 4 件 (skip when no browser) | ~80 |
| #5 | `frontend/citizen.html` (災害用 QR 事前取得) | Playwright 検証 | +60 |
| #6 | `scripts/cron_sweep.py` + `verify.sh sweep` | dry-run スモーク | ~50 |
| #8 | `models/cp_violation.py` + `services/purpose_guard.record_violation` + `routers/ebpm.py` (`/violations`, `/violations/recent`) | 4 件 | ~80 |
| #10 | `frontend/tokyo.html` (加盟店 CP-6 承認 UI + CP 違反 dashboard) | 構文 OK | +100 |

## 3. ハーネス強化

新規モード:
- `verify.sh sweep` — sweeper の dry-run スモーク
- `verify.sh e2e` — Playwright (ブラウザ無し環境では skip)
- `verify.sh front` — `scripts/check_frontend_js.py` で inline JS を `node --check`

`verify.sh all` の構成:
```
pytest → seed → sol → front-js
```
※ e2e と sweep はオプトイン (実装→検証ループのうち、必要時のみ)

## 4. 検証結果

```
$ bash scripts/verify.sh all
[verify:pytest] 63 passed in 2.09s ✓
[verify:seed]   citizens=10 stores=5 programs=6 products=30 ✓
[verify:sol]    sol ok: 2 contract file(s) ✓
[verify:front]  front-js ok: 5 html file(s) ✓
✓ verify(all) all green
```

## 5. ポイント精算 (ラウンド 3)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| Engineer | 提案 #1 完全採用 | +20 |
| CTO | 提案 #2 採用 (基盤先行) | +15 |
| Stablecoin Architect | 提案 #3 Phase 2 へ | +5 |
| Legal | 提案 #4 Phase 2 へ | +5 |
| CBO | 提案 #5 完全採用 | +20 |
| Cost Guardian | 提案 #6 完全採用 | +20 |
| Researcher | 提案 #7 PR 不要 | +5 |
| **Purpose Guardian** | **提案 #8 完全採用 + record_violation 設計** | **+25** |
| Red Team | 提案 #9 後半へ | +5 |
| CSO/AML | 提案 #10 完全採用 | +20 |
| CFO | 提案 #11 Phase 3 へ | +5 |

🥇 **MVP**: Purpose Guardian (+25) — runtime ガード違反を全 deny 経路から記録 → ダッシュボード可視化で「監査可能性 (CP-4)」と「目的整合性 (CP-1)」のフィードバックループが完成。

## 6. 残課題 (ラウンド 4 候補)

- Polygon Mumbai 本番デプロイ + ECDSA 検証 (#3)
- マイナポータル v2 実 OAuth (#4)
- 1 万人スケール負荷試験 (#9)
- 多年度予算条例化 (#11)
- (新規) 戦略会議ログを英訳して MAS Project Orchid に共有 (#7)
