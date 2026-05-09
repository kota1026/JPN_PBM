# JICA Digital Public Goods Initiative — Cover Letter

**To**: JICA Tokyo Headquarters · DPG Team
**From**: JPN-PBM Project Lead (corporate vehicle TBD upon pre-screening)
**Re**: FY2026 funding application — Tokyo + Manila Twin Pilot for Programmable Subsidy Infrastructure
**Date**: 2026-05-09 (draft)

---

Dear JICA DPG team,

We are submitting JPN-PBM, an open-source Programmable-Subsidy Infrastructure that has reached production-ready maturity in the sandbox (175+ passing tests, GitHub Actions CI green, 24-item smart-contract self-audit at `ok=40 / warn=4 / fail=0`).

The project bridges two jurisdictions on a single codebase:

- **Tokyo (Koto Ward)**: childcare and disaster-stockpile subsidies in JPYC stablecoin, leveraging the existing Tokyo Innovation Base partnerships.
- **Manila (Quezon City + DSWD 4Ps)**: 4Ps-PBM pilot in PHPC stablecoin (BSP-approved 2024), specifically designed for sari-sari retail using smartphone barcode scanning + EMV QR Ph (no POS hardware needed).

Why this fits the JICA Digital Public Goods Initiative:

1. **It is operating code, not a concept** — clone the repo and run `bash scripts/verify.sh all`.
2. **It is licensed Apache 2.0**, with documentation in Japanese, English, and Tagalog.
3. **Its world-first feature (CP-6 disaster fallback)** delivers monthly value in the Philippines (~20 typhoons / year) — exactly the LMIC reality the DPG initiative aims to serve.
4. **Both stablecoins (JPYC, PHPC) are regulator-pegged** under PSA Type II (Japan) and BSP regulatory sandbox (Philippines) respectively, avoiding cryptocurrency volatility risk.
5. **The codebase is 99% shared** between the two pilots, making this a true twin-pilot at a fraction of the marginal cost.

What we ask of JICA:

| Step | Form | Time |
|------|------|------|
| 1. Pre-screening conversation | 30-minute call | 1–2 weeks |
| 2. Manila introduction | DSWD + Quezon City Innovation Office | 4–8 weeks |
| 3. Application v2 co-development | Iterative | 2–4 weeks post-call |

Funding requested: **JPY 65M over 24 months** (with ~JPY 27M in-kind co-funding from JPYC Inc. + Coins.ph + Tokyo Innovation Base).

Detailed application: see `../../../docs/jica-application-draft-en.md` in the accompanying repository.

Sincerely,

— JPN-PBM Project Lead
<https://github.com/kota1026/JPN_PBM>

---

*This is a draft cover letter prepared in the development sandbox. The corporate vehicle, signatures, and final project lead will be designated upon JICA pre-screening response.*
