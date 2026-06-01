# Strategy Meeting #20 — Round 21 ─ Donor-PBM Implementation Round

> **Created**: 2026-05-20 (round 21)
> **Topic**: Implement DP-2 through DP-12 (11 items) adopted at Strategy Meeting #19
> **Format**: Short session (#19 covered design discussion; this is plan confirmation only)
> **Output**: 11 implementations + 1 strategy meeting record + 1 EN translation
> **Translated**: 2026-05-20 (round 23)
>
> 🇯🇵 Japanese original: [`strategy-2026-05-round20.md`](./strategy-2026-05-round20.md)

---

## 0. R20 completion status

R20 completed:
- `docs/strategy-2026-05-round19.md` (#19 minutes)
- `docs/expansion-donor-pbm.md` (DP-1 spec, 600 lines, 12 sections)

→ R21 **implements the spec**.

## 1. R21 implementation scope (DP-2 through DP-12)

| ID | File | Effort | Dependencies |
|----|------|--------|--------------|
| DP-2 | `services/kyc_adapter.py` | Medium | R15 adapter pattern |
| DP-3 | `services/aml_screening.py` | Medium | DP-2 |
| DP-4 | `services/tier_policy.py` | Small | DP-2 + DP-3 |
| DP-5 | `services/donor_wallet.py` + `routers/donor_oauth.py` + `models/donor.py` + `models/donation.py` | Medium | DP-4 |
| DP-6 | `services/unhcr_progres_adapter.py` | Medium | (independent) |
| DP-7 | `services/cp8_emergency_bypass.py` | Medium | DP-3 + R18 ndrrmc_alert |
| DP-8 | `frontend/donor.html` (JP/EN/Tagalog) | Medium | DP-5 endpoints |
| DP-9 | `seed/donor/{unicef-mali, wfp-yemen, jica-bangladesh}-2026.json` | Small | (independent) |
| DP-10 | `whitepaper-2026.md` §10-12 (Donor-PBM section) | Medium | DP-1 |
| DP-11 | `handoff-packages/{unicef, wfp-building-blocks, unhcr}/` (3 directories) | Small | DP-1 |
| DP-12 | 50+ tests (per module) | Medium | All services |

Bonus:
- `docs/strategy-2026-05-round19-en.md` (R20 meeting record translation, i18n lag maintenance)
- `docs/strategy-2026-05-round20.md` (this file, R21 plan record)

## 2. Implementation notes

- **Use R15 adapter pattern in all services**: Mock + Real Protocol + factory + env switch
- **Silent fallback forbidden** (R15 rule)
- **HMAC PID / household_id to contract** (DPI-7: don't write biometric)
- **k=50 aggregation** (DPI-3 / R-3)
- **CP-8 emergency bypass** with 14-day audit log deadline
- **Mock-first testing**: real API specs not yet fixed, so mock behavior IS the spec

## 3. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 365+ passed (R20 315 → R21 +50)
✓ verify(all) all green
```

## 4. Point Reconciliation (Round 20 = PR #21)

| Agent | Detail | Points |
|-------|--------|--------|
| **Researcher** | DP-1 spec 600 lines + Strategy Meeting #19 minutes 7 chapters | **+30 (MVP)** |
| Sarah Chen + James Mwangi (new persona collective) | Established DPI-1 through DPI-7 mandatory conditions | +25 |
| Engineer | 80% feature reuse decision + R15 adapter pattern full-layer extension | +15 |
| Red Team | R-1/R-2/R-3 risk integration | +10 |
| CSO/AML Honda | Honest R13 evaluation correction + CP-8 proposal | +10 |

🥇 **R20 MVP**: **Researcher (+30)** — heavyweight contribution of 600-line spec in single round.

## 5. Round 22+ candidates

After R21 completion, **Donor-PBM sandbox implementation is also complete**. R22+:

1. UNHCR ProGres API real connection (data sharing agreement)
2. ComplyAdvantage / World-Check real contract
3. WFP Building Blocks interop proposal (existing $300M+ platform)
4. UNICEF Innovation Office 3-month security review
5. JICA pre-screening v3 revision
6. **Rebase all 21 rounds onto 1 branch** in preparation for main merge

## 6. Phase completion (R20 → R21 estimated)

| Phase | R20 | R21 (forecast) |
|-------|-----|----------------|
| Phase 1 | 86% | 86% |
| Phase 2 | 77% | 77% |
| Phase 3 | 52% | **60%** (+8pt) ← Donor-PBM impl strengthens M+18 evidence |
| **Phase 4 (new)** | 0% | **30%** ← Donor-PBM sandbox complete |
