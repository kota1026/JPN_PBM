# 戦略会議 #12 — フィリピン側基盤完成 (PhilSys / QR Ph / 4Ps seed / JICA)

> **作成日**: 2026-05-08 (round 13)
> **議題**: マニラパイロットを **「画面で動くデモ」** から **「実外交パケット」** に進める。実 PhilSys API 仕様に沿った OAuth mock、EMV QR Code Specification 準拠の QR Ph parser、4Ps の seed データ、JICA Digital Public Goods 申請書 v1 を完成。
> **アウトプット**: 5 件採択 + 戦略文書英訳 1 本

---

## 0. Round 12 までの実装と Round 13 のギャップ

ラウンド 12 完了時点 (PR #13 draft) で:

- ✅ ハイブリッド `item_eligibility` (3 モード, 14 テスト)
- ✅ Tagalog/English citizen UI (`frontend/ph/citizen.html`)
- ✅ Manila ランディング (`frontend/ph/index.html`)
- ✅ QR vs JAN 調査ノート

**まだ無いもの**:

| ギャップ | 影響 | 対応ラウンド |
|---------|------|------------|
| 実 PH 商品マスタ (GS1 480 prefix) | フロントが「未登録 JAN」だらけ | **Round 13** |
| 実 PH 加盟店 / 4Ps program seed | プログラム ID 仮 | **Round 13** |
| PhilSys OAuth mock | フロントだけで HMAC、サーバ側プロバイダなし | **Round 13** |
| EMV QR Ph parser (フィールド 52 = MCC) | フロントが naive `MCH:id:mcc:name` 文字列で済ませている | **Round 13** |
| JICA 申請書 (英文) | 実外交を始める紙がない | **Round 13** |
| iPhone 実機 scanner 検証 | 実機なし | **Round 14** (実機テスト) |

→ **Round 13 はサンドボックス内で「実外交を始められる状態」まで仕上げる**。

## 1. 採択 5 件

| # | エージェント | 提案 | 実装 | 影響 |
|---|--------------|------|------|------|
| **T1** | Researcher | 4Ps seed (PH 商品 / 店舗 / 世帯 / プログラム) | `seed/ph/{citizens,products,stores,programs}.json` | フロントに本物相当の Lucky Me / Bear Brand / Pampers が並ぶ |
| **T2** | Stablecoin Architect | PhilSys OAuth mock | `backend/app/routers/philsys_oauth.py` (myna_oauth と同形) | 本番 PhilSys API に差替え可能なフロー完備 |
| **T3** | Engineer | EMV QR Ph parser (TLV) | `backend/app/services/qr_ph.py` + 8 テスト | BSP Circular 2019-859 準拠、CRC-16 検証つき |
| **T4** | Researcher | JICA Digital Public Goods 申請書 v1 | `docs/jica-application-draft-en.md` (~6 ページ) | JICA 大手町本部に持ち込める紙 |
| **T5** | Researcher | Round 11 戦略会議英訳 | `docs/strategy-2026-05-round11-en.md` | i18n 11/12 維持 |

## 2. PhilSys OAuth Mock の設計

`myna_oauth.py` (RFC 6749 Authorization Code Grant) と同形にする。違いは:

| 観点 | Myna ポータル v2 (JP) | PhilSys (PH) |
|------|----------------------|--------------|
| Endpoint base | `/myna/v2/...` | `/philsys/v1/...` |
| User claims | 4 情報 (氏名・住所・性別・生年月日) | PSN / Name / Address / Date of Birth / **No. of dependents** (4Ps 関連) |
| ID 抽象化 | HMAC(マイナンバー) | HMAC(PSN) |
| 同意画面文言 | 日本語 | English / Tagalog |
| 規制ロジック | 個情法 16 条 | Data Privacy Act of 2012 |

→ **両方とも `services/privacy.py:hmac_pid()` で擬似 ID 化、後段は同一**。Provider abstraction が綺麗に取れる。

## 3. EMV QR Ph parser の仕様

BSP の QR Ph Standard (Circular 2019-859) は EMV QR Code Specification (MPM Mode) に準拠。実装:

```python
def parse_emv_qr_ph(payload: str) -> QrPhInfo:
    """Parse EMV MPM QR string into structured fields.

    Format: TLV (Tag, Length, Value) sequence
        Tag    Field
        00     Payload Format Indicator ("01")
        02     Point of Initiation Method ("11"=static, "12"=dynamic)
        26-51  Merchant Account Information (PSP-specific subfields)
        52     Merchant Category Code (4-digit ISO 18245)  ← 我々のキー
        53     Transaction Currency ("608"=PHP)
        58     Country Code ("PH")
        59     Merchant Name
        60     Merchant City
        62     Additional Data (txID, mobile no., etc.)
        63     CRC-16 checksum (last 4 chars, polynomial 0x1021)
    """
```

CRC-16/CCITT-FALSE の検証もテストで担保 (改ざん検知)。

## 4. JICA Digital Public Goods 申請書の構成

JICA 公開フレームワーク (2024 年版) に沿った 6 セクション:

1. **Project Overview** (1 page) - 何を / 誰のために / なぜ
2. **Open Source / DPG Compliance** (1 page) - Apache 2.0 / DPG Standard 9 項目チェック
3. **Implementation Plan** (1 page) - 90 日 → 18 ヶ月の段階展開
4. **Counterpart Strategy** (1 page) - DSWD / Quezon City / Coins.ph 接触計画
5. **Budget** (1 page) - JPY 30M/year × 2 years 内訳
6. **Risk & Mitigation** (1 page) - PHPC 信用リスク / DSWD 政権交代リスク 等

**DPG Standard 9 項目** (Digital Public Goods Alliance) のセルフ評価表を別添。

## 5. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 175+ passed (R12 168 → R13 +8 qr_ph + tbd)
✓ verify(all) all green

$ # 起動して /ui/ph/citizen.html → 4Ps seed が表示
```

## 6. ポイント精算 (ラウンド 12 = PR #13)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | T1 citizen scanner + T2 PH UI + T3 hybrid eligibility + T4/T5 docs | **+30** |
| Researcher | T4 QR vs JAN 調査ノート | +20 |
| **CSO/AML** | ALWAYS_BLOCKED_MCCS の選定 + tingi cap 設計 | **+15** |
| Red Team | サリサリでバーコードがあるはず指摘 | +15 |
| Cost Guardian | hybrid mode の `cap_no_barcode_jpy` 設計 | +10 |
| Purpose Guardian | MCC 5921 / 5993 / 5813 / 7995 の常時ブロック | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Engineer (+30, 4 ラウンド連続)。**Red Team の指摘採用が今ラウンドの設計改善の核**。

## 7. ラウンド 14 候補

サンドボックス内で更に進める:

1. **PH POS SDK** (`sdk/python/jpn_pbm_pos_ph/`) - GCash mock 連携
2. **multi-locale seed loader** (`seed/{jp,ph}/` を `--locale` で切替)
3. **JICA / DPG Alliance 申請パッケージ zip 化** (whitepaper + pitch + audit + license の bundle)
4. **Loom 動画スクリプト** (議員説明 5 分 + 担当課長 15 分の 2 種)
5. **ホワイトペーパー §4 (CP-6) と §6 (Roadmap) の英文を Manila 章で更新**

実外交 ready のフォルダ:
6. `docs/handoff-packages/{jica,bsp,dswd,coins-ph,quezon-city}/` ─ 提出物専用 dir

## 8. Phase 完了率の推移

| 時点 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| R10 完了 | 86% | 57% | 0% |
| R11 完了 | 86% | 71% | 20% |
| R12 完了 | 86% | 71% | 20% (UI 実装で M+16 の evidence 増) |
| **R13 完了予定** | **86%** | **71%** | **40%** ← M+16 (他自治体 fork) を **partial → ready** に格上げ |

M+16 を ready に格上げできる根拠:
- ✅ コードベース共通 (Tokyo + Manila で 99% 共有確認)
- ✅ ハイブリッド eligibility 実装済 (`item_eligibility.py`)
- ✅ Tagalog/English UI 完成
- ✅ PH seed (本ラウンドで完成)
- ✅ PhilSys OAuth (本ラウンドで完成)
- ✅ JICA 申請書ドラフト (本ラウンドで完成)
- ❌ 実 DSWD / Quezon City 合意 (これだけ実外交)
