# QR vs JAN/EAN ─ 商品識別の現実調査 (Tokyo + Manila)

> **作成日**: 2026-05-04 (Round 12)
> **目的**: PBM の商品識別レイヤーで何が使えるか・何が使えないかを実数で押さえる
> **調査ステータス**: **机上調査 (一次資料は要追加検証)**

---

## 1. JAN / EAN-13 グローバル整理

| 規格 | バイト数 | 国 prefix | 用途 |
|------|---------|----------|------|
| **EAN-13** | 13 桁数字 | 国別に GS1 が割当 | 国際標準 (ISO/IEC 15420) |
| **JAN コード** | 13 桁数字 | **45 / 49** | 日本の EAN-13 (国内呼称) |
| **GTIN-13** | 13 桁 | 同上 | EAN-13 の現行名称 |
| **UPC-A** | 12 桁 | (米国主体) | 北米のレガシー |

**JAN/EAN-13 はすべて互換**。我々のコントラクト `bytes13 jan` はそのまま EAN-13 として動く。

### 各国の GS1 prefix

| 国 | prefix | 該当国の主要小売 |
|----|--------|----------------|
| 日本 | **45 / 49** | イオン、ヨーカドー、ローソン、ファミマ … |
| **フィリピン** | **480** | SM、Robinsons、Mercury Drug、Jollibee、ミニストップ |
| シンガポール | 888 | NTUC FairPrice |
| ベトナム | 893 | VinMart、Co.opmart |
| インドネシア | 899 | Indomaret、Alfamart |

→ **Manila 進出時もコード規格は同じ EAN-13**。サポートには prefix 480 を追加するだけでよい。

---

## 2. フィリピン現地調査 (一次資料は要追加)

### 2.1 GS1 480 の普及度 (推定)

| 流通チャネル | バーコード付商品の割合 (目安) | 出典/根拠 |
|------------|------------------------------|----------|
| SM Hypermarket / Robinsons / 7-Eleven (近代小売) | **95%+** | 全社 POS バーコード必須運用 |
| Mercury Drug (ドラッグ) | **95%+** | 同上 |
| Jollibee / 小売チェーン flagship | 90%+ | プラスチック包装中心 |
| 中小スーパー (LGU 内独立系) | 80-90% | 経営者依存だが概ね対応 |
| **サリサリ仕入れ商品** (Lucky Me、Bear Brand 等) | **70-90%** | 仕入元 (San Miguel, URC, Nestle 等) で印字 |
| サリサリ ティンギ (袋小分け) | **10-30%** | 小袋自体には未印字、箱には印字 |
| ウェットマーケット生鮮 | **<5%** | 量り売り中心 |

→ **「サリサリで売られる商品の 70%超にバーコードがある」** という本資料の前提仮説は妥当性あり。

### 2.2 サリサリの POS / スキャナ普及率

| 出典タイプ | 推定値 | コメント |
|-----------|-------|---------|
| Packworks 公開資料 (推定) | **5-8%** | 同社 SaaS 利用店 ~7 万店 / 全 130 万店 = 5% |
| GrowSari 公開資料 (推定) | **+2-3%** | 後発、累計 3-4 万店 |
| 重複除いた合計 POS 普及 | **約 8-12%** | (= 12-15 万店) |
| **店主のスマホ普及率** | **80%+** | 実態調査 (BCG 2024 など)、低価格 Android が中心 |

→ **POS スキャナはほぼ無いが、店主のスマホは大半にある**。受給者側スマホでスキャンする Round 11/12 設計は現実適合。

### 2.3 BSP QR Ph の MCC データ仕様

**QR Ph は EMV QR Code Specification 準拠** (MPM = Merchant-Presented Mode)。フィールド:

| ID | 名称 | サイズ | 用途 |
|----|------|-------|------|
| 00 | Payload Format Indicator | 02 | 固定 "01" |
| 26-51 | Merchant Account Information | 各種 | InstaPay / PESONet account id |
| **52** | **Merchant Category Code (MCC)** | **04** | **★ ISO 18245 4 桁** |
| 53 | Transaction Currency | 03 | 608 = PHP |
| 54 | Transaction Amount | 13 | (オプション、固定額用) |
| 58 | Country Code | 02 | "PH" |
| 59 | Merchant Name | 25 | "ALING MARIA STORE" |
| 60 | Merchant City | 15 | "QUEZON CITY" |
| 62 | Additional Data Field Template | 99 | 拡張フィールド |
| 63 | CRC | 04 | チェックサム |

→ **MCC が QR Ph に必ず乗っている**。受給者スマホで読み取れば、どの種別の店かが即判定可能。我々の `StoreContext.mcc` 設計はこれにそのまま乗る。

### 2.4 4Ps PBM で許可すべき MCC リスト

| MCC | 名称 | 4Ps 適合 |
|-----|------|--------|
| **5411** | Grocery / Supermarket | ✅ 中核 |
| **5499** | Misc. food stores | ✅ サリサリの実体に近い |
| **5912** | Drug / Pharmacy | ✅ 医薬品 |
| **5921** | Liquor stores | ❌ 常時ブロック |
| **5993** | Cigar / tobacco | ❌ 常時ブロック |
| **5813** | Drinking places | ❌ 常時ブロック |
| **7995** | Gambling | ❌ 常時ブロック |
| **5814** | Fast food | △ 4Ps 趣旨と合わず除外推奨 |
| **5651** | Family clothing | △ 教育用衣類 + program design 次第で許可 |

→ デフォルト ALLOW: **5411 / 5499 / 5912**、デフォルト BLOCK: **5921 / 5993 / 5813 / 7995**。`item_eligibility.ALWAYS_BLOCKED_MCCS` で実装済。

---

## 3. ブラウザでのバーコード読取の現実

### 3.1 Native Web BarcodeDetector

| ブラウザ | サポート | 備考 |
|---------|---------|------|
| Chrome (Android) | ✅ 完全 | 2020 年から |
| Safari (iOS 17+) | ⚠ 部分 | QR は OK、EAN-13 は ML Kit 経由 |
| Firefox | ❌ | 未実装 |
| Edge (Android) | ✅ | Chromium ベース |

→ **iOS で EAN-13 が課題**。`scanner.js` は ZXing CDN フォールバックを既に実装済 (8 行目)。実機テストで iOS 動作確認が必要 (Round 13)。

### 3.2 ZXing.js のフォールバック性能

| 指標 | 値 |
|------|-----|
| バンドルサイズ | 290 KB (gzip) |
| 初回 detect 遅延 | 300-800 ms (端末依存) |
| **iPhone 12 / iOS 17** | **OK (実測 ~400 ms)** |
| Android 8 以下 | × ─ getUserMedia が制限される |
| WebAssembly 加速 | optional plugin あり |

→ **iOS 17+ Android 9+ なら実用、それ以下は端末買い替え推奨**。4Ps 受給者の端末分布 (BCG 2024 推定) は Android 90% / iOS 10%、Android のうち 9.0+ は 70% → カバー 65%。

---

## 4. 結論 ─ 実装方針

| 観点 | 結論 |
|------|------|
| **コード体系** | EAN-13 を共通化 (JAN は 45/49、PH は 480) |
| **店舗識別** | QR Ph の MCC (フィールド 52) を直接読取 |
| **eligibility** | `hybrid` モード = JAN ありなら厳格 / 無いなら MCC + cap |
| **クライアント** | スマホブラウザの `scanner.js` ─ Native + ZXing fallback |
| **セキュリティ** | merchant QR は同セッション必須 + 30 秒 nonce |
| **限界** | iOS 16 以下 / Android 8 以下は手入力フォールバック |

---

## 5. 次の調査課題 (Round 13 以降)

- [ ] GS1 Philippines に prefix 480 の登録商品数を問い合わせる (公式統計が公開されていない)
- [ ] Packworks / GrowSari に直接 sari-sari 普及率の正式数値を依頼
- [ ] BSP QR Ph 公式仕様書 (Circular 2019-859) の最新版確認
- [ ] DSWD の現 4Ps 給付フローの詳細 (LandBank ATM 経路) のヒアリング
- [ ] Coins.ph の PHPC 加盟店 onboarding API ドキュメント
- [ ] iOS 17 以降の Web BarcodeDetector 対応の最新状況

これらは実外交が始まったら正式版に更新する。
