# Strategy Meeting #3 — Toward a Touchable Phase 1

> **Created**: 2026-05-02 / **Format**: 11-Agent Strategic Decision Protocol v1.0
> **Topic**: Now that Phase 1 APIs/SDK from Round 3 are in place, lift the system to a state where users can actually touch it in a browser
> **Output**: 6 functional implementations + Playwright E2E foundation + verify.sh mode expansion
> **Translated**: 2026-05-02 (round 8) for international PBM community

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round3.md`](./strategy-2026-05-round3.md)

---

## 1. Proposals → Adopted

| # | Proposer | Proposal | Status |
|---|----------|----------|--------|
| 1 | Engineer | Web POS in `retailer.html` (JAN scan + offline QR + IndexedDB) | ✅ Phase 1 |
| 2 | CTO | Playwright E2E (3-screen scenario) | ✅ Phase 1 (foundation; runs in real env) |
| 3 | Stablecoin Architect | Polygon Mumbai production deploy | ⏸ Phase 2 (real env required) |
| 4 | Legal | MyNumber Portal v2 real OAuth wire-up | ⏸ Phase 2 (API key required) |
| 5 | CBO | CP-6 experience UI in `citizen.html` | ✅ Phase 1 |
| 6 | Cost Guardian | Sweeper as cron | ✅ Phase 1 |
| 7 | Researcher | External activity (MAS Forum sharing) | — Not a PR |
| 8 | Purpose Guardian | CP violation counter visualization | ✅ Phase 1 |
| 9 | Red Team | 10K-scale load test | ⏸ Phase 1 second half (after #2) |
| 10 | CSO/AML | Merchant simplified eKYC (UI) | ✅ Phase 1 |
| 11 | CFO | Multi-year budget ordinance | ⏸ Phase 3 |

## 2. Implementation Summary

| Adopted | File | Test | Lines |
|---------|------|------|-------|
| #1 | `frontend/retailer.html` (CP-6 disconnected mode added) | Syntax OK + Playwright | +95 |
| #2 | `e2e/playwright.config.ts` + `e2e/tests/flagship-flow.spec.ts` + `e2e/package.json` | 4 (skip when no browser) | ~80 |
| #5 | `frontend/citizen.html` (pre-issue disaster QR) | Playwright | +60 |
| #6 | `scripts/cron_sweep.py` + `verify.sh sweep` | dry-run smoke | ~50 |
| #8 | `models/cp_violation.py` + `services/purpose_guard.record_violation` + `routers/ebpm.py` (`/violations`, `/violations/recent`) | 4 | ~80 |
| #10 | `frontend/tokyo.html` (CP-6 merchant approval UI + CP violation dashboard) | Syntax OK | +100 |

## 3. Harness Strengthening

New modes:
- `verify.sh sweep` — sweeper dry-run smoke
- `verify.sh e2e` — Playwright (skip in browserless env)
- `verify.sh front` — `node --check` each inline JS via `scripts/check_frontend_js.py`

`verify.sh all` flow:
```
pytest → seed → sol → front-js
```

## 4. Verification Result

```
$ bash scripts/verify.sh all
[verify:pytest] 63 passed in 2.09s ✓
[verify:seed]   citizens=10 stores=5 programs=6 products=30 ✓
[verify:sol]    sol ok: 2 contract file(s) ✓
[verify:front]  front-js ok: 5 html file(s) ✓
✓ verify(all) all green
```

## 5. Point Reconciliation (Round 3)

| Agent | Detail | Total |
|-------|--------|-------|
| Engineer | full #1 | +20 |
| CTO | #2 (foundation first) | +15 |
| Stablecoin Architect | #3 → Phase 2 | +5 |
| Legal | #4 → Phase 2 | +5 |
| CBO | full #5 | +20 |
| Cost Guardian | full #6 | +20 |
| Researcher | #7 not a PR | +5 |
| **Purpose Guardian** | **full #8 + record_violation design** | **+25** |
| Red Team | #9 to second half | +5 |
| CSO/AML | full #10 | +20 |
| CFO | #11 → Phase 3 | +5 |

🥇 **MVP**: Purpose Guardian (+25) — runtime violation recording across all deny paths → dashboard visualization closes the feedback loop for "auditability (CP-4)" and "purpose alignment (CP-1)".

## 6. Distinguishing Contributions for International Sharing

- **CP violation dashboard from a single guard module** is novel — most existing PBM systems lack centralized policy-violation telemetry
- **Disaster mode UI** in retailer.html demonstrates that programmable money can degrade gracefully under network outage, addressing a gap in MAS / Stellar / Marshall Islands precedents
- **k=5 anonymity in EBPM** preserves utility for sub-1,000-household ward pilots where DP noise would destroy signal
