# Strategy Meeting #9 — Production Handoff

> **Created**: 2026-05-02 (round 10)
> **Topic**: Before Phase 3 (which is dominated by external-diplomacy / real-environment dependencies), package together everything still doable in the sandbox: production runbook / readiness check / CI / README / fork guide.
> **Output**: 5 implementations + harness expansion (`ready` mode)
> **Translated**: 2026-05-03 (round 11)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round9.md`](./strategy-2026-05-round9.md)

---

## 1. Adopted (5 items)

| # | Proposal | Implementation | Impact |
|---|----------|----------------|--------|
| **A** | Production deployment runbook | `docs/production-runbook.md` (~250 lines) | 5-stage step-by-step for Polygon Mumbai / PostgreSQL / HSM / MyNumber v2 / mainnet pilot |
| **B** | Readiness automated diagnostic | `scripts/readiness_check.py` + `verify.sh ready` | 24-item check for env / deps / files / harness / secrets, auto phase detection |
| **C** | GitHub Actions CI | `.github/workflows/verify.yml` | Auto-runs `verify.sh all + sweep + ready + load` on PR / push |
| **D** | Comprehensive README update | `README.md` | One-page index of all 9 rounds: features, every endpoint, every verify mode, CP-6 differentiation |
| **E** | Multi-municipality fork guide | `docs/fork-guide.md` (~150 lines) | 7-step + checklist for Phase 3 M+16 (Osaka / Aichi forks) |

## 2. Verification

```
$ bash scripts/verify.sh all
[verify:pytest] 138 passed in 4.23s ✓
[verify:seed]   citizens=10 stores=5 programs=7 products=30 ✓
[verify:sol]    ✓ / [verify:front] ✓
✓ verify(all) all green

$ bash scripts/verify.sh ready
detected phase: phase1-sandbox
  ✓ deps.fastapi / sqlalchemy / pydantic / ecdsa / Crypto / multipart
  ✓ file.* (13/13 critical files present)
  ✓ harness.quick: all green
  ✓ security.no_secrets: clean
  ⚠ env.JPN_PBM_PRIVACY_SECRET (warn in sandbox; fail in Phase 2/3)
  ⚠ deps.psycopg2 (required for Phase 3)
summary: ok=21, warn=3, fail=0
✓ verify(ready) all green
```

## 3. Point Reconciliation (Round 9)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | **A runbook + C GitHub Actions + D README** | **+30** |
| Cost Guardian | B readiness automated diagnostic (24 items) | +20 |
| Researcher | E fork guide | +15 |
| Red Team | A rollback strategy + emergency response organization | +10 |
| CSO/AML | B secret detection pattern proposal | +10 |
| Purpose Guardian | A documented automatic CP-6 invocation in runbook | +10 |
| Legal | A reorganized MoU / legal review flow ordering | +10 |
| Others | On standby | +5 each |

🥇 **MVP**: Engineer (+30) — implemented 3 items (250-line runbook / CI workflow / README) in a single round, completing the foundation for production deployment.

## 4. Round 10 Candidates (External Negotiation / Real-Env-Dependent)

- Polygon Mumbai actual deployment (real RPC required)
- MyNumber Portal v2 real OAuth (real API key required)
- HSM real-device connection (PKCS#11 library)
- PostgreSQL real migration + million-citizen scale
- Strategy Meeting #1 M+0 Founders' MoU (external = TMG × JPYC × TIS × Koto Ward)
- Strategy Meetings #8 #9 translation

## 5. Final Phase 1 Completion Rate

| Phase | done | ready | partial | blocked | pending | Total | Completion (done+ready) |
|-------|------|-------|---------|---------|---------|-------|-------------------------|
| Phase 1 | 2 | 4 | 1 | 1 | 0 | 8 | **75%** |
| Phase 2 | 1 | 2 | 2 | 1 | 1 | 7 | 43% |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 | 0% |

**Phase 1 75% complete** = remaining is `partial` (M+6 City Council Report) + `blocked` (M+0 Founders' MoU).
Once M+0 is signed, Closed Alpha can launch immediately.
