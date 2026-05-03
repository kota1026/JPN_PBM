# 戦略会議 #9 — 本番投入仕上げ (Production Handoff)

> **作成日**: 2026-05-02 (round 10)
> **議題**: 実外交・実環境依存の項目が中心になる Phase 3 を前に、サンドボックスでできる「本番投入仕上げ」(runbook / readiness / CI / README / fork ガイド) をまとめて提供
> **アウトプット**: 5 件の実装 + ハーネス強化 (ready モード)

## 1. 採択 5 件

| # | 提案 | 実装 | 影響 |
|---|------|------|------|
| **A** | 本番デプロイ runbook | `docs/production-runbook.md` (~250 行) | Polygon Mumbai / PostgreSQL / HSM / マイナ v2 / mainnet パイロットの 5 段階手順 |
| **B** | Readiness check 自動診断 | `scripts/readiness_check.py` + `verify.sh ready` | env / deps / files / harness / secrets を 24 項目チェック、phase 自動判定 |
| **C** | GitHub Actions CI | `.github/workflows/verify.yml` | PR / push で `verify.sh all + sweep + ready + load` を自動走行 |
| **D** | README 包括的更新 | `README.md` | 9 ラウンドの機能・全 endpoint・全 verify モード・CP-6 差別化要素を 1 画面 index 化 |
| **E** | 多自治体 fork ガイド | `docs/fork-guide.md` (~150 行) | Phase 3 M+16 (大阪府 / 愛知県 fork) 向けに 7 step + チェックリスト |

## 2. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 138 passed in 4.23s ✓
[verify:seed]   citizens=10 stores=5 programs=7 products=30 ✓
[verify:sol]    ✓ / [verify:front] ✓
✓ verify(all) all green

$ bash scripts/verify.sh ready
detected phase: phase1-sandbox
  ✓ deps.fastapi / sqlalchemy / pydantic / ecdsa / Crypto / multipart
  ✓ file.* (13/13 主要ファイル存在)
  ✓ harness.quick: all green
  ✓ security.no_secrets: clean
  ⚠ env.JPN_PBM_PRIVACY_SECRET (sandbox は warn, Phase 2/3 では fail に格上げ)
  ⚠ deps.psycopg2 (Phase 3 必須)
summary: ok=21, warn=3, fail=0
✓ verify(ready) all green
```

## 3. ポイント精算 (ラウンド 9)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | **A runbook + C GitHub Actions + D README** | **+30** |
| Cost Guardian | B readiness 自動診断 (24 項目) | +20 |
| Researcher | E fork ガイド | +15 |
| Red Team | A の Rollback 戦略 + 緊急時対応の整理 | +10 |
| CSO/AML | B の secret 検出パターン提案 | +10 |
| Purpose Guardian | A 緊急時の CP-6 自動発動を runbook に明記 | +10 |
| Legal | A の MoU / 法務レビューフローの順序整理 | +10 |
| その他 | 提案待機 | 各 +5 |

🥇 **MVP**: Engineer (+30) — 1 ラウンドで 3 件 (runbook 250 行 / CI workflow / README) を実装し、本番投入の足場を完成。

## 4. ラウンド 10 候補 (実外交・実環境依存)

- Polygon Mumbai 実デプロイ (実 RPC 必要)
- マイナポータル v2 実 OAuth (実 API key)
- HSM 実機接続 (PKCS#11 library)
- PostgreSQL 実マイグレ + 100 万人スケール
- 戦略会議 #1 M+0 Founders' MoU (実外交 = 都 × JPYC × TIS × 江東区)
- 戦略会議 #8 #9 英訳

## 5. Phase 1 完了率の最終整理

| Phase | done | ready | partial | blocked | pending | 計 | 完了率 (done+ready) |
|-------|------|-------|---------|---------|---------|-----|---------------------|
| Phase 1 | 2 | 4 | 1 | 1 | 0 | 8 | **75%** |
| Phase 2 | 1 | 2 | 2 | 1 | 1 | 7 | 43% |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 | 0% |

**Phase 1 75% 完了** = 残り `partial` (M+6 都議会報告) + `blocked` (M+0 Founders' MoU) のみ。
M+0 が成立すれば即 Closed Alpha 投入可能。
