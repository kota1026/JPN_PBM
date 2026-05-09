# JICA Digital Public Goods Application — JPN-PBM Tokyo + Manila Twin Pilot

> **Document type**: Draft **v1.2** for internal review (NOT for submission).
>
> **v1.2 update (2026-05-09 Round 19)**: Reflects Round 18 CP-6 v2 redesign (Strategy Meetings #16 + #17). Major changes:
> - Withdrew "world first" claim; replaced with "two-country, two-design honest reference"
> - Updated §1 to reference CP-6 v2 (JP A+E hybrid + PH DL Protocol)
> - Added §6 risk for v1 design retraction
> - Added Round 18/19 progress to §3.3
> - All references to CP-6 now point to [`cp6-offline-fallback-v2-jp.md`](./cp6-offline-fallback-v2-jp.md) and [`cp6-offline-fallback-v2-ph.md`](./cp6-offline-fallback-v2-ph.md).
> **Funding window targeted**: JICA Digital Public Goods (DPG) Initiative, FY2026.
> **Applicant lead**: To be designated (corporate vehicle TBD; see §4).
> **Co-applicants** (proposed): JPYC Inc. (Japan), Coins.ph (Philippines), Tokyo Metropolitan Government, DSWD Quezon City Field Office.
> **Repository**: <https://github.com/kota1026/JPN_PBM> · License: Apache 2.0
> **Whitepaper companion**: [`docs/whitepaper-2026.md`](./whitepaper-2026.md)

---

## §1. Project Overview (1 page)

### 1.1 What

**JPN-PBM** is an open-source reference implementation of **Purpose-Bound Money** for
municipal subsidy distribution. Each yen (or peso) issued by a local government carries
machine-readable purpose constraints, redeemed at neighborhood retailers via ordinary
point-of-sale or smartphone, settled in regulated stablecoin (JPYC for Japan, PHPC for
the Philippines).

### 1.2 Why it qualifies as a Digital Public Good

1. **Open source**: Apache 2.0, all code on GitHub since 2026-04.
2. **Operationally ready**: 175+ unit tests passing, GitHub Actions CI green, 24-item
   self-audit on smart contracts (ok=40 warn=4 fail=0). See [`docs/whitepaper-2026.md`](./whitepaper-2026.md) §3.3.
3. **Designed for low-resource environments**: hybrid eligibility (barcode-strict +
   merchant-MCC fallback) means **no POS hardware is required at sari-sari stores** ─
   recipient smartphone scanning suffices. See [`backend/app/services/item_eligibility.py`](../backend/app/services/item_eligibility.py).
4. **Disaster-resilient (CP-6 v2)**: Two distinct designs — Japan's A+E hybrid (MyNumber Felica SE + shelter terminal) and Philippines' Disaster Lista Protocol (paper voucher + sari-sari opt-in lista + barangay & Red Cross). Both designs survive disasters with **no POS dependency** — see [`cp6-offline-fallback-v2-jp.md`](./cp6-offline-fallback-v2-jp.md) and [`cp6-offline-fallback-v2-ph.md`](./cp6-offline-fallback-v2-ph.md). Honestly positioned as "two-country, codebase-shared honest reference" rather than "world-first" claim (v1 was withdrawn after design assumption error was identified — see Strategy Meetings #16 + #17).
5. **Privacy by design**: HMAC pseudonymization at the system boundary; k-anonymity
   (k=5) on all aggregate exports.
6. **Standards compliance**: EMV QR Code Specification (MPM mode, BSP Circular 2019-859);
   ECDSA secp256k1 signatures byte-compatible with Solidity `ecrecover`; RFC 6749 OAuth
   for both Japanese MyNumber Portal v2 and Philippine PhilSys.

### 1.3 Twin-pilot ambition

| Country | Stablecoin | Target program | Households | Annual budget |
|---------|-----------|----------------|------------|---------------|
| **Japan** | JPYC (Polygon) | Koto Ward childcare | 100 → 1,000 → 12,000 | ¥3M → ¥80M |
| **Philippines** | PHPC (Polygon) | DSWD 4Ps pilot | 5 → 500 → 50,000 | PHP 0.5M → PHP 100M |

The codebase is **99% shared between the two countries**. Only the underlying token,
the ID provider (MyNumber vs PhilSys), and the seed data differ. This is the
twin-pilot's primary economic justification: **two pilots at the cost of slightly
more than one**.

### 1.4 Why NOW

- The **2024 Noto Peninsula earthquake** in Japan and the annual **20+ typhoons** in
  the Philippines create active political demand for disaster-resilient digital
  payment continuity. CP-6 directly answers this demand.
- **PHPC was approved by Bangko Sentral ng Pilipinas under the regulatory sandbox in 2024**.
- **Polygon mainnet is the only EVM chain that hosts both JPYC and PHPC**, enabling a
  shared infrastructure layer.

---

## §2. Open Source / Digital Public Good Compliance (1 page)

### 2.1 Digital Public Goods Standard (9 indicators) — self-assessment

| # | Indicator | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Relevance to SDGs | ✅ | SDG 1 (Poverty), 3 (Health), 11 (Cities), 16 (Institutions) |
| 2 | Open license | ✅ | Apache 2.0 (`LICENSE`) |
| 3 | Clear ownership | ⚠️ | To be designated upon corporate formation (§4) |
| 4 | Platform independence | ✅ | Polygon EVM + Python, no proprietary cloud lock-in |
| 5 | Documentation | ✅ | 27+ docs in `docs/`, including English whitepaper, runbook, fork guide |
| 6 | Mechanism for extracting data in non-proprietary formats | ✅ | All exports JSON / CSV / OpenAPI |
| 7 | Adherence to privacy and applicable laws | ✅ | PIPA (JP) + Data Privacy Act 2012 (PH); HMAC PID; consent log |
| 8 | Adherence to standards & best practices | ✅ | EMV QR, RFC 6749 OAuth, GS1, ISO 18245 MCC, ISO 4217, EIP-191 |
| 9 | Do no harm by design | ✅ | MCC blacklist (alcohol/tobacco/gambling); k-anonymity; revocable contracts |

### 2.2 Concrete artifacts already public

- 175+ backend tests (Python pytest)
- 31 ECDSA test vectors (Python ↔ Solidity byte-compat)
- 15 EMV QR Ph parser tests (CRC-16 verified)
- 14 hybrid eligibility tests
- 12 PhilSys OAuth tests + 13 MyNumber OAuth tests
- Pre-flight Polygon Mumbai deploy script (`scripts/deploy_mumbai.sh`)

### 2.3 Languages of documentation

- **Japanese**: 12 strategy meetings, whitepaper draft, runbook, fork guide
- **English**: 11 strategy meetings, whitepaper, runbook (partial), this application
- **Tagalog**: citizen UI (`frontend/ph/citizen.html`)

---

## §3. Implementation Plan (1 page)

### 3.1 Stage gates

| Stage | Duration | Deliverable | Funding tranche |
|-------|----------|-------------|-----------------|
| **0. Foundation** | M+0 to M+3 | Corporate vehicle + 4-party MoU + Polygon Mumbai deploy | ¥5M |
| **1. Tokyo Closed Alpha** | M+3 to M+6 | 100 households × 10 stores in Koto Ward | ¥10M |
| **2. Manila Closed Alpha** | M+4 to M+9 | 5 households × 5 sari-sari + Mercury Drug in Quezon City | ¥10M (PHP 4M) |
| **3. Tokyo Public Beta** | M+9 to M+15 | 1,000 households × 30 stores | ¥20M |
| **4. Manila Public Beta** | M+12 to M+18 | 5,000 households × 50 stores | ¥15M (PHP 6M) |
| **5. Joint reporting & expansion** | M+18 to M+24 | OECD/BIS conference paper + Osaka & Cebu proposals | ¥5M |

**Total request**: ¥65M over 24 months (~$430K USD equivalent, FY2026 rate).

### 3.2 Why 24 months and not 12

External diplomacy gates dominate the schedule:

- M+0 (Founders' MoU) is currently `blocked` in our roadmap because it requires
  4-party signatures (TMG × JPYC × TIS × Koto Ward).
- DSWD onboarding for 4Ps requires policy memorandum approval (~3–6 months).
- BSP regulatory sandbox extension to a foreign-coordinated pilot requires
  bilateral memorandum (~6 months).

### 3.3 Sandbox vs. real-deployment milestones

| Milestone | Sandbox-doable? | Status |
|-----------|------------------|--------|
| Smart contracts (Solidity) | ✅ | Done |
| Self-audit (24 items) | ✅ | Done (ok=40 warn=4 fail=0) |
| Hybrid eligibility | ✅ | Done (Round 12) |
| Tagalog/English UI | ✅ | Done (Round 12) |
| 4Ps seed data | ✅ | Done (Round 13, this round) |
| PhilSys OAuth mock | ✅ | Done (Round 13) |
| EMV QR Ph parser | ✅ | Done (Round 13) |
| **JICA application** | ✅ | This document, Round 13 |
| Polygon Mumbai testnet deploy | ❌ | Needs RPC URL (3 days post-funding) |
| Polygon mainnet pilot | ❌ | Needs external audit + MoU |

---

## §4. Counterpart Strategy (1 page)

### 4.1 Stakeholder map

| Role | Country | Organization | Status | Approach |
|------|---------|--------------|--------|----------|
| Corporate vehicle (applicant) | JP | TBD (合同会社設立予定, ~¥6万 / 1日) | Pending | Form upon JICA pre-screening |
| Stablecoin issuer | JP | JPYC Inc. | Existing rail | Direct outreach + technical demo |
| Stablecoin issuer | PH | Coins.ph (PHPC) | BSP-approved | Direct outreach via CEO Wei Zhou + technical paper |
| Local government | JP | Tokyo Metropolitan Government + Koto Ward | Inbound prep | Through Innovation Base + Sister-City |
| Local government | PH | Quezon City LGU + Manila City LGU | Cold | Through Sister-City (Setagaya ↔ Quezon City exists) |
| Welfare ministry | PH | DSWD (Department of Social Welfare and Development) | Cold | Via JICA Manila office |
| Regulator | JP | FSA (sandbox extension) | None | Phase 3 only |
| Regulator | PH | BSP (sandbox extension) | None | Through Coins.ph existing relationship |
| Telco / fintech rail | PH | GCash (Globe / Mynt) | None | Through Coins.ph or direct |
| Aid coordinator | International | World Bank / ADB Manila | None | After Closed Alpha results published |

### 4.2 First 3 contacts (JICA-mediated)

1. **JICA Tokyo Headquarters DPG team** — initial proposal review + Manila introduction
2. **JICA Manila Office** — DSWD and Quezon City introduction
3. **Coins.ph** — PHPC sandbox testnet allocation + PR coordination

### 4.3 Risks if counterparts don't materialize

If 4-party MoU stalls in Japan, the project pivots to **Manila-only single-pilot**
(PHP 30M, 12 months, PHPC + Quezon City + DSWD). Codebase is country-portable, so
this is a real fallback. Upper bound of risk-adjusted lost work: 30%.

---

## §5. Budget (1 page)

### 5.1 24-month budget (¥65M, ~$430K USD)

| Category | JP allocation | PH allocation | Joint | Total |
|----------|--------------|---------------|-------|-------|
| **Corporate vehicle setup** (one-off) | ¥1.0M | — | — | ¥1.0M |
| **Engineering** (1 lead + 0.5 frontend + 0.5 ops, 24 mo) | ¥18.0M | — | — | ¥18.0M |
| **External smart-contract audit** (Quantstamp/OpenZeppelin) | — | — | ¥6.0M | ¥6.0M |
| **Polygon mainnet gas fund** (24 mo + safety margin) | ¥0.5M | ¥0.5M | — | ¥1.0M |
| **AWS CloudHSM** (24 mo) | ¥1.5M | ¥1.5M | — | ¥3.0M |
| **PostgreSQL hosting** (managed RDS, 24 mo) | ¥0.6M | ¥0.6M | — | ¥1.2M |
| **In-country project lead** (PH only, 18 mo @ PHP 80K/mo) | — | ¥3.6M | — | ¥3.6M |
| **Field operations** (training, audit, store onboarding) | ¥3.0M | ¥4.0M | — | ¥7.0M |
| **Travel + per diems** (JP↔PH, 4 trips/year × 2 ppl) | — | — | ¥4.0M | ¥4.0M |
| **Conference dissemination** (OECD / BIS / MAS) | — | — | ¥3.0M | ¥3.0M |
| **Translation & legal** | ¥1.0M | ¥1.5M | — | ¥2.5M |
| **Reserve / contingency** (~15%) | — | — | ¥9.7M | ¥9.7M |
| **Subtotal** | ¥25.6M | ¥11.7M | ¥22.7M | **¥60.0M** |
| **JICA management overhead** (~8%) | — | — | ¥5.0M | ¥5.0M |
| **TOTAL** | | | | **¥65.0M** |

### 5.2 Co-funding / in-kind contributions

| Source | Form | Estimated value |
|--------|------|-----------------|
| JPYC Inc. | JPYC stablecoin issuance + PR | ¥3M equivalent |
| Coins.ph | PHPC + sandbox slot + technical staff | PHP 5M equivalent (~¥12M) |
| Tokyo Metropolitan Government | Office space + introduction letters | ¥2M equivalent |
| Repository contributors | OSS labor (already incurred) | ¥10M+ equivalent |
| **Total in-kind** | | **~¥27M** |

JICA grant + in-kind = ~¥92M total project value.

---

## §6. Risk & Mitigation (1 page)

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | PHPC peg break | Low | High | Emergency stop (CP-1) + revoke + JPYC/USDC fallback within 24h |
| 2 | DSWD policy reversal (Marcos admin → next admin) | Medium | High | Open-source means city-level forks (e.g., Quezon City alone) survive |
| 3 | BSP withdraws sandbox approval | Medium | High | Project pivots to Tokyo-only with Manila as research counterfactual |
| 4 | 4-party MoU stalls in Tokyo | Medium | Medium | Manila-first launch; Tokyo joins later when ready |
| 5 | iPhone Web BarcodeDetector regression | Low | Medium | Embedded ZXing.js fallback already in `frontend/scanner.js` |
| 6 | sari-sari store fraud (false MCC claims) | Medium | Medium | Quarterly audit + 3-strike removal + barcode-required for high-value items |
| 7 | Recipient smartphone unavailability | Medium | Medium | Pre-issued paper QR (CP-6 design) covers offline case |
| 8 | External audit finds critical bug | Low | High | Audit gates mainnet deploy; testnet pilot continues with bug fixes |
| 9 | Polygon network outage > 24h | Very Low | Medium | CP-6 v2 offline mechanisms (JP: SE counter / PH: paper + barangay) + 30-day reconciliation grace period |
| 11 | **CP-6 v1 design retraction (transparency risk)** | Low | Medium | We openly documented the v1 assumption error (POS dependency) and the v2 redesign reasoning ([`docs/strategy-2026-05-round17.md`](./strategy-2026-05-round17.md)). Treat this as a **transparency feature**, not a hidden flaw — JICA reviewers can verify the iteration history in git log. |
| 10 | Currency redenomination | Very Low | High | Underlying token is regulator-pegged stablecoin, not crypto |

---

## §7. Output / Reporting commitments

To JICA, quarterly:

- 90-day code+docs delta report (auto-generated from `git log` + `auto_metrics()`).
- KPI dashboard URL (live, includes utilization, leakage rate, k-anonymous demographics).
- Incident log (any CP-1 emergency stops, peg drift events, fraud audits).
- 1 conference paper or media engagement per 6 months (OECD / BIS / MAS / academic).

---

## Appendix A — Compliance with DPG Standard 9 Indicators

(Already enumerated in §2.1)

## Appendix B — Letter of Intent templates

To be drafted in Round 14 once initial JICA conversation occurs:

- [ ] LoI from JPYC Inc.
- [ ] LoI from Tokyo Metropolitan Government (Innovation Base)
- [ ] LoI from Koto Ward DX Office
- [ ] LoI from Coins.ph
- [ ] LoI from Quezon City Innovation Office
- [ ] LoI from DSWD Region NCR

---

*End of draft v1.0. Next revision after JICA pre-screening conversation. — Round 13.*
