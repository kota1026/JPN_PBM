---
marp: true
theme: default
paginate: true
size: 16:9
header: "JPN-PBM ─ 友人向け紹介"
footer: "2026-05 · github.com/kota1026/JPN_PBM"
style: |
  section { font-size: 24px; font-family: "Hiragino Sans", "Yu Gothic", "Noto Sans JP", sans-serif; }
  h1 { color: #102b4f; }
  h2 { color: #1f4068; border-bottom: 3px solid #1f4068; padding-bottom: 6px; }
  table { font-size: 20px; }
  code { background: #f1f3f5; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
  .big { font-size: 56px; font-weight: 700; color: #00A040; }
  .lede { font-size: 22px; color: #495057; }
  .quote { background: #fff8db; padding: 16px 20px; border-left: 6px solid #f59f00; font-style: italic; }
  .ok { color: #2b8a3e; font-weight: 700; }
  .not-yet { color: #c92a2a; font-weight: 700; }
  .small { font-size: 16px; color: #868e96; }
---

<!-- _class: lead -->

# JPN-PBM の冒険

## 1 ヶ月で何を作ったか

東京都の助成金を「目的どおりに使えるお金」にする、ぐらいのことを試したよ。
副産物としてフィリピンの 4Ps もカバーした。

**(全部 OSS / Apache 2.0)**

---

## ざっくり何を作ったか

> 「東京都の助成金を、紙の券じゃなくて **使い道がプログラムされたお金 (PBM)** で配ったら、
> 目的外利用が物理的に起きないし、災害時にも止まらないんじゃない？」

を、19 ラウンド回して **手元で動くところまで** 持ってきた。

副産物:
- フィリピン (DSWD 4Ps) も同じコードで動くようにした
- JICA に申請する書類まで書いた
- ホワイトペーパー 英文 30 ページくらい
- セルフ監査 24 項目クリア
- 5 分自動デモも作った

---

## 始まりの問い

東京都が 1 年に配ってる助成金 = **23 区合計 ¥640B**

そのうち、**目的外利用 (子育て券で酒買うとか) で 3-7% 漏れてる**。

```
3-7% × ¥640B = ¥19-44 B / 年が静かに失われている
```

これを **「お金そのもの にルールを書き込む」** ことで止められないか?

---

## アイデア ─ Purpose Bound Money (PBM)

> 使い道がプログラムされた円

```
通常の JPYC: 誰でも・どこでも・何にでも使える
              ↓ wrap
PBM:          ├─ 江東区在住 3 歳児がいる世帯のみ
              ├─ 認定加盟店のみ (区が登録した店)
              ├─ 育児用品 JAN コードのみ
              ├─ 期間内 (2026/4-2027/3)
              └─ 月 ¥10,000 まで
                  ↑ 5 つ全部満たさないと 1 円も動かない
```

ブロックチェーンの強制力で、**目的外利用が「あとで気づく」じゃなくて「最初から起きない」**。

---

## 登場人物 4 役

```
┌────────────┐    ┌────────────┐
│ ①東京都    │ →  │ ②住民       │ ← マイナで認証 → PBM 受領 → QR 取得
│ 予算ロック  │    │            │
└────────────┘    └─────┬──────┘
                         │ QR
                         ▼
┌────────────┐    ┌────────────┐
│ ④EBPM 分析  │ ←  │ ③加盟店レジ │ ← JAN スキャン → 自動補助
│ k=5 匿名集計│    │            │
└────────────┘    └────────────┘
```

各役割で実際に動く画面 (`/ui/citizen.html` 等) が手元にある。

---

## やってみたら動いた

5 分の **自動デモ** あるからまず見てよ:

→ <https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/claude/round17-auto-demo/frontend/demo.html>

ブラウザだけで動く、インストール何もいらない。
日本語 / English / Tagalog 切替もできる。

(これ作るのに 1 日。Loom 動画より安く付いた)

---

## 一番ユニークなところ ─ 11 役の戦略会議

実装した機能の決め方が特殊で、**毎ラウンド 11 役のエージェントが議論** して採択を決めてた:

| 役職 | 何する人 |
|------|---------|
| Engineer | コード書く |
| Researcher | 文書 / 国際比較 / 英訳 |
| Stablecoin Architect | ECDSA / HSM / adapter |
| Cost Guardian | 予算 / 負荷試験 |
| **Red Team** | **「ここ穴あるよ」と言う担当** |
| Purpose Guardian | CP-1〜CP-7 整合性 |
| CSO/AML / Legal / CFO / Field Officer 等 | 専門担当 |

毎回 MVP 認定して点数つけてた (Engineer が 5 ラウンド連続 MVP 取ったり)。

---

## ピボット 1: 「サリサリの POS って無くない？」

フィリピン (マニラ) 展開を検討したら、現場視点で **設計が破綻**:

- フィリピンの 4Ps 受給者は サリサリ (= 小さな雑貨屋) で買い物する
- でも **サリサリには POS スキャナが 1 割未満しかない**
- 商品もティンギ (sachet) で売られて、バーコード無いやつ多い

→ **「受給者が自分のスマホでバーコードを読む」** モデルに変更。
バーコード付き → 厳格判定、無いやつ → 店舗の MCC で fallback (= ハイブリッド)。

これ Tokyo の個人商店にも逆輸入できることが判明 (副産物)。

---

## ピボット 2: 「災害時の POS って…」 (← 君が指摘した)

最初 CP-6 (世界初の差別化要素!) として書いてたんだけど、ある人に:

<div class="quote">

「災害時に加盟店POSって動いてなくない？そもそもなんだけど。」

</div>

って指摘されて、ハッとした。**確かに動かない**。停電で POS は 0-7 日 OFF、店舗倒壊、店員避難。

→ 設計を **やり直し**:
- **JP**: マイナンバーの Felica SE + 避難所端末 (発電機 + Starlink)
- **PH**: 紙 voucher + サリサリ lista + バランガイ + Red Cross 立会

「世界初」表現も撤回 (撤回したら逆に honest で説得力が上がった)。

---

## ピボット 3: 「Bayanihan、文化的に違うよ」

フィリピン設計の名前を **「Lista Bayanihan モデル」** にしてたんだけど、
仮想の人類学者ペルソナ (Dr. Carmela Reyes, UP Diliman) が:

<div class="quote">

「Bayanihan は **短期互恵** が本義。長期制度には不適。
ロマンチック化された貧困観に陥る危険がある。」

</div>

→ 「**Disaster Lista (DL) Protocol**」 に名称変更 (機能を直接表現)。

エージェントが本気で批判してくる議事録、自分で読み返しても面白い。

---

## 数字で見る進捗

| 指標 | 値 |
|------|-----|
| ラウンド数 | **19** |
| バックエンドテスト | **315 passed** |
| Solidity コントラクト | 2 (PBM + 災害時) |
| API ルータ | 13 / サービス 26 |
| ドキュメント | 62 本 (戦略会議議事録 17 + 英訳 16 等) |
| HTML 画面 | 9 (JP/EN/Tagalog 各種 + 自動デモ) |
| GitHub Actions CI | 全 PR 緑 |
| セルフ監査 (24 項目 × 2 contracts) | ok=40 / warn=4 / fail=0 |

---

## 何ができていないか (正直)

サンドボックス内では一通り終わったけど、**実外交 / 実機が要る部分**:

- ❌ Polygon Mumbai 実デプロイ (RPC URL 必要)
- ❌ GCash sandbox API 連携 (Coins.ph 接触必要)
- ❌ iPhone 実機での scanner 検証 (実機必要)
- ❌ DSWD 4Ps の実 LandBank 統合 (政策合意必要)
- ❌ JICA pre-screening の v3 改訂 (会話必要)
- ❌ 避難所端末の実機テスト (Starlink mini + NFC + 発電機 必要)

**設計とコードは全部できてる**、外部資源待ち。

---

## 何がフェアだったか

- 「世界初」と書いたら **設計欠陥が見つかった** → 撤回した
- 「Lista Bayanihan」と命名したら **文化的批判** が出た → 改名した
- 「サリサリでも POS 動く」と仮定したら **現場視点で覆された** → ハイブリッドに修正
- 「動画作る」と決めたけど **収録できる人いない** → 自動再生デモに転換

**間違いを認めてピボットできる速度** が、技術プロジェクトの本当の価値かもね。

---

## 君に頼みたいこと

もし時間あったら:

1. **デモ見て感想ちょうだい** — <https://htmlpreview.github.io/?https://raw.githubusercontent.com/kota1026/JPN_PBM/claude/round17-auto-demo/frontend/demo.html>
2. **GitHub 見て star してくれると嬉しい** — <https://github.com/kota1026/JPN_PBM>
3. **「ここ穴ない？」って Red Team してほしい** ─ 過去の指摘で 2 回設計変わってる
4. **東京都 / 江東区 / DSWD / Coins.ph / JICA に **知り合いいたら紹介して** — 実外交を求めてる

逆に「これ要らなくない？」とか「他にもっと面白いユースケースある」もウェルカム。

---

<!-- _class: lead -->

# 以上

19 ラウンドの冒険でした。

「**プログラム可能な お金** + **災害時にも止まらない 設計** + **文化に合った 2 国実装**」を、サンドボックスで完走。

実外交解禁を待つフェーズに入った。
何か声かけてくれると嬉しい。

```
github.com/kota1026/JPN_PBM
Apache 2.0
```
