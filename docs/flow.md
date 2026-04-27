# フロー / シーケンス

## 1. 東京都: プログラム作成

```
東京都担当者              管理画面               Backend
   │                         │                     │
   │ プログラム入力           │                     │
   │  (対象 JAN, 助成率,      │                     │
   │   予算, 期間, 4情報要件) │                     │
   │ ──────────────────────► │                     │
   │                         │ POST /programs       │
   │                         │ ──────────────────► │
   │                         │                     │ INSERT programs
   │                         │                     │ Treasury.lock(JPYC, budget)
   │                         │ ◄────────────────── │ 201 program_id
```

## 2. 住民: マイナンバーカード認証 → PBM 受領

```
住民             住民ウォレット UI         Backend (auth, programs, wallet)
 │ NFC タップ         │                          │
 │ ─────────────────► │                          │
 │                    │ POST /auth/myna/login    │
 │                    │  {maina_id, name, addr,  │
 │                    │   dob, gender}           │
 │                    │ ────────────────────────►│
 │                    │ ◄────────────── pid, jwt│
 │                    │                          │
 │                    │ GET /programs/eligible  │  (4 情報で絞り込み)
 │                    │ ────────────────────────►│
 │                    │ ◄──── [program list] ── │
 │                    │                          │
 │ プログラム選択      │ POST /programs/{id}/issue│
 │ ─────────────────► │ ────────────────────────►│
 │                    │                          │ Eligibility.check(citizen, prog)
 │                    │                          │ PBMService.mint(prog, citizen)
 │                    │                          │ JPYC: program → escrow
 │                    │ ◄──── pbm_token ─────── │
 │ ◄── 残高更新 ───── │                          │
```

## 3. 加盟店: JAN スキャン購入

```
住民              加盟店 POS UI         Backend (purchase)            JPYC エスクロー
 │ 商品レジ            │                       │                            │
 │ ──────────────────► │                       │                            │
 │ 住民 QR (pid) 提示  │                       │                            │
 │ ──────────────────► │ POST /purchase        │                            │
 │                     │  {jan, qty, pid,      │                            │
 │                     │   store_id}           │                            │
 │                     │ ─────────────────────►│                            │
 │                     │                       │ 1) 商品参照 / 価格取得     │
 │                     │                       │ 2) 適用 PBM 検索           │
 │                     │                       │ 3) eligibility 再確認      │
 │                     │                       │ 4) 助成額算出              │
 │                     │                       │    subsidy = price * rate, │
 │                     │                       │    capped by remaining      │
 │                     │                       │ 5) Aunwrap PBM ──────────► │ store++ (JPYC)
 │                     │                       │ 6) 自己負担 JPYC ────────► │ store++ (JPYC)
 │                     │                       │ 7) EBPMEvent 記録          │
 │                     │ ◄──────── 200 ────── │                            │
 │ レシート ◄──────── │                       │                            │
```

## 4. EBPM: 集計閲覧

```
東京都政策担当       EBPM Dash UI       Backend
   │                   │                   │
   │ プログラム選択     │ GET /ebpm/summary │
   │ ─────────────────►│ ────────────────► │
   │                   │ ◄──── 集計 ──── │
   │ ◄── ダッシュボード│                   │
```

## 5. 失効・取消

- プログラムが期限切れになると、PBM トークンは自動で `EXPIRED` に。
  ロックされていた JPYC は東京都トレジャリーへ返却される。
- 不正検知時 (例: 同一住民が複数自治体で重複申請) は `revoke()` で個別失効。
