# JPN-PBM 本番デプロイ Runbook

> **作成日**: 2026-05-02 (round 10) / **対象**: Phase 2 → Phase 3 移行担当の SRE / DevOps
> **前提**: 本リポジトリの `claude/round*` ブランチが順次マージされ、戦略会議 #1 で確定したロードマップ (M+0〜M+18) を実行する段階

本書は Phase 2 完成形 (PR #3-#9 マージ済) を、実環境 (Polygon Mumbai / PostgreSQL / HSM) に本番投入するための手順を定義する。

---

## 0. 全体フロー

```
sandbox (R1-R9 完了)
  │
  ├─ ① Polygon Mumbai testnet デプロイ (1〜2 週間)
  │
  ├─ ② PostgreSQL 移行 (1 週間)
  │
  ├─ ③ HSM (PKCS#11 / AWS CloudHSM) 接続 (2〜4 週間)
  │
  ├─ ④ マイナポータル v2 OAuth 接続 (実 API 申請 + 1 ヶ月以上)
  │
  └─ ⑤ Polygon mainnet デプロイ + 1 区パイロット投入 (M+3 Closed Alpha)
```

各フェーズで `bash scripts/verify.sh all` + 個別スモークを最低 1 回回す。

---

## ① Polygon Mumbai testnet デプロイ

### 必要なもの
- Polygon Mumbai RPC (Alchemy / Infura / 自前ノード)
- Tokyo Treasury 用の wallet (秘密鍵 OR HSM 鍵)
- MATIC testnet token (faucet 経由で 1+ MATIC)
- 既デプロイ済の **JPYC ERC-20 testnet アドレス** (JPYC 株式会社と協議)

### 手順

1. **Solidity ツールチェーン**
   ```bash
   cd contracts
   npm i -D hardhat @nomicfoundation/hardhat-toolbox
   npx hardhat init
   ```

2. **deploy script 作成** (`contracts/deploy/01_deploy_pbm.js`):
   ```js
   const { ethers } = require("hardhat");
   async function main() {
     const JPYC_ADDR = process.env.JPYC_ADDRESS;  // testnet JPYC
     const PBM = await ethers.deployContract("PBM", [JPYC_ADDR]);
     await PBM.waitForDeployment();
     console.log("PBM:", await PBM.getAddress());
     const Off = await ethers.deployContract("PBMOfflineFallback", [JPYC_ADDR]);
     await Off.waitForDeployment();
     console.log("PBMOfflineFallback:", await Off.getAddress());
   }
   main().catch(e => { console.error(e); process.exit(1); });
   ```

3. **デプロイ実行**
   ```bash
   export MUMBAI_RPC=https://polygon-mumbai.alchemy.com/v2/<KEY>
   export DEPLOYER_PRIVKEY=0x<32 bytes>
   export JPYC_ADDRESS=0x<testnet JPYC>
   npx hardhat run --network mumbai deploy/01_deploy_pbm.js
   ```

4. **Sol ⇄ Python シミュレータ相互運用テスト** (R7 で書いた `services/sol_simulator.py` と一致確認):
   ```bash
   # 1) python で SignedCoupon を 1 件生成
   python -c "
   from app.services.sol_compat import SolCoupon, privkey_from_hex, sign_coupon_eip191
   c = SolCoupon.from_strings(program_id='p', pid='a'*64, month_index=202604, cap_jpy=5000, expires_at=9999999999)
   sk = privkey_from_hex('<DEPLOYER_PRIVKEY 32 bytes>')
   print(sign_coupon_eip191(c, sk).hex())
   "
   # 2) 上記 sig を Sol redeemBatch にそのまま投げる → revert しないことを確認
   ```

### Verify (Mumbai)
- block explorer (PolygonScan Mumbai) で contract verified
- `redeemBatch` 1 件成功 (TX hash 取得)
- `events.Redeemed` が emit されている

---

## ② PostgreSQL 移行

### 必要なもの
- PostgreSQL 15+ (RDS / Cloud SQL / 自前)
- driver: `pip install psycopg2-binary==2.9.9`

### 手順

1. **DB セットアップ**
   ```bash
   createdb jpn_pbm_prod
   createuser pbm_app -P
   psql -c "GRANT ALL ON DATABASE jpn_pbm_prod TO pbm_app"
   ```

2. **環境変数切替**
   ```bash
   export JPN_PBM_DB_URL=postgresql://pbm_app:<pwd>@<host>:5432/jpn_pbm_prod
   ```

3. **`func.strftime` を `func.to_char` に置換** (PostgreSQL 互換):
   - `backend/app/routers/ebpm.py` の `func.strftime("%Y-%m-%d", ...)` → `func.to_char(ts, 'YYYY-MM-DD')`
   - `backend/app/services/fiscal_budget.py` の `spent_by_year_from_ebpm` 内も同様

4. **マイグレーション実行**
   ```bash
   cd backend && python -c "from app.db import init_db; init_db()"
   # → 自動で _migrate (legacy ALTER) + run_migrations (numbered) が走る
   ```

5. **JSONB index 追加** (パフォーマンス改善, optional):
   ```sql
   CREATE INDEX idx_program_categories ON programs USING GIN (eligible_categories);
   ```

### Verify (PostgreSQL)
- `bash scripts/verify.sh load --concurrency 200 --iters 500` (= 100K req)
- p95 < 200ms / fail = 0%

---

## ③ HSM (PKCS#11 / AWS CloudHSM) 接続

### 必要なもの
- HSM (AWS CloudHSM / Thales Luna / Yubico FIPS / SoftHSM2 (テスト用))
- PKCS#11 driver (`.so` library)
- 既存の env 鍵管理から HSM へのマイグレ計画

### 手順

1. **PKCS#11 client インストール**
   ```bash
   pip install python-pkcs11==0.7.0
   sudo apt install opensc-pkcs11  # SoftHSM2 / OpenSC ベース
   ```

2. **HSM 鍵の作成 + 公開鍵取得**
   ```bash
   pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so --keypairgen \
       --key-type EC:secp256k1 --label "tokyo-pbm-2027"
   ```

3. **本コードの拡張**:
   `backend/app/services/hsm_adapter.py` の `Pkcs11Backend` を実装:
   - `python-pkcs11` で session を開く
   - `session.find_objects` で label による key lookup
   - `session.sign(key, digest, mechanism=Mechanism.ECDSA)` で署名
   - r||s|| 戻り値の正規化 (low-s) + recovery id 試行 (Round 6 sol_compat.py を流用)

4. **環境変数**
   ```bash
   export JPN_PBM_HSM_BACKEND=pkcs11
   export JPN_PBM_HSM_PKCS11_LIBRARY=/usr/lib/softhsm/libsofthsm2.so
   export JPN_PBM_HSM_PKCS11_TOKEN=tokyo-pbm-token
   export JPN_PBM_HSM_PKCS11_KEY_IDS=tokyo-pbm-2027
   ```

### Verify (HSM)
- `GET /treasury/keys/rotation` が HSM の address を返す (秘密鍵ではなく公開鍵 = address のみ)
- `POST /offline/coupons` が HSM 経由で署名 → Sol simulator で verify 成功

### Rollback 戦略
- env backend と HSM backend を **並列稼働**: env で署名した coupon は引き続き grace 期間中 verify 通過 (Round 7 鍵 rotation 設計)
- 移行完了後 1 ヶ月で env 鍵を revoke (env から削除)

---

## ④ マイナポータル v2 OAuth 接続

### 必要なもの
- マイナポータル v2 OAuth API key (デジタル庁との協議が必要、申請 + 審査で 1 ヶ月以上)
- redirect_uri に都の本番ドメイン (例: `https://pbm.metro.tokyo.lg.jp/auth/callback`)

### 手順

1. **Round 5 で実装した Mock を本番 IdP に切替**:
   `backend/app/routers/myna_oauth.py` の `CLIENT_ID` / `ALLOWED_REDIRECT_URI_PREFIXES` を本番値に更新

2. **本番 IdP から認可コードを取得**:
   - frontend `citizen.html` の OAuth radio から自動でリダイレクト
   - 認可後 `code=...&state=...` で都サーバに戻ってくる
   - `POST /myna/v2/token` (← 本番 IdP の token endpoint) に置換

3. **ConsentLog に書き込み** (Round 5 で既実装、本番 IdP の payload 構造に合わせて adapter を追加):
   - 同意文面 sha256 / scope / pid (HMAC) を保存

### Verify
- 同意取得 1 件 → `GET /consent/{pid}` で確認
- 取消 1 件 → `revoked_at` が NOT NULL に

---

## ⑤ Polygon mainnet + 1 区パイロット投入

### 前提
- ①-④ がすべて完了
- 都議会 / 江東区 / JPYC 株式会社 / TIS の **Founders' MoU** 締結 (M+0)

### 手順

1. **mainnet デプロイ**
   - Mumbai と同じ deploy script を mainnet に向けて実行
   - 都の treasury wallet に必要な MATIC + JPYC を入金

2. **seed 投入**
   ```bash
   curl -X POST https://pbm.metro.tokyo.lg.jp/seed
   ```
   → `prog-koto-kosodate-2026` が DB に登録される

3. **1 区パイロット 100 世帯**:
   - 江東区在住 0-18 歳子育て世帯 100 世帯にマイナンバーカード経由で OAuth 連携
   - 月 5,000 円相当の食品・日用品 PBM を発行

4. **KPI 監視 (毎日)**:
   - `GET /treasury/audit` → `healthy=True`
   - `GET /ebpm/violations` → 違反 0 件
   - `GET /ebpm/summary` → 利用率 / 平均消化日数 (4 週間後に都議会報告)

### KPI 目標 (M+4)
- 利用率 ≥ 70%
- 平均消化日数 ≤ 28 日 (= 月内消化)
- 二重支給 0 / 個情法インシデント 0

---

## 6. 緊急時対応

### Polygon RPC 停止 / チェーン障害
- **CP-6 オフライン QR フォールバック** が自動的に発動 (R3 で実装済)
- 加盟店 POS は事前配布された月次 QR を使い、復旧後に `redeemBatch` で精算

### JPYC ペッグ 1% 以上乖離
- `peg_monitor` が ALERT (R5 で実装済)
- 3% 以上で AUTO-FREEZE → SOC が手動 unfreeze

### 鍵漏洩
- 漏洩鍵を env から削除 → 即 revoke (R6 で実装済)
- 新鍵を発行・active に設定 → 旧鍵で署名された coupon は grace 期間 (90 日) で expire

### 都議会で予算停止
- `revokeProgram` を実行 → 未消化 budget を treasury に戻す
- 既発行の PBM tokens は `REVOKED` 状態に遷移 (R3 で実装済)

---

## 7. チェックリスト

本番投入前に、以下のすべてが ✓ であること:

- [ ] `bash scripts/verify.sh all` 全モード緑
- [ ] `bash scripts/verify.sh load` p95 < 200ms / fail = 0%
- [ ] PostgreSQL 移行完了 (`/treasury/migrations/status.applied` ≥ 1)
- [ ] HSM 接続完了 (`/treasury/hsm/status.backend = "pkcs11"`)
- [ ] Polygon Mumbai デプロイ完了 (block explorer で verified)
- [ ] マイナポータル v2 実 OAuth 申請 → 承認
- [ ] 都議会 + 江東区 + JPYC + TIS の MoU 締結
- [ ] CSIRT 24h 体制 (SOC ローテーション設定)
- [ ] 月次 準備金監査 cron (R3 で実装済) を本番に投入
