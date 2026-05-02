# Strategy Meeting #1 — Tokyo × JPYC PBM Production Roadmap

> **Created**: 2026-04-30 / **Format**: 11-Agent Strategic Decision Protocol v1.0 (JPYC PBM edition)
> **Topic**: "What is Tokyo's first production use case for a JPYC-based PBM, and how should we transition the prototype to production?"
> **Output**: Flagship adoption (Phase 1) + 18-month roadmap + point reconciliation
> **Translated**: 2026-05-02 (round 5) for sharing with **MAS Project Orchid forum** / international PBM working groups

> 🇯🇵 Original Japanese: [`docs/strategy-2026-04.md`](./strategy-2026-04.md)

---

## 0. Foundational Facts (with sources)

| Domain | Fact | Source |
|--------|------|--------|
| JPYC | Registered as a Funds Transfer Service Provider 2025-08-18; issuance/redemption began 2025-10-27 | JPYC, Nikkei |
| TIS × JPYC | Basic agreement signed 2025-11; PoC in 2026; production "Stablecoin Settlement Support Service" by autumn 2026 | TIS |
| MAS PBM | Project Orchid (2022–) / PBM Technical Whitepaper (2023.06) / Orchid Blueprint (2023) | MAS |
| MAS 4 use-case categories | Government vouchers (DBS×OGP, CDC) / Government grants / Subsidies (UOB×SkillsFuture) / Commercial vouchers & escrow (Amazon×FAZZ×Grab) | MAS PBM WP §3 |
| Stellar UBI | World's first on-chain UBI via Stellar (Marshall Islands) | Stellar 2025 Year in Review |
| Mastercard | Endorsed USDG / PYUSD / USDC / FIUSD (2025) | Mastercard 2025 |
| Tokyo issue | "018 Support" (~JPY 72bn/yr, JPY 5,000/month for ages 0-18, no income gate) is criticized as "blanket cash hand-out" with no usage tracking | Tokyo press 2025/05 |
| Tokyo earthquake | M7-class with 70% probability within 30 years; up to 18,000 deaths; 3 million evacuees + 4.5 million stranded commuters; ¥83 trillion economic damage | Cabinet Office Disaster Mgmt |

---

## 1. Constitutional Principles (CP-1 ~ CP-6)

| ID | Principle | Violation example |
|----|-----------|-------------------|
| **CP-1** | **Purpose alignment** — subsidy tokens cannot be diverted from their declared purpose | Childcare-purpose JPYC spent at a bar |
| **CP-2** | **Privacy preservation** — MyNumber 4-info pseudonymized; raw individual records never leave the source | The metropolitan government holding individual purchase histories |
| **CP-3** | **Automatic eligibility** — zero human gatekeeping; eligibility decided by smart contract + public auth | Manual case-by-case approval at a counter |
| **CP-4** | **Auditability / EBPM hook** — every transaction is verifiable and feeds policy-effectiveness metrics | Aggregation done by hand in Excel |
| **CP-5** | **3-fault elimination** — (1) double-spend (2) impersonation (3) resale-for-cash, all blocked technically | Voucher resale forums emerging |
| **CP-6** | **Disaster availability** — payouts continue under network/power outage (offline QR + post-recovery reconciliation) | Total halt during a major earthquake |

CP-6 was **raised by Red Team and adopted by Purpose Guardian** during this very meeting — Tokyo's distinctive differentiator. Both MAS and Stellar prior art lack this.

---

## 2. The 11 Agents

| Tier | Agent | Role |
|------|-------|------|
| Strategy | Purpose Guardian | Enforces CP-1 ~ CP-6 |
| Strategy | CTO | Smart-contract + MyNumber + POS technical integration |
| Strategy | CSO/AML | AML/CFT, Travel Rule |
| Business | CFO | Budget locking, JPYC liquidity, Tokyo tax integration |
| Business | CBO | Merchant onboarding, wallet-app partnerships |
| Business | Cost Guardian | Double-spend prevention, sweep of unused budget |
| Execution | Engineer | Implementation, testing, E2E |
| Execution | Stablecoin Architect | JPYC peg, reserves, chain selection |
| Execution | Researcher | Latest precedent (MAS / Stellar / Circle) |
| Execution | Legal | Funds Settlement Act, Personal Information Act, electronic payment instrument |
| Execution | Red Team | Attack simulation, criticism |

---

## 3. The 9-Phase Execution Log

### PHASE 1: Topic Statement (5 min)

**Goal**: Within 12-18 months, launch one production use-case + extensible OSS foundation.

### PHASE 2: Competitive Proposals (15 min)

| # | Proposer | Proposal |
|---|----------|----------|
| 1 | Purpose Guardian | **PBM-ize 018 Support**: of the JPY 5,000/month, restrict to education-related JANs (textbooks, school supplies, online learning, lessons) |
| 2 | CTO | **Disaster-stockpile rolling subsidy**: limited to 5-year storable water/food/disaster radios; auto re-issue at 4.5-year mark |
| 3 | CSO/AML | **Merchant KYC + Amazon-FAZZ escrow**: receipt confirmation at POS via JAN scan → release to merchant; per-transaction cap JPY 100k |
| 4 | CFO | **Tokyo-tax recirculation voucher**: PBM limited to shotengai (shopping arcade) merchants; merchants can apply received JPYC to electronic Tokyo tax payment ("tax loop") |
| 5 | CBO | **DBS×OGP CDC clone** = ward-level food/daily-goods subsidy. 4-week pilot with 1,000 households × 6 stores in 1 ward |
| 6 | Cost Guardian | **Full claim-less via MyNumber Portal**: push notification → automatic wallet credit |
| 7 | Engineer | **PBM wrapper as OSS** = `jpn-pbm`, forkable by other municipalities |
| 8 | Stablecoin Architect | **ERC-3643 (permissioned ERC-20)** for recipient whitelist |
| 9 | Researcher | **SkillsFuture-style reskilling subsidy**: reskilling JPYC to SME employees in Tokyo, paid directly to certified training providers |
| 10 | Legal | **Tokyo ordinance sandbox + Funds Settlement Act**: treat JPYC as an "electronic payment instrument" overlaid with a "specific-purpose grant" classification |
| 11 | Red Team | (defers to Phase 3) |

### PHASE 3: Mutual Critique (10 min) — Red Team must attack all proposals

| Target | Attack scenario | Severity |
|--------|-----------------|----------|
| #1 | "Education-related JAN" boundary is fuzzy. Bundling school supplies with game consoles, lesson-flagged entertainment | 🔴 |
| #2 | Weak incentive to swap 5-year water at 4.5 years. Items rot in warehouses | 🟡 |
| #3 | Small merchants drop out under KYC burden. With only 5 stores, no usage circulation | 🟡 |
| #4 | No legal basis to apply JPYC to Tokyo tax electronic payment | 🔴 |
| #5 | Wealth disparity across 23 wards → "different wards get different amounts" → political flashpoint | 🟡 |
| #6 | MyNumber Portal API requires OAuth consent. "Auto credit" with bad UX = privacy law violation | 🔴 |
| #7 | Forking municipalities won't apply security patches. Who is responsible? | 🟡 |
| #8 | JPYC itself is ERC-20; wrapper bifurcates liquidity. Requires JPYC Inc. consent | 🔴 |
| #9 | Population too small for statistical significance. SkillsFuture is several × Tokyo's scale | 🟢 |
| #10 | Tokyo overreaching into FSA's regulatory turf delays implementation | 🔴 |
| **CROSS-CUT** | **What if the earthquake hits during the pilot? Vouchers can't beat paper cash (network down). Fallback design is mandatory** | **🔴** |

### PHASE 4: Integration & Vote (10 min)

Consolidated into 4 clusters:
- **A: Flagship** = #1, #2, #5
- **B: Cross-cutting infrastructure** = #6, #7, #3, #8
- **C: Legal & finance** = #4, #10
- **D: Second wave** = #9

| Motion | Result |
|--------|--------|
| First production: **adopt #5 ward CDC clone**, run #1/#2 in parallel as Phase 2 | 8 yes / 2 no / 1 abstain → **PASSED** |
| Build #6 + #7 + #3 from Day 1 as cross-cutting infra | 10 yes / 0 no / 1 abstain → **UNANIMOUSLY PASSED** |
| #8 ERC-3643 to be re-evaluated in Phase 2; Phase 1 uses raw JPYC + off-chain whitelist | 9 yes / 1 no / 1 abstain → **PASSED** |
| #4 / #10: research-only by Legal, deploy in Phase 3 | 11 yes / 0 no → **UNANIMOUS** |
| #9 reskilling: hold for Phase 2 | 9 yes / 2 no → **PASSED** |

**Red Team veto**: none. However, "disaster fallback" should be elevated to **CP-6** → adopted immediately by Purpose Guardian.

### PHASE 5: Sequencing (15 min) — 18-month roadmap

```
Phase 1 (M+0 ~ M+6) — Flagship Pilot
M+0  Founders' MoU: TMG × JPYC × TIS × 1 ward (Koto presumed) × shotengai association
M+1  Swap existing PoC repo for real JPYC token (Polygon)
     - Recipient PIDs HMAC-ized; MyNumber Portal OAuth consent UI
M+2  Merchant eKYC + POS SDK distribution (barcode scanner integrated)
M+3  Closed alpha: 1 ward, 100 households × 10 stores, food + daily goods only
M+4  KPIs: utilization, average burn-down days, double-spend = zero, privacy incidents = 0
M+5  Public beta: 1 ward, 1,000 households × 30 stores (DBS-OGP scale)
M+6  Pilot results to Tokyo Metro Assembly; Phase 2 budget approval

Phase 2 (M+6 ~ M+12) — Expansion + 2nd use-case
M+6  23-ward roll-out, 5万 → 20万 households
M+7  Disaster-stockpile rolling subsidy (#2) closed alpha (3 wards)
M+8  Claim-less: full automation via MyNumber Portal v2 (#6 final)
M+9  OSS release: github.com/tokyo-metro/jpn-pbm (Apache 2.0)
M+10 PBM wrapper authentication contract (UUPS Proxy) audited
M+11 Disaster fallback (CP-6): offline QR + recovery sync goes live
M+12 Phase 1+2 combined: 1M residents

Phase 3 (M+12 ~ M+18) — Institutional integration + national expansion
M+12 #4 Tax loop: trial Tokyo-tax electronic payment via JPYC (after legal frameworks)
M+14 #10 Sandbox: joint white paper with FSA
M+15 #9 Reskilling: alpha with 5,000 SMEs
M+16 First fork by another prefecture (Osaka / Aichi candidates)
M+18 Publish "Tokyo Model" white paper, mirroring MAS Orchid Blueprint
```

### PHASE 6: Whole-of-Decision Review (10 min)

| Check | Owner | Result |
|-------|-------|--------|
| CP-1 Purpose alignment | Purpose Guardian | ✅ JAN+industry-code 2-axis blocks diversion |
| CP-2 Privacy | Purpose Guardian | ✅ HMAC PID already implemented (`backend/app/services/privacy.py`) |
| CP-3 Auto execution | Purpose Guardian | ✅ MyNumber Portal removes human gatekeepers |
| CP-4 Auditability | Purpose Guardian | ✅ EBPM live; Polygon TX hash externally verifiable |
| CP-5 Fraud elimination | CSO/AML | ⚠️ eKYC strength (MyNumber signature + photo 2-factor) is the open question |
| CP-6 Disaster availability | Engineer | ⚠️ Sketch in Phase 1; production at M+11 |
| Technical feasibility | CTO | ✅ MVP swap in 6 months |
| Budget | CFO | ✅ Phase 1: ¥500M / Phase 2: ¥5B / Phase 3: ¥20B |
| Legal | Legal | ⚠️ Personal Info Act / Funds Settlement Act / Tokyo ordinance — three-way alignment needs external counsel |

### PHASE 7: Concern Re-discovery (10 min) — every agent must raise one

(See original Japanese for full list.)

### PHASE 8: Feature-level Final Vote (10 min)

| Motion | Result |
|--------|--------|
| Chain selection: Polygon-only vs Polygon + Ethereum mirror | **Both** 6 / single 5 → adopt both |
| eKYC: MyNumber sig only vs MyNumber + photo | **2-factor** 7 / single 4 → 2-factor |
| Merchant incentive: 1% cashback vs 0.5% + Tokyo certified-mark | **0.5%+mark** 8 / 1% 3 → mark wins |
| Disaster fallback (CP-6) | **Mandatory** 11 / optional 0 → unanimous |
| Legal budget | ¥50M / ¥100M / ¥150M → ¥100M (median) |

### PHASE 9: Final Sequence Presentation (5 min)

🏛 **Adopted strategy (one-page summary)**

**Flagship**: TMG × JPYC × TIS deliver **"Ward-level Children & Daily-Life Support PBM"** (Tokyo port of the DBS-OGP CDC voucher).

| Axis | Decision |
|------|----------|
| Target | Ages 0-18 households in Koto ward: 1,000 → 50,000 → 200,000 |
| Subsidy | JPY 5,000/month equivalent for food, daily goods + disaster stockpile (partial replacement of 018 Support) |
| Tech | JPYC (Polygon + Ethereum mirror); ERC-3643 deferred to Phase 2 |
| Auth | MyNumber signature + photo 2-factor eKYC; 4-info HMAC-PID-ized |
| Merchants | eKYC + POS SDK + Tokyo certified-mark + 0.5% cashback |
| Application | MyNumber Portal v2 OAuth — fully claim-less, household-head bulk consent |
| **Disaster** | **CP-6 (offline QR fallback) MANDATORY** |
| OSS | `github.com/tokyo-metro/jpn-pbm` (Apache 2.0); CSIRT centralized at TMG |
| Legal | Three-way alignment of Personal Info Act / Funds Settlement Act / Tokyo ordinance; external counsel ¥100M |
| Governance | Multi-year ordinance budget for "regime-change resilience"; monthly reserve audit |

---

## 4. Point Reconciliation

| Agent | Detail | Total |
|-------|--------|-------|
| Purpose Guardian | partial #10 + CP-6 adoption +15 | **+25** |
| CTO | partial #2 +10 / disaster response +8 / chain dual-support +8 | **+26** |
| CSO/AML | partial #3 +10 / 2-factor eKYC +10 | **+20** |
| CFO | partial #4 (Phase 3) | **+5** |
| CBO | full #5 +20 / certified-mark +10 | **+30** |
| Cost Guardian | full #6 +20 | **+20** |
| Engineer | full #7 +20 / disaster impl +8 | **+28** |
| Stablecoin Architect | partial #8 (Phase 2) +10 / constructive critique +5 | **+15** |
| Researcher | partial #9 (Phase 2) +10 / case studies +5 | **+15** |
| Legal | partial #10 (Phase 3) +5 / 3-law alignment surfacing +15 | **+20** |
| **Red Team** | **4 critical defects (incl. CP-6) +60 / mandatory critique of all 10 proposals +5** | **+65** |

🥇 **MVP**: Red Team (+65) — by mandating fallback, secured Tokyo's "world-first" risk posture.

---

## 5. Immediate Actions Reflected in Repository

| # | Content | Commit / PR |
|---|---------|-------------|
| A | Save this strategy log as `docs/strategy-2026-04.md` | PR #3 |
| B | Add Koto-ward 1,000-household flagship to `seed/programs.json` (id=`prog-koto-kosodate-2026`) | PR #3 |
| C | CP-6 offline fallback sketch in `contracts/PBMOfflineFallback.sol` + `backend/app/services/offline_fallback.py` | PR #3 |

---

## 6. Sharing with International PBM Community

This document is intended for:
- **MAS Project Orchid forum** (sharing Tokyo's CP-6 approach)
- **BIS Project Agorá** (CBDC + tokenized money working group)
- **OECD Blockchain Policy Forum** (programmable money governance)

The differentiating contribution from Tokyo is **CP-6: Disaster Availability**, which mandates that programmable money continue functioning under prolonged network/power outage — a requirement absent from the MAS, Stellar, and Marshall Islands precedents but mandatory for any seismic-prone metropolis.
