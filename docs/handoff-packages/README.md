# Handoff Packages — Per-Recipient Submission Bundles

Round 14 で追加 (戦略会議 #13 採択 T5)。

各宛先 (JICA / Coins.ph / DSWD / Quezon City LGU) に送る最小限のドキュメント
セットをディレクトリごとに整理。`scripts/build_handoff_package.sh <target>` で
zip 化して送付できる。

## 構成

```
docs/handoff-packages/
├── README.md            (本ファイル)
├── jica/                JICA Digital Public Goods 申請用
├── coins-ph/            Coins.ph (PHPC 発行体) 接触用
├── dswd/                DSWD (社会福祉省) 接触用 (Tagalog/English)
└── quezon-city/         Quezon City LGU 接触用
```

各 dir には:

| ファイル | 役割 |
|---------|------|
| `README.md` | 宛先用カバー (このパッケージは何で、何を期待されているか) |
| `01-letter.md` | カバーレター (短文 1 ページ) |
| `02-*` 〜 `0N-*` | 添付資料 (whitepaper / runbook / audit 結果 / 仕様書 等) |

## ビルド方法

```bash
$ bash scripts/build_handoff_package.sh jica
→ /tmp/jpn-pbm-handoff-jica-2026-05-09.zip

$ bash scripts/build_handoff_package.sh coins-ph
→ /tmp/jpn-pbm-handoff-coins-ph-2026-05-09.zip

$ bash scripts/build_handoff_package.sh --all
→ 4 つの zip を一括生成
```

zip にはこの dir の内容に加え、リポジトリのコア成果物 (whitepaper / pitch /
README / LICENSE / fork-guide) を相対パスで束ねる。実装は `scripts/build_handoff_package.sh` 参照。

## ステータス

| 宛先 | パッケージ完成度 | 実外交ステータス |
|------|-----------------|-----------------|
| JICA | ✅ v1 | 未接触 |
| Coins.ph | ✅ v1 | 未接触 |
| DSWD | ✅ v1 (Tagalog/English) | 未接触 |
| Quezon City | ✅ v1 | 未接触 |

実外交解禁後、各宛先からのフィードバックを反映して v2 を作る (Round 15+)。
