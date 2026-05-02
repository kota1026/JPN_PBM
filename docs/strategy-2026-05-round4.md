# 戦略会議 #4 — Phase 1 → Phase 2 移行準備

> **作成日**: 2026-05-02 (round 5)
> **議題**: Phase 1 の体験フローが完成 (PR #3-#5 マージ済) した今、Phase 2 (本番に近い形) に進むために何を実装するか?
> **アウトプット**: 5 件の機能実装 + ハーネス強化 (load モード) + 戦略会議 #1 英訳

## 1. 採択 5 件

| # | 提案者 | 実装 | 採択理由 |
|---|--------|------|----------|
| #11 | CFO | `program.fiscal_year_budgets` + `services/fiscal_budget.py` + `/programs/{id}/fiscal-budget` | 政権交代耐性。多年度ロックを技術で担保 |
| #9 | Red Team | `scripts/loadtest.py` + `verify.sh load` モード | 本番投入前のレイテンシ/失敗率を可視化 |
| #3 | Stablecoin Architect | `offline_fallback.py` に ECDSA secp256k1 並列実装 (`sign_coupon_ecdsa` / `verify_coupon_ecdsa` / `is_ecdsa_available`) | Sol 互換、Phase 2 で HSM 鍵に切り替え可能 |
| #4 | Legal | `routers/myna_oauth.py` (Authorization Code Grant 4 endpoints) + ConsentLog integrate | Phase 1 同意取得 UX を Phase 2 OAuth フロー (本番と同形) に接続 |
| #7 | Researcher | `docs/strategy-2026-04-en.md` (英訳) | MAS Project Orchid フォーラム共有用 |

延期: Polygon Mumbai 実デプロイ (Phase 3) / マイナポータル v2 実 OAuth (実 API key 必要) / 多年度予算条例化の Phase 3 完成形。

## 2. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 87 passed in 2.59s ✓
[verify:seed]   ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green

$ bash scripts/verify.sh load
[verify:load] 100 並列 × 100 反復のスモーク負荷試験
    400 requests in 0.93s = 427.9 req/s
    p50=35.8ms p95=84.9ms p99=138.9ms
    failures: 0 (0.00%)
✓ verify(load) all green
```

## 3. ポイント精算 (ラウンド 4)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| CFO | 提案 #11 完全採用 | +20 |
| **Red Team** | **提案 #9 完全採用 + 「100×100 で代替」修正案 +5** | **+25** |
| Stablecoin Architect | 提案 #3 並列実装で完全採用 | +20 |
| Legal | 提案 #4 Mock 完成 | +20 |
| Researcher | 提案 #7 英訳完了 | +15 |
| Purpose Guardian | OAuth 経路でも CP-2 維持 | +10 |
| Engineer | OAuth wire-up 実装 | +10 |
| その他 (CTO/CBO/Cost Guardian/CSO/AML) | 提案待機 | 各 +5 |

🥇 **MVP**: Red Team (+25) — 「サンドボックス DB を破壊しない 100×100 代替案」で実際に走らせ、p95 84.9ms / 失敗 0% という具体数値を獲得。

## 4. ラウンド 5 候補

- Polygon Mumbai 本番デプロイ (#3 続編、実環境)
- マイナポータル v2 実 OAuth (実 API key 必要、外部協議)
- 1 万人スケール本番 (#9 拡大)
- 多年度予算の年度別 spend 分割管理 (Phase 3 課題)
- フロント wire-up: tokyo.html に多年度予算ビュー / OAuth フロー切替トグル
- ECDSA Sol 互換: keccak256 + EIP-191 personal_sign の完全互換実装
