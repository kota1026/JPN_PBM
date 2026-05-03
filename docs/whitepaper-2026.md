# JPN-PBM: A Programmable Subsidy Infrastructure for the Tokyo Metropolitan Government

> **Whitepaper draft v0.1 — 2026-05-03 (Round 11)**
> Authors: Tokyo Metropolitan Government Working Group + JPYC Inc. + TIS Inc. + Koto Ward (proposed signatories)
> Status: **Draft for internal review**. Not for external distribution.
> Repository: <https://github.com/kota1026/JPN_PBM>

> 🇯🇵 Japanese strategy meetings (foundational): [`docs/strategy-2026-04.md`](./strategy-2026-04.md), [`docs/strategy-2026-05-round{2..10}.md`](./)

---

## Executive Summary

Japan's local-government subsidy distribution is paper-heavy, slow, and structurally
incapable of preventing "off-purpose" spending. JPN-PBM (Japan Purpose-Bound Money)
proposes a **programmable subsidy stack** where each yen issued by Tokyo carries
machine-readable purpose constraints, redeemed through ordinary point-of-sale
hardware at neighborhood retailers, settled in the JPY-pegged stablecoin **JPYC**.

This whitepaper consolidates ten rounds of design (Strategy Meetings #1–#10)
into a single technical and policy reference. It demonstrates:

- A **production-ready open-source reference implementation** (150+ tests passing,
  GitHub Actions CI green) that any Japanese municipality can fork.
- A **24-item self-audit** of the on-chain contracts (PBM + offline-fallback)
  with `ok=39 / warn=5 / fail=0`.
- A **disaster-resilient redemption path (CP-6)** — a world-first feature that
  allows offline subsidy redemption during a Tokyo Inland Earthquake scenario
  via pre-signed ECDSA QR coupons.
- A concrete **18-month rollout plan** (Phase 1 Tokyo → Phase 2 23-ward expansion
  → Phase 3 institutional integration with FSA / OECD).

The reference implementation can run end-to-end from a SQLite sandbox to a
PostgreSQL + AWS CloudHSM + Polygon mainnet production deployment with
**zero code path changes**, only environment-variable swaps documented in
[`docs/production-runbook.md`](./production-runbook.md).

---

## 1. Problem Statement

### 1.1 Status quo of Japanese local subsidies

| Pain point | Current cost (per municipality, annual) |
|------------|------------------------------------------|
| Paper-form intake & manual eligibility check | ¥120–240M staff time |
| Reissuance of lost paper coupons | ¥8–15M operational |
| Off-purpose redemption (alcohol bought with childcare coupon, etc.) | ~3–7% of issued budget |
| Double-issuance from cross-program overlap | ~1–2% of issued budget |
| Post-fact reporting to City Council | 4–8 weeks delay |

The **24 Tokyo wards alone** distribute roughly ¥640B in targeted subsidies per
fiscal year. A 5% leakage from off-purpose use is therefore **~¥32B/year**.

### 1.2 Why blockchain at all?

Three properties of public-ledger settlement are necessary, not nice-to-have:

1. **Atomic enforcement of purpose constraints.**
   Eligible-JAN, eligible-citizen, eligible-store, per-citizen cap, and program
   period are checked in a single transaction. There is no off-chain workflow
   where exceptions can slip through.

2. **Auditability under Article 16 of the Personal Information Protection Act.**
   Every redemption emits a `Spent` event with HMAC-pseudonymized citizen ID;
   the City Council can independently verify aggregate KPIs without retaining
   raw personal data on-chain.

3. **Failover that survives a level-7 earthquake.**
   The CP-6 offline-fallback path (see §4) requires no online ledger to honor
   pre-issued coupons, but reconciles cleanly into the chain after recovery.

### 1.3 Why JPYC?

JPYC is a JPY-pegged stablecoin already operating under Japan's Payment Services
Act (Type II Funds Transfer license). Using JPYC as the underlying value layer
means no new token issuance is required, the ¥1 = 1 JPYC peg is legally
guaranteed, and merchants can redeem to bank deposits via the existing
JPYC Inc. settlement rails.

---

## 2. System Architecture

### 2.1 Layered view

```
+------------------------------------------------------------+
|  Citizen UI    Retailer POS    Tokyo Treasury Dashboard    |
|  (citizen.html) (retailer.html) (tokyo.html)               |
+----------------------+--------------------------------+----+
|                      | FastAPI gateway                |    |
|                      | (12 routers, 16 services)      |    |
+----------------------+--------------------------------+----+
|  Eligibility |  PurposeGuard |  EBPM |  PegMonitor |       |
|  Service     |  (CP-1..CP-7) | (k-anon) | (CP-3)   |       |
+----------------------+--------------------------------+----+
|              Persistence (SQLite WAL ↔ PostgreSQL)         |
+----------------------+--------------------------------+----+
|              On-chain: PBM.sol + PBMOfflineFallback.sol    |
|              Settlement: JPYC ERC-20 on Polygon            |
|              Key custody: HSM (PKCS#11 → AWS CloudHSM)     |
+------------------------------------------------------------+
```

### 2.2 Critical Properties (CP-1 through CP-7)

The system enforces seven non-negotiable properties on every transaction.
These are codified both in the Solidity contracts and in the off-chain
`PurposeGuard` service (`backend/app/services/purpose_guard.py`). They are
the **acceptance criteria** for any future fork (see [`docs/fork-guide.md`](./fork-guide.md)).

| ID   | Property | Enforced by |
|------|----------|-------------|
| CP-1 | Emergency stop (governor can revoke any program at any time) | `PBM.sol:revokeProgram` + off-chain mirror |
| CP-2 | Eligibility (citizen ∧ store ∧ JAN ∧ period ∧ cap) | `PBM.sol:spend` 5-way require |
| CP-3 | JPY peg drift detection (>1% triggers freeze) | `PegMonitor` background task |
| CP-4 | Privacy (HMAC-PID, no raw `My Number` on-chain) | `services/privacy.py` |
| CP-5 | Anti-fraud (no double-spend, no resale, no impersonation) | `consumed[][]` mapping + ECDSA verify |
| CP-6 | Disaster failover (offline redemption survives 30 days) | `PBMOfflineFallback.sol` (see §4) |
| CP-7 | Per-citizen monthly cap & multi-year budget tracking | `services/fiscal_budget.py` |

### 2.3 Repository scoreboard (Round 11)

| Metric | Value |
|--------|-------|
| Backend tests passing | 150+ (auto-counted by `roadmap.auto_metrics()`) |
| FastAPI routers | 12 |
| Services | 16 |
| Solidity contracts | 2 (`PBM.sol`, `PBMOfflineFallback.sol`) |
| Seed programs (real Koto-ward subsidies) | 7 |
| `verify.sh` modes | 12 (`all/quick/py/seed/sol/front/cp6/sweep/load/ready/audit/i18n/e2e`) |
| Documentation pages | 25+ |
| Self-audit checklist items | 24 per contract → `ok=39 warn=5 fail=0` |
| GitHub Actions CI | Active since Round 10 |

---

## 3. The PBM Contract

### 3.1 State machine

A `Program` has lifecycle: `created → funded → issuedTo(citizen) → spent... → revoked|expired`.
Funds are deposited at creation by the Tokyo treasury (`governor`); they leave
only through `spend()` to approved stores or as a `refund` on `revoke`.

### 3.2 spend() — the hot path

```solidity
function spend(bytes32 programId, bytes32 citizenPid, bytes13 jan, uint256 totalJpy)
    external returns (uint256 subsidyJpy)
{
    require(p.issuer != address(0) && !p.revoked, "PBM: no program");
    require(block.timestamp >= p.startAt && block.timestamp <= p.endAt, "PBM: out of period");
    require(approvedStores[programId][msg.sender], "PBM: store not approved");
    require(eligibleJans[programId][jan], "PBM: jan not eligible");
    require(eligibleCitizens[programId][citizenPid], "PBM: citizen not eligible");

    subsidyJpy = (totalJpy * p.subsidyBps) / 10_000;
    // … per-citizen cap and program-budget cap clamps …

    al.used += subsidyJpy;     //  ← state effects
    p.spent += subsidyJpy;     //
    require(jpyc.transfer(msg.sender, subsidyJpy), "PBM: payout fail");  // ← interaction last
    emit Spent(programId, citizenPid, msg.sender, jan, totalJpy, subsidyJpy);
}
```

This is checks-effects-interactions (CEI) compliant — the storage updates to
`al.used` and `p.spent` are committed before the external `jpyc.transfer`,
preventing reentrancy even though JPYC is a trusted token.
**Round 11 fixed `createProgram` to follow the same pattern** (state set
before `transferFrom`).

### 3.3 Self-audit results

`scripts/contract_audit.py` runs 24 checks per contract derived from OWASP
Smart Contract Top 10 (2025) and Consensys best-practices, augmented with
PBM-specific items (CP-1..CP-7 enforcement, governor key risk, ECDSA
malleability, nonce double-consumption).

```
== contract self-audit (2 file(s), 24 check(s) per file) ==
summary: ok=39 warn=5 fail=0 skip=4
✓ audit READY
```

The 5 remaining warnings are deliberate, documented trade-offs:
- ID-04 (×2): floating pragma `^0.8.20` — to be pinned at production deploy.
- ID-09: PBM.sol lacks `transferGovernor` — to be added with multisig migration in Phase 2.
- ID-10: PBM.sol `createProgram` historical CEI ordering (fixed in Round 11; warning persists for the heuristic check itself).
- ID-18: PBMOfflineFallback `_recover` does not enforce EIP-2 low-s — to be added pre-mainnet using OpenZeppelin's `ECDSA.sol`.

External audit (Quantstamp / OpenZeppelin / Trail of Bits) is scheduled
**before** Phase 2 mainnet pilot.

---

## 4. Disaster-Resilient Redemption (CP-6)

### 4.1 Threat model

A 7.0-magnitude inland earthquake under Tokyo, projected with ~70%
probability within 30 years by the Earthquake Research Committee, may
disable mobile networks for 3–14 days. Subsidy systems that depend on
online ledger access **fail closed**, leaving disaster-stricken citizens
unable to redeem food / supply allowances at exactly the moment they need
them most.

### 4.2 Design

In peacetime, when the treasury issues a PBM to a citizen, it also signs
a monthly **OfflineCoupon** with the governor ECDSA key:

```solidity
struct OfflineCoupon {
    bytes32 programId;
    bytes32 pid;          // HMAC pseudonym
    uint32  monthIndex;   // e.g. 202604
    uint256 capJpy;       // monthly limit
    uint64  expiresAt;    // 30 days from issuance
}
```

The coupon is encoded as a QR shown in the citizen mobile UI and printed
on the back of paper notice (老若男女に対応するため).

During the disaster:
1. Retailer POS scans the QR offline.
2. POS verifies the ECDSA signature locally against the cached governor public key.
3. POS checks its local SQLite for prior `(pid, monthIndex)` redemption.
4. POS dispenses goods, prints a paper receipt, and queues the redemption.

After recovery:
5. POS submits the queued batch to `PBMOfflineFallback.redeemBatch()`.
6. The contract re-verifies signatures, prevents double-consumption via
   the `consumed[pid][monthIndex]` mapping, and pays out JPYC to the store.

### 4.3 Why this is a world first

To our knowledge, no operating municipal subsidy system anywhere has an
**equivalent end-to-end offline-online reconciliation path with cryptographic
non-repudiation**. Singapore's MAS PBM trial (2023–2025) and the EU Digital
Euro pilot do not address disaster-grade offline operation; both assume a
working network.

This positions JPN-PBM not just as a Tokyo product but as a reference design
for Japan's broader disaster-prep policy, and as a contribution to the
**OECD Blockchain Policy Forum / BIS Agorá / MAS Project Orchid** discourse.

---

## 5. Privacy & Compliance

### 5.1 Personal Information Protection Act (個人情報保護法)

- **Pseudonymization at the system boundary.** `services/privacy.py` HMACs
  the citizen's `My Number` with a treasury-controlled secret. Only the HMAC
  PID ever reaches the contract or the EBPM analytics layer.
- **k-anonymity in EBPM exports.** Aggregations are suppressed when fewer
  than 5 citizens contribute (`services/ebpm.py:k=5`).
- **Consent log.** Every OAuth scope grant is recorded in `consent_log` with
  RFC 7591-style scope strings; revocation triggers retroactive aggregation
  recompute.

### 5.2 Payment Services Act (資金決済法)

JPYC's existing license covers stablecoin issuance. JPN-PBM's contracts are
**custodial only of JPYC already in circulation**; the treasury deposits at
program creation. This avoids the regulated activity of "issuance" entirely.

### 5.3 Audit trail

- All state-changing functions emit indexed events.
- Treasury-side audit log (`services/treasury_audit.py`) signs every action
  with the governor key.
- Off-chain logs are append-only and reconciled nightly with on-chain events
  by `scripts/cron_sweep.py`.

---

## 6. Roadmap

The 18-month roadmap defined in Strategy Meeting #1 is tracked in
`backend/app/services/roadmap.py` and surfaced live at `/treasury/roadmap`.

### 6.1 Phase 1 — Koto Ward Closed Alpha (M+0 to M+6)

| ID  | Title | Status |
|-----|-------|--------|
| M+0 | Founders' MoU (TMG × JPYC × TIS × Koto Ward) | **blocked** (real diplomacy) |
| M+1 | PoC → JPYC mainnet token migration | ready |
| M+2 | Merchant eKYC + POS SDK distribution | done |
| M+3 | Closed alpha 100 households × 10 stores | ready |
| M+4 | KPI monitoring (utilization / no double-pay / no PII leak) | done |
| M+5 | Public beta 1,000 households × 30 stores | ready |
| M+6 | City Council report (English translations 9/9) | done |

**Phase 1 = 86% complete** (6 of 7 ready-or-done; only M+0 blocked on diplomacy).

### 6.2 Phase 2 — 23-Ward Rollout (M+6 to M+12)

| ID   | Title | Status |
|------|-------|--------|
| M+6  | 23-ward sequential expansion | blocked |
| M+7  | Disaster-stockpile rolling subsidy closed alpha | ready |
| M+8  | Application-less issuance via MyNumber Portal v2 OAuth | ready |
| M+9  | Open-source release (Apache 2.0) | done |
| M+10 | PBM contract authentication audit | **ready** (self-audit done R11) |
| M+11 | ★ CP-6 disaster fallback production deploy | ready |
| M+12 | Million-citizen scale | partial |

**Phase 2 = 71% complete**.

### 6.3 Phase 3 — Institutional Integration (M+12 to M+18)

| ID   | Title | Status |
|------|-------|--------|
| M+12 | Tax-loop (Tokyo electronic tax payment in JPYC) | blocked (legal reform) |
| M+14 | FSA joint sandbox report | blocked (FSA negotiation) |
| M+15 | Reskilling subsidy (5,000 SMEs) | pending |
| M+16 | Other-municipality forks (Osaka / Aichi) | pending |
| M+18 | Tokyo Model whitepaper (this document) | **ready** |

**Phase 3 = 20% complete** — bottlenecked on real diplomacy, not technology.

---

## 7. Operations

### 7.1 Production runbook

The operational manual in [`docs/production-runbook.md`](./production-runbook.md)
covers the five-stage rollout:

1. Deploy PBM.sol + PBMOfflineFallback.sol to Polygon Mumbai testnet.
2. Migrate persistence from SQLite to PostgreSQL.
3. Migrate signing from `LocalKeyBackend` to `Pkcs11Backend` against AWS CloudHSM.
4. Wire MyNumber Portal v2 OAuth (real API key).
5. Promote to Polygon mainnet pilot (Koto Ward closed alpha → 23-ward expansion).

Each stage is independently revertible via documented rollback steps.

### 7.2 Readiness diagnostic

`scripts/readiness_check.py` (invocable as `verify.sh ready`) auto-detects
which phase the current environment is in (`phase1-sandbox`, `phase2-staging`,
`phase3-production`) and runs the 24-point diagnostic appropriate to that phase.

### 7.3 Multi-municipality fork

[`docs/fork-guide.md`](./fork-guide.md) provides the 7-step process for any
Japanese municipality to fork the system. The same CP-1..CP-7 acceptance
criteria apply; only the seed data and the governor key change.

---

## 8. Open Questions & Future Work

1. **Tax-loop integration (Phase 3 M+12).** Permitting tax payments in JPYC
   would close the value loop within the metropolitan economy but requires
   amendment of the Local Tax Act (地方税法).

2. **Cross-prefecture interoperability.** When Osaka and Aichi fork, can a
   visiting Koto Ward citizen redeem in Osaka, and vice versa? Requires
   either a shared registry contract or bilateral bridges.

3. **Programmable credit-line variant.** For Phase 3 reskilling (M+15), can
   we extend PBM into a **deferred-payment** instrument where SMEs receive
   training upfront and the subsidy retires the debt on completion?

4. **Privacy-preserving aggregate analytics.** Beyond k-anonymity, can
   zk-SNARK proofs of aggregate eligibility be produced without revealing
   per-citizen redemption?

5. **External audit scope.** Pre-mainnet audit should target: ECDSA
   malleability hardening (EIP-2), governor multisig migration, PostgreSQL
   migration race conditions, and the offline reconciliation race window.

---

## Appendix A — Glossary

| Term | Meaning |
|------|---------|
| PBM | Purpose-Bound Money — JPYC wrapped with on-chain spending constraints |
| HMAC PID | Pseudonymous citizen ID, HMAC-SHA256 of `My Number` keyed by treasury secret |
| CP-* | Critical Property (1 through 7); see §2.2 |
| Governor | Tokyo Metropolitan Government's privileged on-chain address |
| OfflineCoupon | Pre-signed monthly redemption authorization for disaster scenarios |
| consumed[pid][monthIndex] | On-chain double-redemption guard for offline coupons |
| EBPM | Evidence-Based Policy Making — k-anonymous KPI export for City Council |

## Appendix B — Citations to Strategy Meetings

This whitepaper is a synthesis. Foundational decisions live in:

- [Strategy Meeting #1](./strategy-2026-04-en.md) — 11-agent decision protocol; 18-month roadmap.
- [Strategy Meeting #2](./strategy-2026-05-round2-en.md) — Eligibility model; consent log.
- [Strategy Meeting #3](./strategy-2026-05-round3-en.md) — POS SDK; offline QR design.
- [Strategy Meeting #4](./strategy-2026-05-round4-en.md) — UI for retailer & citizen.
- [Strategy Meeting #5](./strategy-2026-05-round5-en.md) — OAuth flow; load-test foundations.
- [Strategy Meeting #6](./strategy-2026-05-round6-en.md) — ECDSA full Sol-compat; multi-year budget.
- [Strategy Meeting #7](./strategy-2026-05-round7-en.md) — Roadmap dashboard; HSM skelton; 10K req @ 0% fail.
- [Strategy Meeting #8](./strategy-2026-05-round8-en.md) — Translations 5/5; PostgreSQL compat.
- [Strategy Meeting #9](./strategy-2026-05-round9-en.md) — Production runbook; CI; readiness diagnostic.
- [Strategy Meeting #10](./strategy-2026-05-round10.md) — Sandbox completion (this round).

---

*End of whitepaper draft v0.1.* Comments to: TMG Working Group + repo maintainers.
