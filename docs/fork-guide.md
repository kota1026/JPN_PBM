# 多自治体 fork ガイド (戦略会議 #9 採択 E)

> **作成日**: 2026-05-02 (round 10)
> **対象**: 東京都モデルを採用したい他自治体 (大阪府 / 愛知県 / 横浜市 など) の DX 担当
> **ロードマップ**: 戦略会議 #1 Phase 3 M+16 (他自治体 fork 第 1 号) の準備

本書は、`github.com/kota1026/JPN_PBM` を fork し、自分の自治体の助成金 PBM として
動かすための手順を定義する。

---

## 0. 前提

- Apache License 2.0 → 商用・公的利用とも可、GitHub fork で派生 OK
- 東京都への帰属表示 (NOTICE) を維持すれば、改変・再配布・SaaS 提供すべて許可
- CP-1〜CP-6 の憲法原則を踏襲することを推奨 (特に CP-6 災害時可用性は日本国内必須)

## 1. fork 〜 起動 (15 分)

```bash
# 1. GitHub Web で fork
# 2. clone
git clone https://github.com/<your-prefecture>/JPN_PBM.git
cd JPN_PBM

# 3. 依存インストール + 起動
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`http://localhost:8000/ui/tokyo.html` が東京都モデルそのまま動く。

## 2. 自治体名 / フラッグシップの差替 (1 時間)

### 2.1 seed プログラムの差替

`seed/programs.json` の `prog-koto-kosodate-2026` を自治体に合わせて新規追加。

例: 大阪市の場合
```json
{
  "id": "prog-osaka-kosodate-2026",
  "name": "大阪市 こども応援 PBM 2026",
  "description": "大阪市内 0-18 歳子育て世帯 × 加盟店パイロット",
  "budget_jpy": 60000000,
  "subsidy_bps": 10000,
  "per_citizen_cap_jpy": 60000,
  "start_at": "2026-04-01T00:00:00",
  "end_at":   "2026-12-31T23:59:59",
  "eligibility": { "wards": ["北区", "中央区"], "min_age": 18, "max_age": 64 },
  "eligible_categories": ["food.baby", "food.daily", "goods.baby"],
  "approved_stores": ["store-osaka-aeon"]
}
```

### 2.2 加盟店 / 住民 sample データ
- `seed/stores.json`: 自治体の加盟店リストに置換
- `seed/citizens.json`: ダミー住民の `ward` フィールドを自治体内に変更

### 2.3 検証
```bash
bash scripts/verify.sh seed   # 整合性 OK
bash scripts/verify.sh py     # tests 全部 通る (138+)
```

## 3. ブランディング (フロントエンド) (1 日)

`frontend/styles.css` の Tokyo color palette を自治体ロゴカラーに差替。
- `--accent` (Tokyo Navy → 自治体メインカラー)
- `--accent-2` (Tokyo Yellow → サブカラー)
- フッターのクレジット行 (= NOTICE 維持必須、東京都の謝辞を入れる)

## 4. 法務確認 (自治体ごと、2-4 週間)

東京都モデルは以下の法令を前提に設計されている。自治体ごとに:

- **個人情報保護法 §27** (第三者提供) — `models/consent.py` のスキーマで対応済
- **資金決済法** (JPYC を電子決済手段として利用) — JPYC 株式会社との利用契約必要
- **自治体条例** (例: 東京都個人情報保護条例) — 自治体内部の条例改正が必要

### 推奨: 法務レビュー
- 個情法専門の弁護士に `models/consent.py` + `routers/myna_oauth.py` をレビュー依頼
- 資金決済法は JPYC 株式会社の法務部門と協議

## 5. CP-6 災害時可用性の地域特化 (1 週間)

東京都の CP-6 設計は **首都直下地震** を前提とした grace 30 日。自治体ごとに:

- 南海トラフ想定地域 (大阪・兵庫・静岡 等): grace 60-90 日推奨
- 内陸自治体 (長野・群馬 等): grace 14 日でも可
- `backend/app/services/offline_fallback.py:GRACE_DAYS_SEC` を調整

## 6. JPYC 決済との接続 (M+1 〜 M+3)

東京都モデル同様:
1. JPYC 株式会社と協議 → testnet JPYC アドレス取得
2. `contracts/PBM.sol` を Polygon Mumbai にデプロイ
3. `services/sol_compat.py` の ECDSA 署名で PoC

詳細は [`production-runbook.md` ① Polygon Mumbai testnet デプロイ](./production-runbook.md) を参照。

## 7. Phase 3 M+16 として東京都モデルへの貢献還元

派生プロジェクトで以下を作った場合は、upstream PR で還元することを推奨:

- 自治体特化の seed バリエーション → `seed/regions/<your-pref>/` に置く設計提案
- ブランディング差替の汎用化 → 環境変数 + テンプレートエンジン化
- 災害時想定の地域別 GRACE_DAYS テーブル
- 自治体ごとの CP-6 試験運用ログ (匿名化済)

東京都が公開ホワイトペーパー (M+18) を発表する際、共著者として記載することを期待。

---

## 付録: チェックリスト

- [ ] GitHub で fork 完了
- [ ] `bash scripts/verify.sh all` 緑
- [ ] 自治体名差替 (seed + frontend)
- [ ] 法務レビュー完了
- [ ] CP-6 grace 期間を地域に合わせて調整
- [ ] JPYC 株式会社との利用契約締結
- [ ] Polygon Mumbai PoC 成功
- [ ] CSIRT 24h 体制設定
- [ ] 自治体議会への報告
- [ ] 1 区パイロット (100 世帯) 開始
