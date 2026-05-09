# Handoff Package: Coins.ph (PHPC stablecoin issuer)

> **Recipient**: Coins.ph executive team (CEO Wei Zhou's office)
> **Subject**: Technical proposal for PHPC integration in JPN-PBM 4Ps pilot
> **Repository**: <https://github.com/kota1026/JPN_PBM>

## What's in this package

| # | File | Role |
|---|------|------|
| 1 | `01-cover-letter.md` | Brief technical letter |
| 2 | `02-architecture.md` | High-level diagram |
| 3 | `../../../docs/whitepaper-2026.md` (§4 CP-6) | Disaster fallback details |
| 4 | `../../../docs/cp6-offline-fallback.md` | CP-6 deep dive |
| 5 | `../../../docs/qr-vs-jan-research.md` | QR Ph parser compatibility analysis |
| 6 | `../../../backend/app/services/qr_ph.py` | Open-source EMV QR Ph parser (PHPC merchant identification) |

## Reading order

1. **`01-cover-letter.md`** — 3 minute read
2. **`02-architecture.md`** — 5 minute diagram
3. **`../../../docs/whitepaper-2026.md` §6.4 (Manila Twin Pilot)** — 10 minutes
4. **Skim `../../../docs/cp6-offline-fallback.md`** for the differentiator — 5 minutes

Total: ~25 minutes.

## Action requested from Coins.ph

1. **PHPC sandbox testnet allocation** — 1 testnet wallet + token mint authorization (no real funds).
2. **GCash / QR Ph sandbox API access** — for cart-payment integration testing.
3. **Joint technical review** of `services/qr_ph.py` to confirm BSP Circular 2019-859 compliance.
4. **Strategic letter of intent** — for inclusion in our JICA application as a co-applicant.

## Why this benefits Coins.ph

- **Lighthouse use case for PHPC**: 4Ps with 4.4M households is the largest single PHPC use case imaginable.
- **Co-branded with JPYC**: cross-border stablecoin demonstration at OECD / BIS / MAS.
- **Public-sector entry path**: from BSP regulatory sandbox to actual DSWD national program.
- **Apache 2.0 means zero IP encumbrance** for Coins.ph; this is a public good.
