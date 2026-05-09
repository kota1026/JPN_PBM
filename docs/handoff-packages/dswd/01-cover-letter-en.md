# To: DSWD Region NCR · 4Ps Program Management

**Re**: 4Ps Programmable Subsidy (PBM) — pilot proposal for Quezon City closed alpha
**From**: JPN-PBM Project (Tokyo + Manila Twin Pilot)
**Date**: 2026-05-09 (draft)

---

Dear DSWD team,

We are an open-source international initiative led from Tokyo, designed to make municipal subsidy distribution **purpose-bound** through stablecoin technology. Our system is already operating in sandbox at <https://github.com/kota1026/JPN_PBM>, with 175+ unit tests, GitHub Actions CI green, and a 24-item smart-contract self-audit done.

We are seeking DSWD's collaboration on a **closed-alpha pilot of 4Ps PBM** in Quezon City: 5 households × 5 sari-sari stores × 3 months. The pilot uses **PHPC** (Bangko Sentral ng Pilipinas-approved peso stablecoin from Coins.ph, regulatory sandbox 2024) as the underlying value layer.

What is different from current cash-based 4Ps:

| Issue | Current 4Ps (cash) | 4Ps PBM (proposed) |
|-------|---------------------|---------------------|
| Off-purpose use (alcohol/tobacco) | ~5–7% silently leaks | **Hard-blocked** by MCC (alcohol = 5921, tobacco = 5993) |
| Disbursement during typhoons | Halts when networks down | **Continues** via pre-signed offline QR (CP-6) |
| Reporting lag | 4–8 weeks | **Real-time** k-anonymous KPI dashboard |
| Fraud detection | Manual audit only | On-chain `consumed[]` mapping prevents double-redemption |
| Vendor lock-in | Possible with proprietary system | **Apache 2.0 open source** — DSWD owns deployment |

What we ask from DSWD:

1. **Identify a pilot LGU** (we propose **Quezon City**, given existing DICT relationships).
2. **Approve participation of 5 mock 4Ps households** for the closed alpha (no real DSWD funds during alpha — uses sandbox PHPC).
3. **Co-author the operational protocol** for sari-sari merchant onboarding.
4. **Provide observer status** in our test runs.

What DSWD gets:

- A working 4Ps leakage reduction tool, validated in sandbox before any real money is touched.
- A real-time KPI dashboard accessible without raw PII.
- A reference implementation other Southeast Asian welfare ministries could adopt.
- An OECD / BIS / MAS conference contribution credit.

What we get:

- DSWD's domain expertise on 4Ps operational realities.
- Permission to engage Coins.ph and GCash with DSWD's blessing.
- A real Letter of Intent, which strengthens our JICA Digital Public Goods application.

The detailed 4Ps PBM specification follows in `02-4ps-pilot-spec.md`. Privacy compliance under the Data Privacy Act of 2012 is documented in `03-data-privacy.md`.

We appreciate DSWD's consideration. We would be honored by a 30-minute introductory meeting at your convenience.

— JPN-PBM Project Lead
<https://github.com/kota1026/JPN_PBM>
