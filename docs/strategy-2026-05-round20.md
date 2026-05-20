# 戦略会議 #20 — Round 21 ─ Donor-PBM 実装ラウンド

> **作成日**: 2026-05-20 (round 21)
> **議題**: 戦略会議 #19 で採択した DP-2 〜 DP-12 (11 件) を実装
> **形式**: 短縮セッション (#19 で設計議論完了済のため計画確認のみ)
> **アウトプット**: 11 件の実装 + 1 件の戦略会議議事録 + 1 件 EN 翻訳

---

## 0. R20 完了状況

R20 で完了:
- `docs/strategy-2026-05-round19.md` (#19 議事録)
- `docs/expansion-donor-pbm.md` (DP-1 設計書 600 行 12 章)

→ R21 で **設計書の通り実装**。

## 1. R21 実装スコープ (DP-2 〜 DP-12)

| ID | ファイル | 工数 | 依存 |
|----|---------|------|------|
| DP-2 | `services/kyc_adapter.py` | 中 | R15 adapter pattern |
| DP-3 | `services/aml_screening.py` | 中 | DP-2 |
| DP-4 | `services/tier_policy.py` | 小 | DP-2 + DP-3 |
| DP-5 | `services/donor_wallet.py` + `routers/donor_oauth.py` + `models/donor.py` + `models/donation.py` | 中 | DP-4 |
| DP-6 | `services/unhcr_progres_adapter.py` | 中 | (independent) |
| DP-7 | `services/cp8_emergency_bypass.py` | 中 | DP-3 + R18 ndrrmc_alert |
| DP-8 | `frontend/donor.html` (JP/EN/Tagalog) | 中 | DP-5 endpoints |
| DP-9 | `seed/donor/{unicef-mali, wfp-yemen, jica-bangladesh}-2026.json` | 小 | (independent) |
| DP-10 | `whitepaper-2026.md` §10-12 (Donor-PBM 章) | 中 | DP-1 |
| DP-11 | `handoff-packages/{unicef, wfp-building-blocks, unhcr}/` (3 ディレクトリ) | 小 | DP-1 |
| DP-12 | テスト 50+ 本 (各モジュールごと) | 中 | 全 services |

おまけ:
- `docs/strategy-2026-05-round19-en.md` (R20 議事録英訳、i18n lag 維持)
- `docs/strategy-2026-05-round20.md` (本ファイル R21 計画記録)

## 2. 実装上の注意

- **R15 adapter pattern を全 services で使う**: Mock + Real Protocol + factory + env switch
- **silent fallback 禁止** (R15 ルール)
- **HMAC PID / household_id を contract に書込み** (DPI-7: biometric は書かない)
- **k=50 集約** (DPI-3 / R-3)
- **CP-8 緊急 bypass** は 14 日 audit log 期限つき
- **テスト書き始めに mock-first**: 実 API 仕様未確定なので mock の挙動が仕様になる

## 3. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 365+ passed (R20 315 → R21 +50)
✓ verify(all) all green
```

## 4. ポイント精算 (Round 20 = PR #21)

| エージェント | 内訳 | 配点 |
|------------|------|------|
| **Researcher** | DP-1 設計書 600 行 + 戦略会議 #19 議事録 7 章 | **+30 (MVP)** |
| Sarah Chen + James Mwangi (新ペルソナ集合) | DPI-1〜DPI-7 必須条件確立 | +25 |
| Engineer | 既存機能 80% 流用判断 + R15 adapter pattern 全層拡張案 | +15 |
| Red Team | R-1/R-2/R-3 大事故シナリオ統合 | +10 |
| CSO/AML Honda | R13 評価の honest 訂正 + CP-8 提案 | +10 |

🥇 **R20 MVP**: **Researcher (+30)** ─ 600 行の設計書を 1 ラウンドで仕上げた重量級寄与。

## 5. Round 22+ 候補

R21 完了で **Donor-PBM サンドボックスも実装完了**。R22+ は:

1. UNHCR ProGres API 実接続 (data sharing agreement)
2. ComplyAdvantage / World-Check 実契約
3. WFP Building Blocks との interop 提案 (existing $300M+ platform)
4. UNICEF Innovation Office との 3 ヶ月 security review
5. JICA pre-screening v3 改訂
6. 全 21 ラウンドを **1 ブランチに rebase** して main マージ準備

## 6. Phase 完了率 (R20 → R21 想定)

| Phase | R20 | R21 (見込) |
|-------|-----|-----------|
| Phase 1 | 86% | 86% |
| Phase 2 | 77% | 77% |
| Phase 3 | 52% | **60%** (+8pt) ← Donor-PBM 実装で M+18 evidence 大幅強化 |
| **Phase 4 (新設)** | 0% | **30%** ← Donor-PBM サンドボックス完了で初期立ち上げ |
