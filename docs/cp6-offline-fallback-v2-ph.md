# CP-6 v2 (Philippines) — Disaster Lista (DL) Protocol

> **作成**: 2026-05-09 (Round 18) / **置換対象**: [`cp6-offline-fallback.md`](./cp6-offline-fallback.md) (v1)
> **参照**: 戦略会議 #16 + #17 ([`strategy-2026-05-round17.md`](./strategy-2026-05-round17.md))
> **名称由来**: 戦略会議 #17 で Dr. Carmela Reyes (UP 人類学) が「Lista Bayanihan」名称を **ロマンチック化された貧困観に陥る危険** と批判 → **「Disaster Lista (DL) Protocol」** に変更

---

## 1. 設計原則

JP は **ハードウェア タンパー耐性** で動くが、PH には:
- マイナンバー相当の SE 内蔵 ID なし (PhilSys は紙)
- 全国均一の避難所端末配備は政府予算的に非現実
- だが **Filipino のコミュニティ信用 (lista 文化)** が既にインフラとして動いている

→ **コミュニティ信用 + 紙 + 復旧時 reconcile** の 3 層で構成。**SE は使わない**。

---

## 2. アーキテクチャ (3 層)

```
[Layer 1] 紙 voucher (耐水ラミネート)
              ─ 平時に opt-in 4Ps 受給者へ配布
              ─ 台風シーズン (6-11 月) 限定発行で年 PHP 50M 程度
              ─ 世帯単位 voucher (主たる受給者写真 + 世帯員数)

[Layer 2] Disaster Lista (DL) ─ サリサリ informal credit デジタル化
              ─ 平時は通常運営に介入しない
              ─ NDRRMC が Code Red 宣言中のみ DL モード起動
              ─ サリサリ店主の opt-in
              ─ 災害特例 PHP 200/世帯/日 のクレジット枠

[Layer 3] バランガイ + Red Cross 立会
              ─ バランガイホール (4.2 万箇所) で台帳管理
              ─ 3 層代理権限: キャプテン → カガワド → タノッド (Padrino リスク緩和)
              ─ PRC (Philippine Red Cross) が必ず立会
              ─ 戸別訪問 (door-to-door) は PRC が実行
```

> **Round 18 では実装しない (R20+ 延期)**:
> - L4 GCash オフライン残高 (Coins.ph 開発に 12-18 ヶ月)
> - L5 Coins.ph piggyback (compliance review に 6 ヶ月)

---

## 3. 各層の詳細

### Layer 1: 紙 voucher (耐水ラミネート)

| 項目 | 内容 |
|------|------|
| **配布範囲** | 4Ps 受給世帯のうち opt-in (推定 10-20%) |
| **配布期間** | 台風シーズン 6-11 月 (年 6 ヶ月) |
| **発行コスト** | PHP 8/枚 (印刷 PHP 5 + ラミネート PHP 3) |
| **総コスト** | 4.4M × 15% × 6 ヶ月 = 約 PHP 32M/年 |
| **voucher 内容** | 世帯 ID HMAC + 主受給者写真 + 世帯員数 + 月次 cap (PHP 1,400 4Ps 標準) + ECDSA 署名 |
| **有効期間** | 発行月内のみ (NDRRMC Code Red 宣言中に限り 30 日 grace) |
| **回収方法** | サリサリ/バランガイ で受領、復旧後にスキャン入力 → contract |

### Layer 2: Disaster Lista (DL)

| 項目 | 内容 |
|------|------|
| **発動条件** | NDRRMC が Code Red declare (SMS gateway で受信) |
| **対象店舗** | opt-in したサリサリ + Mercury Drug 等 |
| **クレジット枠** | PHP 200/世帯/日 (Aling Maria 推奨値、月次累計 PHP 6,000) |
| **記録方式** | (a) 店主の手書き lista 帳 (b) 受給者世帯 ID + 写真 ID 確認 (c) 復旧後 1 週間以内に DSWD 経由で contract に batch |
| **不正対策** | 1 日 1 世帯 × 1 サリサリ uniq、3-strike rule (3 回違反でサリサリ除外) |
| **入金タイミング** | サリサリは **週 1 回 batch 入金** または **同日即時入金** を選択可 (R18 では両方の adapter を用意) |

### Layer 3: バランガイ + Red Cross

| 項目 | 内容 |
|------|------|
| **代理権限** | キャプテン → カガワド (sub-leader) → タノッド (security) の 3 層 (キャプテン避難時の継承) |
| **立会必須** | PRC ボランティア 1 名以上が必ず同席 (Padrino 政治偏向 の独立検証) |
| **戸別訪問** | PRC + バランガイ職員が 4Ps 名簿基準で 自宅訪問 (子供 + 高齢者世帯) |
| **手書き台帳** | バランガイホールで 1 日単位の集計、世帯 ID + 給付内容 + 写真 |
| **復旧後** | 台帳をスマホで撮影 → DSWD に送信 → contract に batch |

---

## 4. データフロー (台風時)

### 4.1 平時 (台風シーズン入り 5 月)

```
DSWD ──→ opt-in 受給者 (15% 想定) に紙 voucher 配布
                月 1 回 配布、写真 ID + 署名済 voucher
sari-sari + Mercury Drug の opt-in 確認
バランガイホール の代理権限訓練 + PRC との連携確認
```

### 4.2 台風接近 (PAGASA Cat 3+ 警報)

```
PAGASA ──→ NDRRMC ──→ Code Red declare (該当 LGU)
                          ↓
            SMS gateway (¥50K/月) で受信
                          ↓
        services/ndrrmc_alert.py が PBM contract に通知
                          ↓
            DL モード起動: voucher 即時有効化 + sari-sari の DL 受領可能
```

### 4.3 災害発生中 (0-7 日)

```
受給者 ──→ サリサリ (徒歩可能なら)
              voucher 提示 + 写真 ID 照合
              店主が lista 帳に記入 (世帯 ID + 品目 + 金額)
              即時または週次 batch で sari-sari に PHPC 入金

受給者 ──→ バランガイホール (PRC 立会)
              voucher 提示 → 手書き台帳記入
              現場で物資配布 (DSWD 備蓄物資)

PRC + バランガイ ──→ 戸別訪問 (徒歩不可世帯)
              voucher 受領 + 写真 + 給付物資配布
              台帳記入
```

### 4.4 復旧後 (8-30 日)

```
バランガイ ──→ 手書き台帳をスマホ撮影 ──→ DSWD ──→ contract batch
sari-sari ──→ lista 帳をスマホ撮影 ──→ DSWD ──→ contract batch
全 redemption が consumed mapping に集約 → 整合性検査 → JPYC payout
```

### 4.5 Yolanda 級 (Cat 5+) 例外

```
Cat 5+ では サリサリ自身も避難 / 倒壊
→ DL Protocol 機能不全
→ NDRRMC 直接配給フェーズ に切替
→ DSWD + AFP (国軍) + PRC が物資直接配給
→ 復旧後、PBM 月次枠を「未使用扱い」 で次月に carry over (受給者は損失なし)
```

---

## 5. CP-1〜CP-7 整合性

| CP | v2 PH での担保 |
|----|----------------|
| CP-1 | governor.revokeProgram() (通常運用と同じ) |
| CP-2 | 4Ps 名簿 + バランガイ承認 + 写真 ID (人 + 紙 の二重) |
| CP-3 | PHPC ペッグ運用 (BSP 監督) |
| CP-4 | HMAC 世帯 ID、生 PSN 不在 |
| CP-5 | **5% 運用許容 + 復旧後監査** (#17 PH-6 で確定、honest 表記) |
| CP-6 | **本 v2 の核** |
| CP-7 | 月次枠 (PHP 1,400/世帯/月) |

---

## 6. 採択 11 件 → 実装マッピング

| #16/#17 ID | 内容 | 本 doc での対応 |
|-----------|------|---------------|
| PH-1 ✏️ | 3 層 DL Protocol | §2 アーキテクチャ |
| PH-2 ✏️ | lista_adapter (opt-in + 災害限定) | §3 Layer 2 |
| PH-3 ✅ | barangay_endpoint (3 層代理) | §3 Layer 3 |
| PH-4 ✏️ | NDRRMC SMS + PRC API 受信 | §4.2 |
| PH-5 ✅ | 紙 voucher opt-in + 台風シーズン | §3 Layer 1 |
| PH-6 ✅ | CP-5 5% 運用的許容 | §5 CP-5 |
| PH-7 ✏️ | 世帯単位 voucher | §3 Layer 1 (世帯 ID + 主受給者写真 + 世帯員数) |
| PH-8 ✅ | DSWD MC + BSP NoL 文書 | 別途 handoff-packages/dswd/ |
| PH-9 🆕 | バランガイ 3 層代理 + PRC 立会 | §3 Layer 3 |
| PH-10 🆕 | 即時 vs 週次 batch 両対応 | §3 Layer 2 (両 adapter) |
| PH-11 🆕 | 名称 「DL Protocol」 | 本 doc 全体 |
| PH-12 🆕 | Yolanda 級は対象外 | §4.5 |

---

## 7. コスト見積 (年間)

| 項目 | コスト |
|------|--------|
| 紙 voucher 印刷+ラミネート (15% opt-in × 6 ヶ月) | PHP 32M (~¥80M) |
| SMS gateway (NDRRMC alert 受信) | PHP 0.6M (~¥1.5M) |
| PRC との運用協定 + 訓練 | PHP 5M (~¥12M) |
| バランガイ 3 層代理訓練 | PHP 3M (~¥7M) |
| sari-sari 写真 ID 設備 (opt-in 5K 店) | PHP 5M (~¥12M) |
| **合計** | **PHP 45M/年 (~¥112M/年)** |

JICA 申請の 24 ヶ月 PHP 90M 程度で 4Ps 全国展開の DL Protocol が動く規模。

---

## 8. 実装ロードマップ

| Phase | 内容 | 状態 |
|-------|------|------|
| **R18** (今ラウンド) | 設計書 (本ファイル) + 4 services mock + tests | ✅ 着手 |
| R19 | Citizen.household_id schema + 4Ps multi-locale loader 拡張 | 後 |
| R20 | NDRRMC SMS gateway 実接続 (実 gateway 契約必要) | 実外交待ち |
| R21 | Coins.ph との PHPC sandbox 接続 | 実外交待ち |
| R22+ | Quezon City 1 バランガイ 5 世帯パイロット | 全外交合意後 |

---

## 9. JP 側 (v2-jp) との比較サマリ

| 観点 | JP v2 (A+E hybrid) | PH v2 (DL Protocol) |
|------|---------------------|---------------------|
| 信頼アンカー | ハードウェア (Felica SE) | コミュニティ + 紙 + 復旧後 reconcile |
| 認証強度 | 機械的厳密 | 5% 運用的許容 + 監査 |
| 配備コスト | 高 (¥7-10B 5 年計画) | 低 (¥112M/年) |
| 災害時運用 | 全国均一 | バランガイ + PRC ハイブリッド |
| 想定災害頻度 | 30 年に 1 度 → 重武装 OK | 年 20+ 回 → 軽装備必須 |
| Yolanda 級例外 | 全国体制で対応 | NDRRMC 直接配給に切替 |

→ 同じ問題 ─ 異なる文脈 ─ 異なる解。**「世界初」とは謳わず、それぞれの社会に最適化した 2 設計** を honest に提示する。
