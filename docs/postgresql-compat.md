# PostgreSQL 互換性 (戦略会議 #8 採択 D)

> **作成日**: 2026-05-02 (round 9)
> **目的**: SQLite (MVP) で動いているコードベースを PostgreSQL (本番) に移行する際の検証ポイント

## 1. 移行手順 (実環境)

```bash
# 1. PostgreSQL 起動
createdb jpn_pbm
createuser pbm_app -P  # password 入力

# 2. driver インストール
pip install psycopg2-binary==2.9.9

# 3. URL 切替
export JPN_PBM_DB_URL=postgresql://pbm_app:<pwd>@localhost:5432/jpn_pbm

# 4. 起動 (init_db で自動マイグレ + create_all)
cd backend && uvicorn app.main:app
```

## 2. SQLAlchemy 互換性チェックリスト

| カテゴリ | 状態 | 備考 |
|----------|------|------|
| 基本型 (Integer, String, DateTime) | ✅ 完全互換 | SQLAlchemy が dialect 抽象化 |
| **JSON 型** | ✅ 互換 (改善余地あり) | SQLite TEXT / PostgreSQL JSONB. 現状 `JSON` は両 dialect で動くが、PostgreSQL では `JSONB` (sqlalchemy.dialects.postgresql.JSONB) の方が高速・index 可能 |
| ForeignKey | ✅ | PostgreSQL では trigger ベース、SQLite と挙動同じ |
| `String(N)` 制約 | ✅ | PostgreSQL では VARCHAR(N) |
| `func.strftime` (EBPM 集計) | ⚠️ 要確認 | SQLite 専用関数。PostgreSQL では `to_char(ts, 'YYYY-MM')` 相当に置換要 |
| WAL モード | — | SQLite 専用。PostgreSQL は MVCC で並列読み書き可能 |

## 3. 既知の SQLite 専用箇所

| ファイル | 行 | 内容 | PostgreSQL での対応 |
|----------|-----|------|---------------------|
| `backend/app/db.py` | `_set_sqlite_pragma` | WAL/synchronous/busy_timeout | listener が `dialect.startswith("sqlite")` でガード済 → PostgreSQL では走らない |
| `backend/app/routers/ebpm.py` | `func.strftime` | 月/日付集計 | PostgreSQL 移行時に `func.to_char(ts, 'YYYY-MM-DD')` 相当に置換 |
| `backend/migrations/__init__.py` | DDL の dialect 分岐 | 各 Migration に `sqlite_sql` / `postgres_sql` を別々に持つ | 既に分岐済 |

## 4. ロードマップ

- ✅ Round 6 で SQLite WAL + busy_timeout を導入 → 5K req @ fail=2.66%
- ✅ Round 8 で並列調整 → 10K req @ fail=0%
- ⏸ Round 10+ で PostgreSQL 移行 → 数十万 req スケール
  - `func.strftime` を `func.to_char` に置換
  - `JSON` → `JSONB` 切替 (任意だが推奨)
  - 接続プールサイズチューニング (pool_size=20-40)

## 5. 検証 (本ラウンドで行ったこと)

- `backend/migrations/__init__.py` が `engine.dialect.name` で SQL を分岐していることを確認 (R6)
- `backend/app/db.py` の `_set_sqlite_pragma` listener が SQLite 専用であることを確認
- 全モデル (Citizen / Program / PBMToken / EBPMEvent / ConsentLog / CPViolation / Wallet) が `String / Integer / DateTime / Date / JSON / Boolean` のみで構成されていることを確認 (PostgreSQL でそのまま動く)
- `engine.dialect.name` が "sqlite" / "postgresql" を分岐するロジックは migration テスト (R6) で既に担保

## 6. 推奨タイムライン

| Phase | アクション |
|-------|----------|
| Phase 1 (現在) | SQLite WAL のままで OK (10K req fail=0% 達成済) |
| Phase 2 (M+12 100 万人スケール) | PostgreSQL 移行必須。本番 + staging を切替えてマイグレ確認 |
| Phase 3 (1,000 万人) | read replica + connection pool tuning + JSONB index |
