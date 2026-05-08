---
marp: true
theme: default
paginate: true
size: 16:9
header: "JPN-PBM · Tokyo Programmable Subsidy"
footer: "Strategy Meetings #1–#10 · 2026-05 · github.com/kota1026/JPN_PBM"
style: |
  section { font-size: 22px; }
  h1 { color: #102b4f; }
  h2 { color: #1f4068; border-bottom: 2px solid #1f4068; padding-bottom: 4px; }
  table { font-size: 18px; }
  code { background: #f1f3f5; padding: 1px 4px; border-radius: 3px; }
  .highlight { background: #fff3cd; padding: 12px 16px; border-left: 4px solid #ffc107; }
---

<!-- _class: lead -->

# JPN-PBM
## Programmable Subsidy Infrastructure for the Tokyo Metropolitan Government

A reference implementation of Purpose-Bound Money for municipal subsidy distribution.

**Round 11 · 2026-05-03 · Whitepaper draft v0.1**

> Sandbox status: 150+ tests passing · CI green · audit ready · 9/10 strategy meetings translated

---

## The problem (1/2)

Tokyo's 24 wards distribute **~¥640B/year** in targeted subsidies via paper.

| Pain point | Annual cost (per municipality) |
|------------|-------------------------------|
| Paper-form intake & manual eligibility | ¥120–240M staff time |
| Reissuance of lost paper coupons | ¥8–15M ops |
| Off-purpose redemption | **3–7%** of issued budget |
| Double-issuance from cross-program overlap | 1–2% of budget |
| City Council reporting lag | 4–8 weeks |

---

## The problem (2/2)

A 5% leakage from off-purpose use across the 23 wards alone is

# **~¥32 B / year**

…that is silently failing the policy intent of the subsidies.

This is the gap programmable money is built to close.

---

## Why blockchain at all?

Three properties are **necessary**, not nice-to-have:

1. **Atomic enforcement of purpose constraints** — eligible JAN × store × citizen × period × cap checked in a single transaction. No off-chain workflow where exceptions slip through.
2. **Auditability under the Personal Information Protection Act** — every redemption emits a `Spent` event with HMAC-pseudonymized citizen ID. City Council verifies KPIs without retaining PII.
3. **Failover that survives a level-7 earthquake** — the **CP-6 offline path** honors pre-issued coupons with no online ledger, and reconciles cleanly after recovery.

---

## Why JPYC?

JPYC is a JPY-pegged stablecoin already operating under Japan's **Payment Services Act** (Type II Funds Transfer license).

- Peg ¥1 = 1 JPYC is legally guaranteed.
- No new token issuance; treasury deposits pre-existing JPYC.
- Merchants redeem to bank deposits via JPYC Inc.'s existing rails.

PBM is therefore a **custodial wrapper**, not an issuance — staying outside the regulated activity.

---

## Architecture

```
+---------------------------------------------------------+
|  Citizen UI    Retailer POS    Tokyo Treasury Console   |
+---------------------------------------------------------+
|  FastAPI gateway · 12 routers · 16 services             |
+---------------------------------------------------------+
|  PurposeGuard (CP-1..CP-7) · EBPM (k-anon) · PegMonitor |
+---------------------------------------------------------+
|  Persistence: SQLite WAL ↔ PostgreSQL                   |
+---------------------------------------------------------+
|  On-chain: PBM.sol + PBMOfflineFallback.sol             |
|  Settlement: JPYC ERC-20 on Polygon                     |
|  Key custody: PKCS#11 → AWS CloudHSM                    |
+---------------------------------------------------------+
```

The same code runs from sandbox SQLite to production HSM via env-var swaps.

---

## Critical Properties (CP-1..CP-7)

The **acceptance criteria** for any fork.

| ID | Property | Enforced by |
|----|----------|-------------|
| CP-1 | Emergency stop (governor revoke) | `PBM.sol:revokeProgram` |
| CP-2 | Eligibility (citizen ∧ store ∧ JAN ∧ period ∧ cap) | `spend()` 5-way require |
| CP-3 | JPY peg drift detection | `PegMonitor` background |
| CP-4 | Privacy (HMAC PID, no raw My Number) | `services/privacy.py` |
| CP-5 | Anti-fraud (no double-spend / resale / impersonation) | `consumed[][]` + ECDSA |
| CP-6 | ★ Disaster failover (offline 30 days) | `PBMOfflineFallback.sol` |
| CP-7 | Per-citizen cap & multi-year budget | `services/fiscal_budget.py` |

---

## ★ World first: CP-6 disaster fallback

**Threat model**: a 7.0-magnitude inland earthquake (~70% probability within 30 years) may disable mobile networks for 3–14 days.

**Design**:
1. Treasury pre-signs monthly **OfflineCoupons** with the governor ECDSA key.
2. Coupon = QR shown on citizen UI + printed on paper notice.
3. POS scans QR offline → verifies signature locally → dispenses goods + paper receipt → queues redemption.
4. After recovery, POS submits batch to `redeemBatch()` which re-verifies and pays out JPYC, gated by `consumed[pid][monthIndex]` to prevent double-spend.

To our knowledge **no operating municipal subsidy system anywhere has an equivalent end-to-end offline-online reconciliation path with cryptographic non-repudiation**.

---

## What's built (Round 11)

| Metric | Value |
|--------|-------|
| Backend tests passing | **150+** |
| FastAPI routers | 12 |
| Services | 16 |
| Solidity contracts | 2 (`PBM.sol`, `PBMOfflineFallback.sol`) |
| Seed programs (real Koto-ward subsidies) | 7 |
| `verify.sh` modes | 12 |
| Documentation pages | 25+ |
| Self-audit checklist | 24 items × 2 contracts → ok=39/warn=5/fail=0 |
| GitHub Actions CI | active |

```
$ bash scripts/verify.sh all
✓ pytest (150+ passed)  ✓ seed  ✓ sol  ✓ front  ✓ audit  ✓ i18n
```

---

## Self-audit results

`scripts/contract_audit.py` — 24 checks per contract from OWASP Smart Contract Top 10 (2025) + Consensys best-practice + PBM-specific items.

```
== contract self-audit ==
summary: ok=39 warn=5 fail=0 skip=4
✓ audit READY
```

The 5 warnings are **deliberate and documented**:
- ID-04 ×2: floating pragma → pin at production deploy.
- ID-09: `transferGovernor` missing on PBM.sol → add with multisig migration.
- ID-10: legacy CEI ordering hint (already fixed in Round 11).
- ID-18: EIP-2 low-s → add OZ `ECDSA.sol` pre-mainnet.

External audit (Quantstamp / OpenZeppelin / Trail of Bits) **before** Phase 2 mainnet pilot.

---

## Privacy & compliance

**Personal Information Protection Act**

- HMAC-pseudonymization at the boundary (`services/privacy.py`).
- k-anonymity in EBPM exports (`k=5`).
- Consent log for every OAuth scope grant; revocation triggers retroactive recompute.

**Payment Services Act**

- JPYC's existing license covers issuance.
- PBM custodies JPYC already in circulation → not a regulated issuance activity.

**Audit trail**

- All state-changing fns emit indexed events.
- Treasury actions signed with governor key.
- Off-chain logs reconciled nightly with on-chain via `cron_sweep.py`.

---

## Roadmap — Phase 1 (Tokyo Closed Alpha)

**M+0 → M+6 · 86% complete**

| ID  | Title | Status |
|-----|-------|--------|
| M+0 | Founders' MoU (TMG × JPYC × TIS × Koto Ward) | **blocked** (real diplomacy) |
| M+1 | PoC → JPYC mainnet token migration | ready |
| M+2 | Merchant eKYC + POS SDK distribution | done |
| M+3 | Closed alpha 100 households × 10 stores | ready |
| M+4 | KPI monitoring | done |
| M+5 | Public beta 1k households × 30 stores | ready |
| M+6 | City Council report (English 9/9) | done |

Only **M+0 blocked**, on real diplomacy not technology.

---

## Roadmap — Phase 2 (23-Ward Rollout) · 71%

| ID   | Title | Status |
|------|-------|--------|
| M+6  | 23-ward sequential expansion | blocked |
| M+7  | Disaster-stockpile rolling subsidy alpha | ready |
| M+8  | Application-less issuance via MyNumber Portal v2 | ready |
| M+9  | OSS release (Apache 2.0) | done |
| M+10 | Contract authentication audit | **ready** ← R11 self-audit |
| M+11 | ★ CP-6 disaster fallback production deploy | ready |
| M+12 | Million-citizen scale | partial |

---

## Roadmap — Phase 3 (Institutional Integration) · 20%

| ID   | Title | Status |
|------|-------|--------|
| M+12 | Tax-loop (Tokyo electronic tax payment in JPYC) | blocked (legal reform) |
| M+14 | FSA joint sandbox report | blocked (FSA negotiation) |
| M+15 | Reskilling subsidy (5,000 SMEs) | pending |
| M+16 | Other-municipality forks (Osaka / Aichi) | pending |
| M+18 | "Tokyo Model" whitepaper | **ready** ← this deck + `docs/whitepaper-2026.md` |

Bottlenecked on real diplomacy, not technology.

---

## What we ask for

<div class="highlight">

To unblock Phase 1 M+0 and Phase 2 M+6:

1. **Founders' MoU** — TMG × JPYC × TIS × Koto Ward signatures.
2. **Polygon Mumbai testnet** — RPC endpoint for first deploy.
3. **MyNumber Portal v2 API key** — for real OAuth integration.
4. **AWS CloudHSM allocation** — for governor-key migration from local backend.
5. **PostgreSQL production instance** — to validate million-citizen scale.

</div>

Each is independently revertible (see `docs/production-runbook.md`).

---

## What we offer (international)

For **MAS / BIS Agorá / OECD Blockchain Policy Forum**:

- An **operating reference implementation** of CP-6 disaster fallback, contributable to global PBM design.
- 9 strategy meetings translated to English; 10th in pipeline.
- A **24-item self-audit framework** for municipal-grade smart contracts, reusable beyond Japan.
- **Apache 2.0** licensed; any country can fork.

This positions Japan not as a follower of Singapore's Project Orchid but as a contributor of the **disaster-resilience** dimension.

---

<!-- _class: lead -->

# Thank you

**Whitepaper**: `docs/whitepaper-2026.md`
**Code**: `https://github.com/kota1026/JPN_PBM`
**License**: Apache 2.0
**Sandbox demo**: `bash scripts/verify.sh all && cd backend && uvicorn app.main:app`

> JPN-PBM is the open-source foundation. The diplomacy is up to us.
