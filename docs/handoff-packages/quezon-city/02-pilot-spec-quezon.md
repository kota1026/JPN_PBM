# Quezon City–specific Operational Plan

> Companion to the DSWD-side spec at [`../dswd/02-4ps-pilot-spec.md`](../dswd/02-4ps-pilot-spec.md).
> Focus here: **what Quezon City executes locally**.

## 1. Locations

| Type | Quantity | Selection criteria | Indicative shortlist |
|------|----------|---------------------|----------------------|
| sari-sari | 5 | MCC 5411 (grocery), 4Ps household concentration, smartphone-using owner | TBD via QC barangay coordination |
| Mercury Drug | 1 | Branch in Brgy. Commonwealth | (existing branch) |
| 7-Eleven | 1 | Same barangay as sari-sari cluster | (existing branch) |
| LGU office | 1 | Citizen onboarding room (1 morning) | QC City Hall Innovation Office |

Total: **7 retail locations**, all in 1 or 2 adjacent barangays for operational simplicity.

## 2. Citizen cohort (5 households)

DSWD identifies 5 mock 4Ps households (uses real demographics but no real DSWD funds during alpha).

Qualifying criteria (per existing 4Ps program):
- ≥ 1 child under 18, or pregnant member
- Income below DSWD threshold
- Resident of Quezon City for ≥ 6 months

## 3. Calendar

| Week | Activity | Owner |
|------|---------|-------|
| W-4 | Final agreement among DSWD + QC + Coins.ph + project | All |
| W-3 | Sari-sari merchant onboarding (per `03-merchant-onboarding.md`) | QC + project |
| W-2 | Citizen onboarding (5 households at LGU office) | DSWD + QC + project |
| W-1 | Smartphone provisioning + paper-QR backup | project |
| W0 | **Alpha launch** — citizens start using PBM in approved stores | All |
| W1–W12 | Operations + weekly review | DSWD + project |
| W4 | Mid-pilot retrospective | DSWD + QC + project |
| W12 | Pilot close + report to JICA, OECD/BIS submission paper draft | All |

## 4. KPIs (Quezon City–visible)

| KPI | Target | Source |
|-----|--------|--------|
| Active citizen redemption rate | ≥ 60% / month | EBPM dashboard |
| Average subsidy delivered per household | ≥ PHP 1,000 / month | EBPM |
| Off-purpose attempts blocked | ≥ 95% (target: 100%) | CP-violation logs |
| Sari-sari merchant satisfaction | ≥ 4 / 5 (survey) | manual survey W4 + W12 |
| Citizen NPS | ≥ 30 | manual survey W12 |
| CP-6 (offline) invocation events | ≥ 1 (during typhoon season) | on-chain `redeemBatch` events |

## 5. Communications

- **Press conference** at W0 (joint DSWD + QC + Coins.ph + project) — optional but recommended.
- **Mid-pilot media briefing** at W4 — share initial results.
- **Closing media event** at W12 — invite OECD / BIS / MAS observers.
- **Sister-city hook**: invite Setagaya Ward representative for at least 1 milestone event.

## 6. Quezon City–specific risks

| Risk | Mitigation |
|------|-----------|
| Mayor's office prefers a different LGU as launch | Pivot to Caloocan or Manila City; Quezon City still in 23-LGU rollout |
| QC barangay-level approval delays | Pre-built Tagalog handout (`../dswd/01-cover-letter-tl.md`) accelerates barangay buy-in |
| Sari-sari owner declines participation | We over-shortlist 8 stores → keep top 5 |
| Selected citizens lack smartphone | Paper QR backup (CP-6 pre-signed coupon, distributed in advance) |
