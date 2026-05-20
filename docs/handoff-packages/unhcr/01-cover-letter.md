# To: UNHCR Innovation Service + Digital Identity Team (Geneva)

**Re**: ProGres federation for transparent donor → beneficiary aid flow
**Date**: 2026-05-20 (draft)

---

Dear UNHCR Innovation team,

ProGres is the most trusted refugee identity system in the world. We do not propose to replace it, and we do not propose any new identity system. Instead, we propose a **read-only federation pattern** that leverages ProGres for beneficiary attestation in transparent donor-funded aid distribution.

Our work, JPN-PBM (<https://github.com/kota1026/JPN_PBM>, Apache 2.0), provides:

- **Purpose-binding** for donations via on-chain PBM contracts
- **Donor-facing transparency dashboard** (k=50 aggregation, country-level only)
- **CP-6 disaster offline mode** addressing network outage scenarios

For the system to function in refugee contexts, we need to identify beneficiaries. We refuse to create a parallel identity system. The right answer is to federate with ProGres.

**Federation pattern proposed**:

```
JPN-PBM Donor-PBM contract  ←─── HMAC(ProGres ID)  ─── UNHCR field
                                                              ↓
                                                       Existing iris auth
                                                       Existing ProGres roster
                                                       Existing biometric never on-chain
```

**What we will NOT do** (explicit, per the Rohingya 2021 incident lesson):
- Biometric data on-chain (DPI-7 in our design)
- Persistent storage of raw ProGres IDs
- Cross-reference with other refugee datasets
- Donor-facing display of individual beneficiary identity

**What we ask**:

1. **30-minute introductory call** to validate / invalidate the federation idea
2. **Joint risk assessment** of our proposed pattern
3. **Decision**: federate, advise alternative pattern, or decline (and we'll adapt)

The reference adapter code is in `../../../backend/app/services/unhcr_progres_adapter.py`. It's currently a **Mock-only** implementation operating on test ProGres-like data (`ML-PRG-001`, `YE-PRG-001`, etc.). Real integration is **explicitly gated** on a UNHCR data-sharing agreement.

We are deliberately approaching UNHCR before any real beneficiary integration. We want this to be done right.

— JPN-PBM Project Lead
