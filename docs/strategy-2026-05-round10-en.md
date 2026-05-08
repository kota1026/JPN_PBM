# Strategy Meeting #10 — Sandbox Completion

> **Created**: 2026-05-03 (round 11)
> **Topic**: Push Phase 1 to 100% and lay groundwork for Phase 3 international expansion by clearing "the last hill of what's doable in the sandbox" in one stretch.
> **Output**: 8 items adopted (A1-A4 directional A + B1-B2 directional B + harness reinforcement audit/i18n + auto-progress detection)
> **Translated**: 2026-05-04 (round 12)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round10.md`](./strategy-2026-05-round10.md)

---

## 0. Situation

At the end of Round 10 (PR #11 merged), `main` had:

- tests **150 passed**
- routers **12** / services **16** / programs **7** / contracts **2**
- verify modes **10** (`all/quick/py/seed/sol/front/cp6/sweep/load/ready/e2e`)
- GitHub Actions CI **running** (first executed in PR #11)
- docs **25** (9 strategy meetings + 7 English translations + runbook + fork guide + …)

Roadmap progress:

| Phase | done | ready | partial | blocked | pending | Total | Completion |
|-------|------|-------|---------|---------|---------|-------|------------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | **86%** |
| Phase 2 | 1 | 3 | 2 | 1 | 0 | 7 | 57% |
| Phase 3 | 0 | 0 | 1 | 2 | 2 | 5 | 0% |

Remaining blocked / partial:

| ID | Title | Status | Doable in sandbox? |
|----|-------|--------|---------------------|
| Phase 1 M+0 | Founders' MoU | blocked | ❌ Real diplomacy |
| Phase 2 M+10 | PBM contract audit | partial | △ Self-audit checklist progresses it |
| Phase 2 M+12 | Million-citizen scale | partial | △ More scale validation |
| Phase 3 M+18 | Whitepaper publication | partial (translations 2/5) | ✅ Remaining translations + integrated whitepaper |
| Phase 3 4 items | Tax loop etc. | blocked / pending | ❌ |

→ **Sandbox-doable progress = M+10 audit + M+18 whitepaper + #8/#9 translations**, 3 items.
This round adds **a thin warm-up for international expansion (English landing + pitch deck)** to prevent stagnation after the PR #11 merge.

## 1. Adopted (8 items: 4 of direction A + 2 of direction B + 2 harness)

| # | Agent | Proposal | Implementation | Phase impact |
|---|-------|----------|----------------|--------------|
| **A1** | Engineer | Contract self-audit | `scripts/contract_audit.py` (~250 lines / 24 checklist) + `verify.sh audit` | M+10 partial → ready |
| **A2** | Researcher | Integrated whitepaper draft | `docs/whitepaper-2026.md` (~600 lines EN, 8 chapters) | M+18 partial → ready |
| **A3** | Researcher | Strategy Meeting #8 #9 translation | `docs/strategy-2026-05-round{8,9}-en.md` | M+18 evidence expansion |
| **A4** | Engineer | Roadmap auto-detect | `roadmap.py` auto-collects test count / commit count / file count → reflected in evidence | M+11 evidence automation |
| **B1** | Engineer | English landing page | `frontend/en/index.html` (instant demo for international forums) | Phase 3 M+14/M+18 warm-up |
| **B2** | CSO/AML + Researcher | Marp pitch deck | `docs/pitch-deck.md` (20 slides) | Phase 3 M+14 OECD/BIS sharing |
| **C1** | Cost Guardian | `verify.sh audit` mode | `scripts/verify.sh` | Auto-runs audit in CI |
| **C2** | Engineer | `verify.sh i18n` mode (JA ↔ EN strategy doc pairing) | `scripts/verify.sh` + `scripts/check_i18n.py` | Auto-detects untranslated strategy docs |

## 2. Rejected / deferred

- Polygon Mumbai actual deploy — needs real RPC (external)
- HSM real device — needs PKCS#11 library
- MyNumber Portal v2 real OAuth — needs real API key
- TypeScript POS SDK — low priority (Python SDK already validates)
- Prometheus `/metrics` — low priority (pre-production)

## 3. Expected verification

```
$ bash scripts/verify.sh all
[verify:pytest] 150+ passed ✓
✓ verify(all) all green

$ bash scripts/verify.sh audit
[verify:audit] PBM.sol + PBMOfflineFallback.sol self-audit
  ✓ checklist: 24/24 passed
✓ verify(audit) all green

$ bash scripts/verify.sh i18n
[verify:i18n] strategy doc translation coverage
  ✓ strategy-2026-04 ↔ -en
  ✓ strategy-2026-05-round2..9 ↔ -en (8/8)
✓ verify(i18n) all green

$ bash scripts/verify.sh ready
detected phase: phase1-sandbox
  summary: ok=23, warn=2, fail=0
✓ verify(ready) all green
```

## 4. Point Reconciliation (Round 10 = PR #11 = harness C / runbook A / readiness B / README D / fork E)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | C GitHub Actions + A runbook + D README | **+30** |
| Cost Guardian | B readiness automated diagnostic (24 items) | +20 |
| Researcher | E fork guide | +15 |
| Red Team | A rollback strategy | +10 |
| Others | Standby +5 |

🥇 **MVP**: Engineer (+30, 2 rounds running)

## 5. Round 12 Candidates (Real Diplomacy Required)

What is doable in the sandbox is mostly exhausted by Round 11. Round 12+ resumes once one of the following lands:

1. **M+0 Founders' MoU** (TMG × JPYC × TIS × Koto Ward) → Closed Alpha launch
2. **Polygon Mumbai testnet RPC** access → real deployment
3. **MyNumber Portal v2 API key** → real OAuth
4. **PostgreSQL production instance** + million-citizen sample data → production scale
5. **HSM real device** (AWS CloudHSM etc.) → real PKCS#11 connection

Until then, "blunt extensions" — whitepaper refinement / international forum sharing / frontend i18n expansion / security hardening (bandit/semgrep) — are the main path.

## 6. Phase 1 Completion Final Target

After Round 11:

| Phase | done | ready | partial | blocked | pending | Total | Completion |
|-------|------|-------|---------|---------|---------|-------|------------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | **86%** (unchanged, M+0 is external diplomacy) |
| Phase 2 | 1 | **4** | 1 | 1 | 0 | 7 | **71%** (M+10 audit promoted to ready) |
| Phase 3 | 0 | **1** | 0 | 2 | 2 | 5 | **20%** (M+18 whitepaper promoted to ready) |

→ **Declare "sandbox completion" at Phase 2 = 71%, Phase 3 = 20%**.
The week after M+0 is signed (the real-diplomacy round), Closed Alpha launch is immediately possible.
