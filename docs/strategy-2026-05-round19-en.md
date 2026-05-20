# Strategy Meeting #19 — Donor-PBM Pivot Decision (TAM 100x expansion)

> **Created**: 2026-05-09 (Round 20)
> **Topic**: Can the PBM infrastructure built across 19 rounds for Tokyo + Manila be expanded to **transparent international donation/aid**?
> **Background**: User insight: "This could be hugely useful for JICA / UN / UNICEF donations — opaque money becomes visible."
> **Format**: Red-team style, KYC/KYB/AML at the center
> **Participants**: Existing 11 agents + 4 new ground-truth personas
> **Output**: 12 adoptions (DP-1 through DP-12), Round 21 implementation, +20-25% codebase
> **Translated**: 2026-05-20 (Round 21)
>
> 🇯🇵 Japanese original: [`strategy-2026-05-round19.md`](./strategy-2026-05-round19.md)

---

## 0. Opening question

> Can we expand the PBM platform built across 19 rounds (Tokyo + Manila) to **transparent donation/fundraising**?
> User's note: "KYC and KYB are key. Especially in developing countries — do these APIs exist? Is the AML data accurate?"
> If we can't answer these two, the pivot fails.

## 1. Mapping existing PBM features → donation use case

| Pain point in donation world | Existing JPN-PBM feature that solves it |
|------------------------------|----------------------------------------|
| "Where did my $10,000 go?" (fully opaque) | on-chain `Spent` event for traceability |
| 15-30% admin fee skim | Contract pays supplier directly — structurally impossible |
| Field corruption/diversion | **CP-2 5-way require** makes off-purpose use physically impossible |
| Donor-beneficiary disconnect | EBPM k-anonymous aggregation → "your donation reached 12 households" real-time |
| Doesn't reach in disasters | **CP-6 v2** is literally this problem |
| Multi-currency / cross-border | JPYC/PHPC validated, USDC extension same adapter |

→ **80% of existing features apply directly**, 20% new (donor wallet, KYC tier, AML, UNHCR federation, CP-8).

## 2. Discussion body: 11 + 4 council

### 🆕 Sarah Chen (UNICEF Innovation Office, NY)

Donor-side KYC is solved by existing stack; problem is **beneficiary side**. UNICEF CryptoFund 2023 lessons:
- Beneficiary ID is hell: "Mali Kayes 1,234 households" exposes PII proportional to specificity
- Solution: **HMAC aggregation** — JPN-PBM's k-anonymous EBPM logic applies directly
- UNICEF internal contracts require 6-month security review → **Apache 2.0 + GitHub Actions CI green** reduces to 3 months

### 🆕 James Mwangi (Africa-region AML Compliance Officer)

KYC/KYB region-by-region reality:

| Region | KYC API | KYB API | AML data quality |
|--------|---------|---------|------------------|
| PH (Manila) | Coins.ph / Jumio, PhilSys restricted | SEC API, medium quality | OFAC linked, local PEP weak |
| Mali / Sub-Saharan | **API essentially zero** | No national registry | OFAC/UN only, local **none** |
| Yemen / Syria conflict zones | **Completely absent** | UN OCHA managed only | UN consolidated only |

"No API" ≠ "no KYC". Alternatives:
1. **Phone number KYC** (SIM issued via carrier KYC, mandatory in most countries)
2. **UN existing roster** (UNHCR / WFP / UNICEF)
3. **Village/barangay attestation** (same as R18 PH design)
4. **biometric** (UN IrisGuard at refugee camps)

Name-only AML matching blocks all "Mohammed Khan" in Jordan. **Risk-based scoring** is essential.

### 🆕 Imran Khan (UNHCR former Identity Specialist)

Refugee camp reality:
- Za'atari (Jordan, 75,000 Syrian refugees): no national ID, ProGres is the only ID
- WFP Building Blocks uses iris ($300M+ moved)

Donor-PBM should **federate with UNHCR ProGres**, not create new IDs.

**Warning**: biometric is political risk (Rohingya 2021 incident: data fell to Myanmar military). Donor-PBM must **not write biometric to contract**, HMAC PID only.

### 🆕 Lina Okabe (former Refinitiv World-Check)

AML data accuracy reality:

| Source | False positive | False negative | Cost |
|--------|---------------|----------------|------|
| OFAC SDN | 30% (name-only) | 5% | Free |
| UN Security Council | 25% | 8% | Free |
| EU Consolidated | 28% | 10% | Free |
| World-Check (Refinitiv) | **12%** advanced | 3% | $30K-100K/year |
| ComplyAdvantage | **10%** | 3% | $20K-80K/year |

**3-source cross-check (OFAC + UN + EU) compresses false positive to 5%**, commercial sources for high-value ($1000+) only.

### CSO/AML Honda (existing) re-evaluation

R13 (JICA application §6) AML evaluation was inadequate. For Donor expansion, required:
1. `services/kyc_adapter.py` (Jumio/Onfido/Sumsub mock + factory)
2. `services/aml_screening.py` (3-source cross-check)
3. `services/tier_policy.py` (tier switching)
4. **FATF Travel Rule** ($3,000+ encrypted sender/receiver)
5. **Sanctions evasion** smurfing detection

### Legal Tanaka (existing)

Donor pivot triggers jurisdiction explosion:

| Jurisdiction | Required |
|--------------|----------|
| US | FinCEN MSB or pass-through |
| Japan | PSA + NPO registration |
| EU | MiCA / AMLD6 / PSD2 |
| UK | FCA AML |
| UN | UNFC + each agency's procurement guide |

**Pass-through structure** = existing certified NPO (UNICEF/WFP/Save the Children) is front-end, JPN-PBM is distribution infrastructure → **we don't acquire VASP license**.

### Red Team Itou (existing) — 3 critical risks

**R-1**: **"Transparency endangers beneficiaries"** ─ Rohingya pattern. "Sahel 100 households" tells armed groups where aid is going. **Coarsen geographic granularity to country level**.

**R-2**: **"False positive fatal in emergencies"** ─ Child can't buy medicine due to AML name-match → dies. **Emergency bypass flag + post-recovery audit** (CP-6 grace concept).

**R-3**: **"Donor curiosity vs beneficiary privacy collision"** ─ Donors want to know, beneficiaries don't want exposure. **k=5 → k=50 strengthening** (UNICEF practice).

These 3 must be in design — otherwise pivot is unsafe.

### Cost Guardian Yamada (existing)

| Item | Cost |
|------|------|
| Donor KYC Tier 1 | $1-3 |
| Donor KYC Tier 2 + AML 3-source | $5-8 |
| Beneficiary (ProGres federate) | $0 (UN side) |
| AML 3-source (OFAC+UN+EU) | $0 |
| ComplyAdvantage (high-value only) | $20K-80K/year |
| Compliance Officer 0.5 FTE | $50K/year |

100K donor scale = $300K-800K compliance = ¥45-120M. For donation volume ¥10B, **0.5-1.5% compliance overhead** → vastly cheaper than existing NGO 15-30%.

### Researcher Tanaka — comparative landscape

| Project | KYC approach | Lesson for us |
|---------|--------------|---------------|
| **WFP Building Blocks** | UN ProGres + iris (refugees) | The right partner to federate with |
| Aid:Tech | Face + national ID | Commercial failure |
| **GiveDirectly** | M-Pesa carrier KYC | Phone-number KYC is realistic |
| UNICEF CryptoFund | Coinbase | Donor-only KYC, separate flow |

Defensible positioning: **WFP Building Blocks interop layer + OSS + CP-6 + individual donor UI**.

### Field Officer Pia (existing, PH perspective)

R18's lista_adapter / barangay_endpoint work directly as Donor-PBM supply side. Renaming "DSWD 4Ps" to "UNICEF Mali program" — that's the only change. **Manila design reusable across half the developing world**.

### Engineer Endo (existing) — honest implementation estimate

11 modules, **+20-25% codebase**. R15 adapter pattern reused throughout.

### Purpose Guardian Sasaki — CP redefinition for Donor-PBM

| CP | Donor-PBM meaning |
|----|-------------------|
| CP-2 | + donor KYC + AML clear |
| CP-4 | + donor-side k-anon + beneficiary k=50 (R-3) |
| CP-5 | + smurfing detection (R-1) |
| CP-6 | UNHCR ProGres federate for conflict zones |
| **CP-8 (new)** | **Emergency AML bypass + 14-day post-audit** (R-2) |

## 3. Synthesis — adoption

All 11 + 4 agents say **YES** to pivot, with mandatory conditions:

### Strong consensus (mandatory) — DPI-1 through DPI-7

| ID | Content |
|----|---------|
| **DPI-1** | Federate with existing UN ID (UNHCR ProGres / WFP Building Blocks); don't create new IDs |
| **DPI-2** | **Pass-through structure** — we're distribution infra, front-end is existing NPO |
| **DPI-3** | Beneficiary granularity = country-level + k=50 aggregation (R-1, R-3) |
| **DPI-4** | AML 3-source default, commercial for high-value only |
| **DPI-5** | Emergency bypass + post-audit (**new CP-8**) |
| **DPI-6** | Tier-based KYC: $0-50 anon, $50-1000 Tier 1, $1000+ Tier 2 |
| **DPI-7** | Biometric never on-chain, HMAC PID only |

### Soft consensus

| ID | Discussion |
|----|------------|
| DPI-8 | Phone-number KYC (M-Pesa style) — mandatory for Sub-Saharan, unneeded for PH/JP → locale-specific adapter |
| DPI-9 | World-Check vs ComplyAdvantage — budget-dependent |

### No opposition (conditioned)

If R-1/R-2/R-3 not integrated, pivot should not proceed. Unanimous on this.

## 4. 12 adoptions (Round 21 implementation)

| ID | Content | Effort |
|----|---------|--------|
| **DP-1** | `docs/expansion-donor-pbm.md` spec (Round 20) | Medium |
| **DP-2** | `services/kyc_adapter.py` (mock + Jumio/Onfido/Sumsub) | Medium |
| **DP-3** | `services/aml_screening.py` (OFAC + UN + EU + commercial pluggable) | Medium |
| **DP-4** | `services/tier_policy.py` | Small |
| **DP-5** | `services/donor_wallet.py` + `routers/donor_oauth.py` + models | Medium |
| **DP-6** | `services/unhcr_progres_adapter.py` | Medium |
| **DP-7** | `services/cp8_emergency_bypass.py` (CP-8 + 14-day audit) | Medium |
| **DP-8** | `frontend/donor.html` (JP/EN/Tagalog impact tracking) | Medium |
| **DP-9** | `seed/donor/{unicef-mali, wfp-yemen, jica-bangladesh}-2026.json` | Small |
| **DP-10** | `whitepaper-2026.md` §10-12: Donor-PBM section | Medium |
| **DP-11** | `handoff-packages/{unicef, wfp-building-blocks, unhcr}/` | Small |
| **DP-12** | 50+ tests | Medium |

## 5. Point reconciliation (#19)

| Agent | Contribution | Points |
|-------|--------------|--------|
| **🆕 Sarah Chen (UNICEF)** | k-anon aggregation + 6→3 month review reduction | **+30 (MVP)** |
| **🆕 James Mwangi (Africa AML)** | KYC regional reality + phone-number KYC + risk-based scoring | **+30 (MVP tied)** |
| 🆕 Imran Khan (UNHCR) | ProGres federate + Rohingya lesson + biometric political risk | +25 |
| 🆕 Lina Okabe (Refinitiv) | AML false positive empirical data, 3-source cross-check | +25 |
| Red Team | R-1/R-2/R-3 risk integration | +20 |
| CSO/AML Honda | R13 honest self-correction + 5 implementation requirements | +15 |
| Legal Tanaka | Pass-through = VASP avoidance | +15 |
| Engineer Endo | Honest +20-25% codebase estimate | +10 |
| Cost Guardian | 0.5-1.5% overhead calculation | +10 |
| Field Officer Pia | Manila design reusable across half the world | +10 |
| Purpose Guardian | CP-8 new proposal | +10 |
| Researcher | 5 comparable projects analysis | +5 |

**🏆 #19 MVP tied**: **Sarah Chen + James Mwangi** ─ international agency + Africa AML perspectives transformed the deskbound pivot proposal into a workable design.

## 6. Conclusion

**PIVOT YES** — conditional on full DPI-1 through DPI-7 implementation.

- Round 20 = Strategy Meeting #19 record (this document) + **DP-1 specification** (`expansion-donor-pbm.md`)
- Round 21 = DP-2 through DP-12 implementation

Scope:
- Codebase +20-25%
- Existing Tokyo + Manila 19 rounds **not negated; superseded above** as wrapper
- TAM: ¥640B (Tokyo) → ¥6T (Japan all-LGUs) → **$50B+ (UN humanitarian)** staged expansion

## 7. User confirmation (received before Round 20 start)

All 3 confirmed **YES**:
1. ✅ DPI-1 through DPI-7 mandatory conditions
2. ✅ Round 20 = meeting record + DP-1 specification
3. ✅ Name: **"Donor-PBM"** adopted (Carmela lesson = avoid romanticized framing, function-direct expression OK)
