# Video Scripts — Selection Guide

> **Created**: 2026-05-09 (Round 16)
> **目的**: 4 種類の動画スクリプトを **誰に / いつ / どこで** 使うかのガイド。
> 実録画は人間オペレータが本ガイドと各スクリプトを使って Loom / OBS で実施する。

---

## 4 種類の動画

| # | スクリプト | 長さ | 言語 | 想定視聴者 | 配信先 | 制作優先度 |
|---|-----------|------|------|-----------|--------|----------|
| **01** | [`01-pitch-5min-jp.md`](./01-pitch-5min-jp.md) | 5:00 | 🇯🇵 JP | 議員 / 課長級 / 首長 / 副市長 | YouTube unlisted、MoU 提出時の同梱、ピッチデッキの末尾 QR | ★★★ 即必要 |
| **02** | [`02-tech-deep-15min-jp.md`](./02-tech-deep-15min-jp.md) | 15:00 | 🇯🇵 JP | 実務責任者 / 担当課長 / TIS / JPYC 技術陣 | YouTube unlisted、技術ミーティング前事前視聴 | ★★ |
| **03** | [`03-international-90sec-en.md`](./03-international-90sec-en.md) | 1:30 | 🇬🇧 EN | OECD / BIS / MAS / 国際投資家 / SNS フォロワー | LinkedIn / X / Vimeo public、OECD Blockchain Forum 投稿 | ★★★ 即必要 |
| **04** | [`04-manila-pilot-5min-tl-en.md`](./04-manila-pilot-5min-tl-en.md) | 5:00 | 🇵🇭 TL/EN | DSWD / Quezon City Innovation Office / Coins.ph | YouTube unlisted、4 者ミーティング前視聴 | ★★ |

実録画段取り: [`05-recording-production-guide.md`](./05-recording-production-guide.md)

## 「どれを送れば良いか」フローチャート

```
あなたが連絡する相手は誰?
│
├─ 都議会議員 / 副市長級 / 首長
│  → 01 (5 min JP)
│
├─ TMG 課長級 / 江東区 DX 課
│  → 01 (5 min JP) を最初、続けて 02 (15 min JP) を「気に入ったら」
│
├─ TIS / JPYC Inc. の技術陣
│  → 02 (15 min JP)
│
├─ JICA 国際協力機構 (DPG team)
│  → 03 (90 sec EN) でアテンション → 02 (JP) が刺さる人もいる
│
├─ Coins.ph CEO 室
│  → 03 (90 sec EN) → 04 (5 min Manila) の順
│
├─ DSWD / フィリピン関係者
│  → 04 (5 min Manila TL/EN)
│
├─ Quezon City Mayor's Office
│  → 04 (5 min Manila TL/EN)
│
├─ OECD / BIS Agorá / MAS Project Orchid 関係者
│  → 03 (90 sec EN) のみ。詳細はホワイトペーパー (docs/whitepaper-2026.md)
│
├─ X / LinkedIn 投稿
│  → 03 (90 sec EN) のみ
│
└─ 開発者 / OSS コントリビュータ候補
   → 02 (15 min JP) または英訳版
```

## 制作の順番 (おすすめ)

1. **03 国際 90 秒 EN** ─ 最短で SNS 公開できる、JPN-PBM の存在を世界に告知
2. **01 国内 5 分 JP** ─ 都議会・江東区への営業で必携
3. **04 Manila 5 分 TL/EN** ─ DSWD / Quezon City 接触時に同梱
4. **02 技術 15 分 JP** ─ 1 と 3 で関心を引いた後の 2 段目資料

## 共通の収録方針

- **生 UI 録画**: Photoshop モックではなく、本物の `frontend/` を Chrome で操作
- **音声は別撮り**: ナレーション と 操作画面 を別々に録音 → 編集で同期 (撮り直しが容易)
- **字幕 mandatory**: 全動画 JP + EN、PH 動画は TL + EN
- **BGM**: ロイヤリティフリー、無音 30%以上
- **ブラウザ**: Chrome / Edge、ズーム 110%、シークレットモード推奨
- **解像度**: 1920×1080 30fps、最終出力 H.264 mp4

詳細は `05-recording-production-guide.md`。

## 各動画の中で必ず見せるシーン

| シーン | 01 | 02 | 03 | 04 |
|--------|----|----|-----|-----|
| `/ui/index.html` トップページ | ✓ | ✓ | ✓ | △ (PH 版) |
| `/ui/citizen.html` マイナ認証 | ✓ | ✓ | ✓ | (PhilSys) |
| `/ui/retailer.html` POS スキャン | ✓ | ✓ | △ | (PH 版) |
| `/ui/tokyo.html` 都ダッシュボード | ☐ | ✓ | ✓ | ☐ |
| `/ui/ebpm.html` k-匿名集計 | ☐ | ✓ | ☐ | △ |
| ⑥ 事前スキャン試算 (citizen.html) | △ | ✓ | ✓ | ✓ |
| `/ui/ph/index.html` Manila ランディング | ☐ | △ | ✓ | ✓ |
| `/ui/ph/citizen.html` Tagalog UI | ☐ | △ | ☐ | ✓ |
| 災害用 QR 発行 (CP-6) | ✓ | ✓ | ✓ | ✓ |
| ターミナル `verify.sh all` 走行 | ☐ | ✓ | ☐ | ☐ |

凡例: ✓ 必須、△ 任意、☐ 不要

## 公開時の運用

| 配信先 | 設定 | 公開期間 |
|--------|------|----------|
| YouTube unlisted | 検索除外、URL 知る人のみ | 永続 |
| Vimeo public | パスワードなし、SNS シェア可 | 永続 |
| LinkedIn (90秒のみ) | 自然動画 + 字幕埋め込み | 投稿後 1 ヶ月活発 |
| X / Twitter (60秒以下) | 90秒は分割 or 14日トリミング | 即時 |
| GitHub README に埋込 (gif 化) | サムネ静止画 + クリック誘導 | 永続 |

## 著作権 / Apache 2.0

- 動画自体: CC-BY 4.0 で公開推奨 (商業二次利用も可、引用元明記のみ)
- BGM: ロイヤリティフリー (Pixabay / Free Music Archive)
- フォント: 商業利用可能なもの (Noto Sans / Inter / Lato)
- 出演者: スタッフ写真は同意書必須、アイコン素材は無問題

## ステータス

| 動画 | スクリプト | 録画 | 字幕 | 公開 |
|------|-----------|------|------|------|
| 01 Pitch 5min JP | ✅ R16 | ☐ | ☐ | ☐ |
| 02 Tech 15min JP | ✅ R16 | ☐ | ☐ | ☐ |
| 03 Intl 90sec EN | ✅ R16 | ☐ | ☐ | ☐ |
| 04 Manila 5min TL/EN | ✅ R16 | ☐ | ☐ | ☐ |

実録画は実機 + 人間オペレータが必要なため Round 17 以降 (実外交解禁と並行)。
