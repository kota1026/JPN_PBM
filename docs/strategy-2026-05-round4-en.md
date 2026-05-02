# Strategy Meeting #4 — Phase 1 → Phase 2 Migration Preparation

> **Created**: 2026-05-02 / **Format**: 11-Agent Strategic Decision Protocol v1.0
> **Topic**: With Phase 1 user-touchable flow complete (PRs #3-#5 merged), what should we implement to advance to Phase 2 (closer to production)?
> **Output**: 5 functional implementations + harness expansion (load mode) + Strategy Meeting #1 English translation
> **Translated**: 2026-05-02 (round 9)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round4.md`](./strategy-2026-05-round4.md)

---

## 1. Adopted (5 items)

| # | Proposer | Implementation | Why |
|---|----------|----------------|-----|
| **#11** | CFO | `program.fiscal_year_budgets` + `services/fiscal_budget.py` + `/programs/{id}/fiscal-budget` | Resilience to regime change. Multi-year lock enforced technically |
| **#9** | Red Team | `scripts/loadtest.py` + `verify.sh load` mode | Visualize latency/failure rate before production |
| **#3** | Stablecoin Architect | `offline_fallback.py` ECDSA secp256k1 in parallel | Sol-compatible, swap to HSM key in Phase 2 |
| **#4** | Legal | `routers/myna_oauth.py` (Authorization Code Grant 4 endpoints) + ConsentLog integrate | Connect Phase 1 consent UX to Phase 2 OAuth flow (production-equivalent) |
| **#7** | Researcher | `docs/strategy-2026-04-en.md` (English) | For MAS Project Orchid forum sharing |

Deferred: Polygon Mumbai actual deploy (Phase 3) / MyNumber Portal v2 real OAuth (real API key required) / Multi-year budget Phase 3 finalization.

## 2. Verification

```
$ bash scripts/verify.sh all
[verify:pytest] 87 passed in 2.59s ✓
[verify:seed]   ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green

$ bash scripts/verify.sh load
[verify:load] 100 並列 × 100 反復のスモーク負荷試験
    400 requests in 0.93s = 427.9 req/s
    p50=35.8ms p95=84.9ms p99=138.9ms
    failures: 0 (0.00%)
✓ verify(load) all green
```

## 3. Point Reconciliation (Round 4)

| Agent | Detail | Total |
|-------|--------|-------|
| CFO | full #11 | +20 |
| **Red Team** | **full #9 + "100×100 alternative" amendment** | **+25** |
| Stablecoin Architect | #3 parallel implementation | +20 |
| Legal | #4 Mock complete | +20 |
| Researcher | #7 translation done | +15 |
| Purpose Guardian | CP-2 maintained on OAuth path | +10 |
| Engineer | OAuth wire-up implementation | +10 |
| Others | Pending proposals | +5 each |

🥇 **MVP**: Red Team (+25) — by amending "100×100 alternative that doesn't break sandbox DB", produced concrete numbers (p95=85ms, fail=0%).

## 4. Round 5 Candidates

- Polygon Mumbai actual deploy (#3 sequel, real env)
- MyNumber Portal v2 real OAuth (real API key, external negotiation)
- 10K-scale production (#9 expansion)
- Multi-year budget per-fiscal-year spend split management (Phase 3 issue)
- Frontend wire-up: multi-year budget view on tokyo.html / OAuth flow toggle
- ECDSA Sol-compatible: full keccak256 + EIP-191 personal_sign compat impl
