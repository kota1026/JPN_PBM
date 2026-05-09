# Philippines (Manila) Seed Data

Round 13 で追加。`seed/{citizens,products,stores,programs}.json` (Tokyo) と並列の PH 版。

## ファイル一覧

| ファイル | 件数 | 内容 |
|---------|-----|------|
| `citizens.json` | 8 | mock 4Ps 受給世帯 (PSN / 名前 / 子供数 / 居住市) |
| `products.json` | 25 | GS1 prefix 480 (PH) 商品 (食品・日用品・ベビー) |
| `stores.json` | 8 | sari-sari + Mercury Drug + 7-Eleven、`mcc` と `qr_ph_id` 含む |
| `programs.json` | 2 | `prog-4ps-2026` (DSWD パイロット) + `prog-disaster-typhoon-2026` (台風備蓄) |

## 通貨単位の変換

PHP は **小数点 2 桁** (centavo)。本コードベースの内部は **整数 centavos** で保持:

```
PHP 85.00 = 8500 centavos
PHP  0.50 =   50 centavos
```

JP の `price_jpy` (整数 yen) と並列に `price_centavos` で表現。サービスレイヤは
両者を「最小単位 (yen / centavo) の整数」として透過的に扱う。

## 4Ps プログラムの設計

`prog-4ps-2026`:

- **subsidy**: 60% (DSWD 想定)
- **per_citizen_cap**: PHP 1,400 / 月 (4Ps 標準支給額)
- **cap_no_barcode**: PHP 300 / 月 (tingi / 量り売り用)
- **mode**: `hybrid`
- **approved_mccs**: 5411 (grocery) / 5499 (misc food) / 5912 (drug)
- **blocked_mccs**: 5921 (liquor) / 5993 (tobacco) / 5813 (drinking) / 7995 (gambling)

## 既存ローダとの互換性

`backend/migrations/__init__.py` (Round 11 までの seed loader) は `seed/*.json` を
直接読みに行く。Round 13 の本 PH seed は **読み込まれない** ─ 将来 Round 14 で
`--locale ph` フラグまたは別 endpoint `/ph/seed/load` を追加して切替えられるようにする。

それまでは:
- `frontend/ph/citizen.html` が直接 fetch する選択肢
- 手動で `python -m migrations --locale ph` のように切替える選択肢

両方検討した上で Round 14 で実装する。
