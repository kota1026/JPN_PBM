# Strategy Meeting #11 — Smartphone scan × Hybrid eligibility (Tokyo + Manila dual-use)

> **Created**: 2026-05-04 (round 12)
> **Topic**: Translate two design insights raised by the user into implementation:
> 1. **"Sari-sari stores can run without POS — barcode-bearing items + recipient smartphone is enough"**
> 2. **"Product-level (JAN) + store-level (MCC) hybrid is the realistic model"**
>
> **Output**: 5 implementations + 1 strategy document
> **Translated**: 2026-05-08 (round 13)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round11.md`](./strategy-2026-05-round11.md)

---

## 0. Situation

In Round 11 (PR #12 draft), `docs/expansion-philippines.md` was first written with:

- Manila product identification = **"merchant-only MCC whitelisting"** (single mode)
- This puts **100% trust in store owners**, weak from 4Ps audit perspective
- No verification mechanism on the recipient side

User's pushback:

> **"Sari-sari stores have barcoded items in their inventory. Smartphones can read those, no?"**

→ This insight is right both for the **sari-sari reality** and for **4Ps ownership**:

| Product class | Sari-sari shelf share | Barcoded? | 4Ps fit | Decision logic |
|---------------|----------------------|-----------|---------|----------------|
| Branded packaged / canned | 50-60% | ✅ | ✅ | **JAN/EAN** strict check |
| Tingi / loose goods | 30-40% | ❌ | △ | **MCC 5411 whitelisted store fallback** |
| Liquor / tobacco | 5-10% | ✅ or ❌ | ❌ | **Both blocked** |

→ **Hybrid** = if barcode present, strict; if absent, store-MCC + monthly cap.
This unifies the model for both the Philippines and Japan (individual shops).

## 1. Adopted (5 items)

| # | Agent | Proposal | Implementation | Impact |
|---|-------|----------|----------------|--------|
| **T1** | Engineer | Smartphone ZXing.js barcode scanner | WebRTC + ZXing in `frontend/citizen.html` + `frontend/ph/citizen.html` | **No POS hardware**; one phone runs |
| **T2** | Researcher | Tagalog UI + GCash QR Ph mock | `frontend/ph/index.html` + `citizen.html` (Tagalog/English) | Manila pilot UX complete |
| **T3** | Stablecoin Architect | Hybrid eligibility | Extension of `services/eligibility.py` + tests | Strict if barcode / MCC fallback if not |
| **T4** | Researcher | QR vs JAN research document | `docs/qr-vs-jan-research.md` | PH GS1 480 / sari-sari POS adoption / QR Ph MCC spec |
| **T5** | Engineer | expansion-philippines.md correction | Rewrite §3 to hybrid design | Design doc consistency |

## 2. Hybrid eligibility data model

```python
# New: stores carry MCC and approved categories
class Store:
    id: str
    mcc: int                    # 5411=grocery, 5912=drug, 5921=liquor, ...
    approved_for_programs: list[str]   # set of approved program IDs

# New: programs choose "JAN required or optional" via eligibility_mode
class Program:
    id: str
    eligibility_mode: Literal["jan_strict", "mcc_only", "hybrid"]
    eligible_jans: set[str]       # used for jan_strict / hybrid
    approved_mccs: set[int]       # used for mcc_only / hybrid
    cap_no_barcode_jpy: int       # in hybrid: monthly cap on "no-barcode purchases"
```

Decision algorithm (Python pseudocode):

```python
def is_eligible(program, store, item):
    if program.eligibility_mode == "jan_strict":
        return item.has_barcode and item.jan in program.eligible_jans
    if program.eligibility_mode == "mcc_only":
        return store.mcc in program.approved_mccs
    if program.eligibility_mode == "hybrid":
        if item.has_barcode:
            return item.jan in program.eligible_jans       # ← strict
        return (store.mcc in program.approved_mccs and
                month_no_barcode_used + item.price <= program.cap_no_barcode_jpy)
    raise ValueError(f"unknown mode: {program.eligibility_mode}")
```

## 3. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 165+ passed (R11 154 → R12 +11)
✓ verify(all) all green

$ # Open /ui/citizen.html in browser, scan barcode (real-device equivalent)
$ # Open /ui/ph/citizen.html, Tagalog UI appears + scanner starts
```

## 4. Point Reconciliation (Round 11)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | A1 audit + A4 auto_metrics + B1 EN landing + B2 pitch + verify mode | **+30** |
| Researcher | A2 whitepaper 600 lines + A3 #8 #9 translations | +25 |
| Cost Guardian | C1 audit / C2 i18n verify mode | +15 |
| **CSO/AML** | Self-pushed honest tone on the implementation | **+15** |
| Red Team | Pointed out unaddressed Polygon-not-deployed issue | +10 |
| Others | Standby +5 |

🥇 **MVP**: Engineer (+30, 3 rounds running)

## 5. Round 13 Candidates

What's doable in the sandbox is genuinely **the last hill** by Round 12 (real webcam dependency starts). Round 13+:

1. **Polygon Mumbai actual deploy** (RPC URL needed)
2. **GCash sandbox API** real-mock integration (assumes Coins.ph contact made)
3. **JICA Philippine application v1** English draft
4. **Marp PDF generation + submission package zip** (form factor for sending)
5. **Video script → actual recording (Loom)** (for council member explanation)

## 6. Phase Completion Update Target

| Phase | done | ready | partial | blocked | pending | Total | Completion |
|-------|------|-------|---------|---------|---------|-------|------------|
| Phase 1 | 3 | 3 | 0 | 1 | 0 | 7 | 86% (unchanged) |
| Phase 2 | 1 | 4 | 1 | 1 | 0 | 7 | 71% (unchanged) |
| Phase 3 | 0 | **2** (+1) | 0 | 2 | 1 | 5 | **40%** (+20pt) ← M+16 (multi-municipality fork) promoted to ready |

**Round 12 effect**: Manila pilot UX complete + hybrid design fixed → Phase 3 M+16 (multi-municipality fork) goes partial → ready.
