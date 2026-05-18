# 戦略会議 #18 — Round 19 ─ サンドボックス内残タスク完遂

> **作成日**: 2026-05-09 (round 19)
> **議題**: Round 18 で延期した「サンドボックス内で出来ること」5 項目を完遂
> **形式**: 短縮セッション (#16 #17 が連続だったので簡略化)
> **アウトプット**: 5 件採択 (R18 で延期項目のうち外部依存なしのもの)

---

## 0. Round 18 後の残タスク棚卸し

R18 で「R19+ 延期」とした 6 項目のうち、サンドボックス内で出来るのは:

| # | 項目 | サンドボックス? | 根拠 |
|---|-----|---------------|------|
| 1 | Citizen.household_id schema 追加 (PH-7 完全実装) | ✅ | 内部 schema 変更だけ |
| 2 | NDRRMC SMS gateway 実接続 | ❌ | gateway 契約必要 |
| 3 | Coins.ph PHPC sandbox 接続 | ❌ | Coins.ph compliance 6 ヶ月 |
| 4 | GCash オフライン残高 | ❌ | Coins.ph 開発 12-18 ヶ月 |
| 5 | Felica SE 実機接続 | ❌ | JPKI API + マイナンバーカードリーダ必要 |
| 6 | 避難所端末 1 台での実機テスト | ❌ | Starlink + NFC + 発電機 必要 |

→ **#1 のみ実装可能**。それに加えて i18n / docs 更新を併せ実施。

## 1. 採択 5 件

| # | 提案 | 担当 | 影響 |
|---|------|------|------|
| **T1** | `Citizen.household_id` schema + 世帯単位 voucher 完全実装 | Engineer | PH-7 終結、JP にも応用可 |
| **T2** | `seed/ph/citizens.json` 改訂 + 世帯リンク seed (8 受給者 → 5 世帯) | Engineer + Researcher | 世帯単位デモ可能に |
| **T3** | CP-6 v2 docs の英訳 (jp + ph) | Researcher | 国際フォーラム共有準備 |
| **T4** | R17 戦略会議の英訳 (R18 議事録、CP-6 v2 council 記録) | Researcher | i18n lag 維持 + 国際展開 |
| **T5** | JICA 申請書 v1.2 改訂 (CP-6 v2 反映 + Round 18 採択 +R17 council) | Researcher | 実外交準備 |

## 2. T1 (household schema) の設計

### 2.1 モデル変更

```python
# backend/app/models/citizen.py
class Citizen(Base):
    pid: ... (既存)
    name: ...
    address: ...
    ward: ...
    dob: ...
    gender: ...
    # 🆕 R19 (戦略会議 #17 PH-7 採択)
    household_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # household_id = HMAC(主たる受給者の PSN/My Number)
    # 同一世帯員は同じ household_id を共有
    # JP で個人単位を続けたい場合は household_id = pid (1人1世帯) にすれば後方互換
```

### 2.2 自動マイグレーション

```python
# backend/app/db.py:_PENDING_COLUMNS
("citizens", "household_id", "VARCHAR(64)", "NULL"),
```

### 2.3 サービス層

新規 `services/household.py`:
- `get_household_members(household_id)` ─ 同一世帯メンバー一覧
- `household_aggregate_eligibility(household_id, program)` ─ 世帯単位 eligibility
- `is_household_voucher(voucher)` ─ voucher が世帯単位か個人単位か判定

`lista_adapter` / `barangay_endpoint` は既に **household_id を string 引数** として
受けているので、コードの変更は不要 ─ 呼び出し側 (R20+) で正しい id を渡せば動く。

### 2.4 PH seed 改訂

```json
// 8 受給者 → 5 世帯にグループ化
{
  "psn": "PH-0001", "household_id": "HH-001-santos", ...
  "psn": "PH-0001-A", "household_id": "HH-001-santos", ... (子1)
  "psn": "PH-0001-B", "household_id": "HH-001-santos", ... (子2)
  "psn": "PH-0002", "household_id": "HH-002-reyes", ...
  ...
}
```

JP 側 (`seed/citizens.json`) は **後方互換のため変更しない** (household_id 未設定 = 個人単位扱い)。

## 3. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 305+ passed (R18 297 → R19 +tbd)
[verify:i18n]   16/17 (round18 が最新 lag = 1、許容)
✓ verify(all) all green
```

## 4. ポイント精算 (Round 18 = PR #19)

| エージェント | 内訳 | 配点 |
|------------|------|------|
| **Engineer** | 4 mock services 実装 + demo.html Scene 7-9 改訂 + 全 297 tests 緑 | **+25** |
| **Field Officer Pia + Aling Maria + Roberto + Carmela (新ペルソナ集合)** | #16 #17 で **PH の前提を 4 件覆した**現場視点 | **+30** |
| Researcher | CP-6 v2 docs 2 本 + whitepaper §4 改訂 + 戦略会議 議事録 | +20 |
| Red Team | v1 「世界初」 撤回提言 + 4 つの修正項目統合 | +15 |
| Purpose Guardian | CP-5 honest 5% 許容の文章化 | +10 |
| Cost Guardian | PH 紙 voucher コスト試算で全員配布案を却下 | +10 |

🥇 **R18 MVP**: **新ペルソナ集合 (+30)** ─ Field Officer + Aling Maria + Roberto + Carmela。**「机上の council」 を 「現場の council」に転換** したことが Round 18 の核心成果。

## 5. ラウンド 20+ 候補 (実外交解禁が必要)

R19 完了後、サンドボックスで残るのは **小粒な改善のみ**:

| 候補 | 必要な外部資源 |
|------|--------------|
| Polygon Mumbai 実デプロイ | RPC URL (Alchemy/Infura) |
| GCash sandbox API 連携 | Coins.ph 接触 (LoI 提出後) |
| iPhone 実機 scanner 検証 | iPhone 13/15 実機 |
| DSWD 4Ps 実 LandBank 統合 | DSWD 政策合意 |
| JICA pre-screening v3 | JICA 担当者との会話 |
| NDRRMC SMS gateway 実接続 | gateway 契約 (PHP 50K/月) |
| Felica SE 実機 (マイナ + JPKI) | JPKI API 拡張 (総務省協議) |

## 6. Phase 完了率 (R18 → R19 想定)

| Phase | R18 | R19 (見込) | 差分 |
|-------|-----|----------|------|
| Phase 1 | 86% | 86% | M+0 待ち、変化なし |
| Phase 2 | 75% | **77%** (+2pt) | M+11 evidence 強化 (世帯単位対応) |
| Phase 3 | 48% | **52%** (+4pt) | M+18 国際展開準備 (CP-6 v2 EN + JICA v1.2) |

R19 は数字より **「外部解禁時の残作業ゼロ」** が成果。
