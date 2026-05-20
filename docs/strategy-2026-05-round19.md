# 戦略会議 #19 — Donor-PBM ピボット可否 (TAM 100x 拡張議論)

> **作成日**: 2026-05-09 (round 20)
> **議題**: Tokyo + Manila で 19 ラウンド回した PBM 基盤を、**国際寄付/募金の透明化** に拡張するか
> **背景**: ユーザーから「JICA・UN・UNICEF の募金でめっちゃ使えるんじゃない？」 という指摘 ─ 不透明資金の可視化への適合性
> **フォーマット**: red-team 風、KYC/KYB/AML を中心に叩く
> **参加**: 11 役 (既存) + 🆕 国際寄付の現場声 4 ペルソナ
> **アウトプット**: 12 件採択 (Round 21 実装、計 +20-25% コードベース)

---

## 0. 開会の問い

> Tokyo+Manila で 19 ラウンド回した PBM 基盤を、**寄付/募金の透明化** に拡張するか?
> ユーザー指摘: 「KYC と KYB が鍵。特に発展途上国の API が存在するか、AML データが正確かが課題」
> この 2 つに答えられなければピボットは **失敗確定**。

## 1. 既存 PBM の機能 → 寄付ユースケースへのマッピング

| 寄付の世界の痛点 | 既存 JPN-PBM 機能 で解 |
|----------------|--------------------|
| 「私の ¥10,000、何に使われたの？」 (完全 opaque) | on-chain `Spent` イベントで **トレーサブル** |
| 管理費 15-30% が中抜き | contract が直接 supplier に payout = 構造的不可 |
| 現地での横流し・横領 (事後監査のみ) | **CP-2 (5 段 require)** で目的外利用 物理的に不可 |
| 寄付者と受益者の断絶 | EBPM k-匿名集計で **「あなたの寄付で 12 世帯に蚊帳」** リアルタイム表示 |
| 災害時に届かない | **CP-6 v2** が文字通りこの問題 |
| 多国・多通貨対応 | JPYC/PHPC で実証済、USDC への拡張は同じ adapter |

→ **既存機能の 80% が donor 用途にそのまま流用可能**、新規追加は 20%。

## 2. 議論本体: 11 + 4 名の council

### 🆕 Sarah Chen (UNICEF Innovation Office, NY)

> 寄付者側 KYC は既存 stack で解決済、問題は **受益者側**。UNICEF が 2023 年に CryptoFund で苦労した教訓:
> - 受益者識別は地獄: 「Mali Region Kayes 1,234 世帯」と書けば書くほど現地 PII リスク
> - **解決策にしたのは集約後の HMAC** ─ JPN-PBM の k-匿名 EBPM ロジックがそのまま使える
>
> UNICEF として個別契約には 6 ヶ月のセキュリティレビュー必要、**Apache 2.0 + GitHub Actions CI 緑** はそれを 3 ヶ月に縮める。

### 🆕 James Mwangi (Africa-region AML Compliance Officer)

> KYC/KYB の地域別現実:
>
> | 地域 | KYC API | KYB API | AML data quality |
> |------|--------|--------|------------------|
> | PH (Manila) | Coins.ph / Jumio、PhilSys 制限 | SEC API、品質中 | OFAC 連携、ローカル PEP 弱 |
> | Vietnam / Indonesia / Thailand | 銀行 eKYC | 商業 (中) | 中-良 |
> | **Mali / Sub-Saharan** | **API ほぼゼロ** | 国家登録なし | OFAC/UN のみ、ローカル **皆無** |
> | Bangladesh | NID 政府専用 | 大手 NGO は MRA | 中 |
> | Yemen / Syria 紛争地 | **完全に無** | UN OCHA 管理のみ | UN consolidated のみ |
>
> 「API 無い」 ≠ 「KYC できない」、代替あり:
> 1. **携帯番号 KYC** (SIM 発行時 carrier が KYC、大半の国で義務)
> 2. **UN 既存ロスター** (UNHCR / WFP / UNICEF)
> 3. **村長/バランガイ立会** (R18 PH 設計と同じ)
> 4. **biometric** (UN IrisGuard が難民キャンプで実績)
>
> AML 名前一致のみの照合は ヨルダンの Mohammed Khan を全員ブロックする。**risk-based scoring** が必須。

### 🆕 Imran Khan (UNHCR 元 Identity Specialist)

> 難民キャンプの現実:
> - Za'atari (Jordan, Syrian 75,000 人) では **国家 ID なし**
> - **UNHCR ProGres ID** が事実上の唯一 ID (生体認証 + UN-issued)
> - WFP Building Blocks は **iris scan** で配給 ($300M+)
>
> Donor-PBM をやるなら **UNHCR ProGres と federate**、新規 ID は作らない。
> 「12 世帯に蚊帳」と書けるが、「その 12 世帯は誰か」は UNHCR にしか分からない設計が正しいプライバシー。
>
> **注意**: biometric は政治リスク (Rohingya データが Myanmar 軍に渡った 2021 年事件)。
> Donor-PBM では **biometric を contract に書かない**、pid HMAC のみ。

### 🆕 Lina Okabe (元 Refinitiv World-Check データ品質)

> AML データ精度の実数:
>
> | データソース | false positive | false negative | コスト |
> |------------|---------------|---------------|--------|
> | OFAC SDN | 30% (名前一致のみ) | 5% | 無料 |
> | UN Security Council | 25% | 8% | 無料 |
> | EU Consolidated | 28% | 10% | 無料 |
> | World-Check (Refinitiv) | **12%** advanced | 3% | $30K-100K/年 |
> | ComplyAdvantage | **10%** | 3% | $20K-80K/年 |
> | Dow Jones | 15% | 4% | $50K-150K/年 |
>
> **3 ソース cross-check (OFAC + UN + EU) で false positive を 5% に圧縮、commercial は high-value ($1000+) のみ** ─ コスト最適化。

### CSO/AML Honda (既存) 再評価

> R13 当時 (JICA 申請書 §6) の AML 評価は甘かったと認める。Donor 拡張で必須:
>
> 1. `services/kyc_adapter.py` (Jumio/Onfido/Sumsub mock + factory)
> 2. `services/aml_screening.py` (3 ソース cross-check)
> 3. `services/tier_policy.py` (tier 切替)
> 4. **FATF Travel Rule** ($3,000 以上の送金元/先暗号化)
> 5. **Sanctions evasion**: smurfing (細切れ寄付) 検知

### Legal Tanaka (既存)

> 寄付ピボットは法域爆発:
>
> | 法域 | 必要対応 |
> |------|---------|
> | 米国 | FinCEN MSB or pass-through |
> | 日本 | 資金決済法・NPO 認定 |
> | EU | MiCA / AMLD6 / PSD2 |
> | UK | FCA Money Laundering |
> | UN | UNFC, 各 agency 調達ガイド |
>
> **pass-through 構造** = 既存認定 NPO (UNICEF / WFP / Save the Children) が front-end で募金、JPN-PBM は配給インフラに徹する → **我々は VASP ライセンスを取らない**。

### Red Team Itou (既存) 厳しい質問

> Donor-PBM の本当のリスク 3 件:
>
> **R-1 透明化が受益者を危険にする** ─ Rohingya 事件。地域粒度を粗くする (国レベル) 必要
> **R-2 false positive が緊急時致命的** ─ Lina の指摘。**緊急 bypass + 事後監査** (= CP-8 新設)
> **R-3 donor 情報量 vs 受益者プライバシー** ─ 個人粒度では見せない、**k=5 → k=50** 強化

### Cost Guardian Yamada (既存)

> | 項目 | コスト |
> |------|--------|
> | 寄付者 KYC Tier 1 | $1-3 |
> | 寄付者 KYC Tier 2 + AML 3 ソース | $5-8 |
> | 受益者 (ProGres 連携) | $0 (UN 側) |
> | AML 3 ソース (OFAC+UN+EU) | $0 |
> | ComplyAdvantage (high-value のみ) | $20K-80K/年 |
> | Compliance Officer 0.5 FTE | $50K/年 |
>
> 寄付 10 万人規模 = $300K-800K compliance cost = ¥45-120M。
> 寄付額 ¥10B 規模で **0.5-1.5% overhead** → 既存 NGO の 15-30% より圧倒的に安い。

### Researcher Tanaka (既存) 国際比較

> | プロジェクト | KYC アプローチ | 我々への学び |
> |------------|--------------|------------|
> | **WFP Building Blocks** | UN ProGres + iris | federate するべき相手 |
> | Aid:Tech | 顔認証 + 国 ID | 商業化失敗 → 教訓 |
> | **GiveDirectly** | M-Pesa carrier KYC | 携帯番号 KYC が現実解 |
> | UNICEF CryptoFund | Coinbase 経由 | 受益者は別フロー |
> | Disberse (閉鎖) | 不明 | 商業ビジネス難 |
>
> 我々の defensible positioning: **WFP Building Blocks の interop layer** + **OSS + CP-6** + **個人寄付者向け UI**。

### Field Officer Pia (既存, PH 視点)

> マニラ受給者にとっては「中抜きが減って渡る額が増えれば良い」だけ。
> R18 で作った lista_adapter / barangay_endpoint は **そのまま Donor-PBM 供給側で使える** ─ 「DSWD 4Ps」を「UNICEF Mali プログラム」に名前変えただけで動く。
> **マニラ仕様の PH 設計が地球の半分の発展途上国で再利用できる** ことに気付いた。

### Engineer Endo (既存) 技術実装

> | アイテム | 工数 | R15 adapter 流用 |
> |---------|------|---------------|
> | kyc_adapter.py | 中 | ✅ |
> | aml_screening.py | 中 | ✅ |
> | tier_policy.py | 小 | 新規 |
> | donor_wallet.py | 中 | citizen 対称 |
> | donor_dashboard.py | 中 | 新規 |
> | models/donor.py + donation.py | 中 | 新規 |
> | routers/donor_oauth.py | 中 | 新規 |
> | routers/donor.py + donor_dashboard.py | 中 | 新規 |
> | frontend/donor.html (JP/EN/Tagalog) | 中 | citizen.html 対称 |
> | seed/donor/ 3 種 mock | 小 | 新規 |
> | UNHCR ProGres federate adapter mock | 中 | 新規 |
> | テスト 50+ | 中 | 新規 |
>
> 合計: コードベース **+20-25%**。

### Purpose Guardian Sasaki (既存)

> CP の Donor-PBM 再定義:
>
> | CP | Donor-PBM での意味 |
> |----|-------------------|
> | CP-2 | + donor KYC + AML clear |
> | CP-4 | + donor side k-anon + 受益者 k=50 (R-3 反映) |
> | CP-5 | + smurfing 検知 (R-1) |
> | CP-6 | UNHCR ProGres federate で難民キャンプ対応 |
> | **CP-8 (新設)** | **緊急時 AML bypass + 事後監査** (R-2 反映) |

## 3. 議論 synthesis

11 役 + 新ペルソナ 4 全員 が **ピボット YES**、ただし必須条件あり:

### 強い合意 (採用必須) DPI-1 〜 DPI-7

| ID | 内容 |
|----|------|
| **DPI-1** | UN 既存 ID (UNHCR ProGres / WFP Building Blocks) と federate、新規 ID 作らない |
| **DPI-2** | **pass-through 構造** ─ 我々は配給インフラ、front-end は既存 NPO |
| **DPI-3** | 受益者粒度 = 国レベル + k=50 集約 (R-1, R-3 反映) |
| **DPI-4** | AML 3 ソース cross-check デフォルト、commercial は high-value のみ |
| **DPI-5** | 緊急時 bypass + 事後監査 (CP-8 新設) |
| **DPI-6** | tier-based KYC: $0-50 anon, $50-1000 Tier 1, $1000+ Tier 2 |
| **DPI-7** | biometric は contract に書かない、HMAC PID のみ |

### 弱い合意

| ID | 議論点 |
|----|------|
| DPI-8 | 携帯番号 KYC (M-Pesa 型) ─ Sub-Saharan で必須、PH/JP 不要 → locale 別 adapter |
| DPI-9 | World-Check vs ComplyAdvantage ─ 予算次第 |

### 反対意見ゼロ (条件付き)

「3 つの大事故シナリオ (R-1〜R-3) を組み込まなければピボット止めるべき」 という条件は全員一致。

## 4. 採択 12 件 (Round 21 で実装)

| ID | 内容 | 工数 |
|----|------|------|
| **DP-1** | `docs/expansion-donor-pbm.md` 設計仕様書 (Round 20 で着手) | 中 |
| **DP-2** | `services/kyc_adapter.py` (mock + Jumio/Onfido/Sumsub interface) | 中 |
| **DP-3** | `services/aml_screening.py` (OFAC + UN + EU 3 ソース) | 中 |
| **DP-4** | `services/tier_policy.py` | 小 |
| **DP-5** | `services/donor_wallet.py` + `routers/donor_oauth.py` | 中 |
| **DP-6** | `services/unhcr_progres_adapter.py` | 中 |
| **DP-7** | `services/cp8_emergency_bypass.py` (CP-8 緊急 bypass) | 中 |
| **DP-8** | `frontend/donor.html` (JP/EN/Tagalog impact tracking) | 中 |
| **DP-9** | `seed/donor/{unicef-mali, wfp-yemen, jica-bangladesh}-2026.json` | 小 |
| **DP-10** | `whitepaper-2026.md` §10-12 追加: Donor-PBM 章 | 中 |
| **DP-11** | `handoff-packages/{unicef, wfp-building-blocks, unhcr}/` 3 宛先 | 小 |
| **DP-12** | テスト 50+ 本 | 中 |

## 5. ポイント精算 (#19)

| エージェント | 貢献 | 配点 |
|------------|------|------|
| **🆕 Sarah Chen (UNICEF)** | k-anon 集約 + 6→3 ヶ月レビュー短縮 | **+30 (MVP)** |
| **🆕 James Mwangi (Africa AML)** | KYC 地域別現実 + 携帯番号 KYC + risk-based | **+30 (MVP 同点)** |
| 🆕 Imran Khan (UNHCR) | ProGres federate + Rohingya 教訓 + biometric 政治リスク | +25 |
| 🆕 Lina Okabe (Refinitiv) | AML false positive 実数 + 3 ソース cross-check | +25 |
| Red Team | R-1/R-2/R-3 統合 | +20 |
| CSO/AML Honda | R13 評価の honest 自己訂正 | +15 |
| Legal Tanaka | pass-through 構造 = VASP 回避 | +15 |
| Engineer Endo | +20-25% コードベース honest 見積 | +10 |
| Cost Guardian | 0.5-1.5% overhead 試算 | +10 |
| Field Officer Pia | マニラ仕様の地球半分再利用に気付く | +10 |
| Purpose Guardian | CP-8 新設提案 | +10 |
| Researcher | 類似 5 件比較 | +5 |

**🏆 #19 MVP 同点**: **Sarah Chen + James Mwangi** ─ 国際機関 + アフリカ AML の 2 つの専門 perspective が、机上のピボット案を「動かせる設計」に変えた。

## 6. 結論

**ピボット YES** ─ DPI-1 〜 DPI-7 全実装が条件。

- Round 20 = この戦略会議 #19 議事録 + **DP-1 設計書** (`expansion-donor-pbm.md`)
- Round 21 = DP-2 〜 DP-12 実装

スコープ感:
- コードベース +20-25%
- 既存 Tokyo + Manila 19 ラウンドを **否定せず上位包含**
- TAM: ¥640B (東京) → ¥6T (日本全国) → **$50B+ (UN 人道援助)** の段階拡張

## 7. ユーザー確認事項 (Round 20 着手前)

3 つすべて **YES** 確認済:
1. ✅ DPI-1 〜 DPI-7 必須条件
2. ✅ Round 20 = 議事録 + DP-1 設計書 まで
3. ✅ 名称: **「Donor-PBM」** で採用 (Carmela 教訓 = ロマンチック化避ける名称、機能直接表現で OK)

---

→ Round 20 着手。**Round 21 で実装**。
