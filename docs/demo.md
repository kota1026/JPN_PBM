# E2E デモ実行ログ

ローカル環境で `uvicorn app.main:app` を立て、cURL で全エンドポイントを順次叩いた
**実際のレスポンス**を載せている (内容は再現可能)。

> このログをそのまま助成金申請のデモ資料 / PR 説明に貼って使えます。
> 環境変数 `JPN_PBM_DB_URL` を未設定の場合 `sqlite:///./jpn_pbm.db` が作られます。

ベース URL: `http://localhost:8000`

## 0. 起動と Swagger 確認

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

```bash
$ curl http://localhost:8000/
```
```json
{
  "name": "JPN PBM",
  "ui": ["/ui/tokyo.html", "/ui/citizen.html", "/ui/retailer.html", "/ui/ebpm.html"],
  "docs": "/docs"
}
```

API ドキュメントは `http://localhost:8000/docs` (Swagger UI)。

---

## 1. シードデータ投入

`POST /seed/load` でトレジャリーへ JPYC 1 億円ミント、商品 10 件・加盟店 5 件・住民
10 名・プログラム 3 件を一括登録、住民にも自己負担用 ¥50,000 ずつ配布。

```bash
$ curl -X POST http://localhost:8000/seed/load
```
```json
{
  "ok": true,
  "pid_map": {
    "MN-0001": "badf24b56f34d3a46d4250359f330838e8535bbc9a0fcf360035abb183bd2e50",
    "MN-0002": "6dcabc3c0e491552ef69af3b5b7f9891c84c5989b71f30644a3c304a5962fe2e",
    "MN-0003": "d55b9da22ef752ff25b5e1c093c1e0a95b3cfe47c372ef6c9380d09205f39752",
    "MN-0004": "e8098a09fb17b4e2f9eaca7eaf4e97860268174d678cf221440011e9cce31063",
    "MN-0005": "92de59eb9712d9e5b637e7a5de165d8e85bf0770b8163d117a94792fc392c853",
    "MN-0006": "f1a89c085c9b03e306a663d422fda4f2ad13d3f7f59f5b1382c9df741f3e43b6",
    "MN-0007": "ec480d8f34f30659c99436969ca451b06ba082cae618b20914694018214f2995",
    "MN-0008": "cfc5d24f046e5cc0e0bc3e380ff809e7a7aed15af26371b801fd9e8308224a48",
    "MN-0009": "c76e19b4c256e8089a1c23565f8f9cdc5932d97b89606e707fd2154765a9f915",
    "MN-0010": "9c9e5a6c37105ab8361a1111ba64caed1760c0678a491c6d2d97cbdc26eb6fe6"
  }
}
```

`pid_map` は **マイナンバー → HMAC 擬似 ID** の対応。以降この pid を使う。

| 短縮名     | 元 ID    | 擬似 PID (先頭 16 桁)      | 属性                       |
|-----------|---------|---------------------------|---------------------------|
| 山田太郎   | MN-0001 | `badf24b56f34d3a4…`       | 70 歳 / 新宿区 / M         |
| 佐藤花子   | MN-0002 | `6dcabc3c0e491552…`       | 35 歳 / 渋谷区 / F         |
| 田中健司   | MN-0005 | `92de59eb9712d9e5…`       | 77 歳 / 千代田区 / M       |

---

## 2. 受給可能プログラムの自動絞り込み (eligibility)

```bash
$ curl http://localhost:8000/programs/eligible/$P_TARO
```

| 住民       | 該当プログラム                                                   |
|-----------|------------------------------------------------------------------|
| 山田太郎   | `prog-eco-2026` (省エネ家電) / `prog-senior-2026` (高齢者ヘルスケア) |
| 佐藤花子   | `prog-eco-2026` (省エネ家電) / `prog-baby-2026` (子育て食品)        |
| 田中健司   | `prog-eco-2026` / `prog-senior-2026`                              |

→ **マイナンバー 4 情報の住所(区)・年齢でフィルタが効いている**ことを確認。

---

## 3. eligibility NG が API レベルで拒否される

35 歳の佐藤花子に高齢者プログラムを発行しようとすると弾かれる。

```bash
$ curl -X POST http://localhost:8000/programs/prog-senior-2026/issue \
       -H "Content-Type: application/json" \
       -d '{"citizen_pid":"6dca…"}'
```
```json
{"detail": "not eligible: 年齢 35 は最低年齢 65 未満"}
```
HTTP `400 Bad Request`。

---

## 4. PBM 発行 (= 助成金枠の付与)

```bash
$ curl -X POST http://localhost:8000/programs/prog-eco-2026/issue \
       -H "Content-Type: application/json" -d '{"citizen_pid":"badf…"}'
```
```json
{
  "pbm_id": "f90e9250-e023-4987-be06-16e0d68af8a0",
  "program_id": "prog-eco-2026",
  "holder_pid": "badf24b56f34d3a46d4250359f330838e8535bbc9a0fcf360035abb183bd2e50",
  "remaining_jpy": 50000,
  "expires_at": "2026-12-31T23:59:59"
}
```

| 住民       | プログラム            | 枠      |
|-----------|----------------------|---------|
| 山田太郎   | `prog-eco-2026`      | ¥50,000 |
| 山田太郎   | `prog-senior-2026`   | ¥20,000 |
| 田中健司   | `prog-senior-2026`   | ¥20,000 |
| 佐藤花子   | `prog-eco-2026`      | ¥50,000 |

---

## 5. 自己負担用に住民へ JPYC をトップアップ (デモ用)

```bash
$ curl -X POST http://localhost:8000/wallet/citizen/$P_TARO/topup \
       -H "Content-Type: application/json" -d '{"amount_jpy": 200000}'
```
```json
{ "jpyc_balance": 250000 }
```

(seed で ¥50,000 入っていたので合計 ¥250,000)

---

## 6. 加盟店 POS で JAN 購入 (PBM 自動適用)

### 6a. 山田太郎: 省エネエアコン ¥120,000 を購入

eco プログラムの助成率 30% → raw 36,000 円、住民上限 ¥50,000 内なので満額付与。

```bash
$ curl -X POST http://localhost:8000/purchase \
       -H "Content-Type: application/json" \
       -d '{"citizen_pid":"badf…","store_id":"store-bic-shinjuku","jan":"4901234567890","qty":1}'
```
```json
{ "ok": true, "reason": "OK", "total_jpy": 120000, "subsidy_jpy": 36000, "citizen_pay_jpy": 84000 }
```

### 6b. 山田太郎: シニアプロテイン ¥4,200 ×2 = ¥8,400

senior プログラムの 50%。

```json
{ "ok": true, "reason": "OK", "total_jpy": 8400, "subsidy_jpy": 4200, "citizen_pay_jpy": 4200 }
```

### 6c. 田中健司: 高血圧薬 ¥3,200 ×3 回購入

毎回 senior 50% で減額される。

```json
{ "ok": true, "reason": "OK", "total_jpy": 3200, "subsidy_jpy": 1600, "citizen_pay_jpy": 1600 }
{ "ok": true, "reason": "OK", "total_jpy": 3200, "subsidy_jpy": 1600, "citizen_pay_jpy": 1600 }
{ "ok": true, "reason": "OK", "total_jpy": 3200, "subsidy_jpy": 1600, "citizen_pay_jpy": 1600 }
```

### 6d. 山田太郎: 対象外商品 (おにぎり ¥180) → 助成 0

JAN がどのプログラムにも含まれないので自動的に通常決済。

```json
{ "ok": true, "reason": "OK", "total_jpy": 180, "subsidy_jpy": 0, "citizen_pay_jpy": 180 }
```

→ **「目的どおりにしか助成金が出ない」**ことが PBM のロジックで保証されている。

### 6e. 佐藤花子: LED ライト ¥18,000 (eco 30%)

```json
{ "ok": true, "reason": "OK", "total_jpy": 18000, "subsidy_jpy": 5400, "citizen_pay_jpy": 12600 }
```

---

## 7. 山田太郎ウォレット (購入後)

```bash
$ curl http://localhost:8000/wallet/citizen/$P_TARO
```
```json
{
  "pid": "badf24b56f34d3a46d4250359f330838e8535bbc9a0fcf360035abb183bd2e50",
  "jpyc_balance": 161620,
  "pbm_tokens": [
    { "id": "f90e9250-…", "program_id": "prog-eco-2026",    "remaining_jpy": 14000, "status": "ISSUED" },
    { "id": "693ee20e-…", "program_id": "prog-senior-2026", "remaining_jpy": 15800, "status": "ISSUED" }
  ]
}
```

`50,000 - 36,000 = 14,000` (eco 残枠) / `20,000 - 4,200 = 15,800` (senior 残枠) と一致。
JPYC 残高 = 250,000 − 84,000 − 4,200 − 180 = **161,620** で一致。

---

## 8. 加盟店残高 (JPYC 受領)

```bash
$ curl http://localhost:8000/wallet/store/store-bic-shinjuku
```

| 店舗                    | JPYC 残高 | 内訳                                              |
|-------------------------|-----------|---------------------------------------------------|
| ビック家電 新宿東口店     | ¥120,180  | エアコン 120,000 + おにぎり 180                   |
| マツモトキヨシ渋谷店     | ¥18,000   | プロテイン 8,400 + 高血圧薬 3,200×3 = 9,600        |
| ヨドバシ秋葉原店         | ¥18,000   | LED ライト                                        |

PBM のアンラップ分 (助成金) と住民の自己負担分が、両方とも JPYC として
**店舗ウォレットに合算**されている。店舗からみれば「フルで JPYC を受け取った」
だけなので会計フローはシンプル。

---

## 9. EBPM サマリ

```bash
$ curl http://localhost:8000/ebpm/summary
```
```json
[
  {
    "program_id": null, "program_name": null,
    "tx_count": 1, "unique_citizens": 1,
    "total_jpy": 180, "subsidy_jpy": 0, "citizen_pay_jpy": 180
  },
  {
    "program_id": "prog-eco-2026", "program_name": "省エネ家電購入支援 2026",
    "tx_count": 2, "unique_citizens": 2,
    "total_jpy": 138000, "subsidy_jpy": 41400, "citizen_pay_jpy": 96600,
    "budget_jpy": 50000000, "budget_remaining_jpy": 49958600,
    "leverage_pay_per_subsidy": 2.33
  },
  {
    "program_id": "prog-senior-2026", "program_name": "高齢者ヘルスケア商品支援 2026",
    "tx_count": 4, "unique_citizens": 2,
    "total_jpy": 18000, "subsidy_jpy": 9000, "citizen_pay_jpy": 9000,
    "budget_jpy": 20000000, "budget_remaining_jpy": 19991000,
    "leverage_pay_per_subsidy": 1.0
  }
]
```

**読み方の例**:
- eco プログラムは助成金 ¥41,400 に対し住民の自己負担が ¥96,600 → **レバレッジ 2.33 倍** (1 円の助成で 2.33 円の自己消費)
- senior は薬・サプリ中心で 1 倍 (=半額補助の構造どおり)
- `program_id: null` の行は対象外 JAN のおにぎり購入。**助成 0 円でもログに残る**ので、政策外消費との比較分析が可能

## 10. プログラム単位の uptake

```bash
$ curl http://localhost:8000/ebpm/programs/prog-eco-2026/uptake
```
```json
{
  "program_id": "prog-eco-2026", "name": "省エネ家電購入支援 2026",
  "budget_jpy": 50000000, "spent_jpy": 41400,
  "consumption_rate": 0.000828,
  "tx_count": 2, "unique_citizens": 2, "subsidy_jpy": 41400
}
```

## 11. ブレイクダウン (k-匿名性で保護)

```bash
$ curl 'http://localhost:8000/ebpm/breakdown?dim=category'
```
```json
[
  { "key": "appliance.air_conditioner", "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-" },
  { "key": "appliance.light",           "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-" },
  { "key": "food.daily",                "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-" },
  { "key": "med.rx",                    "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-" },
  { "key": "med.supplement",            "tx_count": "-", "unique_citizens": "-", "total_jpy": "-", "subsidy_jpy": "-" }
]
```

→ デモではユニーク人数が k=5 未満のため**全セルが `-` に丸められる**。
本番運用で利用者が増えれば自動的に数値が表示される (`backend/app/routers/ebpm.py` 内 `K_ANON = 5`)。

---

## 12. プログラム取消 → 残予算返却

```bash
$ curl -X DELETE http://localhost:8000/programs/prog-baby-2026
```
```json
{ "ok": true, "refund_jpy": 30000000 }
```

```bash
$ curl http://localhost:8000/programs
# → prog-baby-2026 の revoked: true
```

取消後、その住民が持っていた PBM トークンは `REVOKED` ステータスとなり購入時に
助成は出ない (テスト `test_revoke_program_blocks_future_purchases` で検証)。

---

## まとめ — このログから読み取れること

| 観点               | このログでの根拠                                                   |
|--------------------|-------------------------------------------------------------------|
| Purpose 拘束       | 対象 JAN 以外は助成 0 (6d), 対象 JAN は自動で減額決済 (6a-c, 6e)    |
| eligibility 自動化 | 4 情報フィルタが API で機能 (2, 3)                                  |
| 上限制御           | 30% raw 計算 → per_citizen_cap で頭打ち (実装は `_calc_subsidy`)    |
| プライバシー       | 個票ではなく集計・k=5 未満は丸め (11)                              |
| EBPM 即時集計      | レバレッジ・消化率・受給ユニーク人数を 1 API で取得 (9, 10)         |
| 失効・予算返却     | revoke で残予算がトレジャリーに戻る (12)                            |

**全 8 件の pytest** (`backend/tests/`) が同じ挙動を回帰検証している。
