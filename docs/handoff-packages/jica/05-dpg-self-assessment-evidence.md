# DPG Standard Self-Assessment — Evidence Appendix

> Companion to JICA application v1 §2.1
> Maps each of the 9 Digital Public Goods Standard indicators to specific repository files / commits / external links so JICA reviewers can verify each claim with a click.

---

## Quick reference

Repository: <https://github.com/kota1026/JPN_PBM>
License: Apache 2.0 (`LICENSE` at repo root)
Public release date: 2026-04 (initial commit)

---

## Indicator 1 — Relevance to SDGs

**Claim**: ✅ Aligned with SDGs 1, 3, 11, 16.

| SDG | Project alignment | Evidence |
|-----|-------------------|----------|
| 1 — No Poverty | Manila pilot targets DSWD 4Ps (4.4M households below poverty line) | [`docs/expansion-philippines.md` §2](../../expansion-philippines.md) |
| 3 — Good Health | Childcare subsidy for Tokyo prevents financial barrier to baby formula / diapers | [`seed/programs.json:prog-koto-kosodate-2026`](../../../seed/programs.json) |
| 11 — Sustainable Cities | Disaster-resilient subsidy distribution (CP-6) keeps cities functional during crises | [`docs/cp6-offline-fallback.md`](../../cp6-offline-fallback.md) |
| 16 — Strong Institutions | On-chain audit trail + k-anonymous EBPM increases government accountability | [`backend/app/services/treasury_audit.py`](../../../backend/app/services/treasury_audit.py) + [`backend/app/services/ebpm.py`](../../../backend/app/services/ebpm.py) |

---

## Indicator 2 — Open License

**Claim**: ✅ Apache 2.0 for all code; CC-BY 4.0 for documentation.

Evidence:
- [`LICENSE`](../../../LICENSE) at repo root.
- All 70+ source files start with no proprietary notice.
- No CLA required for contributions (DCO sign-off only).
- License compatible with DPG Standard Indicator 2 acceptance list.

---

## Indicator 3 — Clear Ownership

**Claim**: ⚠️ Pending corporate vehicle formation (TBD upon JICA pre-screening response).

Evidence:
- Currently a personal repository on `kota1026`'s GitHub account, with all PRs being made by this single contributor.
- A 合同会社 (LLC) will be formed in Tokyo (~¥6万 / 1 day) immediately upon JICA pre-screening positive response.
- This is the **only "amber"** indicator and is intentionally deferred to keep operational costs zero during sandbox phase.

---

## Indicator 4 — Platform Independence

**Claim**: ✅ Polygon EVM (open) + Python + SQLite/PostgreSQL — no proprietary cloud lock-in.

Evidence:
- Backend in pure Python with SQLAlchemy: [`backend/app/db.py`](../../../backend/app/db.py)
- Smart contracts on Polygon (open EVM L2): [`contracts/`](../../../contracts/)
- Multi-locale seed loader: [`backend/app/routers/seed.py`](../../../backend/app/routers/seed.py)
- Adapter pattern for chain / GCash / LandBank backends:
  - [`backend/app/services/chain_adapter.py`](../../../backend/app/services/chain_adapter.py) — swap mock ↔ Mumbai ↔ mainnet via env var
  - [`backend/app/services/gcash_adapter.py`](../../../backend/app/services/gcash_adapter.py) — swap mock ↔ sandbox ↔ production
  - [`backend/app/services/landbank_bridge.py`](../../../backend/app/services/landbank_bridge.py) — swap mock ↔ DSWD proxy

---

## Indicator 5 — Documentation

**Claim**: ✅ 45+ documentation pages.

Evidence:
- Whitepaper: [`docs/whitepaper-2026.md`](../../whitepaper-2026.md) (8 sections + 2 appendices, ~30 pages)
- Architecture: [`docs/architecture.md`](../../architecture.md)
- Production runbook: [`docs/production-runbook.md`](../../production-runbook.md)
- Multi-municipality fork guide: [`docs/fork-guide.md`](../../fork-guide.md)
- Manila expansion spec: [`docs/expansion-philippines.md`](../../expansion-philippines.md)
- Per-recipient handoff packages: [`docs/handoff-packages/`](../../)
- Strategy meetings: 14 in JP, 13 in EN translation
- Inline code documentation: docstrings on every public function

---

## Indicator 6 — Mechanism for Extracting Data in Non-Proprietary Formats

**Claim**: ✅ All exports JSON / CSV / OpenAPI.

Evidence:
- API responses: JSON (FastAPI default).
- Seed data: JSON ([`seed/citizens.json`](../../../seed/citizens.json) etc.).
- EBPM exports: CSV / JSON via [`backend/app/routers/ebpm.py`](../../../backend/app/routers/ebpm.py).
- OpenAPI spec auto-generated at `/docs` (Swagger).
- Smart contract events: standard EVM event format (consumable by any block explorer).

---

## Indicator 7 — Privacy and Applicable Laws

**Claim**: ✅ PIPA Article 16 (Japan) + Data Privacy Act of 2012 (Philippines).

Evidence:
- HMAC pseudonymization: [`backend/app/services/privacy.py`](../../../backend/app/services/privacy.py)
- k-anonymity (k=5): [`backend/app/services/ebpm.py:K_THRESHOLD`](../../../backend/app/services/ebpm.py)
- Consent log: [`backend/app/models/consent.py:ConsentLog`](../../../backend/app/models/consent.py)
- DSWD-specific Data Privacy Act compliance brief: [`docs/handoff-packages/dswd/03-data-privacy.md`](../../dswd/03-data-privacy.md)
- 250+ tests verify privacy invariants (HMAC determinism, consent log writes, k-threshold enforcement)

---

## Indicator 8 — Standards & Best Practices

**Claim**: ✅ EMV QR, RFC 6749 OAuth, GS1, ISO 18245 MCC, ISO 4217, EIP-191.

| Standard | Where used | Evidence file |
|----------|-----------|---------------|
| EMV QR Code Specification (MPM) | QR Ph parser | [`backend/app/services/qr_ph.py`](../../../backend/app/services/qr_ph.py) |
| BSP Circular 2019-859 | Same | Same |
| RFC 6749 (OAuth 2.0 Authorization Code Grant) | MyNumber + PhilSys mocks | [`backend/app/routers/myna_oauth.py`](../../../backend/app/routers/myna_oauth.py), [`backend/app/routers/philsys_oauth.py`](../../../backend/app/routers/philsys_oauth.py) |
| GS1 EAN-13 (JAN, prefix 480 PH) | Product catalog | [`seed/products.json`](../../../seed/products.json), [`seed/ph/products.json`](../../../seed/ph/products.json) |
| ISO 18245 MCC | Merchant categorization | [`backend/app/services/item_eligibility.py:ALWAYS_BLOCKED_MCCS`](../../../backend/app/services/item_eligibility.py) |
| ISO 4217 currency codes | Token denomination | "608" = PHP in QR Ph parser |
| EIP-191 personal_sign | Offline coupon signatures | [`backend/app/services/sol_compat.py:eth_signed_digest`](../../../backend/app/services/sol_compat.py) |
| EIP-2 low-s ECDSA | (planned for production) | self-audit warns at ID-18 |
| OWASP Smart Contract Top 10 (2025) | Self-audit checklist | [`scripts/contract_audit.py`](../../../scripts/contract_audit.py) (24 items × 2 contracts) |

---

## Indicator 9 — Do No Harm by Design

**Claim**: ✅ MCC blacklist + k-anonymity + revocable contracts.

Evidence:
- **Revocable contracts**: `governor.revokeProgram()` returns all funds to treasury, prevents new spend ([`contracts/PBM.sol:revokeProgram`](../../../contracts/PBM.sol)).
- **Blocked MCCs** (alcohol/tobacco/gambling): [`backend/app/services/item_eligibility.py:ALWAYS_BLOCKED_MCCS`](../../../backend/app/services/item_eligibility.py)
- **k-anonymity** prevents demographic re-identification: [`backend/app/services/ebpm.py`](../../../backend/app/services/ebpm.py)
- **Per-citizen monthly cap** prevents over-disbursement: PBM contract `Allowance.used` enforcement.
- **Audit trail** every state change: 14 routers, all emit indexed events.
- **No-barcode cap** in hybrid eligibility prevents store-side fraud: [`backend/app/services/item_eligibility.py:hybrid mode`](../../../backend/app/services/item_eligibility.py).

---

## Summary

| Indicator | Status | Confidence |
|-----------|--------|-----------|
| 1. SDG relevance | ✅ | High |
| 2. Open license | ✅ | High |
| 3. Clear ownership | ⚠️ | Pending corporate vehicle (1-day formation) |
| 4. Platform independence | ✅ | High |
| 5. Documentation | ✅ | High (45+ docs) |
| 6. Open data formats | ✅ | High |
| 7. Privacy compliance | ✅ | High (250+ tests) |
| 8. Standards adherence | ✅ | High |
| 9. Do no harm | ✅ | High |

**8 of 9 fully met today; 9 of 9 within 1 business day of JICA positive response.**

This appendix is one of the 6 documents in the JICA handoff package generated by `bash scripts/build_handoff_package.sh jica`.
