# Strategy Meeting #12 — Philippines foundation completion (PhilSys / QR Ph / 4Ps seed / JICA)

> **Created**: 2026-05-08 (round 13)
> **Topic**: Move the Manila pilot from "demo running on screen" to **"a real-diplomacy packet"** — a PhilSys OAuth mock matching the actual API spec, an EMV QR Code Specification-compliant QR Ph parser, 4Ps seed data, and the JICA Digital Public Goods application v1.
> **Output**: 5 items adopted + 1 strategy doc translated.
> **Translated**: 2026-05-09 (round 14)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round12.md`](./strategy-2026-05-round12.md)

---

## 0. Implementation gaps after Round 12

By the end of Round 12 (PR #13 draft):

- ✅ Hybrid `item_eligibility` (3 modes, 14 tests)
- ✅ Tagalog/English citizen UI (`frontend/ph/citizen.html`)
- ✅ Manila landing page (`frontend/ph/index.html`)
- ✅ QR vs JAN research note

**What was still missing**:

| Gap | Impact | Round |
|-----|--------|-------|
| Real PH product master (GS1 480 prefix) | Frontend was full of "unregistered JANs" | **Round 13** |
| Real PH stores / 4Ps program seed | Program IDs were placeholders | **Round 13** |
| PhilSys OAuth mock | Frontend had only HMAC client-side, no server provider | **Round 13** |
| EMV QR Ph parser (field 52 = MCC) | Frontend used naive `MCH:id:mcc:name` strings | **Round 13** |
| JICA application (English) | No paper to start real diplomacy | **Round 13** |
| iPhone real-device scanner verification | No real device | **Round 14** (real-device test) |

→ **Round 13 brings the sandbox to "ready to start real diplomacy"**.

## 1. Adopted (5 items)

| # | Agent | Proposal | Implementation | Impact |
|---|-------|----------|----------------|--------|
| **T1** | Researcher | 4Ps seed (PH products / stores / households / programs) | `seed/ph/{citizens,products,stores,programs}.json` | Lucky Me / Bear Brand / Pampers populate the demo realistically |
| **T2** | Stablecoin Architect | PhilSys OAuth mock | `backend/app/routers/philsys_oauth.py` (same shape as myna_oauth) | Drop-in replaceable with real PhilSys API |
| **T3** | Engineer | EMV QR Ph parser (TLV) | `backend/app/services/qr_ph.py` + 8 tests | BSP Circular 2019-859 compliant, with CRC-16 verification |
| **T4** | Researcher | JICA Digital Public Goods application v1 | `docs/jica-application-draft-en.md` (~6 pages) | Paper to bring into JICA Tokyo HQ |
| **T5** | Researcher | Round 11 strategy meeting translation | `docs/strategy-2026-05-round11-en.md` | i18n maintained at 11/12 |

## 2. PhilSys OAuth Mock design

Same shape as `myna_oauth.py` (RFC 6749 Authorization Code Grant). Differences:

| Aspect | MyNumber Portal v2 (JP) | PhilSys (PH) |
|--------|------------------------|--------------|
| Endpoint base | `/myna/v2/...` | `/philsys/v1/...` |
| User claims | 4 facts (name / address / sex / DoB) | PSN / Name / Address / DoB / **No. of dependents** (4Ps relevant) |
| ID abstraction | HMAC(MyNumber) | HMAC(PSN) |
| Consent screen text | Japanese | English / Tagalog |
| Regulatory base | PIPA Article 16 | Data Privacy Act of 2012 |

→ **Both use `services/privacy.py:hmac_pid()` for pseudonymization, common downstream**. Provider abstraction comes out cleanly.

## 3. EMV QR Ph parser spec

BSP's QR Ph Standard (Circular 2019-859) is EMV QR Code Specification (MPM Mode) compliant. Implementation:

```python
def parse_emv_qr_ph(payload: str) -> QrPhInfo:
    """Parse EMV MPM QR string into structured fields.

    Format: TLV (Tag, Length, Value) sequence
        Tag    Field
        00     Payload Format Indicator ("01")
        02     Point of Initiation Method ("11"=static, "12"=dynamic)
        26-51  Merchant Account Information (PSP-specific subfields)
        52     Merchant Category Code (4-digit ISO 18245)  ← our key
        53     Transaction Currency ("608"=PHP)
        58     Country Code ("PH")
        59     Merchant Name
        60     Merchant City
        62     Additional Data (txID, mobile no., etc.)
        63     CRC-16 checksum (last 4 chars, polynomial 0x1021)
    """
```

CRC-16/CCITT-FALSE verification is also covered by tests (tampering detection).

## 4. JICA Digital Public Goods application structure

6 sections per JICA's published framework (2024 edition):

1. **Project Overview** (1 page) - what / for whom / why
2. **Open Source / DPG Compliance** (1 page) - Apache 2.0 / DPG Standard 9-indicator check
3. **Implementation Plan** (1 page) - 90-day → 18-month staged rollout
4. **Counterpart Strategy** (1 page) - DSWD / Quezon City / Coins.ph contact plan
5. **Budget** (1 page) - JPY 30M/year × 2 years breakdown
6. **Risk & Mitigation** (1 page) - PHPC trust risk / DSWD admin change risk / etc.

**DPG Standard 9 indicators** (Digital Public Goods Alliance) self-assessment table attached.

## 5. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 175+ passed (R12 168 → R13 +tbd)
✓ verify(all) all green

$ # Open /ui/ph/citizen.html → 4Ps seed shows up
```

## 6. Point Reconciliation (Round 12 = PR #13)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | T1 citizen scanner + T2 PH UI + T3 hybrid eligibility + T4/T5 docs | **+30** |
| Researcher | T4 QR vs JAN research | +20 |
| **CSO/AML** | ALWAYS_BLOCKED_MCCS selection + tingi cap design | **+15** |
| Red Team | Pointed out sari-sari should have barcodes after all | +15 |
| Cost Guardian | hybrid mode `cap_no_barcode_jpy` design | +10 |
| Purpose Guardian | Permanent block for MCC 5921 / 5993 / 5813 / 7995 | +10 |
| Others | Standby +5 |

🥇 **MVP**: Engineer (+30, 4 rounds running). **Red Team's pushback became the design improvement core of this round**.

## 7. Round 14 Candidates

What's doable in the sandbox going forward:

1. **PH POS SDK** (`sdk/python/jpn_pbm_pos_ph/`) - GCash mock integration
2. **multi-locale seed loader** (`seed/{jp,ph}/` switching via `--locale`)
3. **JICA / DPG Alliance submission package zip** (whitepaper + pitch + audit + license bundle)
4. **Loom video script** (council member explanation 5 min + lead officer 15 min, 2 versions)
5. **Whitepaper §4 (CP-6) and §6 (Roadmap) updated to incorporate Manila chapter**

Real-diplomacy ready folder:
6. `docs/handoff-packages/{jica,bsp,dswd,coins-ph,quezon-city}/` ─ submission-only dirs

## 8. Phase Completion Trajectory

| Time | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| End R10 | 86% | 57% | 0% |
| End R11 | 86% | 71% | 20% |
| End R12 | 86% | 71% | 20% (M+16 evidence increased via UI) |
| **End R13 (target)** | **86%** | **71%** | **40%** ← M+16 (multi-municipality fork) promoted partial → ready |

Reasons M+16 can be promoted to ready:
- ✅ Codebase shared (Tokyo + Manila confirmed at 99%)
- ✅ Hybrid eligibility implemented (`item_eligibility.py`)
- ✅ Tagalog/English UI complete
- ✅ PH seed (this round)
- ✅ PhilSys OAuth (this round)
- ✅ JICA application draft (this round)
- ❌ Real DSWD / Quezon City agreement (real diplomacy only)
