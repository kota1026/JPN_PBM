# JPN_PBM — 東京都ステーブルコイン助成金 PBM MVP

東京都の「Web3 / ステーブルコインを活用した行政サービス」助成金エントリ向けの
**PBM (Purpose Bound Money)** MVP 実装。

JPYC をラップしたプログラマブルマネーで、JAN コードによる商品識別と、
マイナンバーカードから取得できる 4 情報（氏名・住所・生年月日・性別）による
受給資格判定を組み合わせ、助成金が「目的どおり」に使われたことを保証しつつ、
全取引を EBPM (Evidence-Based Policy Making) 基盤へ蓄積する。

## ハイライト

- **PBM ラッパー**: JPYC を Purpose 付きでロック → 条件成立時のみ自動アンラップ
- **JAN 識別**: 商品マスタ × プログラム対象 JAN リストで購入判定
- **マイナンバー 4 情報**: 住所＝都内 / 年齢 / 性別 等を eligibility に利用
- **EBPM ダッシュボード**: 年齢層 × 地域 × 商品カテゴリ × 時刻の助成効果可視化
- **プライバシー**: 4 情報は HMAC で擬似 ID 化し、個票は外部に出さず集計のみ提供

## ディレクトリ構成

```
JPN_PBM/
├── README.md
├── docs/
│   ├── architecture.md       # 全体設計
│   ├── ebpm.md               # EBPM 設計と KPI
│   └── flow.md               # ユーザーフロー / シーケンス
├── contracts/
│   └── PBM.sol               # 参考用 Solidity (オンチェーン実装の指針)
├── backend/                  # FastAPI 実装 (MVP の中核)
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models/
│   │   ├── routers/
│   │   └── services/
│   └── tests/
├── frontend/                 # 4 つのロール別最小 UI
│   ├── tokyo.html            # 東京都: プログラム作成・予算管理
│   ├── citizen.html          # 住民: マイナンバー認証 + ウォレット + 購入
│   ├── retailer.html         # 加盟店: JAN スキャン POS
│   └── ebpm.html             # EBPM ダッシュボード
└── seed/
    ├── products.json         # サンプル JAN 商品マスタ
    ├── programs.json         # サンプル助成金プログラム
    └── citizens.json         # ダミー住民 (マイナンバー疑似データ)
```

## 起動方法

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

ブラウザで:

- 東京都管理: http://localhost:8000/ui/tokyo.html
- 住民ウォレット: http://localhost:8000/ui/citizen.html
- 加盟店 POS: http://localhost:8000/ui/retailer.html
- EBPM ダッシュボード: http://localhost:8000/ui/ebpm.html

API ドキュメントは http://localhost:8000/docs (Swagger UI)。

## 想定する助成金プログラム例

1. **省エネ家電購入支援**: 都内在住者に対し、対象 JAN の家電購入額の 30% (上限 5 万円) を助成
2. **子育て家庭食品支援**: 0–18 歳の子を持つ世帯に、対象 JAN の食品 1 万円分を毎月支給
3. **高齢者ヘルスケア商品支援**: 65 歳以上の都内在住者に、対象 JAN の医薬品・栄養食品の 50% を助成

## ロードマップ

- [x] MVP: モック JPYC・モックマイナポータル・SQLite
- [ ] JPYC v2 (ERC-20) との結合 (Polygon zkEVM 想定)
- [ ] マイナポータル API (公的個人認証) 連携
- [ ] 加盟店 POS SDK (バーコード読取 + JPYC 決済)
- [ ] 都税・住民税控除との連動
