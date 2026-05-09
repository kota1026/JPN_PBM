# 4Ps PBM Pilot Specification — Quezon City Closed Alpha

> **Program**: `prog-4ps-2026` (defined in `seed/ph/programs.json`)
> **Phase**: Closed alpha (5 households × 5 sari-sari stores × 3 months)
> **Token**: PHPC (Coins.ph BSP-approved peso stablecoin)
> **Settlement**: Polygon mainnet (planned), Polygon Mumbai testnet (initial)
> **Target start**: 2026-Q3 (subject to DSWD + Coins.ph + LGU coordination)

## 1. Program parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Subsidy rate | 60% (subsidy_bps = 6000) | DSWD 4Ps standard rate |
| Per-citizen monthly cap | PHP 1,400 (140,000 centavos) | 4Ps standard household allowance |
| No-barcode (tingi) sub-cap | PHP 300 / month | Round 12 design (Red Team review) |
| Eligible categories | food.* / household.baby / household.daily | derived from 4Ps purpose statement |
| Approved MCCs | 5411 (grocery), 5499 (misc food), 5912 (drug) | ISO 18245 |
| Blocked MCCs | 5921 (liquor), 5993 (tobacco), 5813 (drinking), 7995 (gambling) | hard-coded in `services/item_eligibility.py` |
| Eligibility mode | `hybrid` | barcode strict + MCC fallback |
| Pilot duration | 3 months (2026-09 → 2026-11) | covers typhoon season for CP-6 trigger |

## 2. Stakeholder roles

| Role | Org | Responsibility |
|------|-----|---------------|
| Program owner | DSWD Region NCR | Identify 5 mock households + observer access |
| LGU | Quezon City Innovation Office | Identify 5 sari-sari + 1 Mercury Drug + 1 7-Eleven |
| Stablecoin issuer | Coins.ph | PHPC testnet allocation + GCash QR Ph sandbox |
| Tech operator | JPN-PBM project | Smart contract deploy + monitoring + audit |
| Funding | JICA Digital Public Goods | ¥10M alpha tranche (subject to JICA approval) |

## 3. Citizen experience

```
[Day 1: Onboarding (DSWD + LGU together)]
1. Citizen comes to LGU office with PhilSys ID.
2. Officer verifies eligibility (existing 4Ps roster) and PSN.
3. PSN is HMAC-pseudonymized at boundary (Data Privacy Act compliant).
4. Citizen's smartphone is provisioned with the 4Ps PBM mini-app
   (or paper QR backup for citizens without smartphone).

[Day 1+: Monthly redemption]
1. Citizen visits an approved sari-sari store.
2. Citizen scans store's QR Ph wall sticker → app verifies MCC + CRC.
3. Citizen scans each branded product's barcode → app shows running subsidy.
4. For tingi/loose goods, citizen taps "Tingi" + enters price.
5. Total cart shown: total / subsidy / self-pay.
6. Citizen pays self-pay via GCash QR Ph; subsidy portion (PHPC) flows to merchant on-chain.

[Typhoon scenario (CP-6 invocation)]
1. If network drops, citizen's pre-signed offline coupon QR is used instead.
2. Sari-sari verifies coupon signature locally (governor public key cached).
3. Goods dispensed; sari-sari prints paper receipt + queues redemption locally.
4. After network recovery, sari-sari submits batch on-chain → settlement proceeds.
```

## 4. Audit & monitoring

| What | How | Who reads |
|------|-----|-----------|
| Real-time utilization | EBPM dashboard (k-anonymous) | DSWD + LGU |
| Per-merchant volume | EBPM dashboard | DSWD field office |
| Off-purpose attempt logs | CP violations table | DSWD + JPN-PBM monitoring |
| Fraud alerts (rapid sequential redemption) | heuristic in `services/purpose_guard.py` | DSWD + JPN-PBM |
| Smart contract events | on-chain (Polygon, public) | Anyone |
| Personal data access | requires explicit consent (logged in `consent_logs`) | DSWD only |

## 5. Failure modes & response

| Failure | Response |
|---------|---------|
| PHPC peg drift > 1% | `PegMonitor` triggers alert; if > 5%, automatic emergency stop (CP-1) |
| Sari-sari fraud (3 strikes) | Removed from approved store list; on-chain `setApprovedStore(false)` |
| Citizen smartphone lost | Issue paper QR replacement at LGU office |
| Network outage > 30 days | Investigation; offline coupons expire after 30 days |
| Smart contract critical bug | `governor.revokeProgram()` → all funds returned to DSWD treasury |

## 6. Out of scope (alpha)

- Real DSWD funds (alpha uses sandbox PHPC only)
- 4Ps conditionality enforcement (school attendance, health checkups) — Phase 2
- Tax loop integration — Phase 3
- Cross-LGU interoperability — Phase 3
