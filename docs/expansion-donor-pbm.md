# Donor-PBM Expansion Specification (DP-1)

> **Created**: 2026-05-09 (Round 20)
> **Status**: Design spec (Round 21 で実装)
> **Parent**: 戦略会議 #19 ([`strategy-2026-05-round19.md`](./strategy-2026-05-round19.md))
> **License**: Apache 2.0

---

## 0. Executive Summary

Tokyo + Manila 19 ラウンドで構築した PBM 基盤を、**国際寄付/募金の透明化** に拡張する仕様書。
既存機能の 80% を流用、新規追加は 20% (donor wallet, KYC tier, AML screening, UNHCR federate)。

**TAM 拡張**: ¥640B (東京) → ¥6T (日本全国) → **$50B+ (UN 人道援助)** 段階拡張。

**核心アイディア**: PBM の "Citizen → Retailer" モデルを **"Donor → Beneficiary"** に inversion + 受益者側に "Citizen → Supplier" を維持。

---

## 1. アーキテクチャ

### 1.1 既存 vs 新規

```
[既存 JPN-PBM]
  Treasury (TMG/DSWD) → Citizen → Retailer
                  └─ on-chain PBM contract

[Donor-PBM 拡張]
  Donor (個人/法人) → NPO/UN front-end → Treasury (= UN agency) → Beneficiary → Supplier
            ↑ KYC                              ↑                ↑              ↑
            tier-based                         (我々の責務)      既存 PBM      既存 PBM
            AML 3 ソース                       pass-through      Citizen 役    Retailer 役
            FATF Travel Rule
```

→ **PBM 配給インフラ部分 (右 3 つ) は既存実装**、**Donor 側 (左 2 つ) が新規**。

### 1.2 3 役の責務分担

| 役割 | 役 | 責務 | KYC |
|------|----|----|----|
| **Donor** (寄付者) | 個人 / 法人 / 財団 | 寄付実行 + impact tracking | tier-based (DPI-6) |
| **Front-end NPO** | UNICEF / WFP / JICA / Red Cross | 募金集め + 規制対応 | 既存 KYC pass-through |
| **Treasury** | UN agency / NPO / 我々 (configurable) | 寄付集約 + PBM 発行 | (pass-through) |
| **Beneficiary** (受益者) | 受給世帯 / 難民 | 既存 Citizen 役 (R19 household 単位) | **UNHCR ProGres federate** (DPI-1) |
| **Supplier** | 認定卸 / 加盟店 | 既存 Retailer 役 | **KYB** (DPI 範囲外、既存) |

### 1.3 既存コードの再利用

| 既存 (R1-R19) | Donor-PBM での利用 |
|--------------|-------------------|
| `services/pbm.py` | そのまま配給ロジック |
| `services/eligibility.py` + `item_eligibility.py` | そのまま |
| `services/privacy.py` | HMAC PID/世帯 ID 派生 |
| `services/ebpm.py` (k-anon) | **k=5 → k=50 に強化** (DPI-3) |
| `services/treasury_audit.py` | governor 監査 (Treasury = UN agency) |
| `services/sweeper.py` | 期限切れ寄付の残高返却 |
| `contracts/PBM.sol` | そのまま |
| `contracts/PBMOfflineFallback.sol` | 災害時 (UNHCR ProGres + ECDSA) |
| `services/chain_adapter.py` | Polygon multi-token (JPYC/PHPC/USDC) |
| `services/landbank_bridge.py` | 拡張: 一般 NPO bridge interface |

---

## 2. 5 シナリオ ─ 具体的ユースケース

### 2.1 UNICEF Mali Mosquito Net Program

```
Donor: 個人 X が UNICEF Japan に ¥10,000 寄付
  ↓ Coinbase / PayPal KYC (Tier 1)
UNICEF Japan: ¥10,000 → USDC ¥9,800 (FX マージン) → Treasury wallet
  ↓
Treasury: prog-unicef-mali-llin-2026 program create
  - eligible_jans: {LLIN 蚊帳 GS1 4 種}
  - eligible_beneficiaries: UNHCR ProGres roster (Mali region Kayes, 5歳以下児童世帯)
  - approved_suppliers: 5 認定卸
  - subsidy_bps: 10000 (100% 補助 = 全額 補填)
  - per_household_cap: USDC 30
  - eligibility_mode: hybrid
  - start_at / end_at: 雨季 5-9 月
  ↓
受益者: ProGres ID 提示 → 認定卸で LLIN を受領
                          → PBM contract が USDC を卸に送金
                          → consumed mapping 更新
  ↓
個人 X の Dashboard (24h 以内更新):
  「あなたの ¥10,000 (USDC 65 相当) で、Mali Kayes region の 3.3 世帯に LLIN 2 枚ずつ配布完了」
  + 国レベル集約のみ (R-1: 地域粒度を粗く)
  + k=50 集約 (R-3)
```

### 2.2 WFP Yemen Food Distribution

```
Donor: 米国 個人 / 法人複数  →  WFP Building Blocks (既存 $300M+ 動作)
                                  ↓ federate (DPI-1)
                              Donor-PBM の bridge adapter
                                  ↓
受益者: Yemen 難民 (UNHCR ProGres iris)
                                  ↓
Supplier: WFP の認定食料配給 cooperative
                                  ↓
                              donor X が「私の ¥5,000 が Yemen 6 世帯に食料」と見える
                              ただし個人粒度では見えない (k=50 + 国レベル)
```

### 2.3 JICA Bangladesh School Program

```
Donor: 日本国民 (税金 = JICA ODA 経由)  →  JICA Treasury
                                              ↓
                                          prog-jica-bangladesh-school-2026
                                              ↓
受益者: Bangladesh 小学生世帯 (NID + 携帯 KYC)
Supplier: Bangladesh 認定書店 + 文房具屋
                                              ↓
                                          tax-payer dashboard:
                                          「JICA ODA ¥1.7T の使途を見る」
                                          (国会報告書代替、リアルタイム)
```

### 2.4 個人寄付者 + 災害緊急 (台風 / 地震)

```
台風 Yolanda Cat 5 → NDRRMC Code Red
  ↓ services/ndrrmc_alert.py (既存 R18)
  ↓
緊急 PBM mode 起動:
  - 寄付者の Tier 0 (anon) 上限を $50 → $200 に一時拡大
  - **CP-8 (新設): AML bypass + 事後監査** (Yemen の Khan さん救済 ロジック)
  - 受益者粒度: 個人寄付者は dashboard で「PH 全土の被災 12K 世帯に配布中」
  ↓ 復旧後
  CP-8 audit log を 全件 review、suspicious tx は事後返金
```

### 2.5 既存 Tokyo + Manila との共存

```
Tokyo TMG / DSWD は Treasury 役 (既存通り)、Donor 拡張は **option 機能**
  ↓
TMG が「江東区プログラム + 国際寄付者からの追加 funding」を受け入れる場合
  ─ 同じ prog-koto-kosodate-2026 に外部 donor が contribute
  ─ Treasury の budget が動的に膨らむ仕組み (programs.budget_jpy が増加)
  ─ 江東区民は普段通り、Tokyo PBM を使うだけ
```

---

## 3. KYC Tier Policy (DPI-6)

### 3.1 寄付者 (Donor) 側

| Tier | 寄付額 | KYC | AML | コスト | UX |
|------|--------|-----|-----|--------|-----|
| **0 Anon** | $0-50 | なし | OFAC のみ (名前-only) | $0 | クリック決済、即時 |
| **1 Light** | $50-1000 | 氏名 + DOB + email | OFAC + UN + EU 3 ソース | $1-3 | フォーム入力 3 分 |
| **2 Full** | $1000-10000 | photo ID + biometric (Jumio) | + commercial provider | $5-8 | 5-10 分、24h レビュー |
| **3 Enhanced** | $10000+ | + source of wealth + 法人実体確認 | + FATF Travel Rule | $15-30 | 1-3 日、人手 review |

### 3.2 受益者 (Beneficiary) 側

| シナリオ | KYC method | コスト |
|---------|-----------|--------|
| **PH 4Ps 受給世帯** | 既存 PhilSys + バランガイ立会 (R18 PH 設計流用) | $0 (DSWD ロスター) |
| **JP 江東区** | マイナンバー + JPKI (既存) | $0 (TMG ロスター) |
| **Mali / Sub-Saharan** | **UNHCR ProGres federate** + 携帯番号 KYC | $0 (UN 側) |
| **Bangladesh** | NID 政府専用 API (経由は MRA 大手 NGO) | $0 |
| **Yemen / Syria 難民** | **UNHCR ProGres iris** のみ | $0 (UNHCR 側) |
| **紛争地・無 ID** | **村長/Community attestation** + 写真 (R18 PH 設計の Tagalog 流用) | $0 |

### 3.3 Supplier 側 (KYB)

| 規模 | KYB method | コスト |
|------|-----------|--------|
| 大手 (Mercury Drug, SM, Coca-Cola Mali) | SEC / 国家登録 + DUNS number | $0-100 |
| 中小サリサリ | バランガイキャプテン立会 + 写真 (R18 lista_adapter 流用) | $0 |
| UN 認定 NGO | UN-OCHA Sphere 認定 | $0 |

---

## 4. AML Screening (DPI-4)

### 4.1 デフォルト: 3 ソース cross-check (無料)

```python
# services/aml_screening.py の擬似コード
def screen(*, full_name: str, dob: date, country: str) -> ScreeningResult:
    hits = []
    hits += check_ofac_sdn(full_name, dob)        # 米国 OFAC
    hits += check_un_consolidated(full_name, dob) # UN Security Council
    hits += check_eu_consolidated(full_name, dob) # EU Consolidated
    
    # risk-based: 単純名前一致だけでは reject しない
    score = risk_score(hits, full_name, dob, country)
    if score >= THRESHOLD_AUTO_REJECT:
        return ScreeningResult.rejected(hits, reason="multi-source PEP confirmed")
    if score >= THRESHOLD_MANUAL_REVIEW:
        return ScreeningResult.review_queue(hits)
    return ScreeningResult.cleared()
```

3 ソース cross-check で false positive を **30% → 5%** に圧縮 (Lina 試算)。

### 4.2 High-value: Commercial provider 上乗せ

寄付額 $1000+ は **ComplyAdvantage / World-Check** に escalate:

```python
if donation_amount_usd >= 1000:
    enhanced = commercial_provider.check(donor)  # +$5-8/check
    if enhanced.has_pep_match:
        return ScreeningResult.review_queue([...])
```

予算: 寄付額の **0.5-1.5% overhead** に収まる (Cost Guardian 試算)。

### 4.3 CP-8 緊急 bypass (DPI-5)

```python
# services/cp8_emergency_bypass.py
def screen_with_emergency_override(
    *, donor: Donor, donation_amount_usd: int, 
    ndrrmc_active: bool, emergency_lgu: str | None,
) -> ScreeningResult:
    # 通常チェック
    normal = aml_screening.screen(donor)
    if normal.is_cleared():
        return normal
    
    # 災害時の AML reject は緊急監査キューへ
    if ndrrmc_active and emergency_lgu and donor.lgu == emergency_lgu:
        emergency_audit_log.append({
            "donor_hash": donor.hmac_pid,
            "amount_usd": donation_amount_usd,
            "screening_hits": normal.hits,
            "bypass_reason": f"NDRRMC Code Red active in {emergency_lgu}",
            "review_due_by": datetime.now() + timedelta(days=14),
        })
        return ScreeningResult.cleared_with_audit(normal.hits)
    return normal
```

復旧後 14 日以内に **CSO/AML が全件 review**、suspicious tx は事後返金。

---

## 5. UNHCR ProGres Federation (DPI-1)

### 5.1 アーキテクチャ

我々は **新規 ID システムを作らない**。UNHCR ProGres が既に持つ:
- 7,500 万人の難民 + IDP 登録
- iris/finger biometric (UN IrisGuard)
- name + DOB + family composition
- UN agency 間で共有可能 (WFP/UNICEF も読める)

→ Donor-PBM は **ProGres から HMAC pid を派生** するだけ。

### 5.2 federate adapter (R21 実装)

```python
# services/unhcr_progres_adapter.py
class UnhcrProGresBackend(Protocol):
    def resolve_household(self, *, progres_id: str) -> HouseholdInfo: ...
    def check_active_status(self, *, progres_id: str) -> bool: ...
    def get_eligibility_country(self, *, progres_id: str) -> str: ...

class MockUnhcrProGresBackend:
    # Round 21 mock、Yemen/Syria/Mali テスト用 5-10 family
    ...

class RealUnhcrProGresBackend:
    # UNHCR HCB API (data sharing agreement 締結後)
    # R22+ 実外交解禁待ち
    ...
```

### 5.3 Privacy considerations

- ProGres ID は **HMAC で 即座 pseudonymize**、生 ID は contract に渡さない
- **biometric は contract に書かない** (DPI-7 / Rohingya 教訓)
- 地域粒度は **国レベルのみ** (R-1: Rohingya 事件回避)

---

## 6. Pass-through 構造 (DPI-2)

### 6.1 我々は何で、何でないか

| 我々は... | 我々は ... ではない |
|---------|--------------------|
| ✅ 配給インフラ (PBM contract + UI) | ❌ VASP (Virtual Asset Service Provider) |
| ✅ 透明化レイヤー (impact dashboard) | ❌ MSB (Money Service Business) |
| ✅ OSS reference implementation | ❌ 認定 NPO |
| ✅ 既存 NPO の wrapper API 提供 | ❌ 直接募金集める法人 |

### 6.2 front-end NPO の役割

| 役割 | 担当 |
|------|------|
| 寄付者 KYC | NPO (Coinbase / PayPal pass-through 含む) |
| AML 1 次審査 | NPO |
| 寄付金 受領・暫定保管 | NPO の認定 wallet |
| Treasury への送金 (PHPC/JPYC 等に変換) | NPO |
| 受益者選定 (4Ps roster / UNHCR ProGres) | NPO (UN agency) |
| 配給実行 (PBM contract 操作) | **我々の領域 (= 既存 Tokyo + Manila 実装)** |
| 寄付者への impact 報告 | **我々の領域 (donor_dashboard.py)** |
| 規制対応 (VASP / MSB / FATF) | NPO (我々は外側) |

→ **我々は 4 者 (寄付者 / NPO / 受益者 / supplier) の "プロトコル仲介"** だが **法人実体としては関与しない**。

### 6.3 法的 boundary

| 国 | 我々の status | NPO の status |
|----|--------------|--------------|
| 日本 | OSS 提供者 (民法上の創作物のみ) | 公益認定 NPO / JICA |
| 米国 | software developer (DMCA 保護) | 501(c)(3) |
| EU | open source contributor | charity registered |
| UN | implementer (UN procurement Tier 3) | host agency |

→ **VASP / MSB / FATF 規制は NPO 側に帰属**。我々は **OSS リポジトリ + spec** のみ。これにより 法令爆発を回避。

---

## 7. CP-1 〜 CP-8 整合性

| CP | 既存定義 | Donor-PBM での意味 |
|----|---------|-------------------|
| CP-1 緊急停止 | governor.revokeProgram() | UN agency の Treasury role で同じ |
| CP-2 eligibility | citizen + store + JAN + period + cap | **+ donor KYC tier + AML clear** |
| CP-3 peg | JPYC ±1% | + USDC / EURC peg monitor 追加 |
| CP-4 privacy | HMAC PID | **+ k=50 集約 (R-3)** + **biometric off-chain (DPI-7)** |
| CP-5 二重支給 | consumed mapping | **+ smurfing 検知 (R-1)** |
| CP-6 災害 | JP A+E / PH DL Protocol | **+ UNHCR ProGres federate** (Yemen 等紛争地) |
| CP-7 cap | 月次 per_citizen | **per_household_per_program_per_country** (世帯 + プログラム + 国の 3 軸) |
| **CP-8 (新設)** | ─ | **緊急時 AML bypass + 14 日以内 事後監査** (R-2 反映) |

---

## 8. 既存類似プロジェクトとの honest 比較

| プロジェクト | 強み | 弱み | 我々との差 |
|------------|------|------|----------|
| **WFP Building Blocks** | $300M+ 実績、UN 公式 | 専有、UN agency only | **OSS + 個人寄付者 UI + CP-6** |
| Aid:Tech (Ireland) | 中東難民 KYC 実績 | 商業化失敗 | OSS = 失敗してもコミュニティで継続 |
| Disberse (UK, 閉鎖) | 早期 mover | 2020 年 BCP 限界で閉鎖 | NPO 依存ではなく community 駆動 |
| **GiveDirectly** | $700M+/年、M-Pesa | crypto/blockchain なし | **on-chain transparency** + 多通貨 |
| UNICEF CryptoFund | $50M、UN 公式 | 受け取りのみ、PBM 機能なし | **purpose binding** + 受益者 dashboard |
| GiveCrypto (Brian Armstrong) | 2018-2022 運営 | 個人主体で持続性なし | 機関連携設計 |

→ **我々の defensible positioning**:
1. **Apache 2.0 完全 OSS** (Building Blocks / Aid:Tech はそれぞれ専有)
2. **CP-6 災害 fallback v2** (どのプロジェクトも持たない)
3. **2 国 codebase 共用** (JP + PH) で国際 NPO の fork コスト最小
4. **個人寄付者 dashboard** (Building Blocks にない、Donor 拡張の核)
5. **honest framing** (「世界初」謳わない、Building Blocks にリスペクト)

---

## 9. Risks (R-1, R-2, R-3 の正式記録)

### R-1: 透明化が受益者を危険にする (Rohingya 教訓)

| 場面 | リスク | 緩和策 |
|------|------|------|
| 「Sahel 地域 100 世帯に配給」 公開 | 武装勢力に援助先教える | **国レベルまで粒度を粗くする** |
| 個人レベル location 公開 | 同上 | **k=50 集約** (UNICEF 慣行) |
| biometric on-chain 記録 | Myanmar 軍が読む | **HMAC のみ contract 書込み、biometric off-chain** (DPI-7) |

### R-2: false positive が緊急時致命的 (Lina 警告)

| 場面 | リスク | 緩和策 |
|------|------|------|
| AML 名前-only 一致で病院支援拒否 | 子供死亡 | **3 ソース cross-check + risk-based score** |
| 緊急時 (台風中) の AML reject | 救命遅延 | **CP-8 緊急 bypass + 14 日事後監査** |
| 重複なし wallet からの細切れ寄付 | sanctions evasion (smurfing) | smurfing 検知ヒューリスティック |

### R-3: Donor の知りたさと受益者プライバシーの衝突

| 場面 | リスク | 緩和策 |
|------|------|------|
| 「あなたの $50 が誰に行ったか具体的に教えて」 | 個人特定 | **k=50 + 国レベル のみ** |
| 受益者からの「私の状況を知らされたくない」 | 尊厳侵害 | opt-out 機能 (donor 視点では unattributed と表示) |
| donor 側の悪意ある "追跡" (stalking risk) | DV / 暴力リスク | donor は **集約のみ閲覧可** (UI 制限) |

---

## 10. 実装ロードマップ

### Round 21 (Donor-PBM 実装)

| ID | 内容 | 工数 | 状態 |
|----|------|------|------|
| DP-2 | `kyc_adapter.py` (mock + Jumio/Onfido/Sumsub interface + factory) | 中 | 未着手 |
| DP-3 | `aml_screening.py` (3 ソース cross-check + ComplyAdvantage pluggable) | 中 | 未着手 |
| DP-4 | `tier_policy.py` (寄付額別 KYC tier) | 小 | 未着手 |
| DP-5 | `donor_wallet.py` + `routers/donor_oauth.py` (Coinbase/PayPal mock) | 中 | 未着手 |
| DP-6 | `unhcr_progres_adapter.py` (受益者 federate mock) | 中 | 未着手 |
| DP-7 | `cp8_emergency_bypass.py` (CP-8 + 14 日監査) | 中 | 未着手 |
| DP-8 | `frontend/donor.html` (JP/EN/Tagalog impact tracking) | 中 | 未着手 |
| DP-9 | `seed/donor/{unicef-mali, wfp-yemen, jica-bangladesh}-2026.json` | 小 | 未着手 |
| DP-10 | `whitepaper-2026.md` §10-12: Donor-PBM 章 | 中 | 未着手 |
| DP-11 | `handoff-packages/{unicef, wfp-building-blocks, unhcr}/` 3 宛先 | 小 | 未着手 |
| DP-12 | テスト 50+ 本 | 中 | 未着手 |

### Round 22+ (実外交解禁待ち)

- UNHCR ProGres API 実接続 (data sharing agreement)
- ComplyAdvantage / World-Check 実契約
- WFP Building Blocks との interop 提案
- UNICEF Innovation Office との 3 ヶ月 security review
- JICA pre-screening v3 改訂

---

## 11. 成功判定 (1 年後)

| 指標 | Target |
|------|--------|
| Donor 1 件以上の実寄付 (sandbox 含む) | 100 件 |
| 受益者識別 (PoC scale) | 100 世帯 |
| 国際 NPO 1 機関との pilot 合意 | 1 機関 |
| OSS contributor 数 | 10+ |
| メディア言及 (OECD/BIS/MAS 連動含む) | 5 件 |
| Phase 3 完了率の上昇 | 52% → 70%+ |

---

## 12. なぜ「Donor-PBM」名称 (Carmela 教訓を踏まえて)

戦略会議 #17 で Dr. Carmela Reyes が「Lista Bayanihan」を **「ロマンチック化された貧困観」** と批判した教訓を反映:

| 候補名称 | 採否 | 理由 |
|---------|------|------|
| ❌ **Compassion-PBM** | 不採用 | 慈善ロマンチック化 |
| ❌ **Charity-PBM** | 不採用 | 上から目線 |
| ❌ **Hope-PBM** | 不採用 | 美化 |
| ❌ **Aid-PBM** | 不採用 | 援助 vs 自立の対立感 |
| ✅ **Donor-PBM** | **採用** | 機能直接表現 (寄付者と受益者の関係をフラットに表現)、Carmela 基準 OK |

**Donor-PBM** = 寄付者 (donor) が PBM 経由で受益者 (beneficiary) に届ける、機能だけを表現する命名。

---

## 付録 A: 5 シナリオ Seed Mock Data (Round 21 で実装)

```json
// seed/donor/unicef-mali-mosquito-2026.json (mock)
{
  "program_id": "prog-unicef-mali-llin-2026",
  "name": "UNICEF Mali LLIN Distribution 2026 (rainy season)",
  "treasury": "unicef-mali-treasury",
  "front_end_npo": "unicef-japan",
  "underlying_token": "USDC",
  "subsidy_bps": 10000,
  "per_household_cap_usdc": 30000000,
  "start_at": "2026-05-01",
  "end_at": "2026-09-30",
  "eligibility_mode": "hybrid",
  "eligible_jans": ["1234567890123", "..."],
  "approved_suppliers": ["supplier-bamako-001", "..."],
  "beneficiary_registry": "unhcr-progres-mali-kayes-llin",
  "expected_donors": 1000,
  "expected_beneficiaries": 5000,
  "k_anon_threshold": 50,
  "geo_granularity": "country"
}

// seed/donor/wfp-yemen-food-2026.json (mock)
// seed/donor/jica-bangladesh-school-2026.json (mock)
```

---

## 付録 B: User-facing dashboard (Donor 視点)

```
┌─ あなたの寄付の impact ─────────────────────┐
│  寄付額累計:    ¥50,000 (USDC 320 相当)    │
│  受益世帯:     16.6 世帯 (Mali Kayes)      │
│  配布物:       LLIN 33 枚 + 食料 5kg ×8    │
│  最終配布:     2026-06-15                   │
│                                              │
│  [プログラム別の internal breakdown]        │
│  prog-unicef-mali-llin-2026   ¥30,000      │
│    → 10 世帯、LLIN 20 枚 (Mali Kayes)      │
│  prog-wfp-yemen-food-2026     ¥20,000      │
│    → 6.6 世帯、食料セット 8 (Yemen Sa'ada) │
│                                              │
│  [すべて k=50 集約、国レベル粒度のみ]       │
└──────────────────────────────────────────────┘
```

---

> **Round 20 = この設計書まで。Round 21 で DP-2 〜 DP-12 を実装する。**
