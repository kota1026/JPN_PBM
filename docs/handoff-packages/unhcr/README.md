# Handoff Package: UNHCR (UN Refugee Agency)

> **Recipient**: UNHCR Innovation Service + Digital Identity team (Geneva)
> **Subject**: ProGres federation for Donor-PBM (beneficiary identification, NOT new ID system)
> **Repository**: <https://github.com/kota1026/JPN_PBM>

## What's in this package

| # | File | Role |
|---|------|------|
| 1 | `01-cover-letter.md` | One-page cover letter |
| 2 | `02-progres-federation.md` | Federation protocol spec |
| 3 | `../../../docs/expansion-donor-pbm.md` §3, §5 | Donor-PBM design with ProGres role |
| 4 | `../../../backend/app/services/unhcr_progres_adapter.py` | Reference adapter code |

## Critical message

We **do not** propose:
- A new identity system competing with ProGres
- On-chain biometric storage
- Direct API access to ProGres beneficiary data

We **do** propose:
- HMAC-pseudonymized federation of ProGres IDs
- Read-only attestation API (Active/Inactive status, country, region — no biometric)
- Apache 2.0 OSS reference, UNHCR can fork

The Rohingya 2021 data incident is explicitly cited in our design as the reason **biometric is off-chain only** (DPI-7).

## Action requested

1. **30-minute introductory call**
2. **Joint risk assessment** of the proposed federation
3. **Decision**: federate (proceed) / advise alternative / decline (and explain so we adapt)
