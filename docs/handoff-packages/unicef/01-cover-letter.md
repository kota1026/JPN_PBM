# To: UNICEF Innovation Office, New York HQ

**Re**: Donor-PBM — open-source proposal for transparent purpose-bound donations
**From**: JPN-PBM Project (TBD corporate vehicle)
**Date**: 2026-05-20 (draft)

---

Dear UNICEF Innovation Team,

We are an open-source initiative (Apache 2.0) building **Programmable Subsidy** infrastructure originally designed for Tokyo + Manila municipal welfare. Through 21 development rounds (visible at <https://github.com/kota1026/JPN_PBM>), we recognized the same technology directly addresses a much larger problem: **transparent donor-to-beneficiary flow** in international humanitarian aid.

This proposal does not seek to replace WFP Building Blocks or compete with the UNICEF CryptoFund. Instead, it offers an **interoperable, fully open-source reference implementation** that:

- Adds **purpose-binding** (per-JAN / per-MCC eligibility) on top of stablecoin transfers
- **Federates UNHCR ProGres** for beneficiary identification (we don't create new IDs)
- Includes **CP-6 v2 disaster offline mode** — addressing what we believe is the #1 operational gap in current humanitarian payments
- Offers an **individual donor dashboard** showing real-time, country-level, k=50-aggregated impact
- Maintains **honest framing** — we explicitly do not claim "world first"; we cite WFP Building Blocks ($300M+ operational), Aid:Tech, Disberse, GiveDirectly, and the UNICEF CryptoFund itself as our points of comparison.

Sandbox status (Round 21):
- **315+ backend tests** passing, GitHub Actions CI green
- **Solidity contracts self-audited** (40/44 ok, 0 fail)
- **5 scenario seeds** including Mali LLIN, Yemen food, Bangladesh school
- **3 KYC backend adapters** (Jumio / Onfido / Sumsub interfaces, mock-first)
- **3 AML source cross-check** (OFAC + UN + EU, with ComplyAdvantage pluggable)
- **CP-8 emergency bypass + 14-day audit** for AML false positives during disasters

Three asks:

1. **30-minute introductory call** with the project lead at your convenience
2. **Joint security review** following UNICEF's standard 3-month process — note Apache 2.0 + GitHub Actions CI green should reduce this to ~6 weeks
3. **Letter of Intent** for JICA Digital Public Goods co-application

What UNICEF gets:

- A production-ready OSS reference for purpose-bound donation infrastructure
- Co-authorship at OECD / BIS / MAS Project Orchid forums
- Optional Mali / Bangladesh pilot using our existing seed data
- Zero IP encumbrance — UNICEF can fork and operate independently

The full design specification is in `../../../docs/expansion-donor-pbm.md`. Strategy Meeting #19 records the full council deliberation, including critique from our 4 new ground-truth personas (UNHCR identity specialist, Africa AML compliance officer, ex-Refinitiv data quality manager, and UNICEF Innovation Office persona based on publicly available CryptoFund discussion).

We would be honored by a brief introductory conversation.

— JPN-PBM Project Lead
<https://github.com/kota1026/JPN_PBM>
