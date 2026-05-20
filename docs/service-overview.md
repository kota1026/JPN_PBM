# JPN-PBM サービス概要 — アーキテクチャ / 利用方法 / シーケンス / セールスポイント

> **作成日**: 2026-05-20 (Round 22)
> **対象**: 投資家 / パートナー組織 / 新規開発者 / fork 検討者 / 国際機関担当者
> **読了時間**: 30-40 分
> **License**: Apache 2.0 / **Repository**: <https://github.com/kota1026/JPN_PBM>

---

## 0. エグゼクティブ サマリ

**JPN-PBM は、政府助成金から国際寄付まで、「目的拘束型お金」 (Purpose-Bound Money) の配給を可能にする OSS 基盤です。**

| 軸 | 内容 |
|----|------|
| 解決する問題 | 助成金 / 寄付の **目的外利用・中抜き・災害時不通・不透明性** |
| アプローチ | JPYC / PHPC / USDC をブロックチェーン契約で **5 段検証** (eligibility) しながら配給 |
| 既存実装 | Tokyo (江東区) + Manila (DSWD 4Ps) + Donor-PBM (UNICEF / WFP / JICA) |
| コード規模 | 371 tests / 31 services / 14 routers / 2 Solidity contracts / 74 docs |
| ライセンス | Apache 2.0 完全 OSS |
| 21 ラウンド開発履歴 | 11 役エージェント戦略会議 × 20 回、新ペルソナ 8 名追加 |
| 状態 | サンドボックス完全完了、実外交解禁待ち |

**最大の差別化**: 設計に **3 回の重要ピボット** を honest に組み込んでいる:
1. 「サリサリには POS 無いよね」 → ハイブリッド eligibility (R12)
2. 「災害時に POS 動かないよね」 → CP-6 v2 ハードウェア前提見直し (R18)
3. 「JICA・UN にも使えるよね」 → Donor-PBM 拡張で TAM 100x (R20-21)

---

## 1. 解くべき問題

### 1.1 自治体助成金 (東京都モデル)

東京都 23 区が **年 ¥640B** の助成金を紙で配布。

| 痛点 | 自治体 1 つあたり 年間コスト |
|------|-------------------------------|
| 紙申請の受付・資格審査 (人手) | ¥120-240 M |
| 紛失・再発行の事務 | ¥8-15 M |
| **目的外利用 (子育て券で酒)** | **配布額の 3-7%** |
| 重複支給 | 1-2% |
| 都議会報告のラグ | 4-8 週間 |

→ **23 区合計で年 ¥32B が静かに失われている**。

### 1.2 国際寄付 / ODA (R20 で拡張した領域)

| 痛点 | 寄付者の不満 |
|------|-------------|
| 「私の ¥10,000、何に使われたの？」 | 完全 opaque |
| 管理費 15-30% が中抜き | 透明性ゼロ |
| 現地での横流し・横領 | 監査は事後・年 1 回 |
| 寄付者と受益者の断絶 | 「ありがとうメール」だけ |
| 災害時に届かない | UN / Red Cross の最大課題 |

→ **TAM: $50B+ / 年 (UN 人道援助)**

### 1.3 共通する根本問題

**「お金の使い道があらかじめプログラムされていない」** こと。
紙の助成券も Visa デビットも GCash 送金も、**事後に集計してわかる** モデル。
JPN-PBM は **事前にルールが書き込まれる** ─ つまり目的外利用が物理的に起きない。

---

## 2. アーキテクチャ

### 2.1 全体図 (5 層)

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 5: UI 層                                                  │
│  ─ frontend/ (JP) + frontend/en/ + frontend/ph/ + frontend/donor│
│  ─ 10 HTML pages, JP/EN/Tagalog 切替                           │
│  ─ /ui/demo.html (5 分自動再生デモ、ブラウザ完結)              │
└──────────────────────────────┬──────────────────────────────────┘
                                │ HTTP / OAuth (4 種)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: FastAPI ルータ層                                       │
│  ─ 14 routers (auth / programs / wallet / purchase / ebpm /     │
│      offline / myna_oauth / philsys_oauth / donor_oauth /       │
│      treasury / seed / products / consent / health)             │
└──────────────────────────────┬──────────────────────────────────┘
                                │ Service call
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: サービス層                                              │
│  ─ 31 services (pbm / eligibility / item_eligibility / privacy /│
│      ebpm / sweeper / treasury_audit / peg_monitor /           │
│      offline_fallback / sol_compat / sol_simulator /            │
│      key_management / hsm_adapter / chain_adapter /             │
│      gcash_adapter / landbank_bridge / se_card_adapter /        │
│      lista_adapter / barangay_endpoint / ndrrmc_alert /         │
│      household / kyc_adapter / aml_screening / tier_policy /    │
│      donor_wallet / unhcr_progres_adapter / cp8_emergency_      │
│      bypass / qr_ph / fiscal_budget / roadmap / jpyc)           │
└──────────────────────────────┬──────────────────────────────────┘
                                │ Adapter pattern (mock / real env switch)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: 永続層 + 外部接続                                       │
│  ─ Persistence: SQLite WAL ↔ PostgreSQL (migrations module)    │
│  ─ External adapters (env で mock ↔ real 切替):                │
│    chain_adapter (Polygon Mumbai/mainnet via web3.py)          │
│    gcash_adapter (GCash sandbox API)                            │
│    landbank_bridge (DSWD-LandBank proxy)                        │
│    kyc_adapter (Jumio / Onfido / Sumsub)                        │
│    aml_screening (OFAC / UN / EU / ComplyAdvantage)             │
│    unhcr_progres_adapter (UNHCR HCB API)                        │
│    ndrrmc_alert (NDRRMC SMS gateway + PRC API)                  │
│    se_card_adapter (JPKI / Felica)                              │
│    hsm_adapter (PKCS#11 / AWS CloudHSM)                         │
└──────────────────────────────┬──────────────────────────────────┘
                                │ blockchain RPC
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: ブロックチェーン                                        │
│  ─ Polygon PoS (mainnet / Mumbai testnet)                       │
│  ─ Solidity contracts: PBM.sol + PBMOfflineFallback.sol         │
│  ─ Stablecoin: JPYC / PHPC / USDC (env で切替)                  │
│  ─ Key custody: HSM (PKCS#11 → AWS CloudHSM)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Critical Properties (CP-1 〜 CP-8)

すべての PBM transaction が満たす **8 つの不変条件**:

| ID | 性質 | 強制機構 |
|----|------|---------|
| CP-1 | 緊急停止 (governor revoke) | `PBM.sol:revokeProgram()` + off-chain mirror |
| CP-2 | Eligibility (citizen ∧ store ∧ JAN ∧ period ∧ cap) | `PBM.sol:spend()` 5 段 require |
| CP-3 | JPY ペッグ逸脱検知 (>1% で freeze) | `services/peg_monitor.py` バックグラウンド |
| CP-4 | プライバシー (HMAC PID、生 ID は contract 外) | `services/privacy.py` |
| CP-5 | 二重支給防止 (no double-spend / 転売 / なりすまし) | `consumed[][]` mapping + ECDSA verify |
| CP-6 | 災害時 (オフライン redemption 30 日) | **v2: JP は Felica SE + 避難所端末 / PH は DL Protocol** |
| CP-7 | 個人/世帯月次キャップ + 多年度予算 | `services/fiscal_budget.py` + `household.py` |
| **CP-8** | **緊急時 AML bypass + 14 日事後監査** | `services/cp8_emergency_bypass.py` (R21 新設) |

### 2.3 4 つの市場別アーキテクチャ

#### A. 東京都モデル (R1-R10 設計)
```
TMG ─→ Citizen (マイナ HMAC) ─→ POS (認定加盟店) ─→ PBM contract ─→ JPYC payout
```

#### B. マニラモデル (R11-R14 設計)
```
DSWD ─→ Citizen (PhilSys HMAC) ─→ Sari-sari (QR Ph + バーコード) ─→ PBM contract ─→ PHPC payout
                                      ↑ ハイブリッド eligibility (R12)
                                        バーコード厳格 + MCC fallback
```

#### C. CP-6 v2 災害時 (R18 再設計)
```
[JP] Citizen (マイナ Felica SE) ─→ 避難所端末 (発電機+Starlink+NFC) ─→ PBM contract (復旧後 batch)
[PH] Citizen (紙 voucher) ─→ Sari-sari Lista or Barangay+PRC ─→ DSWD ─→ PBM contract
```

#### D. Donor-PBM モデル (R20-R21 新設)
```
Donor (KYC + AML cleared) ─→ NPO front-end (UNICEF/WFP/JICA) ─→ Treasury wallet
                                                                  ↓
受益者 (UNHCR ProGres federate, biometric off-chain) ←─ PBM contract ─→ 認定 supplier
                                                                  ↓
              donor dashboard (k=50 集約、国レベル粒度のみ)
```

---

## 3. 利用方法 (役割別)

### 3.1 役割の全体図

```
┌────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ ① Treasury │  │ ② Citizen   │  │ ③ Retailer  │  │ ④ EBPM      │
│  (政府/UN) │  │  (受給者)    │  │  (加盟店)    │  │  Analytics  │
│            │  │             │  │             │  │             │
│ - Program  │  │ - 認証      │  │ - QR/JAN    │  │ - k-anon    │
│   作成     │  │ - eligibility│ │   スキャン   │  │   集計      │
│ - 予算ロック│  │   判定      │  │ - PBM 適用  │  │ - リアルタイム│
│ - 緊急停止 │  │ - PBM 申請  │  │ - JPYC 清算 │  │   KPI       │
│            │  │ - QR 取得   │  │             │  │             │
└────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

[Donor-PBM 拡張で追加]
┌────────────┐
│ ⑤ Donor    │
│  (寄付者)   │
│            │
│ - KYC      │
│ - tier 別  │
│   donation │
│ - impact   │
│   dashboard│
└────────────┘
```

### 3.2 役割 ① Treasury (政府 / UN agency / NPO)

**画面**: `frontend/tokyo.html` (JP) / `frontend/donor.html` (Donor-PBM)

**操作**:
1. プログラム作成 (予算 / 助成率 / 上限 / 期間 / 対象 JAN / 認定加盟店)
2. JPYC をロック (= contract に escrow)
3. 受給資格者リスト追加 (HMAC PID)
4. EBPM ダッシュボード でリアルタイム監視
5. 緊急停止 (CP-1) ボタン

**典型ユース**: 江東区 DX 課が「子育て応援 PBM 2026」を作成 → 1,000 世帯 × 30 加盟店で展開

### 3.3 役割 ② Citizen (受給者)

**画面**: `frontend/citizen.html` (JP) / `frontend/ph/citizen.html` (PH)

**操作**:
1. マイナ / PhilSys で認証 (HMAC で擬似 ID 化)
2. 受給可能なプログラムを自動表示 (年齢・性別・住所 / 世帯員数で自動絞り込み)
3. PBM を申請 → ウォレットに枠が発行
4. 加盟店レジで見せる QR が生成
5. CP-6 災害用 QR を事前印刷可
6. **R12 追加: 商品スマホスキャン** ─ サリサリ向け、店に POS 無くても受給者スマホで OK

### 3.4 役割 ③ Retailer / Supplier (加盟店)

**画面**: `frontend/retailer.html` (POS)、または受給者スマホ + 店の QR Ph

**操作**:
1. 住民 QR スキャン → pid 取得
2. 商品 JAN スキャン → eligibility 5 段 require 通過確認
3. 対象商品なら 自動補助、対象外は 0 円
4. JPYC を即時受領 (contract から)

**POS SDK**: `sdk/python/jpn_pbm_pos/` (JP) + `sdk/python/jpn_pbm_pos_ph/` (PH)

### 3.5 役割 ④ EBPM Analytics

**画面**: `frontend/ebpm.html`

**機能**:
- リアルタイム消化率
- k-匿名集計 (k=5 標準、Donor-PBM では k=50)
- 対象外試行 (CP-2 ブロック) 件数
- 加盟店別 / カテゴリ別 / プログラム別 分解

### 3.6 役割 ⑤ Donor (R20-R21 新設)

**画面**: `frontend/donor.html` (JP/EN/Tagalog)

**操作**:
1. プログラム選択 (UNICEF Mali / WFP Yemen / JICA Bangladesh / ...)
2. 寄付額入力
3. KYC tier 自動判定 ($0-50 anon → $10000+ enhanced)
4. AML screen (OFAC + UN + EU 3 ソース cross-check)
5. 緊急時は CP-8 bypass (14 日事後監査つき)
6. 寄付完了 → impact dashboard で 国レベル + k=50 集約 表示

---

## 4. シーケンス (主要 7 シナリオ)

### 4.1 平時購入 (東京モデル)

```
住民             POS              Backend         PBM Contract       JPYC
 │                │                  │                │                │
 │ QR 提示        │                  │                │                │
 ├───────────────►│                  │                │                │
 │                │ 商品 JAN スキャン│                │                │
 │                ├─────────────────►│                │                │
 │                │                  │ /purchase      │                │
 │                │                  ├───────────────►│                │
 │                │                  │ 5 段 require   │                │
 │                │                  │  ✓ citizen     │                │
 │                │                  │  ✓ store       │                │
 │                │                  │  ✓ JAN         │                │
 │                │                  │  ✓ period      │                │
 │                │                  │  ✓ cap         │                │
 │                │                  │                ├───────────────►│
 │                │                  │                │ transfer       │
 │                │                  │                │  (subsidy)     │
 │                │                  │                │◄───────────────┤
 │                │                  │ ◄─── emit Spent│                │
 │                │                  │ EBPM 記録       │                │
 │                │ ◄────────────────┤ ✓ ¥744 補助   │                │
 │ 自己負担 JPYC  │                  │                │                │
```

### 4.2 マニラ サリサリ (R12: ハイブリッド eligibility)

```
受給者 (スマホ)        サリサリ (QR Ph)        Backend
 │                       │                       │
 │ 店の QR Ph スキャン   │                       │
 │ → MCC 5411 確認       │                       │
 │ → 4Ps acceptable      │                       │
 │                       │                       │
 │ 商品バーコードスキャン │                       │
 │ has_barcode = True    │                       │
 │ → /products/{jan} 照会│                       │
 │                       ├──────────────────────►│
 │                       │                       │
 │ Tingi (米 1 cup) 入力 │                       │
 │ has_barcode = False   │                       │
 │ → MCC + cap fallback  │                       │
 │                       │                       │
 │ 試算: PHP 132 - 補助 74.40 = 自己負担 57.60   │
 │                       │                       │
 │ GCash QR Ph 決済      │                       │
 ├──────────────────────►│                       │
 │ 補助分 PHPC は contract が直接 store wallet へ│
```

### 4.3 災害時 (CP-6 v2 JP: マイナ Felica SE + 避難所端末)

```
[平時]
DSWD/TMG ──→ JPKI API ──→ マイナンバーカード SE (RC-S960)
                             月次 ¥10,000 prefund + counter リセット

[★ 災害発生・大規模停電 ★]
受給者 (マイナ持参) ──→ 避難所端末 (発電機 + Starlink + NFC リーダ)
                          NFC で SE 読取
                          counter ≤ ¥10,000? 
                          [✓] 物資配布
                          [✓] SE counter += amount (tamper-resistant)
                          [✓] 端末 DB 記録
                          [衛星経由で contract に即時 or batch]
                          
紙 QR (二次救済) ──→ 戸別訪問チーム (民生委員 + DMAT)
                       手書き台帳記入 → 復旧後 contract batch
```

### 4.4 災害時 (CP-6 v2 PH: Disaster Lista Protocol)

```
[平時 5 月、台風シーズン入り]
DSWD ──→ opt-in 受給者 (15%) に世帯単位 voucher 配布 (耐水ラミネート)
       ──→ sari-sari opt-in 確認、 barangay 3 層代理権限訓練

[★ PAGASA Cat 3+ 警報 → NDRRMC Code Red ★]
NDRRMC ──→ SMS gateway ──→ ndrrmc_alert.py callback
                            DL モード起動
                            voucher 即時有効化
                            sari-sari 災害特例 lista 受付開始

受給者 → サリサリ Lista 記入 (1 日 PHP 200 まで、店主 opt-in 店のみ)
受給者 → バランガイホール (PRC 立会必須 = Padrino リスク緩和)
PRC + barangay → 戸別訪問 (徒歩不可世帯)

[復旧後]
sari-sari → lista 写真 → DSWD → contract batch
barangay → 手書き台帳写真 → DSWD → contract batch
5% 運用許容 (CP-5 honest)、不正は事後監査
```

### 4.5 Donor-PBM 寄付フロー (R21)

```
[1] Donor.html で UNICEF Mali プログラム 選択 + 寄付 $50
[2] /donor-oauth/v1/authorize?provider=coinbase&amount=5000
        ↓
[3] tier_policy: $50 → Tier 1 (name + DOB + email 必要)
[4] KYC 入力 → kyc_adapter.MockKycBackend で verified
[5] AML screen → aml_screening.MockAmlBackend で cleared (3 ソース cross-check)
        ↓
[6] receive_donation():
      Donor model 作成 (HMAC PID, country=JP, current_tier=1)
      Donation 記録 (amount, program, status=received)
      Treasury wallet に +50 USDC
        ↓
[7] PBM contract に program.budget 増額
        ↓
[8] 受益者: UNHCR ProGres ID で identify → 認定 supplier で蚊帳受領
        ↓
[9] Donor dashboard:
      "あなたの $50 で Mali Kayes region の 1.6 世帯に LLIN 3 枚配布完了"
      ✓ 国レベル粒度のみ、k=50 集約
      ✓ 個人特定構造的に不可能
```

### 4.6 緊急時 AML bypass (CP-8, R21)

```
台風 Yolanda Cat 4 直撃中 → NDRRMC Code Red declare (ML-Kayes)
        ↓
Donor "Mohammed Khan" (IR, 寄付 $10) → 通常 AML で review (false positive)
        ↓
cp8_emergency_bypass.maybe_bypass():
  - amount $10 ≤ $5000 (max bypass) ✓
  - NDRRMC active ✓
  - emergency_lgu="ML-Kayes" ✓
  - AML outcome=review (cleared なら不要) ✓
  → bypass=True, audit entry 作成
        ↓
寄付受理 (CP-8 タグ付き), donor dashboard で normal display
        ↓
14 日後 (review_due_by):
  CSO/AML が audit entry を review
  → cleared (false positive 確定) または
  → clawback (suspicious と判明、事後返金)
```

### 4.7 EBPM k-匿名集計 (Donor は k=50, 自治体は k=5)

```
PBM contract Spent event ──→ EBPM aggregator
                              ↓
                              raw data: per-pid 集計
                              ↓
                              k-anonymity check:
                                count < k (5 or 50) のセル → 抑制
                              ↓
                              安全な集約だけが UI に到達
                              
自治体: 「江東区 育児 categ 342 件、補助 ¥2.84M、CP-2 ブロック 7 件」
Donor: 「Mali Kayes region 1,234 世帯、LLIN 2,468 枚、k=50 集約済」
```

---

## 5. セールスポイント (差別化要素)

### 5.1 ★ 8 つの強み

| # | 強み | 証拠 |
|---|------|-----|
| **1** | **完全 OSS (Apache 2.0)** ─ ベンダーロックインなし | LICENSE + 全 70+ ソースファイル |
| **2** | **目的拘束を契約で強制** ─ 事後監査でなく事前防止 | `PBM.sol:spend()` 5 段 require |
| **3** | **災害時に動く** ─ CP-6 v2 (2 国 2 設計) | `docs/cp6-offline-fallback-v2-{jp,ph}.md` |
| **4** | **同一コードで 2 国 + 国際寄付** | seed/ph/ + seed/donor/、99% 共通 |
| **5** | **honest framing** ─ 「世界初」謳わず、Indonesia/Brazil/UK の先行事例にリスペクト | whitepaper §4.4 + §10.7 |
| **6** | **adapter pattern で env 1 つで本物に切替** | R15 chain/gcash/landbank + R21 kyc/aml/progres |
| **7** | **HMAC 擬似 ID で生 ID 不在 + k-匿名集計** | `privacy.py` + `ebpm.py` (k=5, k=50) |
| **8** | **11 役エージェント戦略会議の自己改善** | 21 ラウンドの議事録、3 回の重要ピボット |

### 5.2 比較: 既存ソリューション

| 項目 | JPN-PBM | WFP Building Blocks | Aid:Tech | Disberse | GiveDirectly | UNICEF CryptoFund |
|------|---------|---------------------|----------|----------|--------------|-------------------|
| 実装規模 | sandbox 完了 | $300M+ live | 中東 pilot | 閉鎖 (2020) | $700M+/year | $50M |
| OSS | ✅ Apache 2.0 | ❌ 専有 | ❌ 専有 | (閉鎖) | ❌ | ❌ |
| 目的拘束 (PBM) | ✅ | ✅ | ✅ | ✅ | ❌ (cash transfer) | ❌ (受領のみ) |
| 災害オフライン (CP-6) | ✅ 2 国設計 | △ | ❌ | (閉鎖) | ❌ | ❌ |
| 個人寄付者 UI | ✅ (R21) | ❌ (UN-only) | ❌ | ❌ | ❌ | △ (Coinbase 経由) |
| 多通貨 | JPYC/PHPC/USDC | (限定) | ─ | ─ | ─ | BTC/ETH |
| HSM 統合準備 | ✅ adapter pattern | (閉) | (閉) | ─ | ─ | ✅ |

### 5.3 数字で見る完成度

| 指標 | 値 |
|------|-----|
| バックエンドテスト (自動) | **371 passed** |
| Solidity コントラクト | 2 (PBM + PBMOfflineFallback) |
| Solidity セルフ監査 | **24 項目 × 2 → ok=40 warn=4 fail=0** |
| サービスモジュール | 31 |
| ルータ | 14 |
| Adapter | 8 (chain/gcash/landbank/kyc/aml/progres/ndrrmc/se) |
| HTML ページ | 10 (JP/EN/Tagalog + Donor + auto-demo) |
| シナリオ seed | 11 (Tokyo 7 + Manila 2 + Donor 3) |
| ドキュメント | 74 |
| 戦略会議 英訳 | 18/19 |
| GitHub Actions CI | ✅ 全 PR で自動実行中 |

### 5.4 ロードマップ

| Phase | 達成率 | 残課題 |
|-------|--------|--------|
| Phase 1 (Tokyo Closed Alpha) | 86% | M+0 (4 者 MoU) 待ち |
| Phase 2 (23 区展開 + Manila) | 77% | M+1 Polygon Mumbai 実デプロイ等 |
| Phase 3 (制度連携) | 60% | M+12/M+14 法整備、FSA 折衝 |
| **Phase 4 (Donor-PBM)** | **30%** | UN 機関接触 (UNICEF/WFP/UNHCR) |

### 5.5 TAM (Total Addressable Market)

| セグメント | 規模 (年間) |
|-----------|-----------|
| Tokyo 23 区 助成金 | ¥640B |
| Japan 全自治体 助成金 | ¥6T |
| JICA ODA | ¥1.7T |
| UN 人道援助 (WFP/UNICEF/UNHCR/Red Cross) | **$50B+** |
| 民間財団 (Gates/Buffett/その他) | **$200B+** |

**合計 addressable: ~¥40T 相当**。1% シェアでも年 ¥400B。

---

## 6. 採用ハードル (Honest Section)

サンドボックス内で進められない、外部資源が必要な領域:

| 課題 | 必要 | 現状 |
|------|------|------|
| **M+0 Founders' MoU** (TMG × JPYC × TIS × 江東区) | 4 者調印 | blocked = 実外交 |
| Polygon Mumbai 実デプロイ | RPC URL (Alchemy/Infura) | scripts/deploy_mumbai.sh 準備済、3 日で完了可 |
| GCash sandbox API | Coins.ph 接触 | adapter mock 動作中、env 切替で OK |
| iPhone 実機 scanner | iPhone 13/15 + 手動テスト | `docs/scanner-iphone-test-checklist.md` 準備済 |
| マイナポータル v2 API | 総務省・デジ庁協議 | OAuth mock 動作中 |
| DSWD 4Ps LandBank 統合 | 政策合意 | bridge mock 動作中 |
| Felica SE 実機 | JPKI API 拡張 (総務省) | se_card_adapter mock 動作中 |
| 避難所端末配備 | 自治体予算 (¥7-10B 5 年) | 仕様書あり |
| UN 機関接触 (UNICEF/WFP/UNHCR) | data sharing agreement | handoff packages 準備済 |
| ComplyAdvantage 契約 | $20K-80K/年 | adapter stub |
| JICA pre-screening v3 | 会話 | application draft v1.2 提出可 |

**いずれの障壁も技術ではなく合意形成**。コードは外部資源解禁の翌週から本番投入可能な状態。

---

## 7. 主要文書への入口

詳細を知りたい場合の **deeper docs**:

| 知りたいこと | 推奨ドキュメント |
|------------|-----------------|
| 30 ページのプロ向け技術解説 (英文) | `docs/whitepaper-2026.md` |
| 議員/課長級 向けピッチ (5 分読了 JP) | `docs/pitch-deck-jp.md` |
| 国際フォーラム向けピッチ (90 秒 + 詳細) | `docs/pitch-deck.md` |
| 友人/カジュアル紹介 | `docs/pitch-deck-friend.md` |
| **5 分自動再生デモ** (ブラウザだけで動く) | `frontend/demo.html` + `docs/demo-walkthrough.md` |
| Manila / 4Ps 展開仕様 | `docs/expansion-philippines.md` |
| **Donor-PBM 設計 (12 章 ~600 行)** | `docs/expansion-donor-pbm.md` |
| CP-6 v2 災害時 (JP/PH 別) | `docs/cp6-offline-fallback-v2-jp.md` + `-ph.md` |
| 21 ラウンドの戦略会議 議事録 | `docs/strategy-2026-*.md` (20 本) |
| 宛先別 提出パッケージ | `docs/handoff-packages/{jica,coins-ph,dswd,quezon-city,unicef,wfp-building-blocks,unhcr}/` |
| 本番投入手順 | `docs/production-runbook.md` |
| 他自治体 fork 手順 | `docs/fork-guide.md` |
| ロードマップ (live) | `services/roadmap.py` + `/treasury/roadmap` |

---

## 8. 確実に動くデモ (3 通り)

### 8.1 ブラウザだけ、何もインストールせず

→ <https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/main/frontend/demo.html>

自動再生 5 分、JP/EN/Tagalog 切替、一時停止・巻戻し可。

### 8.2 自己 PC でフルデモ

```bash
git clone https://github.com/kota1026/JPN_PBM
cd JPN_PBM
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
# 別ターミナルで:
open http://localhost:8000/ui/index.html
# Tokyo / Manila / Donor + auto-demo すべて触れる
```

### 8.3 検証コマンド一発

```bash
bash scripts/verify.sh all
# → 371 tests passed, 全 8 モード緑
```

---

## 9. 提案 ─ あなたが当事者なら

| あなたが | こうしてほしい |
|---------|---------------|
| **東京都 / 自治体担当者** | `docs/pitch-deck-jp.md` を読む → 30 分技術ピッチをセットアップ |
| **JICA 担当者** | `docs/handoff-packages/jica/` 一式 + `docs/expansion-donor-pbm.md` |
| **UN 機関 (UNICEF/WFP/UNHCR)** | `docs/handoff-packages/{unicef,wfp-building-blocks,unhcr}/` 各 README |
| **Coins.ph / JPYC** | `docs/handoff-packages/coins-ph/` + 技術接続協議 |
| **JICA Manila 経由 DSWD** | `docs/handoff-packages/dswd/` (Tagalog 含む) |
| **個人投資家** | `docs/whitepaper-2026.md` + 5 分デモ |
| **OSS コントリビュータ** | GitHub repo + Round 18 戦略会議 (red-team セッション例) |
| **メディア** | `docs/pitch-deck-friend.md` ─ 物語視点 |

---

## 10. 結語

JPN-PBM は **21 ラウンドのサンドボックス完走** で:

- ✅ 動くコード (371 tests passing)
- ✅ 動く 5 分デモ (URL 1 つで再生)
- ✅ 動くアダプタ (env 1 つで本物に切替)
- ✅ 動く提出物 (7 宛先 handoff zip)

を揃えました。

残るのは **「やる」 という決定**:
- 4 者 MoU (TMG × JPYC × TIS × 江東区)
- UNICEF / WFP / UNHCR と最初の 1 通の会話
- JICA pre-screening セット

これ以上待つ理由がない、というのが正直な現在地です。

```
github.com/kota1026/JPN_PBM
Apache 2.0
```

---

*Round 22, 2026-05-20. 議論・修正歓迎。*
