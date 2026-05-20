# ProGres Federation for Donor-PBM (Spec v0.1)

> **Status**: Draft, requires UNHCR Innovation Service validation.
> **Risk lens**: Rohingya 2021 incident, biometric data leakage prevention.

## 1. Principles (non-negotiable)

| Principle | Implementation |
|-----------|----------------|
| Biometric never on-chain | DPI-7 in our design — only HMAC PID reaches contract |
| Raw ProGres ID never persisted in our DB | HMAC at API ingestion boundary |
| Read-only federation | We never write to ProGres; we only ask "is this PID active?" |
| Minimal data exposure | Country + region (not specific camp) + active status + member count |
| Donor-side display: k=50, country-level only | Per-individual identification structurally impossible |

## 2. API surface (read-only)

UNHCR provides (or hosts) an attestation endpoint:

```
POST /unhcr/v1/attest
Headers: { Authorization: "Bearer <data-sharing-agreement-token>" }
Body: {
  "progres_ids": ["ML-PRG-001", "YE-PRG-002", ...]
}

Response: {
  "attestations": [
    {
      "progres_id_hmac": "abc123...",   // HMAC by UNHCR-side key
      "country_of_residence": "ML",
      "region": "Kayes",
      "status": "active",
      "member_count": 5,
      "children_under_5_count": 2,
      "attested_at": 1718000000,
      "valid_until": 1720592000     // 30-day attestation
    },
    ...
  ],
  "signature": "..."                 // UNHCR signing key
}
```

JPN-PBM caches attestations for 30 days. If a beneficiary status changes (e.g., resettled), we re-fetch.

## 3. What JPN-PBM stores

```python
# Citizen.household_id = HMAC(progres_id)
# Citizen does NOT store: raw progres_id, biometric, name, location > region
```

## 4. Audit trail (UNHCR can audit anytime)

JPN-PBM exposes a UNHCR-only endpoint:

```
GET /jpn-pbm/v1/unhcr/audit?progres_id_hmac=...
Headers: { Authorization: "Bearer <unhcr-audit-token>" }

Response: {
  "household_id_hmac": "abc123...",
  "donations_used_this_month_centi": 12500,
  "monthly_cap_centi": 50000,
  "programs": ["prog-unicef-mali-llin-2026"],
  "distribution_count": 2,
  "last_distribution_at": "2026-06-15"
}
```

UNHCR can verify: are aid recipients receiving what they should? Is anyone over-cap? Are sanctions being respected?

## 5. Rollback path

If UNHCR identifies a problem:
- UNHCR can **revoke our data-sharing token** unilaterally
- Within 24h, JPN-PBM stops distribution to all federated beneficiaries
- Within 7 days, JPN-PBM purges all UNHCR-sourced HMAC attestations
- Audit log preserved for 90 days (Data Privacy Act / GDPR compliance)

## 6. Mock implementation status (R21)

```python
# backend/app/services/unhcr_progres_adapter.py
class MockUnhcrProGresBackend:
    # 10 mock households across Mali (Kayes/Koulikoro/Sikasso),
    # Yemen (Sa'ada/Hodeidah/Hajjah), Bangladesh (Chattogram/Dhaka)
    # 7 tests passing
```

Real `HcbUnhcrProGresBackend` is stubbed with `NotImplementedError("R22+")` — explicit gating on UNHCR agreement.

## 7. Why this matters

Refugees deserve the same transparency in aid as any other recipient — **and** the same privacy protection. The current state of humanitarian payments is opaque to donors but also uncomfortably opaque to refugees themselves (they often don't know what they're entitled to, or why they received this amount and not more).

This federation lets a Syrian refugee in Za'atari potentially see (via UNHCR-provided UI):
- "Your household qualified for $50/month food allowance this month"
- "Of that, $42 has been distributed at WFP-cooperatives in your camp"
- "$8 remains for the next 6 days"

— without exposing any individual data to donors, who only see country-level k=50 aggregates.

This is the design pattern we wish to validate with UNHCR.
