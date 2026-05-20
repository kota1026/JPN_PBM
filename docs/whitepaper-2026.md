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

- An **open-source sandbox implementation** (150+ tests passing, GitHub Actions
  CI green, Apache 2.0) that any Japanese municipality can fork.
- A **24-item self-audit** of the on-chain contracts (PBM + offline-fallback)
  with `ok=39 / warn=5 / fail=0`.
- A **disaster-resilient redemption design (CP-6 v2)** — two designs, one codebase
  that allows offline subsidy redemption during a Tokyo Inland Earthquake
  scenario via pre-signed ECDSA QR coupons.
- A concrete **18-month rollout plan** (Phase 1 Tokyo → Phase 2 23-ward expansion
  → Phase 3 institutional integration with FSA / OECD).

### Honest status of the implementation

What is **real and reproducible today**:

- A Python service layer (`backend/app/services/*`) that mirrors the Solidity
  contract semantics one-to-one.
- Solidity source for two contracts (`PBM.sol`, `PBMOfflineFallback.sol`) that
  passes the 24-item self-audit checklist.
- Byte-level cryptographic compatibility between the Python signer and Solidity
  `ecrecover` (`services/sol_compat.py` + 31 ECDSA test vectors).
- A Python EVM mini-simulator (`services/sol_simulator.py`) that reproduces the
  contract state transitions for `redeemBatch` without an actual chain.

What is **not yet real** (and the whitepaper is explicit about it):

- The contracts have **not been deployed to any blockchain**, including Polygon
  Mumbai testnet. Deployment is scheduled for the day a testnet RPC URL is
  provisioned (Round 12 candidate, ~3 working days).
- JPYC is not yet wired against the deployed contract. Wiring is straightforward
  once both are on the same chain.
- HSM custody is implemented as a stub adapter; a real PKCS#11 / AWS CloudHSM
  binding is required before mainnet pilot.
- External smart-contract audit (Quantstamp / OpenZeppelin / Trail of Bits) is
  scheduled before Phase 2 mainnet pilot.

The reference implementation is designed so the same code can run end-to-end
from a SQLite sandbox to a PostgreSQL + AWS CloudHSM + Polygon mainnet
production deployment with **zero code path changes**, only environment-variable
swaps documented in [`docs/production-runbook.md`](./production-runbook.md).
That migration path has been **validated by tests**, not by a live deployment.

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

## 4. Disaster-Resilient Redemption (CP-6) — v2 (revised 2026-05)

> **Important note**: An earlier v1 design (preserved at [`docs/cp6-offline-fallback.md`](./cp6-offline-fallback.md)) assumed retailer POS terminals continued to operate during a disaster. **This assumption is wrong**: power outages disable POS, store buildings may collapse, and shop staff evacuate themselves. The v2 design below redesigns CP-6 from first principles. Full meeting record: [`docs/strategy-2026-05-round17.md`](./strategy-2026-05-round17.md).

### 4.1 The right question

❌ Old framing: "How do we keep the POS running offline?"
✅ Correct framing: **"With zero power and zero connectivity, what authentication system prevents impersonation and double-spending?"**

This shift acknowledges power loss as a *baseline* assumption, not an edge case.

### 4.2 Five solution directions known from BoJ / BIS / ECB CBDC research

| ID | Approach | Examples |
|----|----------|----------|
| A | SE-embedded prepaid (Felica/Suica) | BoJ Phase 2 Pilot (2023-24); Suica 30-year operation |
| B | 2-tier wallet (smartphone + IC card) | Banque de France; BoJ CBDC Forum 2023 sub-WG |
| C | Time-limited offline credit | ECB Digital Euro pilot; Visa/Mastercard floor limit |
| D | Hash-chain ticket | BIS Project Polaris (Riksbank/BIS) |
| E | Government endpoint terminal | 311 SDF cash distribution; LGU evacuation centers |

### 4.3 Two designs for two countries

JPN-PBM proposes **two CP-6 v2 designs**, optimized for the local infrastructure and disaster characteristics of each country.

#### 4.3.1 Japan v2 — A + E hybrid (Felica SE + shelter terminal)

See [`docs/cp6-offline-fallback-v2-jp.md`](./cp6-offline-fallback-v2-jp.md) for full spec.

| Layer | Component |
|-------|-----------|
| **Layer A** | MyNumber card Felica SE — pre-stage monthly offline allowance, monotonic counter for tamper resistance |
| **Layer E** | Government tablet at evacuation centers — generator + Starlink mini + NFC reader |
| **Layer paper** | Secondary fallback for SE-cardless citizens (door-to-door by welfare officers) |

**Why this works for Japan**: MyNumber Felica is already universal (90%+ penetration), eliminating new hardware deployment. Evacuation centers (15,000 nationwide) become PBM endpoints, justified by shared use with health-insurance / certificate-issuance terminals.

#### 4.3.2 Philippines v2 — Disaster Lista (DL) Protocol

See [`docs/cp6-offline-fallback-v2-ph.md`](./cp6-offline-fallback-v2-ph.md) for full spec.

| Layer | Component |
|-------|-----------|
| **Layer 1** | Laminated paper voucher — opt-in, typhoon-season-only, household-unit (with photo) |
| **Layer 2** | Disaster Lista — sari-sari informal credit, opt-in, NDRRMC Code Red activation only |
| **Layer 3** | Barangay + Red Cross — 3-tier delegated authority (captain → kagawad → tanod), PRC volunteer witness mandatory |

**Why this works for the Philippines**: There is no SE infrastructure. PhilSys ID is paper-based. But Filipino bayanihan / lista culture is a working informal-trust infrastructure. The DL Protocol formalizes that culture without overriding it.

**Yolanda-class (Cat 5+) exception**: When typhoon intensity exceeds the DL Protocol's tolerance (sari-sari themselves destroyed), CP-6 yields to direct national-disaster distribution (NDRRMC + AFP + PRC), and unspent monthly allowances roll over to the next month at no loss to recipients.

### 4.4 Honest framing — what is NOT a "world first"

The v1 whitepaper claimed "world first end-to-end offline-online reconciliation." That claim is withdrawn. Reality:

- **Indonesia BPNT** has had IC-card-based subsidy distribution since 2017, including disaster operation.
- **India PDS** has Aadhaar biometric + ePOS with paper fallback during disasters.
- **Brazil Bolsa Familia / Auxilio Brasil** uses Caixa Econômica's mobile branches in disaster zones.

**What JPN-PBM v2 contributes**:
- A **two-country, codebase-shared** reference design (Japan + Philippines)
- **Honest accounting** of the trade-offs: Japan = hardware-mechanical; Philippines = community-operational
- The **multi-agent design protocol** (Strategy Meetings #1–#17) that produced these designs and is itself reusable

This is a contribution to **OECD Blockchain Policy Forum / BIS Agorá / MAS Project Orchid** discourse — but as a *disciplined twin-pilot reference*, not a "world first" boast.

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
| M+16 | Other-municipality forks (Osaka / Aichi / **Manila**) | **ready** |
| M+18 | Tokyo Model whitepaper (this document) | **ready** |

**Phase 3 = 40% complete** — Manila twin-pilot stack is feature-complete; bottleneck is real diplomacy, not technology.

### 6.4 Manila Twin Pilot (added Round 13–14)

The same codebase serves a second jurisdiction: **Quezon City + DSWD 4Ps**, settled in **PHPC** (Bangko Sentral ng Pilipinas–approved peso stablecoin by Coins.ph) on Polygon. 99% of the code is shared with Tokyo; what differs:

| Layer | Tokyo | Manila |
|-------|-------|--------|
| Stablecoin | JPYC (Polygon) | **PHPC** (Polygon, BSP regulatory sandbox 2024) |
| ID provider | MyNumber Portal v2 OAuth | **PhilSys OAuth** ([`backend/app/routers/philsys_oauth.py`](../backend/app/routers/philsys_oauth.py)) |
| ID hashing | HMAC(MyNumber) | HMAC(PSN) — same `services/privacy.py` |
| Eligibility mode | `jan_strict` (POS scanners common) | **`hybrid`** (barcode + MCC fallback) |
| Merchant identity | Store list (manual whitelist) | **EMV QR Ph parser** ([`backend/app/services/qr_ph.py`](../backend/app/services/qr_ph.py)) reading MCC from BSP Circular 2019-859 QR |
| POS hardware | iPad / dedicated | **Recipient smartphone** (no POS at sari-sari) |
| Disaster context | Earthquakes (rare, severe) | **Typhoons + flooding (frequent)** — CP-6 invoked monthly |
| Target program | Koto Ward childcare | **DSWD 4Ps** (4.4M households nationwide; pilot starts at 5 households × 5 sari-sari) |
| Regulatory base | PIPA Article 16 | Data Privacy Act of 2012 (RA 10173) |
| Funding path | TMG / Innovation Base | **JICA Digital Public Goods** ([`docs/jica-application-draft-en.md`](./jica-application-draft-en.md)) |

The Manila pilot's value proposition for the international community is **CP-6 (offline disaster fallback) on a recurring, monthly basis**, not the once-a-decade frequency assumed in earthquake-prepared Tokyo. This is positioned as Japan's contribution back to Southeast Asia at OECD / BIS Agorá / MAS Project Orchid forums.

Concrete artifacts, all in this repo:

- 4Ps seed data: [`seed/ph/`](../seed/ph/) (8 mock households, 25 GS1-480 products, 8 stores, 2 programs)
- PH POS SDK: [`sdk/python/jpn_pbm_pos_ph/`](../sdk/python/jpn_pbm_pos_ph/) (Tagalog/English UX, GCash QR Ph mock)
- Tagalog citizen UI: [`frontend/ph/citizen.html`](../frontend/ph/citizen.html)
- JICA application draft: [`docs/jica-application-draft-en.md`](./jica-application-draft-en.md) (24 months, ¥65M cash + ¥27M in-kind)
- Detailed expansion spec: [`docs/expansion-philippines.md`](./expansion-philippines.md)

What remains for Manila to launch is **not** code; it is the four-party MoU (DSWD × Quezon City LGU × Coins.ph × project lead).

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

## 10. Donor-PBM — TAM 100x expansion (added Round 20-21)

> See full design in [`docs/expansion-donor-pbm.md`](./expansion-donor-pbm.md).
> Strategy Meeting #19 record: [`strategy-2026-05-round19.md`](./strategy-2026-05-round19.md).

### 10.1 Motivation

Beyond municipal subsidies (Tokyo + Manila), the same PBM contract architecture
solves a much larger problem: **donor transparency in international aid**.

| Pain point in donor world | JPN-PBM existing feature that addresses it |
|---------------------------|--------------------------------------------|
| "Where did my $100 go?" (opaque) | on-chain `Spent` event for traceability |
| 15-30% admin overhead | contract pays supplier directly = middleman structurally impossible |
| Field corruption | CP-2 5-way require makes off-purpose use impossible |
| Donor-beneficiary disconnect | EBPM k-anonymous aggregation shows real-time impact |
| Doesn't reach in disasters | **CP-6 v2** is literally this problem |

→ **80% of existing features apply directly**, with 20% new (donor wallet, KYC tier, AML screening, UNHCR ProGres federation, CP-8 emergency bypass).

### 10.2 Three-role architecture

```
[Donor (individual / corporation / foundation)]
   ↓ KYC tier + AML screen (DP-2 / DP-3 / DP-4)
[Front-end NPO (UNICEF / WFP / JICA)]      ← Pass-through (DPI-2): NPO holds VASP/MSB
   ↓
[Treasury = UN agency / NPO]
   ↓ PBM contract
[Beneficiary]      ← UNHCR ProGres federate (DPI-1)
   ↓
[Approved supplier]
```

The PBM distribution layer (right three blocks) is **the existing implementation**. The donor-side (left two blocks) is the Round 21 addition.

### 10.3 KYC tier policy (DPI-6)

| Tier | Donation amount | KYC requirements | Cost |
|------|-----------------|-------------------|------|
| 0 Anonymous | $0-50 | None | $0 |
| 1 Light | $50-1000 | Name + DOB + email | $1-3 |
| 2 Full | $1000-10000 | + photo ID + biometric | $5-8 |
| 3 Enhanced | $10000+ | + source of wealth | $15-30 |

FATF Travel Rule forces Tier 2+ for $3,000+ donations.

### 10.4 AML 3-source cross-check (DPI-4)

Default: **OFAC + UN Consolidated + EU Consolidated** (all free, public).
Cross-checking 3 sources reduces false positive from 30% (OFAC alone) to 5%.
High-value donations ($1000+) escalate to ComplyAdvantage / World-Check (commercial).

Risk-based scoring: country + multi-source hit count determines auto-reject vs manual review.

### 10.5 CP-8: Emergency bypass + 14-day audit (DPI-5)

A new critical property added in Round 18: in declared emergencies (NDRRMC Code Red or equivalent), an AML-rejected donation can be accepted with mandatory 14-day post-recovery audit. If audit finds the bypass was inappropriate, clawback is initiated.

This addresses Red Team finding R-2: "AML false positive is fatal in emergencies." For example, a "Mohammed Khan" buying medicine for a child during a typhoon should not be blocked by name-only OFAC matching.

### 10.6 UNHCR ProGres federation (DPI-1)

JPN-PBM **does not create new identity systems** for beneficiaries. Instead, it federates UNHCR's existing ProGres registry (75 million refugees + IDPs, iris-biometric for unbanked populations).

ProGres IDs are HMAC-pseudonymized at the boundary; raw IDs and biometrics **never reach the on-chain contract** (DPI-7). This is critical: it directly addresses the 2021 Rohingya data incident where biometric data fell into the wrong hands.

### 10.7 Honest framing — what is NOT a "world first"

Following the Round 18 lesson, this section is explicit about prior art:

| Project | Strength | Weakness | Our difference |
|---------|----------|----------|----------------|
| **WFP Building Blocks** | $300M+ live, UN-official | Proprietary, UN-agency-only | OSS + individual donor UI + CP-6 |
| Aid:Tech (Ireland) | Middle East refugee KYC | Commercial failure | OSS survives community-driven |
| Disberse (UK, closed 2020) | Early mover | Business model failed | Not NPO-dependent |
| **GiveDirectly** | $700M+/year, M-Pesa | No blockchain | On-chain transparency + multi-currency |
| UNICEF CryptoFund | $50M, UN-official | Receive-only, no PBM | Purpose binding + beneficiary dashboard |

Our **defensible positioning**:
1. **Full Apache 2.0 OSS** (Building Blocks / Aid:Tech are proprietary)
2. **CP-6 v2 disaster fallback** (none of the comparators have this)
3. **2-country codebase shared** (JP + PH) — minimal fork cost for international NPOs
4. **Individual donor dashboard** (Building Blocks lacks this — it's UN-agency-only)
5. **Honest framing** (no "world first" claim, respect existing implementations)

### 10.8 Pass-through structure (DPI-2)

JPN-PBM **does not become a VASP / MSB**. The front-end NPO (UNICEF / WFP / JICA / Save the Children) is responsible for:
- Donor KYC
- Initial AML screening
- Donation receipt + custody
- Treasury conversion (fiat → stablecoin)
- Regulatory compliance (VASP / MSB / FATF)
- Beneficiary roster (with UN agencies' help)

JPN-PBM provides:
- The PBM contract (Tokyo + Manila existing)
- The donor dashboard (impact tracking)
- The unified protocol (4 roles speak the same API)
- Open source reference (Apache 2.0)

This separation means **regulatory burden does not fall on the OSS implementer**, only on the operating NPO.

---

## 11. Five Scenarios

The Donor-PBM design supports 5 concrete scenarios, each backed by mock seed data:

| ID | Scenario | Token | Beneficiaries | Donor side |
|----|----------|-------|---------------|------------|
| **A** | UNICEF Mali Mosquito Net | USDC | 5,000 households (Kayes region) | Individual donors via Coinbase |
| **B** | WFP Yemen Food Distribution | USDC | 12,000 households (Sa'ada/Hodeidah) | WFP Building Blocks interop |
| **C** | JICA Bangladesh School Materials | JPYC | 3,000 households (Chattogram/Dhaka) | Japanese taxpayers via ODA |
| **D** | Individual + Disaster Emergency | USDC | Filipino typhoon victims | Personal donors + CP-8 |
| **E** | Tokyo+Manila existing coexistence | JPYC/PHPC | Koto Ward / 4Ps recipients | International donors layered on top |

Each scenario has corresponding seed JSON at [`seed/donor/`](../seed/donor/).

---

## 12. Roadmap impact

Adding Donor-PBM introduces a new **Phase 4** to the roadmap:

| Phase | Pre-R20 | Post-R20 |
|-------|---------|----------|
| Phase 1 (Tokyo Closed Alpha) | 86% | 86% (unchanged) |
| Phase 2 (23-ward + Manila) | 77% | 77% (unchanged) |
| Phase 3 (Institutional integration) | 52% | 60% (Donor-PBM strengthens M+18 evidence) |
| **Phase 4 (Donor-PBM / international aid) [NEW]** | n/a | **30% (sandbox complete)** |

The TAM expansion:

- **Tokyo + Manila municipal**: ¥640B + PHP 100B = ~¥900B annual addressable
- **+ Japan all-LGUs**: ~¥6T annual addressable
- **+ JICA ODA**: ¥1.7T annual addressable
- **+ UN humanitarian (WFP, UNICEF, UNHCR, Red Cross)**: **$50B+ annual addressable**

≒ **100x expansion** from the original Tokyo target, with the same codebase.

---

## Appendix B — Citations to Strategy Meetings (updated)

(Through R20)
- [Strategy Meeting #1](./strategy-2026-04-en.md) — 11-agent decision protocol; 18-month roadmap.
- [Strategy Meeting #2-#9](./strategy-2026-05-round2-en.md) ... — Eligibility, POS SDK, OAuth, ECDSA Sol compat, etc.
- [Strategy Meeting #10](./strategy-2026-05-round10-en.md) — Sandbox completion (Round 11).
- [Strategy Meeting #11](./strategy-2026-05-round11-en.md) — Smartphone scan + hybrid eligibility (Round 12).
- [Strategy Meeting #12](./strategy-2026-05-round12-en.md) — Philippines foundation (Round 13).
- [Strategy Meeting #13](./strategy-2026-05-round13-en.md) — Manila Phase 1 + handoff packages (Round 14).
- [Strategy Meeting #14](./strategy-2026-05-round14-en.md) — Adapter layer + LoI templates (Round 15).
- [Strategy Meeting #15](./strategy-2026-05-round15-en.md) — Video recording packet (Round 16).
- [Strategy Meeting #16-#17](./strategy-2026-05-round17-en.md) — CP-6 v2 redesign (Round 18).
- [Strategy Meeting #18](./strategy-2026-05-round18-en.md) — Household schema + i18n (Round 19).
- [Strategy Meeting #19](./strategy-2026-05-round19.md) — Donor-PBM pivot (Round 20).
- [Strategy Meeting #20](./strategy-2026-05-round20.md) — Donor-PBM implementation plan (Round 21, this round).

---

*Updated through Round 21.* Tokyo + Manila + Donor-PBM. Open source / Apache 2.0.
