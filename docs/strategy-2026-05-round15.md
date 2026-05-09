# 戦略会議 #15 — 動画記録パケット (R16)

> **作成日**: 2026-05-09 (round 16)
> **議題**: Round 15 で「外部解禁時の即応性」が完成。Round 16 では **実外交を始める前に**、JICA / TMG / DSWD / Quezon City / 国際フォーラムへ同時に展開できる **動画素材** を整備する。
> **アウトプット**: 6 件採択 (動画スクリプト 4 種 + 録画ガイド + 戦略文書英訳 1 本)

---

## 0. なぜ Round 16 で動画か

Round 1 で `docs/video-script.md` (Tokyo 4 分版) を作ったが、その後 14 ラウンドで以下が追加されている:

- マニラツインパイロット (4Ps + サリサリ + GCash + Tagalog UI)
- ハイブリッド eligibility + バーコードスマホスキャン
- CP-6 災害時フォールバックの世界初設計
- アダプタ層 (chain / gcash / landbank)
- JICA 申請書 + LoI テンプレ + DPG エビデンス

これらが **動画素材として未収録**。実外交が始まると「30 分のミーティング前に 5 分動画を見ておいてもらう」という運用が決定打になるため、宛先別に 4 種の動画スクリプトを用意する。

## 1. 採択 6 件

| # | エージェント | 提案 | 実装 | 影響 |
|---|--------------|------|------|------|
| **T0** | Researcher | 動画スクリプト index | `docs/video-scripts/README.md` (どれを誰に見せるかのガイド) | 4 種の使い分けを明文化 |
| **T1** | Researcher | 5 分 議員/課長級向け JP | `docs/video-scripts/01-pitch-5min-jp.md` | TMG / 江東区 DX 課に持ち込める |
| **T2** | Engineer | 15 分 技術担当 / 実務責任者向け JP | `docs/video-scripts/02-tech-deep-15min-jp.md` | DSWD 観察員 / 実装パートナーへ |
| **T3** | Researcher | 90 秒 国際 SNS / OECD teaser EN | `docs/video-scripts/03-international-90sec-en.md` | LinkedIn / X / OECD Blockchain Forum |
| **T4** | Researcher + Field | 5 分 マニラ pilot bilingual TL/EN | `docs/video-scripts/04-manila-pilot-5min-tl-en.md` | DSWD / Quezon City Innovation Office |
| **T5** | Engineer | 録画 / 編集 / 公開ガイド | `docs/video-scripts/05-recording-production-guide.md` | 機材 / OBS / Loom / 編集 / 多言語字幕 |
| **T6** | Researcher | Round 14 戦略会議英訳 | `docs/strategy-2026-05-round14-en.md` | i18n 14/15 維持 |

## 2. 4 動画の役割マトリクス

| 動画 | 長さ | 言語 | 想定視聴者 | 配信先 | 制作優先度 |
|------|------|------|-----------|--------|-----------|
| **01 Pitch 5min** | 5:00 | 🇯🇵 JP | 議員 / 課長級 / 首長 | YouTube unlisted, MoU 提出時の同梱 | ★★★ 即必要 |
| **02 Tech 15min** | 15:00 | 🇯🇵 JP | 実務責任者 / 担当課長 / 開発パートナー | YouTube unlisted | ★★ |
| **03 Intl 90sec** | 1:30 | 🇬🇧 EN | OECD / BIS / MAS / 国際 SNS | LinkedIn, X, Vimeo public | ★★★ 即必要 |
| **04 Manila 5min** | 5:00 | 🇵🇭 TL/EN | DSWD / Quezon City / Coins.ph | YouTube unlisted, 4 者ミーティング | ★★ |

R1 の `docs/video-script.md` (4 分 Tokyo 単体) は legacy として残し、R16 の 4 種は新ディレクトリ `docs/video-scripts/` に置く。

## 3. 共通の収録方針

- **生 UI を画面録画** (Photoshop で作った仮想 UI ではなく、本物の `/ui/` を Chrome で操作)
- **語り (ナレーション)** は別撮り、後で同期 (撮り直し容易性のため)
- **背景 BGM**: ロイヤリティフリー、無音区間 30%以上
- **キャプション (字幕)**: 全動画で **JP + EN** を mandatory、PH 動画は **TL + EN**
- **撮影環境**: macOS + QuickTime / Loom / OBS、ブラウザ ズーム 110% 推奨

## 4. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 267+ passed (Round 16 はスクリプト中心、テスト追加なし想定)
✓ verify(all) all green

$ ls docs/video-scripts/
README.md   01-pitch-5min-jp.md   02-tech-deep-15min-jp.md   03-international-90sec-en.md
04-manila-pilot-5min-tl-en.md  05-recording-production-guide.md
```

## 5. ポイント精算 (ラウンド 15 = PR #16)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Stablecoin Architect** | T1 chain + T2 gcash adapter (Mock + Real protocol + factory) | **+30** |
| Engineer | T1/T2/T3 シリーズの実装統合 + iOS hardening | +25 |
| Researcher | T5/T6 LoI テンプレ + DPG エビデンス + R13 英訳 | +20 |
| Purpose Guardian | T4 LandBank CP-5/CP-6 enforcement 設計 | +15 |
| Red Team | silent fallback 禁止の指摘 | +10 |
| Cost Guardian | gcash adapter idempotency 必須化 | +10 |
| Legal | LandBank bridge audit log フォーマット監修 | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Stablecoin Architect (+30) ─ Round 5/6 以来の MVP 復帰、3 アダプタを統一規約で実装。

## 6. ラウンド 17 候補

R16 完了後、サンドボックス内で残るタスクは **動画の実録画と公開** だけ (人間オペレータの作業)。実外交解禁が必要な領域:

1. JICA pre-screening 会話
2. Polygon Mumbai 実 RPC URL
3. Coins.ph 接触 → GCash sandbox API key
4. iPhone 実機での scanner 検証
5. 4 者 MoU 合意
6. **動画の実録画** (R16 のスクリプトを使って)

→ Round 17 はおそらく「人間が実働した結果のフィードバックをコードに反映」となる見込み (録画後の言い回し改善、JICA からのコメント対応 等)。

## 7. Phase 完了率 (R15 → R16 想定)

| Phase | R15 | R16 | 差分 |
|-------|-----|-----|------|
| Phase 1 | 86% | 86% | 変化なし |
| Phase 2 | 71% | 71% | 変化なし |
| Phase 3 | 40% | 40% | M+18 evidence 補強 (動画スクリプト 4 種を whitepaper §6.4 から参照) |

数値は変化なし、ただし **「動画 1 本送れる状態」になることで実外交ミーティング設定の障壁が大幅低下** という運用品質の向上。
