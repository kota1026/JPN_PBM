# To: WFP Building Blocks team (Munich + globally distributed)

**Re**: Interoperability proposal between Building Blocks and JPN-PBM Donor-PBM
**Date**: 2026-05-20 (draft)

---

Dear Building Blocks team,

Your work since 2017 is the **single most important real-world demonstration** of blockchain in humanitarian payments. Reading the WFP Innovation Accelerator papers, the $300M+ moved across 1M+ beneficiaries (Jordan, Bangladesh, Lebanon, Ukraine) is the proof point we've all been waiting for in this space.

We are JPN-PBM, an open-source Programmable Subsidy infrastructure (originally Tokyo + Manila municipal). Through 21 development rounds, we recognized our purpose-binding + disaster offline architecture is **highly complementary to Building Blocks** — not competing.

**What we have that you might value**:

1. **Apache 2.0 OSS** — fully forkable, no IP encumbrance
2. **CP-6 v2 offline disaster mode** — addresses the network-outage gap that has been hard for Building Blocks (we believe — please correct us)
3. **Individual donor UI** — the donor-facing dashboard layer Building Blocks does not have (UN-agency-only)
4. **Multi-stablecoin + multi-country** — JPYC, PHPC, USDC adapters already implemented

**What Building Blocks has that we deeply respect**:

1. **Operational scale** ($300M+, 1M+ beneficiaries)
2. **UN procurement compatibility** (we're outside; you're inside)
3. **iris-biometric integration** with UNHCR ProGres
4. **Field operational expertise** across conflict zones

**Proposed interoperability**:

```
[JPN-PBM Donor side]              [Building Blocks beneficiary side]
   ↓ federated PID attestation       ↓
   ↓ ←  consumed-state cross-check ─ ↓
   ↓                                  ↓
   Donor dashboard sees combined impact
```

Concrete federation protocol draft is in `02-interop-spec.md`. We're proposing JPN-PBM as the **donor-facing public layer**, Building Blocks as the **operational distribution layer**. We do NOT propose to replace any of your existing infrastructure.

**What we ask**:

1. A 30-minute call to validate / invalidate the interop idea
2. Joint API specification iteration (if validated)
3. Pilot consideration at one existing Building Blocks deployment

**Optional**: Joint paper at OECD Blockchain Policy Forum 2026 or BIS Agorá — Building Blocks + JPN-PBM as a reference pattern.

Repository: <https://github.com/kota1026/JPN_PBM>
License: Apache 2.0

We would be honored by a brief technical conversation.

— JPN-PBM Project Lead
