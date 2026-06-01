# 戦略会議 #21 — Round 23 ─ 最後の玄関整備

> **作成日**: 2026-05-20 (round 23)
> **議題**: サンドボックスで進められる残り最後の小粒タスクを完遂
> **形式**: 短縮セッション (議論材料なし、整理ラウンド)
> **アウトプット**: 3 件採択 (README 全面更新 + R20 EN 翻訳 + 議事録)

---

## 0. Round 22 完了状況

R22 で完了:
- `docs/service-overview.md` (604 行 10 章、総合資料)

ユーザーから次のサジェスチョンは `「サンドボックスの件は進めよう」`。
残るサンドボックス内タスクは:

| # | 候補 | 価値 | リスク |
|---|------|------|------|
| 1 | 全 13 stacked PRs を main rebase + cleanup | 大 | **大** (git history 変更、12 PR テスト必要) |
| 2 | R20 戦略会議の英訳 | 中 | 小 |
| 3 | README.md を Round 22 状態に更新 | **大** (玄関) | 小 |
| 4 | OECD/BIS/MAS 共有準備 (新規 handoff) | 中 | 中 (重複作業の懸念) |
| 5 | (新) `docs/INDEX.md` ─ 74 docs の単一索引 | 中 | 小 |

## 1. 採択 3 件

| # | 提案 | 理由 |
|---|------|------|
| **T1** | **README.md 全面更新 (Round 10 → Round 22 反映)** | 玄関、最も visible、現状 168 行が Round 10 時点でストップ |
| **T2** | **R20 戦略会議の英訳** | i18n maintain (lag を 1 本に維持) |
| **T3** | 戦略会議 #21 議事録 (本ファイル) | meta record |

**選外**:
- **#1 rebase**: 12 PR の history rewrite は **ユーザーの明示同意**を待つべき。本 Round では実施しない
- **#4 OECD/BIS/MAS**: 既存 handoff packages (jica/unicef/wfp-bb 等) で実質カバー、重複作業を回避
- **#5 INDEX.md**: `service-overview.md §7` で 12 主要文書のナビゲーション済、追加価値小

## 2. README.md 改訂方針

現状の README (179 行):
- Round 10 時点の状態 (Phase 2 完成形 + Phase 3 接続準備)
- 「世界初」表現が残ったまま (R18 で撤回済)
- Manila / Donor-PBM / CP-6 v2 の言及なし
- 戦略会議 #2-#7 まで言及 (#8-#20 が抜け)

改訂内容:
- Round 22 時点の全機能を反映
- 「世界初」表現を撤回 (whitepaper §4.4 / pitch-deck 同様)
- Manila ツインパイロット明記
- Donor-PBM (TAM 100x) 明記
- CP-6 v2 (JP A+E + PH DL Protocol) 明記
- 21 ラウンドの 3 ピボット (サリサリ POS / 災害 POS / Donor TAM) 明記
- 数字を最新化 (371 tests / 31 services / 14 routers / 74 docs)
- `docs/service-overview.md` への入口を最上部に配置
- 5 分自動デモ (htmlpreview) URL を最上部に配置

## 3. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 371 passed (Round 22 と同じ)
[verify:i18n]   19/20 (round21 が最新 lag = 1、許容)
✓ verify(all) all green
```

## 4. ポイント精算 (Round 22 = PR #23)

| エージェント | 内訳 | 配点 |
|------------|------|------|
| **Researcher** | service-overview.md 604 行 10 章 (アーキテクチャ / 利用方法 / 7 シーケンス / 8 セールスポイント / TAM 試算 / 競合比較) | **+30 (MVP)** |
| Engineer | 既存実装の整合性確認 + 数字監査 | +10 |
| Cost Guardian | TAM 試算 (¥40T → 1% で年 ¥400B) | +10 |

🥇 **R22 MVP**: Researcher (R20 設計書 + R22 総合資料の 2 連続 MVP)

## 5. ラウンド 24+ (実外交解禁を待つフェーズ)

R23 完了で、サンドボックス内で進められる **明確な独立タスクは枯渇**。残るは:

| 候補 | 必要条件 |
|------|---------|
| Polygon Mumbai 実デプロイ | RPC URL |
| Coins.ph 接触 → PHPC sandbox | LoI 提出後 |
| UNICEF / WFP / UNHCR 接触 | handoff zip 送付後 |
| JICA pre-screening v3 | 担当者との会話 |
| 12 PR を main rebase | ユーザー同意 |
| 全 21 ラウンドの **動画録画** | 人間オペレータ + Loom |
| 国際会議 (OECD/BIS/MAS) 共有 | スピーカー枠 |
| 法人化 (合同会社) + ¥6 万 | ユーザー決断 |

→ サンドボックスの「次の意味のある進捗」は **ユーザーの実外交開始決断** が必要。

## 6. Phase 完了率 (R22 → R23 想定)

| Phase | R22 | R23 | 差分 |
|-------|-----|-----|------|
| Phase 1 | 86% | 86% | 変化なし |
| Phase 2 | 77% | 77% | 変化なし |
| Phase 3 | 60% | 60% | 変化なし |
| Phase 4 (Donor-PBM) | 30% | 30% | 変化なし |

R23 は **可視性向上 + i18n maintenance** であり、新機能追加ではない。
よって完了率の動きはなし、ただし **「初見の人が repo を訪れたとき」の説得力** が大幅向上。
