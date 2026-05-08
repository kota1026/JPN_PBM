# Polygon Mumbai testnet デプロイ手順 (Phase 2 移行 第 1 ステップ)

> **目的**: `contracts/PBM.sol` と `contracts/PBMOfflineFallback.sol` を **本物のチェーン (Polygon Mumbai testnet)** にデプロイし、サンドボックスから「実 RPC 互換」へ第一歩を進める。
>
> **所要時間**: 環境変数が揃えば **30 分**。揃っていなければ取得作業を含め **3 営業日**。
>
> **コスト**: ¥0 (Mumbai testnet は MATIC をフォーセットで無料取得可能)。

---

## 1. 前提条件

| アイテム | 取得方法 | 所要 |
|----------|---------|------|
| **Polygon Mumbai RPC URL** | <https://www.alchemy.com/> でアカウント作成 → "Create app" → Polygon Mumbai 選択 → HTTPS URL コピー | 5 分 |
| **Testnet wallet 秘密鍵** | `openssl rand -hex 32` でローカル生成 (本番では HSM に置く) | 1 分 |
| **Testnet MATIC** | <https://faucet.polygon.technology/> で wallet アドレスに送金依頼 (1日最大 0.5 MATIC) | 5 分 |
| **Test JPYC アドレス** | (a) JPYC 株式会社にテストネット用 token アドレスをリクエスト、または (b) 自前の MockJPYC ERC20 を deploy | 1 営業日 |
| **PolygonScan API key** (verify 用) | <https://polygonscan.com/myapikey> で取得 | 5 分 |
| **Foundry** | `curl -L https://foundry.paradigm.xyz \| bash && foundryup` | 5 分 |

## 2. 実デプロイ手順

### 2.1 環境変数を設定

```bash
export POLYGON_MUMBAI_RPC_URL="https://polygon-mumbai.g.alchemy.com/v2/YOUR_KEY"
export GOVERNOR_PRIVKEY="$(openssl rand -hex 32)"   # 本番では HSM
export JPYC_TESTNET_ADDRESS="0x..."                  # JPYC Inc. から受領
export POLYGONSCAN_API_KEY="ABC123..."               # 任意 (verify 用)
```

### 2.2 ドライチェック (オフラインで前提条件確認)

```bash
bash scripts/deploy_mumbai.sh --dry-check
```

→ 全 OK なら次へ。

### 2.3 実デプロイ

```bash
bash scripts/deploy_mumbai.sh
```

期待出力:

```
[deploy:env]      ✓ 環境変数 OK
[deploy:tooling]  ✓ forge 0.2.0
[deploy:syntax]   ✓ syntax
[deploy:audit]    ✓ audit (ok=40 warn=4 fail=0)
[deploy:build]    ✓ build
[deploy:deploy]   ✓ deploy
=== JPN-PBM Deployment ===
deployer            : 0x...
PBM deployed at     : 0x...
PBMOfflineFallback  : 0x...

✓ Polygon Mumbai deployment complete
```

**デプロイされたアドレスをメモ**。後段で backend に渡す。

### 2.4 PolygonScan で確認

`https://mumbai.polygonscan.com/address/<PBM_ADDRESS>` を開く → contract タブで verify されていれば成功。

## 3. backend 結線

`.env` に追加:

```
JPN_PBM_CHAIN_RPC=https://polygon-mumbai.g.alchemy.com/v2/...
JPN_PBM_PBM_CONTRACT=0x...
JPN_PBM_OFFLINE_CONTRACT=0x...
JPN_PBM_JPYC_CONTRACT=0x...
JPN_PBM_GOVERNOR_PRIVKEY=...    # HSM 移行までの一時運用
```

backend 側に `services/chain_adapter.py` を追加 (Round 13 以降) し、`PbmService.spend()` の中で chain にも書き込みする dual-write パスを実装する。**この段階で「サンドボックスのみ」から「サンドボックス + Mumbai testnet」へ進む**。

## 4. 戻し方 (rollback)

testnet なので失敗しても無料・無リスクですが、念のため:

```bash
# 1. backend の chain adapter を無効化
export JPN_PBM_CHAIN_ENABLED=0

# 2. スクリプト経由で revoke (必要なら)
# (Mumbai はガスフリーなので contract の destruct は不要)
```

mainnet では destruct パスを `contracts/PBM.sol:revokeProgram` で実装済 → 治験 alpha 終了時に refund 全額返金可能。

## 5. なぜ Mumbai を最初の足場にするか

| 比較 | local sandbox (現状) | **Polygon Mumbai (次)** | Polygon mainnet (Phase 2) |
|------|---------------------|------------------------|---------------------------|
| 実 RPC | ❌ Python 模倣 | ✅ alchemy/infura | ✅ alchemy/infura |
| 実 ECDSA | ✅ (Sol-compat lib) | ✅ (Sol ecrecover) | ✅ |
| 実 JPYC | ❌ ledger 模倣 | ✅ test JPYC | ✅ JPYC mainnet |
| ガスコスト | ¥0 | ¥0 (faucet) | 月 ~¥5,000 (1k 世帯規模) |
| 改ざん耐性 | ✗ (中央 DB) | ✓ (testnet) | ✓ (mainnet) |
| 失敗リスク | なし | testnet なのでなし | mainnet bug は資金損失 |
| audit 必須 | 不要 | **不要** ← ここが最大価値 | 必須 (Quantstamp 等) |

→ Mumbai での実証は **MoU 不要・JPYC 法人提携不要・audit 不要** で、サンドボックス完全脱出ができる唯一のステップ。**3 日で「本物のブロックチェーンで動いている」という事実を獲得できる**。

---

## 6. デプロイ後の自動 verify (将来拡張)

`scripts/verify.sh` に新モード `chain` を追加し、デプロイ済 contract に対して:

- `getProgram(id)` 読み取り (view)
- `couponHash(coupon)` のオンチェーン計算結果が Python `sol_compat.coupon_hash()` と一致
- `verifyCoupon(coupon, sig)` がローカル `verify_coupon_eip191()` と同じ true/false を返す

を毎日 1 回 cron で確認する。これで **Mumbai 上で本物に動き続けていること** が証明される。

実装は Round 13 以降。
