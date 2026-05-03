# JPN_PBM — 東京都 × JPYC 助成金 PBM (Purpose Bound Money)

東京都向けの **PBM (Purpose Bound Money) システム**。
JPYC をラップしたプログラマブルマネーで、JAN コードによる商品識別 +
マイナンバーカード 4 情報による受給資格判定を組み合わせ、
助成金が「目的どおり」に使われたことを保証しつつ、全取引を **EBPM**
(Evidence-Based Policy Making) 基盤へ蓄積する。

> 戦略会議 #1 (2026-04-30, [docs/strategy-2026-04.md](docs/strategy-2026-04.md))
> で確定した 18 ヶ月ロードマップを 9 ラウンド (PR #3 〜 #10) で実装。
> 現在 Phase 2 完成形 + Phase 3 接続準備が完了し、
> M+11 (CP-6 災害時オフラインフォールバック) は本番投入待ち。

---

## ハイライト

- **PBM ラッパー**: JPYC を Purpose 付きでロック → 条件成立時のみ自動アンラップ
- **CP-1〜CP-6 runtime 強制**: `services/purpose_guard.py` の単一関門で
  目的整合 / プライバシー / 自動執行 / 監査可能 / 不正排除 / 災害時可用 を deny
- **CP-6 災害時フェイルセーフ** (世界初): 首都直下時に offline QR + 復旧後
  batch 精算で給付が止まらない (`contracts/PBMOfflineFallback.sol` +
  `services/sol_compat.py` + `services/sol_simulator.py`)
- **多年度予算条例化**: `program.fiscal_year_budgets` で政権交代耐性
- **ECDSA 鍵 rotation**: env multi-key + active 切替 + 全鍵 verify (`services/key_management.py`)
- **JPYC ペッグ監視**: ±100bps ALERT / ±300bps AUTO-FREEZE
- **準備金 24h 監査**: JPYC 全量 + PBM outstanding 突合
- **マイナポータル v2 OAuth Mock**: 同意ログ (Personal Info Act §27 対応)
- **EBPM (k=5 anonymity)** + **CP 違反 dashboard**
- **POS SDK (Python)**: 加盟店端末向け、urllib のみ依存・JSONL ローカルキュー
- **ロードマップ進捗 dashboard**: 18 ヶ月計画の現在地を画面で可視化

## ディレクトリ構成

```
JPN_PBM/
├── README.md
├── .devcontainer/                # Codespaces / VS Code Dev Container
├── .github/workflows/verify.yml  # GitHub Actions CI (Round 10)
├── docs/
│   ├── architecture.md           # 全体設計
│   ├── strategy-2026-04.md       # 戦略会議 #1 (フラッグシップ確定)
│   ├── strategy-2026-04-en.md    # English (MAS forum 共有用)
│   ├── strategy-2026-05-round*.md  # 戦略会議 #2-#7 + 各英訳
│   ├── cp6-offline-fallback.md   # CP-6 設計
│   ├── postgresql-compat.md      # PostgreSQL 移行手順
│   ├── production-runbook.md     # 本番デプロイ runbook (Round 10)
│   ├── fork-guide.md             # 多自治体 fork ガイド (Round 10)
│   ├── ebpm.md / flow.md / demo.md / video-script.md
├── contracts/
│   ├── PBM.sol                   # PBM ラッパー (参考)
│   └── PBMOfflineFallback.sol    # CP-6 災害時フォールバック (世界初)
├── backend/                      # FastAPI 実装
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py                 # SQLite WAL + マイグレ
│   │   ├── models/               # citizen / consent / cp_violation /
│   │   │                         #   ebpm / pbm / product / program / store / wallet
│   │   ├── routers/              # auth / consent / ebpm / myna_oauth / offline /
│   │   │                         #   products / programs / purchase / seed / treasury / wallet
│   │   └── services/             # purpose_guard / pbm / eligibility / privacy /
│   │                             #   jpyc / offline_fallback / sweeper / treasury_audit /
│   │                             #   peg_monitor / fiscal_budget / sol_compat /
│   │                             #   sol_simulator / key_management / hsm_adapter / roadmap
│   ├── migrations/               # 番号付き PostgreSQL 互換マイグレ
│   └── tests/                    # 138 件 (Round 8 時点)
├── frontend/
│   ├── tokyo.html                # 都管理: 監査/Peg/CP-6/CP違反/多年度/ロードマップ
│   ├── citizen.html              # 住民: 認証 (Phase 1 直接 / Phase 2 OAuth) + ウォレット + 災害用 QR
│   ├── retailer.html             # 加盟店 POS + CP-6 ネット断モード
│   └── ebpm.html                 # EBPM ダッシュボード
├── seed/                         # JAN 30 / 加盟店 5 / プログラム 7
├── sdk/python/jpn_pbm_pos/       # POS SDK (Python, urllib のみ)
├── e2e/                          # Playwright E2E (4 ケース)
└── scripts/
    ├── verify.sh                 # 実装→検証ハーネス (10 モード)
    ├── check_seed.py / check_sol.py / check_frontend_js.py
    ├── cron_sweep.py             # 期限切れ token sweep cron
    ├── loadtest.py               # 負荷試験 (asyncio + httpx)
    └── readiness_check.py        # 本番投入 readiness 自動診断 (Round 10)
```

## 起動方法

### A. GitHub Codespaces / Dev Container (推奨)

`.devcontainer/` が同梱されているので、Code → Codespaces で開けば
依存インストールとサーバ起動が自動で走る。

### B. ローカル

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

ブラウザ:
- 東京都管理: http://localhost:8000/ui/tokyo.html
- 住民: http://localhost:8000/ui/citizen.html
- 加盟店 POS: http://localhost:8000/ui/retailer.html
- EBPM: http://localhost:8000/ui/ebpm.html
- API docs: http://localhost:8000/docs (Swagger UI)

E2E API 実行ログは [docs/demo.md](docs/demo.md)、動画台本は [docs/video-script.md](docs/video-script.md)。

## 検証ハーネス (`scripts/verify.sh`)

```bash
bash scripts/verify.sh all     # pytest + seed + sol + front-js
bash scripts/verify.sh py      # pytest のみ
bash scripts/verify.sh quick   # pytest + seed
bash scripts/verify.sh seed    # seed JSON 妥当性
bash scripts/verify.sh sol     # Solidity 軽量構文
bash scripts/verify.sh front   # frontend inline JS
bash scripts/verify.sh cp6     # CP-6 オフラインフォールバック スモーク
bash scripts/verify.sh sweep   # 期限切れ token sweep dry-run
bash scripts/verify.sh load    # 負荷試験 (50×200 = 10K req)
bash scripts/verify.sh ready   # 本番投入 readiness 診断 (Round 10)
bash scripts/verify.sh e2e     # Playwright (ブラウザ無し時 skip)
```

GitHub Actions の `.github/workflows/verify.yml` が PR / push のたびに
自動で `all` + `sweep` + `ready` + `load` を回す。

## 主要 API エンドポイント

| 領域 | エンドポイント | 用途 |
|------|--------------|------|
| auth | POST /auth/myna/login | マイナ Mock 認証 (Phase 1) |
| auth | POST /myna/v2/authorize/consent → /token → /userinfo | OAuth Mock (Phase 2) |
| consent | POST /consent/grant / /revoke | 個情法 §27 同意ログ |
| programs | POST /programs / GET /eligible/{pid} / GET /{id}/fiscal-budget | 助成金プログラム CRUD + 多年度 |
| purchase | POST /purchase | 加盟店 POS からの購入 (PBM 自動適用) |
| offline | POST /offline/coupons / /redeem-batch / /stores/approve | CP-6 災害時 |
| ebpm | GET /ebpm/summary / /breakdown / /violations / /violations/recent | k=5 集計 + CP 違反 |
| treasury | GET /treasury/audit / /peg/status / /keys/rotation / /migrations/status / /roadmap / /hsm/status | SOC dashboard |

## 想定する助成金プログラム (seed)

1. **江東区 こども・くらし応援 PBM 2026 ★ フラッグシップ** (`prog-koto-kosodate-2026`)
   - 戦略会議 #1 採択 / DBS-OGP CDC バウチャー東京移植 / 1,000 世帯 × 30 店舗
2. **江東区 防災備蓄ローリング助成 2026** (`prog-koto-disaster-pack-2026`)
   - 戦略会議 #4 + #7 採択 / 多年度予算 (5,000 万 × 3 年度)
3. 省エネ家電 / 子育て食品 / 高齢者ヘルスケア / 防災備蓄 / 在宅介護 (デモ)

## 全体計画 (戦略会議 #1 ロードマップの達成状況)

| Phase | done | ready | partial | blocked | pending | 計 |
|-------|------|-------|---------|---------|---------|-----|
| Phase 1 | 2 | 4 | 1 | 1 | 0 | 8 |
| Phase 2 | 1 | 2 | 2 | 1 | 1 | 7 |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 |

**M+11 (CP-6 本番投入) は ready** = 技術的準備完了。実 Polygon Mumbai デプロイ /
HSM 接続 / マイナポータル v2 実 API key の手順は [docs/production-runbook.md](docs/production-runbook.md) に記述。

詳細は `GET /treasury/roadmap` または `tokyo.html` の「ロードマップ進捗」セクションで参照可能。

## デモデータについて

商品マスタ (`seed/products.json`) には、Panasonic / 三菱電機 / 象印 / 明治 / P&G / 花王 /
ライオン / 大正製薬 / 大塚製薬 / サントリー / アイリスオーヤマ / 尾西食品 / ソニー /
大王製紙 / コクヨ / 三菱鉛筆 / 山崎製パン 各社の **メーカー公式ページ等で公開されている
実在の JAN コード (EAN-13)** を使用 (各レコードに `source` URL を併記)。

価格 (`price_jpy`) は UI 表示の参考値であり、メーカー希望小売価格でも実売価格でもありません。
`programs.json` の助成金プログラムは MVP デモ用の架空設計で、本リポジトリは
**「これら実在製品を東京都が実際に助成対象に指定している」ことを意味しません**。

## 国際公開準備

戦略会議 #1, #2, #3 は英訳済 ([docs/strategy-2026-04-en.md](docs/strategy-2026-04-en.md) ほか)。
MAS Project Orchid forum / BIS Agorá / OECD Blockchain Policy Forum での共有を想定。

## ライセンス

[Apache License 2.0](LICENSE)
