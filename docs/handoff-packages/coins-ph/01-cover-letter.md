# To: Coins.ph executive team

**Re**: Open-source PHPC integration — JPN-PBM 4Ps pilot proposal
**From**: JPN-PBM project lead (corporate vehicle TBD)
**Date**: 2026-05-09 (draft)

---

Dear Coins.ph team,

We are an open-source initiative (Apache 2.0) designed to deploy **Programmable Subsidy** infrastructure for municipal welfare programs. Our Round 13–14 work (visible at <https://github.com/kota1026/JPN_PBM>) builds the Manila pilot specifically around **PHPC** as the underlying token.

What we have already implemented to support PHPC integration:

- **EMV QR Ph parser** ([`backend/app/services/qr_ph.py`](../../../backend/app/services/qr_ph.py)) — BSP Circular 2019-859 compliant, with CRC-16/CCITT-FALSE verification and tamper detection. 15 unit tests passing.
- **Hybrid eligibility model** ([`backend/app/services/item_eligibility.py`](../../../backend/app/services/item_eligibility.py)) — designed for sari-sari retail where POS scanners are absent, using barcode scan from the recipient smartphone + MCC-fallback for tingi/loose goods. 14 tests.
- **PhilSys OAuth Mock** ([`backend/app/routers/philsys_oauth.py`](../../../backend/app/routers/philsys_oauth.py)) — symmetric to our Japanese MyNumber Portal v2 OAuth, ready to swap in the production PhilSys API.
- **Tagalog/English citizen UI** ([`frontend/ph/citizen.html`](../../../frontend/ph/citizen.html)) — works on the same kind of low-end Android device sari-sari recipients carry today.
- **PH POS SDK** ([`sdk/python/jpn_pbm_pos_ph/`](../../../sdk/python/jpn_pbm_pos_ph/)) — drives the QR Ph + GCash mock flow end-to-end with 11 unit tests.

What we want from Coins.ph:

1. **PHPC sandbox testnet allocation** — a test wallet and token mint authorization.
2. **GCash QR Ph sandbox API access** — for end-to-end charge flow testing.
3. **Joint technical review** of our `qr_ph.py` parser implementation (BSP Circular 2019-859 conformance).
4. **Strategic Letter of Intent** for our JICA Digital Public Goods application — co-application strengthens both sides.

What Coins.ph gets:

- The largest concrete PHPC use case proposed to date (DSWD 4Ps, 4.4M households).
- Cross-border stablecoin demo (JPYC ↔ PHPC) for OECD / BIS Agorá presentations.
- Direct path from BSP regulatory sandbox to DSWD national program.
- Apache 2.0 license: zero IP encumbrance.

We would be grateful for a 30-minute introductory call. The full whitepaper is at `../../../docs/whitepaper-2026.md`; the Manila pilot specifics are at `../../../docs/expansion-philippines.md`.

Thank you for your consideration.

— JPN-PBM Project Lead
<https://github.com/kota1026/JPN_PBM>
