# 戦略会議 #7 — Phase 2 ⇄ Phase 3 接続

> **作成日**: 2026-05-02 (round 8)
> **議題**: Phase 2 完成形 (Round 7) を踏まえ、Phase 3 (制度統合) への橋渡し + 進捗の可視化
> **アウトプット**: 5 件の機能実装 + ハーネス強化 + 戦略会議 #3 英訳

## 1. 全体計画の現在地

戦略会議 #1 (PR #3) で確定した 18 ヶ月ロードマップに対する達成状況:

| Phase | done | ready | partial | blocked | pending | 計 |
|-------|------|-------|---------|---------|---------|-----|
| Phase 1 | 2 | 4 | 1 | 1 | 0 | 8 |
| Phase 2 | 1 | 2 | 2 | 1 | 1 | 7 |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 |

**現在地: Phase 2 の M+11 (CP-6 本番投入) の技術的準備が完了**。

## 2. 採択 5 件

| # | 提案 | 実装 | 影響 |
|---|------|------|------|
| **A** | ロードマップ進捗 API + dashboard | `services/roadmap.py` + `/treasury/roadmap` + tokyo.html | 18 ヶ月計画の現在地が画面で見える |
| **B** | HSM 連携 skelton (env→アダプタ→Mock) | `services/hsm_adapter.py` + `/treasury/hsm/status` | Phase 3 の HSM 移行で同インターフェースに差替可能 |
| **C** | 戦略会議 #3 英訳 | `docs/strategy-2026-05-round3-en.md` | MAS forum 共有 (#1, #2 に続く 3 本目) |
| **D** | 防災備蓄 江東区統合 | `seed/programs.json:prog-koto-disaster-pack-2026` | Phase 2 M+7 の予告: 多年度予算 (5,000 万円 × 3 年度) |
| **E** | 1 万 req 負荷試験 | `verify.sh load` を 50 並列 × 200 反復 = 10,000 req に拡大 | **fail = 0%** (Round 5/6 は 5K @ 2.66%) |

## 3. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 138 passed in 4.23s ✓
[verify:seed]   citizens=10 stores=5 programs=7 products=30 ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green

$ bash scripts/verify.sh load
10000 requests in 31.29s = 319.6 req/s
p50=146.6ms p95=238.8ms p99=293.4ms
failures: 0 (0.00%)
```

## 4. ポイント精算 (ラウンド 7)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| Engineer | A dashboard + B HSM adapter + D seed | +25 |
| Stablecoin Architect | B HSM Mock 設計 + 鍵リーク検出テスト | +20 |
| **CFO** | **D 多年度 (3 年度 × 5,000 万) のフラッグシップ統合採択** | **+20** |
| Researcher | C 戦略会議 #3 英訳 | +15 |
| Cost Guardian | E 並列 50 で fail=0% を達成 | +15 |
| Purpose Guardian | A roadmap 上で CP-6 ready ステータス確認 | +10 |
| Red Team | A の手動 status と git 進捗の差を指摘 | +10 |

🥇 **MVP**: Engineer (+25) — 1 ラウンドで 3 件 (進捗可視化 + HSM + 防災シード) を実装し、Phase 3 接続を加速。

## 5. 次の課題 (ラウンド 8)

- ✓ Phase 2 完成形 (R6)
- ✓ Phase 3 接続準備 (R7)
- 残り (実外交・実環境):
  - Polygon Mumbai 実デプロイ
  - マイナポータル v2 実 OAuth (実 API key)
  - PostgreSQL 移行 (1 万 req @ fail=0% 達成済 → 数十万 req 用)
  - HSM 実機接続 (PKCS#11 backend 実装)
  - 戦略会議 #4, #5 英訳
- 戦略会議 #1 のフラッグシップ M+0 (Founders' MoU) を待つ段階
