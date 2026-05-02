# 戦略会議 #6 — Phase 2 防御層 + Phase 3 への橋渡し

> **作成日**: 2026-05-02 (round 7)
> **議題**: Round 6 で Sol 互換 ECDSA を整備済。Phase 3 (Polygon 本番) に移る前に、鍵管理・契約等価性・migration 設計を固める
> **アウトプット**: 5 件の機能実装 + ハーネス強化 + 戦略会議 #2 英訳

## 1. 採択 5 件

| # | 提案 | 実装 | 影響 |
|---|------|------|------|
| **A** | ECDSA 鍵 rotation 経路 | `services/key_management.py` + `/treasury/keys/rotation` | env 複数鍵 + active 切替 + 検証時に全鍵試行 → revoke は env 削除で実現 |
| **B** | Sol コントラクト Python シミュレータ | `services/sol_simulator.py` + `cross_check_with_offchain` | Polygon 本番デプロイ前にコントラクト挙動を完全模倣テスト可能 |
| **C** | PostgreSQL 互換マイグレーション | `migrations/__init__.py` + `/treasury/migrations/status` | Alembic 風 (numbered + idempotent + dialect 切替) で SQLite/PostgreSQL 両対応 |
| **D** | E2E 拡張 | `e2e/tests/flagship-flow.spec.ts` に 3 件追加 | OAuth ラジオ + 多年度ビュー + keys/migrations 監査エンドポイント |
| **E** | 戦略会議 #2 英訳 | `docs/strategy-2026-05-round2-en.md` | MAS forum 共有 (#1 英訳に続く 2 本目) |

## 2. ECDSA 鍵 rotation 設計

```
ENV 例 (Phase 2 移行時):
    JPN_PBM_GOVERNOR_PRIVKEYS=key_2027,key_2026,key_2025  # 新しい順
    JPN_PBM_GOVERNOR_ACTIVE_IDX=0                          # 最新を active
    JPN_PBM_KEY_GRACE_DAYS=90                              # 旧鍵の grace 期間

サンプル運用:
    1. 月初: 新 key_NEW を先頭に追加 → ACTIVE_IDX=0
    2. grace 期間中: 旧 key で署名された coupon も検証成功
    3. grace 後: 旧 key を ENV から外す → 旧 key 署名は reject
```

`verify_against_any_governor` は登録鍵全部を試すため、本番運用では 2-3 世代まで。

## 3. Sol シミュレータ vs 実コントラクト

| 観点 | Sol (`redeemBatch`) | Python シミュレータ | 等価 |
|------|---------------------|----------------------|------|
| 1 件失敗 → 全体 revert | Solidity revert | `SolRevert` raise | ✅ |
| nonce | `consumed[pid][month]` mapping | dict[(pid, month)] | ✅ |
| approved store | `approvedStores[msg.sender]` | set | ✅ |
| 署名検証 | `ecrecover == governor` | `verify_coupon_eip191` | ✅ keccak256 互換 |
| grace | `expires_at + 30 days` | `GRACE_DAYS_SEC` | ✅ |
| payout | `jpyc.transfer(store, amount)` | `store_balances[s] += amount` | ✅ |

## 4. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 123 passed in 4.62s ✓
[verify:seed]   ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green
```

100 → 123 tests pass (+23):
- key_rotation: 8 件
- sol_simulator: 9 件
- migrations: 6 件

## 5. ポイント精算 (ラウンド 6)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Stablecoin Architect** | **A 完全採用 + B (Sol シミュレータ) 設計** | **+30** |
| Engineer | C migrations + D E2E 拡張 | +20 |
| Researcher | E 戦略会議 #2 英訳 | +15 |
| Cost Guardian | C migrations の冪等性確認 | +10 |
| Red Team | A の rotation 危険シナリオ拾い | +10 |
| Purpose Guardian | A の旧鍵 reject 設計確認 | +10 |
| CTO | B シミュレータの etherem ABI 互換確認 | +10 |
| その他 | 提案待機 | 各 +5 |

🥇 **MVP**: Stablecoin Architect (+30) — Phase 3 本番デプロイ前の互換性リスクを 2 段 (A 鍵 rotation + B シミュレータ) で解消。

## 6. ラウンド 7 候補

- Polygon Mumbai 実デプロイ (実 RPC 必要 = 残課題)
- マイナポータル v2 実 OAuth wire-up (実 API key)
- 戦略会議 #3, #4, #5 の英訳継続
- HSM 連携 (鍵を env から HSM API 取得に切替)
- 1 万人本番スケール (PostgreSQL 上で測定)
