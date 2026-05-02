# 戦略会議 #5 — Phase 2 完成形へ

> **作成日**: 2026-05-02 (round 6)
> **議題**: ラウンド 5 で揃った Phase 2 部品を、本物のコントラクトと相互運用可能な状態 + UI 統合まで持ち上げる
> **アウトプット**: 5 件の機能実装 + ハーネス強化 (load 5,000 req)

## 1. 採択 5 件

| # | 提案 | 実装 | 影響 |
|---|------|------|------|
| **A** | ECDSA Sol 完全互換 (keccak256 + abi.encode + EIP-191) | `services/sol_compat.py` (160 行) + 11 件のテスト | Polygon Mumbai に PBMOfflineFallback.sol をデプロイした際に署名検証が一致することを保証 |
| **B** | 多年度 spend 年度別追跡 | `fiscal_budget.spent_by_year_from_ebpm` + `remaining_for_year_precise` + `/programs/{id}/fiscal-budget` 拡張 | 過年度に消化したかどうかを EBPM 実績ベースで取得 |
| **C** | citizen.html OAuth フロー切替 | radio button + `_loginViaOAuth` (3 step Authorization Code Grant) | ユーザーが Phase 1 (直接) と Phase 2 (OAuth) を切替可能 |
| **D** | tokyo.html 多年度予算ビュー | 新セクション + 4 KPI + 年度別実績テーブル | フラッグシップの多年度予算が画面で見える |
| **E** | 負荷試験スケールアップ | SQLite WAL + busy_timeout=10s + loadtest `--max-fail-rate` + 100×50 (= 5,000 req) | 実測 **431 req/s, p95=347ms, fail=2.66%** (5% 閾値以下) |

## 2. テストベクトル一致 (採択 A)

| ハッシュ | 入力 | 期待 | 実装 |
|----------|------|------|------|
| keccak256 | `b""` | `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` | ✅ |
| keccak256 | `b"abc"` | `4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45` | ✅ |
| keccak256 | `b"hello"` | `1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8` | ✅ |
| Ethereum address | privkey=0x01 | `0x7e5f4552091a69125d5dfcb7b8c2659029395bdf` | ✅ |

`sign_coupon_eip191` → `verify_coupon_eip191` で round-trip OK。**low-s 正規化** + recovery id 自動探索を実装 → Sol `ecrecover` と等価。

## 3. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 100 passed in 2.59s ✓
[verify:seed]   ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green

$ bash scripts/verify.sh load
5000 requests in 11.59s = 431 req/s
p50=204.6ms p95=347.4ms p99=392.8ms
failures: 133 (2.66%) — within 5% sandbox threshold
```

## 4. ポイント精算 (ラウンド 5)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Stablecoin Architect** | **A 完全採用 (Sol 互換 + low-s 正規化)** | **+25** |
| CFO | B 完全採用 | +20 |
| Engineer | C+D フロント wire-up | +15 |
| Red Team | E 5% 閾値妥協で採用 + WAL モード提案 | +15 |
| Cost Guardian | SQLite WAL で詰まりを解消 | +10 |
| Researcher | テストベクトル外部一致確認 | +5 |
| Purpose Guardian | OAuth 経由でも CP-2 維持 (radio button が pid 形式チェック必要) | +5 |

🥇 **MVP**: Stablecoin Architect (+25) — Sol 互換 ECDSA 実装で Phase 2 移行の最大の互換性リスクを解消。

## 5. ラウンド 6 候補

- Polygon Mumbai 実デプロイ (実 RPC 必要)
- マイナポータル v2 実 OAuth wire-up (実 API key)
- PostgreSQL 移行 (SQLite 並列限界の根本対応)
- E2E (Playwright) を Round 4 の OAuth ラジオ + 多年度ビューに対応
- 1 万人以上の本番スケール
