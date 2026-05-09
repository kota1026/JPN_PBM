# iPhone Scanner Manual Test Checklist (Round 15)

> **目的**: `frontend/scanner.js` が iPhone 実機 (Safari iOS 16/17/18) で動くかを 手動で検証するチェックリスト。サンドボックスでは Web BarcodeDetector の iOS 対応状況を断定できないため、実機ありオペレータ向けの台本。
>
> **実施タイミング**: Coins.ph または江東区 DX 課から **iPhone 13 / iPhone 15 を 1 台ずつ借りられた日** に実施。
> 所要時間: 約 30 分。

---

## 0. 事前準備 (5 分)

| 項目 | 確認 |
|------|------|
| 実機 iPhone (iOS 17 推奨) | ☐ |
| iPhone 13 (iOS 16 残存ユーザ向け) | ☐ |
| ブラウザ Safari の最新化 (Settings → General → Software Update) | ☐ |
| HTTPS でアクセスできる URL (`https://localhost` は iOS で動かない) | ☐ — ngrok / Cloudflare Tunnel で公開 |
| 試験用 EAN-13 バーコード (例: Bear Brand 4806515600015 を印刷 or PC 画面表示) | ☐ |
| 試験用 QR コード (`/ui/citizen.html` の災害用 QR を印刷) | ☐ |
| GS1 480 prefix のフィリピン商品 (実物手配可能なら) | ☐ — 任意 |

ngrok 起動例:
```bash
$ ngrok http 8000
→ https://xxxx.ngrok-free.app  (この URL を iPhone Safari に入力)
```

## 1. iOS Safari 実機確認 (各 5 分)

### 1.1 iPhone 15 (iOS 17+, BarcodeDetector 期待動作)

| ステップ | 期待 | 結果 |
|----------|------|------|
| Safari で `https://xxxx.ngrok-free.app/ui/citizen.html` を開く | 認証画面が表示 | ☐ |
| 「マイナンバーカードで認証」 を実行 | QR が表示 | ☐ |
| ⑥ 事前スキャン試算セクションへスクロール | 「📷 商品をスキャン」ボタンが表示 | ☐ |
| 「📷 商品をスキャン」をタップ | カメラ許可ダイアログ | ☐ |
| カメラ許可を 許可 | ライブ映像が表示 | ☐ |
| 試験用バーコード (印刷物) をかざす | バーコード値が読み取り、商品名が表示 | ☐ |
| 試験用 QR をかざす | QR 中の文字列が読み取り | ☐ |

**コンソール (Web Inspector) で確認**:
- `BarcodeDetector` が `window` にあるか? (= ネイティブ対応)
- 対応フォーマット (`getSupportedFormats()`) に `ean_13`, `qr_code` が含まれるか?
- 含まれない場合は ZXing fallback に切替わったか?

### 1.2 iPhone 13 (iOS 16, BarcodeDetector 制限の可能性)

| ステップ | 期待 | 結果 |
|----------|------|------|
| 同 URL を Safari で開く | 認証画面が表示 | ☐ |
| 商品スキャンを実行 | **ZXing fallback** に切替わる (BarcodeDetector が EAN-13 未対応のため) | ☐ |
| バーコード読み取り | 数秒以内に成功 | ☐ |

**期待される挙動**:
- ZXing.js (CDN 経由) が ~290KB ダウンロード
- 初回 detect は 300-800ms かかる (バンドル展開)
- 一度 ZXing が起動した後は 100-200ms 程度

## 2. PH UI (`/ui/ph/citizen.html`) 動作確認 (5 分)

| ステップ | 期待 | 結果 |
|----------|------|------|
| `/ui/ph/index.html` を開く | Tagalog ランディング表示 | ☐ |
| 「Citizen wallet (Tagalog/EN)」をタップ | citizen.html が Tagalog で起動 | ☐ |
| 言語切替 (English) をタップ | 全テキストが英語に切替 | ☐ |
| ① mock login (`PH-0001`) を実行 | PID hash が表示 | ☐ |
| ② Scan merchant QR → カメラ起動 → QR をかざす | merchant 情報 (MCC 5411) が表示、緑のバッジ | ☐ |
| ③ 「Scan Barcode」 → 製品バーコードをかざす | カートに追加 | ☐ |
| ③ 「Tingi item」 ボタン → price 入力 (PHP 15) | カートに追加 | ☐ |
| ④ 合計 / 補助 / 自己負担 が正しく計算 | total - subsidy = self pay | ☐ |
| ④ Pay now (mock) | 緑のレシート表示 | ☐ |

## 3. 失敗ケース (各 2 分)

| ケース | 期待 | 結果 |
|--------|------|------|
| カメラ許可を拒否 | エラー表示 + 手入力欄が表示される | ☐ |
| 改ざんされた QR (CRC mismatch) を読む | ZXing は読み取り成功するが、サーバ側 verify で reject | ☐ |
| ブラックリスト MCC (5921 liquor) の merchant QR | 赤いバッジ + "BLOCKED" 表示 | ☐ |
| バーコード無し商品で `cap_no_barcode` 超過 | カート行が "対象外" 扱い (理由メッセージあり) | ☐ |
| ネット切断中に商品スキャン | 一覧は出るが API 叩けず "対象外" 扱い (商品マスタ未引取のため) | ☐ |

## 4. 性能 (各 1 分)

| 指標 | 目標 | 実測 (記入) |
|------|------|-------------|
| 初回ページロード (キャッシュ無し) | < 3 秒 | _____ ms |
| カメラ起動からバーコード読み取りまで | < 1 秒 (ネイティブ) / < 2 秒 (ZXing) | _____ ms |
| 商品マスタ照会 (`/products/{jan}`) | < 200ms | _____ ms |
| カート 5 件で estimate_cart 計算 | < 500ms | _____ ms |

## 5. レポート フォーマット

実機テスト終了後、以下の形式で実施者がコメントを `frontend/scanner.js` の上部に追記:

```javascript
/* iPhone Manual Test Results (記入日: YYYY-MM-DD)
   Device: iPhone 15 / iOS 17.4 / Safari
   - BarcodeDetector ネイティブ対応: YES
   - ean_13 / qr_code 両方検出: YES
   - 平均 detect time: 120ms
   - issues: なし
*/
```

これにより repo を読む人が「実機で何が確認されたか」を即把握できる。

## 6. 既知の落とし穴

- **iOS 16 以下**: BarcodeDetector は QR のみ対応、EAN-13 は ZXing 経由必須。
- **HTTPS 必須**: `getUserMedia` は localhost と HTTPS 以外で動かない。
- **Camera 反転**: フロントカメラ (selfie) で起動すると逆向きで読みづらい。`facingMode: 'environment'` を必ず指定済 (`scanner.js:53`)。
- **Safari の Tab 切替で stream が止まる**: 戻った時に再起動するロジックは未実装。手動で「リセット」ボタンを押し直す。

## 7. 失敗した場合の応急処置

| 失敗事象 | 緊急対応 |
|---------|---------|
| iOS 17 Safari でカメラが全く起動しない | URL が HTTPS であることを再確認、別ブラウザ (Chrome iOS) で試す |
| ZXing fallback で 10 秒以上読まない | 解像度を下げる (`video: { width: 640, height: 480 }`) |
| 商品マスタ未登録で空表示 | `/seed/load?locale=ph` を再実行、店舗が認定済みか確認 |
| "Pay now" で API エラー | この PR ではフロントだけの mock。backend `/purchase/with-context` 統合は Round 16+ |

## 8. 報告書テンプレ

実施完了後、以下を `docs/handoff-packages/quezon-city/04-iphone-test-results.md` などに記録:

```
## iPhone Test Results — YYYY-MM-DD

| Device       | iOS  | Browser    | BarcodeDetector | ZXing fallback | Pass/Fail |
|--------------|------|------------|-----------------|----------------|-----------|
| iPhone 15    | 17.4 | Safari     | YES (EAN-13 OK) | not used       | PASS      |
| iPhone 13    | 16.7 | Safari     | YES (QR only)   | YES (EAN-13)   | PASS      |
| iPhone 12    | 18.0 | Chrome iOS | NO              | YES            | PASS      |

Notes:
- ……
```
