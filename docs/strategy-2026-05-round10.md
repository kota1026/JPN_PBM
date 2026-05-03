# 戦略会議 #10 — サンドボックス完遂 (Sandbox Completion)

> **作成日**: 2026-05-03 (round 11)
> **議題**: Phase 1 を 100% 達成 + Phase 3 国際展開のために「サンドボックス内で出来ることの最後の山」を一気に片付ける
> **アウトプット**: 8 件採択 (A1-A4 + B1-B2 + ハーネス強化 audit/i18n + 自動進捗判定)

## 0. 状況整理

ラウンド 10 完了時点 (PR #11 マージ済) で main は:

- tests **150 passed**
- routers **12** / services **16** / programs **7** / contracts **2**
- verify モード **10** (all/quick/py/seed/sol/front/cp6/sweep/load/ready/e2e)
- GitHub Actions CI **稼働中** (PR #11 で初稼働)
- docs **25 本** (戦略会議 9 本 + 英訳 7 本 + runbook + fork ガイド + …)

ロードマップ達成:

| Phase | done | ready | partial | blocked | pending | 計 | 完了率 |
|-------|------|-------|---------|---------|---------|-----|--------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | **86%** |
| Phase 2 | 1 | 3 | 2 | 1 | 0 | 7 | 57% |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 | 0% |

残った blocked / partial:

| ID | タイトル | 状態 | サンドボックスでできる? |
|----|---------|------|------------------------|
| Phase 1 M+0 | Founders' MoU | blocked | ❌ 実外交 |
| Phase 2 M+10 | PBM コントラクト audit | partial | △ セルフ audit checklist で前進可 |
| Phase 2 M+12 | 100 万人スケール | partial | △ さらにスケール検証 |
| Phase 3 M+18 | ホワイトペーパー公開 | partial (英訳 2/5) | ✅ 残り英訳 + 統合 1 本 |
| Phase 3 4 件 | 税ループ等 | blocked / pending | ❌ |

→ サンドボックスで前進できるのは **M+10 audit + M+18 whitepaper + 英訳 #8/#9** の 3 件。
今回はここに **国際展開の薄い助走 (英語フロント + ピッチデッキ)** を足して、PR #11 マージ後の停滞を防ぐ。

## 1. 採択 8 件 (方向 A 4 件 + 方向 B 2 件 + ハーネス 2 件)

| # | エージェント | 提案 | 実装 | Phase 影響 |
|---|--------------|------|------|------------|
| **A1** | Engineer | コントラクトセルフ audit | `scripts/contract_audit.py` (~250 行 / 24 checklist) + `verify.sh audit` | M+10 を partial → ready に格上げ |
| **A2** | Researcher | 統合ホワイトペーパー素案 | `docs/whitepaper-2026.md` (~600 行 EN / 8 章) | M+18 を partial → ready に格上げ |
| **A3** | Researcher | 戦略会議 #8 #9 英訳 | `docs/strategy-2026-05-round8-en.md`, `-round9-en.md` | M+18 evidence 拡張 |
| **A4** | Engineer | roadmap auto-detect | `roadmap.py` に test 数 / commit 数 / file count を自動取得し evidence に反映 | M+11 evidence 自動化 |
| **B1** | Engineer | 英語ランディング | `frontend/en/index.html` (国際フォーラム即デモ可) | Phase 3 M+14/M+18 助走 |
| **B2** | CSO/AML + Researcher | ピッチデッキ Marp | `docs/pitch-deck.md` (20 スライド) | Phase 3 M+14 OECD/BIS 共有用 |
| **C1** | Cost Guardian | `verify.sh audit` モード追加 | scripts/verify.sh | CI で audit が自動回るように |
| **C2** | Engineer | `verify.sh i18n` モード追加 (英訳 ↔ 和文の対応関係チェック) | scripts/verify.sh + scripts/check_i18n.py | 英訳忘れを自動検出 |

## 2. ボツ案 / 次回送り

- Polygon Mumbai 実デプロイ — 実 RPC 必要 (実外交)
- HSM 実機接続 — PKCS#11 ライブラリ必要
- マイナポータル v2 実 OAuth — 実 API key 必要
- TypeScript POS SDK — 優先度低 (Python SDK で実証中)
- Prometheus /metrics — 優先度低 (本番運用前)

## 3. 期待される検証結果

```
$ bash scripts/verify.sh all
[verify:pytest] 150+ passed ✓
[verify:seed] / [verify:sol] / [verify:front] ✓
✓ verify(all) all green

$ bash scripts/verify.sh audit
[verify:audit] PBM.sol + PBMOfflineFallback.sol セルフ audit
  ✓ checklist: 24/24 passed
  ✓ bytecode size: PBM=12.8KB / Fallback=11.2KB (limit 24KB)
✓ verify(audit) all green

$ bash scripts/verify.sh i18n
[verify:i18n] strategy 文書英訳カバレッジ
  ✓ strategy-2026-04 ↔ -en
  ✓ strategy-2026-05-round2..9 ↔ -en (8/8)
✓ verify(i18n) all green

$ bash scripts/verify.sh ready
detected phase: phase1-sandbox
  summary: ok=23, warn=2, fail=0
✓ verify(ready) all green
```

## 4. ポイント精算 (ラウンド 10 = PR #11 = ハーネス C/runbook A/readiness B/README D/fork E)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | C GitHub Actions + A runbook + D README | **+30** |
| Cost Guardian | B readiness 自動診断 (24 項目) | +20 |
| Researcher | E fork ガイド | +15 |
| Red Team | A の Rollback 戦略 | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Engineer (+30, 2 ラウンド連続)

## 5. ラウンド 12 候補 (実外交解禁が必要)

サンドボックス内で出来ることはラウンド 11 でほぼ完遂する見込み。
ラウンド 12 以降は以下のいずれかが揃ったら再開:

1. **M+0 Founders' MoU** (TMG × JPYC × TIS × 江東区) 成立 → Closed Alpha 起動
2. **Polygon Mumbai testnet RPC** 接続情報 → 実デプロイ
3. **マイナポータル v2 API key** 取得 → 実 OAuth
4. **PostgreSQL 本番インスタンス** + 100 万人サンプルデータ → 本番スケール
5. **HSM 実機** (AWS CloudHSM 等) → PKCS#11 実接続

それまでは **ホワイトペーパー精緻化 / 国際フォーラム共有 / フロント i18n 拡充 / セキュリティ強化 (bandit/semgrep)** などの「鈍い拡張」がメインになる。

## 6. Phase 1 完了率の最終目標

ラウンド 11 完了時点で:

| Phase | done | ready | partial | blocked | pending | 計 | 完了率 |
|-------|------|-------|---------|---------|---------|-----|--------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | **86%** (変化なし、M+0 は実外交) |
| Phase 2 | 1 | **4** | 1 | 1 | 0 | 7 | **71%** (M+10 audit が ready に) |
| Phase 3 | 0 | **1** | 0 | 2 | 2 | 5 | **20%** (M+18 whitepaper が ready に) |

→ **Phase 2 = 71%, Phase 3 = 20% で「サンドボックス完遂」宣言**。
M+0 が成立する翌週 (実外交 round) から Closed Alpha 投入が即可能な状態に。
