# JPN-PBM ─ Programmable Subsidy & Donation Infrastructure

> **Tokyo × Manila × International donor aid** ─ 1 codebase, 3 markets, OSS.
> Status: **Sandbox complete (Round 23)**, awaiting real diplomacy.
> License: **Apache 2.0**

```
[ "目的どおりに使えるお金" を、政府助成金から国際寄付まで動かす ]
JPYC (Tokyo)  ─┐
PHPC (Manila) ─┼─→ PBM contract (Polygon) ─→ 認定加盟店 / supplier
USDC (Donor)  ─┘   ─ CP-1〜CP-8 強制
                     ─ 災害時 fallback (CP-6 v2)
                     ─ k-匿名集計
```

## 🌐 まず動画を見る (5 分・インストール不要)

→ <https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/main/frontend/demo.html>

ブラウザだけで 5 分自動再生。日本語 / English / Tagalog 切替、一時停止 / 巻戻し可。

## 📖 全部を 30 分で理解する

→ [`docs/service-overview.md`](docs/service-overview.md) ─ アーキテクチャ / 利用方法 / 7 シーケンス / 8 セールスポイント / TAM 試算

---

## 1 行説明

東京都の助成金から JICA・UNICEF・WFP の寄付まで、**「使い道があらかじめプログラムされたお金」** で配給する OSS 基盤。**契約レイヤでの 5 段検証** で、目的外利用が **物理的に起きない**。災害時にも **POS なしで動く** 仕組み (CP-6 v2)。

## 数字で見る現状 (Round 23 時点)

| 指標 | 値 |
|------|-----|
| バックエンドテスト | **371 passed** |
| Solidity コントラクト | 2 (PBM + PBMOfflineFallback)、self-audit `ok=40 warn=4 fail=0` |
| サービスモジュール | 31 |
| FastAPI ルータ | 14 |
| Adapter モジュール | 8 (chain / gcash / landbank / kyc / aml / progres / ndrrmc / se) |
| HTML ページ | 10 (JP / EN / Tagalog / Donor / auto-demo) |
| シナリオ seed | 11 (Tokyo 7 + Manila 2 + Donor 3) |
| ドキュメント | 74 (戦略会議議事録 20 本 + 英訳 19 本 + 設計 + 提出物) |
| Handoff packages | 7 (jica / coins-ph / dswd / quezon-city / unicef / wfp-building-blocks / unhcr) |
| GitHub Actions CI | ✅ 全 PR で自動実行中 |
| ライセンス | Apache 2.0 |

## 3 つの市場 + 1 つの新規拡張

### 🇯🇵 東京都 (Phase 1-2, R1-R10)
- 江東区 子育て / 防災備蓄を含む 7 program (seed/)
- マイナンバーカード OAuth Mock + 加盟店 POS SDK (Python)
- **災害時 (CP-6 v2)**: Felica SE + 避難所端末 ハイブリッド設計
- TAM: 23 区合計 **¥640B/年**

### 🇵🇭 マニラ (Phase 2-3, R11-R14)
- DSWD 4Ps PBM Pilot + 台風備蓄
- PhilSys OAuth Mock + サリサリ用 ハイブリッド eligibility (バーコード + MCC fallback)
- EMV QR Ph parser (BSP Circular 2019-859 準拠) + GS1 480 製品マスタ
- **災害時 (CP-6 v2)**: 紙 voucher + Lista + Barangay + Red Cross ─ Disaster Lista Protocol
- TAM: 4Ps 単独で **PHP 100B (¥260B)/年**、4.4M 世帯

### 🌍 国際寄付 / Donor-PBM (Phase 4, R20-R21 新設)
- UNICEF Mali LLIN 蚊帳 + WFP Yemen 食料 + JICA Bangladesh 教科書 (3 seed)
- KYC tier ($0-50 anon → $10000+ enhanced) + AML 3-source cross-check (OFAC + UN + EU)
- UNHCR ProGres federation (biometric は contract に書かない)
- **CP-8 緊急 AML bypass** + 14 日事後監査 (Lina Okabe 警告反映)
- TAM: UN 人道援助 **$50B+/年**、民間財団 **$200B+/年**

### 🔄 4 つの市場共通の基盤
- Polygon (mainnet / Mumbai testnet)
- adapter pattern (mock ↔ real env 1 つで切替)
- HMAC pseudonymization で生 ID 不在
- k-匿名 EBPM (自治体 k=5、Donor k=50)

---

## クリティカル プロパティ (CP-1 〜 CP-8)

すべての PBM transaction が満たす 8 つの不変条件:

| ID | 性質 | 強制機構 |
|----|------|---------|
| CP-1 | 緊急停止 (governor revoke) | `PBM.sol:revokeProgram()` |
| CP-2 | Eligibility (citizen ∧ store ∧ JAN ∧ period ∧ cap) | `PBM.sol:spend()` 5 段 require |
| CP-3 | JPY ペッグ逸脱検知 | `services/peg_monitor.py` |
| CP-4 | プライバシー (HMAC PID) | `services/privacy.py` |
| CP-5 | 二重支給防止 (no double-spend / 転売 / なりすまし) | `consumed[][]` + ECDSA verify |
| CP-6 | 災害時オフライン redemption ─ **v2 で 2 国別設計** | `cp6-offline-fallback-v2-{jp,ph}.md` |
| CP-7 | 個人 / 世帯月次 cap + 多年度予算 | `services/fiscal_budget.py` + `household.py` |
| **CP-8** | **緊急時 AML bypass + 14 日事後監査** (R21 新設) | `services/cp8_emergency_bypass.py` |

---

## 21 ラウンドの設計上の 3 ピボット

1. **R12 (PR #13): サリサリの POS 無いよね** → ハイブリッド eligibility (バーコード厳格 + MCC fallback) を導入
2. **R18 (PR #19): 災害時に POS 動かないよね** → CP-6 v1 撤回、JP A+E hybrid + PH DL Protocol に再設計、「世界初」表現を撤回
3. **R20-R21 (PR #21-22): JICA・UN にも使えるよね** → Donor-PBM 拡張で TAM 100x、UNHCR ProGres federation

**各ピボットは強制された誤り訂正** ─ user / red-team / Carmela (人類学者ペルソナ) / Roberto (元 Coins.ph ペルソナ) からの指摘で設計が変わった。これが OSS としての価値 (隠さず議事録化済)。

---

## 動かしてみる (3 通り)

### A. ブラウザだけ
→ <https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/main/frontend/demo.html>

### B. ローカルでフル
```bash
git clone https://github.com/kota1026/JPN_PBM
cd JPN_PBM
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
# 別ターミナルで:
open http://localhost:8000/ui/index.html
```

### C. 全部検証
```bash
bash scripts/verify.sh all
# → 371 tests passed
# → 8 モード全緑 (pytest / seed / sol / front / audit / i18n / deploy-check / handoff)
```

---

## ロードマップ達成度

戦略会議 #1 (R1) で確定した 18 ヶ月計画:

| Phase | 達成率 | 残課題 |
|-------|--------|--------|
| **Phase 1** (Tokyo Closed Alpha) | 86% | M+0 (4 者 MoU) ─ 実外交待ち |
| **Phase 2** (23 区 + Manila 拡張) | 77% | M+1 Polygon Mumbai 実デプロイ等 |
| **Phase 3** (制度連携) | 60% | M+12/M+14 法整備、FSA 折衝 |
| **Phase 4** (Donor-PBM / 国際) ★ R20 新設 | 30% | UNICEF/WFP/UNHCR 接触 |

ライブ表示: `services/roadmap.py` + `GET /treasury/roadmap`

---

## 主要文書 (用途別)

| 目的 | 読むファイル |
|------|------------|
| **30 分で全部知る** | [`docs/service-overview.md`](docs/service-overview.md) |
| **5 分自動デモ** | [`frontend/demo.html`](frontend/demo.html) ([プレビュー](https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/main/frontend/demo.html)) |
| 議員 / 課長級 ピッチ | [`docs/pitch-deck-jp.md`](docs/pitch-deck-jp.md) |
| 国際フォーラム ピッチ | [`docs/pitch-deck.md`](docs/pitch-deck.md) |
| 友人 カジュアル | [`docs/pitch-deck-friend.md`](docs/pitch-deck-friend.md) |
| 技術論文 30 ページ | [`docs/whitepaper-2026.md`](docs/whitepaper-2026.md) |
| マニラ展開仕様 | [`docs/expansion-philippines.md`](docs/expansion-philippines.md) |
| **Donor-PBM 設計** | [`docs/expansion-donor-pbm.md`](docs/expansion-donor-pbm.md) |
| CP-6 v2 災害時 | [`docs/cp6-offline-fallback-v2-jp.md`](docs/cp6-offline-fallback-v2-jp.md) + [`-ph.md`](docs/cp6-offline-fallback-v2-ph.md) |
| 本番投入 runbook | [`docs/production-runbook.md`](docs/production-runbook.md) |
| 他自治体 fork | [`docs/fork-guide.md`](docs/fork-guide.md) |
| 7 宛先 提出パッケージ | [`docs/handoff-packages/`](docs/handoff-packages/) |
| 21 ラウンド議事録 | `docs/strategy-2026-*.md` (20 本) |

---

## ハイライト (差別化要素)

- ✅ **完全 OSS (Apache 2.0)** ─ ベンダーロックインなし、自治体 / NPO が fork 可
- ✅ **目的拘束をコントラクトで強制** ─ 事後監査ではなく事前防止
- ✅ **災害時に動く (CP-6 v2)** ─ 2 国 2 設計、JP は SE / PH はコミュニティ信用
- ✅ **同一コードで 3 市場** ─ Tokyo / Manila / Donor-PBM (99% 共通)
- ✅ **honest framing** ─ 「世界初」謳わず、WFP Building Blocks / Indonesia BPNT 等にリスペクト
- ✅ **Adapter pattern** ─ env 1 つで mock ↔ real 切替、silent fallback 禁止
- ✅ **HMAC 擬似 ID + k-匿名集計** ─ プライバシー設計の二重防御
- ✅ **11 役エージェント戦略会議** ─ 設計判断の audit trail、3 回の重要ピボット記録

---

## 採用ハードル (Honest)

サンドボックス内で進められない、実外交 / 実機が必要な領域:

| 課題 | 必要 |
|------|------|
| M+0 Founders' MoU (TMG × JPYC × TIS × 江東区) | 4 者調印 |
| Polygon Mumbai 実デプロイ | RPC URL (Alchemy/Infura) |
| GCash sandbox API | Coins.ph 接触 |
| iPhone 実機 scanner 検証 | iPhone 13/15 + 手動テスト |
| マイナポータル v2 API | 総務省・デジ庁協議 |
| DSWD 4Ps LandBank 統合 | 政策合意 |
| Felica SE 実機 | JPKI API 拡張 (総務省) |
| UN 機関接触 (UNICEF/WFP/UNHCR) | data sharing agreement |
| ComplyAdvantage 契約 | $20K-80K/年 |
| JICA pre-screening v3 | 会話 |

**いずれの障壁も技術ではなく合意形成**。コードは外部資源解禁の翌週から本番投入可能な状態。

---

## TAM (Total Addressable Market)

| セグメント | 規模 (年間) |
|-----------|-----------|
| Tokyo 23 区 助成金 | ¥640B |
| Japan 全自治体 助成金 | ¥6T |
| JICA ODA | ¥1.7T |
| UN 人道援助 (WFP / UNICEF / UNHCR / Red Cross) | **$50B+** |
| 民間財団 (Gates / Buffett / その他) | **$200B+** |

**合計 addressable: ~¥40T 相当**。1% シェアでも年 ¥400B。

---

## 連絡先

- リポジトリ: <https://github.com/kota1026/JPN_PBM>
- License: Apache 2.0 (商用 / 二次利用 / fork 自由)
- Issue / PR / Discussion: GitHub 上で歓迎

---

*Round 23 (2026-05-20) 時点の状態。21 ラウンドの開発履歴は `docs/strategy-2026-*.md` 20 本に全記録。*
