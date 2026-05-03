# 戦略会議 #8 — ドキュメント完結 + Phase 3 backend 拡充

> **作成日**: 2026-05-02 (round 9)
> **議題**: 戦略会議 #4-#7 の英訳を完了し、Phase 3 (HSM 実機接続 + PostgreSQL 移行) の backend stub を整備
> **アウトプット**: 5 件の機能実装 + 戦略会議 4 本英訳完了 (5/5)

## 1. 採択 5 件

| # | 提案 | 実装 | 影響 |
|---|------|------|------|
| **A** | 戦略会議 #4 #5 #6 #7 英訳 | `docs/strategy-2026-05-round{4,5,6,7}-en.md` | MAS forum / BIS Agorá / OECD Blockchain Policy Forum 共有準備完了 (5/5) |
| **B** | HSM PKCS#11 backend stub | `services/hsm_adapter.py:Pkcs11Backend` | Phase 3 で AWS CloudHSM / Thales Luna に切替可能、sandbox では Mock fallback |
| **C** | ECDSA 鍵 age tracking | `key_management.GovKey.age_days/is_overage` + `JPN_PBM_GOVERNOR_ISSUED_AT` | 365 日超過で WARNING、SOC dashboard で可視化 |
| **D** | PostgreSQL 互換性検証 | `docs/postgresql-compat.md` + `tests/test_postgres_compat.py` | 全モデルが PostgreSQL 方言で compile 可能、SQLite 専用箇所を明文化 |
| **E** | ロードマップ更新 | `services/roadmap.py:M+6 → done`, `M+7 → ready` | 18 ヶ月計画の Phase 1 完了率が向上 |

## 2. 全体計画の現在地 (更新)

| Phase | done | ready | partial | blocked | pending | 計 |
|-------|------|-------|---------|---------|---------|-----|
| Phase 1 | **3** (+1) | 4 | **0** (-1) | 1 | 0 | 8 |
| Phase 2 | 1 | **3** (+1) | **1** (-1) | 1 | 1 | 7 |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 |

**進捗: M+6 都議会報告 = done (英訳 5/5 達成)、M+7 防災備蓄 = ready**

## 3. 検証

```
$ bash scripts/verify.sh all
[verify:pytest] 150 passed in 2.95s ✓
[verify:seed]   citizens=10 stores=5 programs=7 products=30 ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green
```

138 → 150 tests pass (+12):
- HSM PKCS#11: 4 件
- 鍵 age tracking: 4 件
- PostgreSQL compat: 4 件

## 4. ポイント精算 (ラウンド 8)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Researcher** | **A 戦略会議 4 本英訳完了** | **+30** |
| Stablecoin Architect | B PKCS#11 stub + C 鍵 age tracking | +25 |
| Engineer | D PostgreSQL 互換性 + E ロードマップ更新 | +20 |
| Cost Guardian | C 過齢警告閾値設計 | +10 |
| Red Team | C 鍵 rotation の age 抜け穴指摘 | +10 |
| Purpose Guardian | A 英訳の "国際差別化要素" 整理 | +5 |
| その他 | 提案待機 | 各 +5 |

🥇 **MVP**: Researcher (+30) — 戦略会議 5 本中 4 本を 1 ラウンドで英訳し、MAS / BIS / OECD への共有準備を完了。

## 5. ラウンド 9 候補 (実外交・実環境依存が多い)

- Polygon Mumbai 実デプロイ (実 RPC 必要)
- マイナポータル v2 実 OAuth (実 API key 必要)
- HSM 実機接続 (PKCS#11 実装の library + token 設定)
- PostgreSQL 実環境マイグレ (psycopg2 + 実 DB)
- 戦略会議 #1 M+0 Founders' MoU (実外交)
- 100 万人スケール本番 (PostgreSQL + connection pool tuning)
