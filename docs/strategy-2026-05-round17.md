# 戦略会議 #16 + #17 — CP-6 災害時オフライン認証 再設計 (連続セッション)

> **作成日**: 2026-05-09 (round 18)
> **議題**: 災害時 CP-6 v1 設計に重大な前提誤り (POS 動作前提) → JP / PH 両国の v2 設計
> **形式**: 戦略会議 #16 (initial council) + #17 (red-team review with 4 PH ground-truth personas)
> **アウトプット**: JP 採択 6 件 + PH 採択 11 件 + 共通修正 4 件

---

## 0. 前史: なぜ再設計が必要か

ユーザーからの 1 行の指摘:

> **「災害時に加盟店POSって動いてなくない？」**

これが CP-6 v1 (`docs/cp6-offline-fallback.md`) の根本的欠陥を露呈:

| v1 が暗黙に仮定 | 実態 |
|----------------|------|
| 加盟店 POS が電源 ON | ❌ 大半が停電 |
| 店員が店舗にいる | ❌ 自分も避難 |
| POS が DB を保持 | △ バッテリー切れで喪失 |
| 紙レシート用紙がある | ❌ 補給途絶 |

**問いの再定義**: 「電源も通信も無い状況で、なりすまし防止 + 二重支給防止を担保する認証はどう設計するか」

---

## 1. 過去の議論 (BoJ + BIS + ECB) ─ 5 つの解の方向性

| ID | アプローチ | 例 | オフライン動作 | 電源 | 二重支給防止 |
|----|----------|-----|--------------|-----|------------|
| **A** | SE 内蔵 prepaid (Felica/Suica) | BoJ Phase 2 Pilot, Suica | ✅ 完全 | △ 端末側 | SE counter |
| **B** | 2-tier wallet (smartphone + IC card) | Banque de France, BoJ Forum 2023 | ✅ | △ | 同上 |
| **C** | Time-limited offline credit | ECB Digital Euro, Visa floor | ✅ 限度額内 | △ | pre-auth + reconcile |
| **D** | Hash-chain ticket | BIS Project Polaris | ✅ | △ | hash 不可逆 + counter |
| **E** | Government endpoint terminal | 311 後 SDF 配給 | ✅ (衛星) | ✅ 専用 | 公務員管理 |

---

## 2. 戦略会議 #16 — Initial Council (PH only)

参加: Field Officer, Researcher, Stablecoin Architect, Cost Guardian, Red Team, Purpose Guardian, CSO/AML, Legal, CFO, Engineer, **🆕 Local Diplomacy Officer, 🆕 Disaster Response Officer (PH 専用)**

**初回採択 8 件** (PH-1 〜 PH-8):

| ID | 採択 |
|----|------|
| PH-1 | 5 層 Lista Bayanihan モデル ─ 紙 + lista + barangay + GCash + Coins.ph |
| PH-2 | `lista_adapter.py` mock |
| PH-3 | `barangay_endpoint.py` mock |
| PH-4 | `ndrrmc_alert.py` mock (NDRRMC API 連携想定) |
| PH-5 | 紙 voucher は opt-in + 台風シーズン限定 |
| PH-6 | CP-5 は 5% 運用的許容 + 監査 |
| PH-7 | 写真貼付 voucher (個人単位) |
| PH-8 | DSWD MC + BSP NoL 文書 |

**🥇 #16 MVP**: Field Officer Pia Mendoza (+30) ─「サリサリ自身が被災する」「戸別訪問必須」

---

## 3. 戦略会議 #17 — Red-team Review

ユーザー指示: 「もう 1 回 PH エージェント会議」 → **4 つの新ペルソナ** で ground-truth 検証:

### 新規ペルソナ

| ペルソナ | 視点 | 主な指摘 |
|---------|------|---------|
| **Aling Maria** (サリサリ店主, 60歳, 22年) | 供給側現実 | Lista デジタル化拒否 / 即時入金必須 / 店ごと流失リスク |
| **Maria Santos** (4Ps 受給者, 38歳, 子3人) | 需要側現実 | スマホ家族 1 台共用 / バランガイ徒歩無理 / 家族単位給付必要 |
| **Engr. Roberto Lim** (元 Coins.ph) | 技術内部 | GCash オフライン limited / NDRRMC API 不存在 / Coins.ph piggyback 6 ヶ月 |
| **Dr. Carmela Reyes** (UP 人類学) | 文化批判 | Bayanihan は短期互恵 / Padrino リスク / 名称ロマンチック化危険 |

### #16 → #17 の修正サマリ

| #16 ID | 状態変化 | 理由 |
|--------|---------|------|
| PH-1 | ✏️ **5 層 → 3 層に縮小** | L4 (GCash) + L5 (Coins.ph piggyback) が 2026 年内不可 |
| PH-2 | ✏️ **opt-in + Disaster 限定** | Aling Maria の本能的拒否 + Carmela の文化批判 |
| PH-3 | ✅ そのまま | 政治リスクは PH-9 で別途対応 |
| PH-4 | ✏️ **SMS gateway + PRC API 併用** | NDRRMC API は実在せず |
| PH-5-6, PH-8 | ✅ そのまま | |
| PH-7 | ✏️ **個人 → 世帯単位** | Maria Santos の代理使用ニーズ |
| (L4) | ❌ **削除** | Roberto: 12-18 ヶ月開発必要 |
| (L5) | ❌ **R20+ 延期** | Roberto: Coins.ph compliance 6 ヶ月 |

### 新規採択 4 件 (#17 で追加)

| ID | 提案 | 担当 |
|----|------|------|
| **PH-9** | バランガイ 3 層代理権限 + PRC 立会必須 (Padrino リスク緩和) | Carmela + Red Team |
| **PH-10** | 加盟店入金タイミング ─ 即時 vs 週次 batch の両 adapter 用意 | Cost Guardian |
| **PH-11** | 名称変更: 「Lista Bayanihan」→ **「Disaster Lista (DL) Protocol」** | Carmela |
| **PH-12** | Yolanda 級 (Cat 5+) は **NDRRMC 直接配給フェーズ** に切替、PBM 対象外と明記 | Disaster |

**🥇 #17 MVP 同点**: **Aling Maria + Roberto Lim** (各 +30) ─ 現場 + 技術内部の 2 つの reality check

---

## 4. JP 側採択 (#16 で確定、#17 で変更なし)

| ID | 採択 | 状態 |
|----|------|------|
| **JP-1** | A + E ハイブリッド (マイナンバー Felica SE + 避難所端末) | 設計 |
| **JP-2** | `services/se_card_adapter.py` mock | 実装 |
| **JP-3** | 紙 QR (CP-6a) は二次救済として保持 | 設計 |
| **JP-4** | 避難所端末は発電機 + 衛星通信が前提 | 運用 |
| **JP-5** | CP-5 (二重支給) は SE counter + on-chain consumed の二重防御 | 設計 |
| **JP-6** | 既存 `offline_fallback.py` のロジックは流用、エンドポイントを差替 | 実装 |

---

## 5. Round 18 最終スコープ (確定 ─ JP 6 + PH 11 + 共通)

### JP 側 (Round 18)
- `docs/cp6-offline-fallback-v2-jp.md` 新設
- `backend/app/services/se_card_adapter.py` (mock + tests)

### PH 側 (Round 18)
- `docs/cp6-offline-fallback-v2-ph.md` 新設 (3 層 DL Protocol、PH-1 ~ PH-12 反映)
- `backend/app/services/lista_adapter.py` (opt-in mock + tests)
- `backend/app/services/barangay_endpoint.py` (3 層代理 + PRC 立会 mock + tests)
- `backend/app/services/ndrrmc_alert.py` (SMS gateway + PRC API mock + tests)

### 共通修正 (Round 18)
- `docs/cp6-offline-fallback.md` 冒頭に **「v1 設計の前提誤りに関する正誤」** 節
- `docs/whitepaper-2026.md` §4 全面改訂 (両国併記)
- `docs/pitch-deck-jp.md` + `docs/pitch-deck.md` の「世界初」表現修正
- `frontend/demo.html` Scene 7-9 修正 (POS 不要モデルへ)

### Round 19+ に延期 (#17 で明示)
- Citizen.household_id schema 変更 (PH-7 の世帯単位 voucher 完全実装)
- L4 GCash オフライン残高 (Coins.ph 開発待ち)
- L5 Coins.ph piggyback (Coins.ph compliance 6 ヶ月)
- NDRRMC SMS gateway 実接続 (gateway 契約必要)
- Felica SE 実機接続 (マイナンバーカードリーダ必要)

---

## 6. 主な意思決定の正当化

### Q1: なぜ JP は SE + 避難所端末 で、PH は紙 + バランガイ + PRC か?

**回答**: **インフラ + 文化が 違うから**。

| 観点 | JP | PH |
|------|----|----|
| SE 普及 | マイナンバーカード Felica 既存 | PhilSys ID は紙のみ |
| 災害頻度 | 30 年に 1 度 → 重武装 OK | 年 20+ 回 → 軽装備が必要 |
| 信頼アンカー | ハードウェア タンパー耐性 | コミュニティ + 復旧時 reconcile |

### Q2: なぜ「世界初」表現を撤回したか?

**回答**: **CP-6 v1 が前提誤りで動かない以上、「世界初」と謳うのは不誠実**。

正しい表現:
- ❌ 旧: 「世界初の災害時オフラインフォールバック」
- ✅ 新: 「災害時オフライン PBM の **2 国 2 設計** 提案 (JP A+E ハイブリッド / PH DL Protocol)」

### Q3: なぜ「Lista Bayanihan」名称を捨てたか?

**回答**: Dr. Carmela Reyes の人類学的批判が正しい:
- Bayanihan は **短期互恵** が本義、長期制度には不適
- ロマンチック化された貧困観に陥る危険
- → 「**Disaster Lista (DL) Protocol**」 に変更 (機能を直接表現)

### Q4: なぜ世帯単位 voucher への schema 変更を R19 に延期するか?

**回答**: PH-7 の世帯単位化は Citizen モデルに `household_id` 追加が必要 → JP 側にも影響 → R18 で対応すると **scope explosion**。R18 は 設計書 + mock サービス まで、schema 変更は R19 で扱う。

---

## 7. ポイント精算 (Round 17 = PR #18 = auto-demo)

| エージェント | 内訳 | 配点 |
|------------|------|------|
| Engineer | demo.html 600 行 + 14 シーン × 3 言語 narration + standalone 化 | +30 |
| Researcher | demo-walkthrough.md (browser-less preview) | +10 |
| Cost Guardian | demo は録画より優れる ROI 試算 | +5 |

**🏆 R17 MVP**: Engineer (5 ラウンド連続)

---

## 8. Phase 完了率 (R17 → R18 想定)

| Phase | R17 | R18 (予定) | 差分根拠 |
|-------|-----|-----------|---------|
| Phase 1 | 86% | 86% | 変化なし |
| Phase 2 | 71% | **75%** (+4pt) | M+11 (CP-6) を v1 ready → **v2 ready** に再評価 |
| Phase 3 | 40% | **48%** (+8pt) | M+18 evidence 強化 (CP-6 v2 が PH/JP 並列実装) |

CP-6 v2 で **「世界初」を撤回した方が逆に内容の誠実性が上がる** = 国際フォーラムでの説得力増。
