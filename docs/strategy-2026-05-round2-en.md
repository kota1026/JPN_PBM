# Strategy Meeting #2 — What's Missing to Make Phase 1 Actually Work

> **Created**: 2026-05-02 / **Format**: 11-Agent Strategic Decision Protocol v1.0 (JPYC PBM edition)
> **Topic**: With Strategy Meeting #1's "Koto-ward flagship + CP-6" adopted, what must be implemented to actually run **M+3 Closed Alpha (100 households × 10 stores)**?
> **Output**: 6 functional implementations + 22 additional tests (43 tests pass total)
> **Translated**: 2026-05-02 (round 7) for sharing with **MAS Project Orchid forum** / international PBM working groups

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round2.md`](./strategy-2026-05-round2.md)

---

## 1. Proposals → Adopted

| # | Proposer | Proposal | Status |
|---|----------|----------|--------|
| 1 | Purpose Guardian | `purpose_guard.py` enforces CP-1 ~ CP-6 at runtime | ✅ Phase 1 |
| 2 | CTO | Change `pbm.py` program selection to "most beneficial to resident" | ✅ Phase 1 |
| 3 | CSO/AML | Merchant eKYC module | ⏸ Phase 2 (initial 10 stores manual) |
| 4 | CFO | Reserve audit, 24h auto + alert | ✅ Phase 1 second half |
| 5 | CBO | Merchant certified-mark UI | ⏸ Phase 2 |
| 6 | Cost Guardian | Auto-sweep of expired PBM | ✅ Phase 1 |
| 7 | Engineer | Expose CP-6 over REST in `routers/offline.py` + EBPM write-back | ✅ Phase 1 |
| 8 | Stablecoin Architect | Peg monitor (hardcoded threshold version) | ⏸ Phase 1 second half |
| 9 | Researcher | EBPM CP-2 protection test | ✅ Phase 1 |
| 10 | Legal | `consent.py` model (Personal Info Act §27) | ✅ Phase 1 |
| 11 | Red Team | (defers to Phase 3) | — |

## 2. Critical Defects Caught by Red Team

- **Ambiguity in #2's "most beneficial"** → stabilized with 3-stage tie-break: `subsidy_jpy desc → remaining_jpy desc → program.id asc`
- **#6 sweeper might prematurely sweep future tokens** → strict-past only (`expires_at < now`) + `dry_run` mode
- **#7 offline redemption misses EBPM write-back (CP-4 violation)** → in `routers/offline.py:redeem_batch`, accepted items all written to `EBPMEvent`, with `guard_offline_redemption` re-validation
- **#9 individual record leakage risk** → explicitly tested k-anonymity (k=5) in `cp2_no_personal_info_in_aggregate`

## 3. Implementation Summary

| Adopted | Files | Tests | Lines |
|---------|-------|-------|-------|
| #1 | `backend/app/services/purpose_guard.py` | 11 | ~180 |
| #2 | `backend/app/services/pbm.py` (refactor) | 1 | +20 |
| #6 | `backend/app/services/sweeper.py` | 3 | ~75 |
| #7 | `backend/app/routers/offline.py` | 3 (E2E) | ~180 |
| #9 | (test only) | 1 | — |
| #10 | `backend/app/models/consent.py` | 1 | ~30 |

## 4. Verification Harness Result

```
$ bash scripts/verify.sh all
[verify:pytest] 43 passed in 1.24s ✓
[verify:seed]   seed ok: citizens=10 stores=5 programs=6 products=30 ✓
[verify:sol]    sol ok: 2 contract file(s) ✓
✓ verify(all) all green
```

Round 1 (21 tests) → Round 2 (43 tests) = **+22 tests**.

## 5. Point Reconciliation (Round 2)

| Agent | Detail | Total |
|-------|--------|-------|
| Purpose Guardian | full #1 | +20 |
| CTO | full #2 | +20 |
| CSO/AML | partial #3 (Phase 2) | +5 |
| CFO | partial #4 (Phase 1 second half) | +10 |
| CBO | partial #5 (Phase 2) | +5 |
| Cost Guardian | full #6 | +20 |
| **Engineer** | **full #7 + EBPM write-back design victory** | **+25** |
| Stablecoin Architect | partial #8 (Phase 1 second half) | +10 |
| Researcher | full #9 | +20 |
| Legal | full #10 | +20 |
| **Red Team** | **4 critical defects (#2, #6, #7, #9)** | **+20** |

🥇 **MVP**: Engineer (+25) — by designing the EBPM write-back for offline redemption, plugged the CP-4 hole left by Round 1.
🥈 Runner-up: Red Team (+20) — 4 defect findings hardened the implementation.

## 6. Remaining Issues (Round 3 Candidates)

- Frontend: surface `prog-koto-kosodate-2026` on tokyo.html
- POS SDK: real-device integration of barcode scanner + `/offline/redeem-batch`
- MyNumber Portal v2 OAuth: write ConsentLog from real API
- Reserve 24h audit cron (#4)
- Peg monitor (#8) thresholds and alert routing
- E2E browser test (Playwright)

---

## 7. International Sharing Notes

This round's distinguishing contributions for the international PBM community:

- **Runtime CP enforcement** (purpose_guard) is a pattern not previously documented in MAS Project Orchid or Stellar. The "single gate" at `services/purpose_guard.py` keeps all CP rules in one auditable module.
- **k-anonymity (k=5) in EBPM** materializes the privacy/utility tradeoff via cell suppression rather than DP noise — appropriate for small ward-level pilots where DP would destroy signal.
- **Offline redemption ↔ EBPM write-back** closes a gap that purely-online PBM systems do not face. A residency-of-truth question that earthquake-prone metropolises must answer.
