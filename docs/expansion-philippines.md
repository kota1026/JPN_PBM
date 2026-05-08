# Philippines Expansion ─ Manila Twin-Pilot Spec (v0.1 draft)

> **作成日**: 2026-05-04
> **目的**: JPN-PBM を **Tokyo + Manila ツインパイロット** に拡張する戦略・技術仕様の初版
> **位置付け**: 戦略会議 #11 候補 (Round 12 以降)、まだ実外交はゼロ
> **ステータス**: **構想段階** ─ JICA / DICT / DSWD / BSP との接触は未

---

## 1. なぜマニラか (東京と並列で進める根拠)

### 1.1 マニラが「東京より動きやすい」 5 つの理由

| 観点 | 東京 | マニラ |
|------|------|--------|
| **ステーブルコイン規制** | 資金決済法 (Type II 取得済) | **BSP 規制サンドボックス**で柔軟、PHPC が認可済 |
| **災害頻度** | 地震 30 年に 1 度 | **台風 年 20+ / 洪水 / 火山** ─ CP-6 が **月次で価値発揮** |
| **対象プログラム規模** | 23 区合計 ¥640B/年 | **4Ps 単独で ¥1,200億/年・440 万世帯** |
| **モバイル決済普及** | 40% | **GCash 8,000 万 UU + Maya** = ほぼ全人口 |
| **政府の Web3 受容** | 慎重 | DICT が積極推進、BSP がサンドボックス開放 |

### 1.2 PHP ステーブルコイン (2026 年時点)

| 名称 | 発行体 | 状態 | チェーン |
|------|--------|------|---------|
| **PHPC** (Philippine Peso Coin) | **Coins.ph** | ✅ **BSP 規制サンドボックス認可済 (2024)** ─ フィリピン初の正式 PHP ステーブルコイン | Polygon (mainnet) |
| PHPT | UnionBank | 検討段階 | 未定 |
| BSP CBDC (Project Agila) | BSP 直営 | wholesale 卸売のみ | 私設 |

→ **PHPC が JPYC と同じポジション**。技術的には JPN-PBM の `JPYC_TESTNET_ADDRESS` 環境変数を **PHPC アドレスに差し替えるだけ** で動作する。

---

## 2. 対象プログラム ─ 4Ps が最有力候補

### 2.1 4Ps とは

**Pantawid Pamilyang Pilipino Program** (条件付き現金給付):

- DSWD (社会福祉省) 主管
- 対象: 貧困家庭 **440 万世帯** (約 2,000 万人 = 全人口の 18%)
- 給付: 月額 PHP 700-1,400 (~¥1,800-3,600)
- **条件**: 子供の就学率 85% 以上、医療検診受診、母子保健プログラム参加
- 年間予算: 約 PHP 100B (~¥260B = ¥1,200億)
- 国際的に注目: 世界銀行・ADB が支援

### 2.2 PBM が解く 4Ps の課題

| 4Ps の現状の問題 | JPN-PBM の解 |
|-----------------|-------------|
| Cash 配布なので **酒・タバコへの転用** が一定発生 | JAN コードレベルで対象を制限 (米・粉ミルク・教科書・医薬品) |
| 受給資格の **二重計上** が散発 | HMAC PID で chain 上一意性保証 |
| 台風時に **配布停止** | CP-6 オフライン QR で配布継続 |
| 効果測定 (DSWD → 議会) に **6 ヶ月ラグ** | EBPM ダッシュボードでリアルタイム k-匿名集計 |

### 2.3 段階的 rollout 案

```
[Pilot α]   3 ヶ月   500 世帯 × 5 sari-sari store (Quezon City 1 区)
[Pilot β]   6 ヶ月   5,000 世帯 × 50 store (Quezon City + Manila City 2 区)
[Closed]    1 年     50,000 世帯 × 500 店舗 (Metro Manila 17 LGU 全域)
[Public]    2 年     500,000 世帯 (Luzon 全域)
[Full]      3 年     4,400,000 世帯 (全国)
```

---

## 3. Tokyo + Manila ツインパイロット ─ 共通基盤

JPN-PBM のコードベースを **2 都市で共用** することで、開発コストを抑えつつ国際比較データが取れます。

### 3.1 何を共通化できるか (= ほぼ全部)

| レイヤー | 共通化 | 都市差分 |
|---------|--------|---------|
| Solidity contracts | ✅ 100% 共通 | underlying token (JPYC vs PHPC) のみ |
| backend services (Python) | ✅ 100% 共通 | seed JSON のみ |
| 認証 OAuth | ✅ pluggable | マイナポータル v2 vs PhilSys (Philippine ID) |
| EBPM 集計ロジック | ✅ 100% 共通 | k 値・閾値のみ調整 |
| frontend UI | ✅ 共通 (i18n) | 言語: 日本語/英語/Filipino |
| POS SDK | ✅ 100% 共通 | プリンタ I/F のみ機種依存 |

### 3.2 都市ごとに必要なもの (= 30%)

| アイテム | Tokyo | Manila |
|---------|-------|--------|
| Stablecoin | JPYC (Polygon) | **PHPC (Polygon)** ─ 同じチェーンなので技術差分ほぼゼロ |
| 政府パートナー | TMG + 江東区 + JPYC + TIS | **DSWD + DICT + Coins.ph + LGU** |
| 個人 ID | マイナンバー (HMAC PID) | **PhilSys** (HMAC PID) ─ 同じ仕組み |
| 法令準拠 | 個情法 / 資金決済法 | **Data Privacy Act / BSP VASP framework** |
| 災害種別 | 地震 | **台風・洪水** |
| seed プログラム | 子育て / 防災備蓄 | **4Ps / 災害支援** |

### 3.3 コードベース構造案

```
JPN_PBM/
├── contracts/                    # ← 共通 Solidity (今のまま)
├── backend/
│   ├── app/
│   │   ├── services/            # ← 共通サービス (今のまま)
│   │   └── locale/
│   │       ├── jp/              # 既存
│   │       │   ├── seed.py      # 江東区 seed
│   │       │   └── id_provider.py  # マイナポータル
│   │       └── ph/              # 新規
│   │           ├── seed.py      # 4Ps seed
│   │           └── id_provider.py  # PhilSys
│   └── tests/
├── seed/
│   ├── jp/                      # 既存 (citizens.json, programs.json, ...)
│   └── ph/                      # 新規
└── docs/
    ├── expansion-philippines.md  # 本ドキュメント
    └── ...
```

→ 既存コードを壊さず、`locale/` と `seed/` だけ国別 namespace を切る形が最小侵襲。

---

## 4. ステークホルダー (推定リスト)

| 役割 | 候補組織 | 接触ルート |
|------|---------|-----------|
| **国レベル監督官庁** | DSWD (社会福祉省) | JICA フィリピン事務所経由 |
| **デジタル推進** | DICT (情報通信技術省) | Tokyo Innovation Base → ASEAN 連携 |
| **金融規制** | BSP (中央銀行) | Coins.ph 経由 (既に対話中) |
| **stablecoin 発行体** | **Coins.ph** | 直接 (CEO Wei Zhou に DM 可能性あり) |
| **LGU パートナー** | Quezon City (Joy Belmonte 市長は Web3 受容的) | Sister-City 関係を持つ目黒区経由 |
| **加盟店ネットワーク** | Sari-sari stores 連合 + 7-Eleven Philippines | LGU 経由 |
| **資金提供** | **JICA デジタル公共財枠** (年 ¥30-100M) | 大手町本部 |
| **国際機関** | ADB Manila + World Bank Philippines | 4Ps 支援実績で接触可能 |

---

## 5. JICA グラント獲得シナリオ (一番現実的な資金経路)

JICA は 2024 年から「**デジタル公共財 (DPGs)**」カテゴリで OSS プロジェクトに直接予算を配分。条件:

| JICA 要件 | 充足状況 |
|----------|---------|
| OSS (Apache 2.0 / MIT) | ✅ Apache 2.0 |
| 開発途上国での実証計画 | ✅ Manila 計画あり (本ドキュメント) |
| 日本の専門家・組織が関与 | ✅ Tokyo 側で実装、JPYC 株式会社の関与想定 |
| 現地カウンターパートの確約 | ❌ DSWD / Quezon City との MoU 未 |
| 国際公共財としての貢献 | ✅ CP-6 災害時フォールバック (世界初設計) |

→ **不足は現地カウンターパート 1 件のみ**。JICA フィリピン事務所に Quezon City を紹介してもらう経路が最有力。

獲得時の予算規模: **年 ¥30-80M × 2-3 年 = 総額 ¥60-240M**。

---

## 6. リスクと反論への準備

| 反論 | 想定回答 |
|------|---------|
| 「日本国内も終わってないのに海外に手を広げるのか」 | コードベース共通なので開発コストは増えない。むしろ Manila で先に動かせれば Tokyo の説得材料になる (海外実績が日本では効く文化) |
| 「PhilSys と マイナンバーは別物」 | HMAC pseudonymization レイヤで吸収可能。PHP/JPN 両方で `id_provider.py` を pluggable 化。 |
| 「フィリピン政府は腐敗が…」 | DSWD の 4Ps は **世界銀行・ADB が監査** している例外的にクリーンなプログラム。チェーン上のスペンド ログでさらに透明化される (利点こそ大きい)。 |
| 「PHPC が破綻したらどうする」 | ステーブルコインを差し替え可能な設計 (`JPN_PBM_JPYC_CONTRACT` を `JPN_PBM_STABLE_CONTRACT` にリネームすれば PHPC/USDC/etc に置換可)。 |

---

## 7. 次の 90 日で何をするか (机上のみで進む範囲)

| Week | アクション | サンドボックス内? |
|------|-----------|-------------------|
| W1 | `seed/ph/` に 4Ps の seed JSON を draft (架空 5 世帯 × 5 sari-sari store) | ✅ |
| W2 | `backend/app/locale/ph/id_provider.py` で PhilSys mock OAuth を実装 | ✅ |
| W3 | `frontend/ph/index.html` を Tagalog + English で作成 | ✅ |
| W4 | `docs/whitepaper-2026.md` に Manila section を追加、英訳完成 | ✅ |
| W5-6 | JICA フィリピン事務所への申請書ドラフト作成 (英文) | ✅ (実申請は外交) |
| W7-8 | Coins.ph に PHPC testnet アクセスを問い合わせる準備 (英文 1 枚) | ✅ |
| W9-12 | Quezon City Innovation Office への Sister-City 経由ルート探索 | △ (実外交) |

→ **JICA 申請書ドラフト + Manila seed + Tagalog UI まではサンドボックスで完結**。

---

## 8. このドキュメントを誰に送るか

| 宛先 | 同梱資料 | 期待アクション |
|------|---------|---------------|
| JICA 大手町本部 デジタル課 | このドキュメント英訳 + whitepaper-2026.md | JICA フィリピン事務所への紹介 |
| Coins.ph CEO Wei Zhou | 英訳 pitch-deck + whitepaper §4 (CP-6 章) | PHPC testnet アクセス + 技術ミーティング |
| ADB Manila Digital Lead | 英訳 whitepaper + 4Ps section (本書 §2) | 4Ps 共同実証提案ミーティング |
| Tokyo MTG (二国間連携課) | 本書日本語版 + 都との Sister-City 関係整理 | TMG 国際交流局からの紹介状 |

---

> **本ドキュメントは draft v0.1**。フィリピンとの実外交が一切始まっていない段階での机上構想であり、現地カウンターパートが付き次第、大幅な改訂が必要になる。
> 議論の出発点として用いること。
