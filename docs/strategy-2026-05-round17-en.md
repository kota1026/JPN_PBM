# Strategy Meetings #16 + #17 — CP-6 Disaster-time Offline Authentication Redesign (consecutive sessions)

> **Created**: 2026-05-09 (Round 18)
> **Topic**: CP-6 v1 had a critical assumption error (POS operating premise) → v2 designs for both JP and PH
> **Format**: Strategy Meeting #16 (initial council) + #17 (red-team review with 4 PH ground-truth personas)
> **Output**: 6 JP adoptions + 11 PH adoptions + 4 common modifications
> **Translated**: 2026-05-09 (Round 19)
>
> 🇯🇵 Japanese original: [`strategy-2026-05-round17.md`](./strategy-2026-05-round17.md)

---

## 0. Background: Why redesign?

User's one-line critique:

> **"During a disaster, retailer POS isn't running, is it?"**

This exposed the fundamental flaw of CP-6 v1 ([`docs/cp6-offline-fallback.md`](./cp6-offline-fallback.md)):

| v1 implicit assumption | Reality |
|------------------------|---------|
| Retailer POS powered ON | ❌ Most stores blacked out |
| Staff present at store | ❌ Also evacuated |
| POS retains DB | △ Loss risk if battery dies |
| Paper receipt rolls available | ❌ Supply disrupted |

**Question redefined**: "With zero power and zero connectivity, what authentication system prevents impersonation and double-spending?"

---

## 1. Past discussions (BoJ + BIS + ECB) ─ 5 solution directions

| ID | Approach | Examples | Offline | Power | Double-spend prevention |
|----|----------|----------|---------|-------|------------------------|
| **A** | SE-embedded prepaid (Felica/Suica) | BoJ Phase 2 Pilot, Suica | ✅ Full | △ Reader-side | SE counter |
| **B** | 2-tier wallet (smartphone + IC card) | Banque de France, BoJ Forum 2023 | ✅ | △ | Same |
| **C** | Time-limited offline credit | ECB Digital Euro, Visa floor | ✅ Within limit | △ | pre-auth + reconcile |
| **D** | Hash-chain ticket | BIS Project Polaris | ✅ | △ | Hash irreversibility + counter |
| **E** | Government endpoint terminal | Post-311 SDF distribution | ✅ (satellite) | ✅ Dedicated | Civil servant management |

---

## 2. Strategy Meeting #16 — Initial Council (PH only)

Participants: Field Officer, Researcher, Stablecoin Architect, Cost Guardian, Red Team, Purpose Guardian, CSO/AML, Legal, CFO, Engineer, **🆕 Local Diplomacy Officer, 🆕 Disaster Response Officer (PH-specific)**

**Initial 8 adoptions** (PH-1 through PH-8):

| ID | Adoption |
|----|----------|
| PH-1 | 5-layer Lista Bayanihan model — paper + lista + barangay + GCash + Coins.ph |
| PH-2 | `lista_adapter.py` mock |
| PH-3 | `barangay_endpoint.py` mock |
| PH-4 | `ndrrmc_alert.py` mock (assumed NDRRMC API integration) |
| PH-5 | Paper voucher: opt-in + typhoon season only |
| PH-6 | CP-5 5% operational tolerance + audit |
| PH-7 | Photo-attached voucher (per-individual) |
| PH-8 | DSWD MC + BSP NoL document |

**🥇 #16 MVP**: Field Officer Pia Mendoza (+30) ─ "sari-sari themselves get hit" / "door-to-door visit mandatory"

---

## 3. Strategy Meeting #17 — Red-team Review

User instruction: "Hold the PH agent meeting once more" → **4 new personas** for ground-truth verification:

### New personas

| Persona | Perspective | Main critique |
|---------|-------------|---------------|
| **Aling Maria** (sari-sari owner, 60yo, 22 years) | Supply-side reality | Refuses lista digitization / immediate payout required / store loss risk |
| **Maria Santos** (4Ps recipient, 38yo, 3 children) | Demand-side reality | Smartphone shared by family / barangay walk impossible / household-unit needed |
| **Engr. Roberto Lim** (former Coins.ph) | Internal tech | GCash offline limited / NDRRMC API doesn't exist / Coins.ph piggyback 6 months |
| **Dr. Carmela Reyes** (UP anthropologist) | Cultural critique | Bayanihan = short-term reciprocity / Padrino risk / name romanticization danger |

### #16 → #17 modifications summary

| #16 ID | Status change | Reason |
|--------|---------------|--------|
| PH-1 | ✏️ **5 layers → 3 layers** | L4 (GCash) + L5 (Coins.ph piggyback) impossible within 2026 |
| PH-2 | ✏️ **opt-in + Disaster only** | Aling Maria's instinctive refusal + Carmela's cultural critique |
| PH-3 | ✅ unchanged | Political risk handled separately by PH-9 |
| PH-4 | ✏️ **SMS gateway + PRC API combined** | NDRRMC API doesn't exist |
| PH-5-6, PH-8 | ✅ unchanged | |
| PH-7 | ✏️ **per-individual → household-unit** | Maria Santos' proxy-use need |
| (L4) | ❌ **deleted** | Roberto: 12-18 months development needed |
| (L5) | ❌ **deferred to R20+** | Roberto: Coins.ph compliance 6 months |

### 4 new adoptions (added in #17)

| ID | Proposal | Owner |
|----|----------|-------|
| **PH-9** | Barangay 3-tier delegated authority + mandatory PRC witness (Padrino mitigation) | Carmela + Red Team |
| **PH-10** | Store payout timing ─ both immediate and weekly batch adapters provided | Cost Guardian |
| **PH-11** | Name change: "Lista Bayanihan" → **"Disaster Lista (DL) Protocol"** | Carmela |
| **PH-12** | Yolanda-class (Cat 5+) → **NDRRMC direct distribution phase**, PBM out of scope | Disaster |

**🥇 #17 MVP tied**: **Aling Maria + Roberto Lim** (each +30) ─ field + tech-internal reality checks

---

## 4. JP-side adoptions (#16 confirmed, no #17 changes)

| ID | Adoption | Status |
|----|----------|--------|
| **JP-1** | A + E hybrid (MyNumber Felica SE + shelter terminal) | Design |
| **JP-2** | `services/se_card_adapter.py` mock | Implementation |
| **JP-3** | Paper QR (CP-6a) retained as secondary fallback | Design |
| **JP-4** | Shelter terminal premised on generator + satellite | Operations |
| **JP-5** | CP-5 (no double-spend) = SE counter + on-chain consumed double defense | Design |
| **JP-6** | Existing `offline_fallback.py` logic reused; only endpoints swapped | Implementation |

---

## 5. Round 18 final scope (confirmed ─ JP 6 + PH 11 + common)

### JP side (Round 18)
- `docs/cp6-offline-fallback-v2-jp.md` new
- `backend/app/services/se_card_adapter.py` (mock + tests)

### PH side (Round 18)
- `docs/cp6-offline-fallback-v2-ph.md` new (3-layer DL Protocol, PH-1 through PH-12 reflected)
- `backend/app/services/lista_adapter.py` (opt-in mock + tests)
- `backend/app/services/barangay_endpoint.py` (3-tier delegation + PRC witness mock + tests)
- `backend/app/services/ndrrmc_alert.py` (SMS gateway + PRC API mock + tests)

### Common modifications (Round 18)
- `docs/cp6-offline-fallback.md` head: **"Errata about v1 design assumption error"** section
- `docs/whitepaper-2026.md` §4 full rewrite (both countries listed)
- `docs/pitch-deck-jp.md` + `docs/pitch-deck.md` "world first" expression revision
- `frontend/demo.html` Scene 7-9 fix (to POS-not-needed model)

### Deferred to Round 19+ (explicit in #17)
- Citizen.household_id schema change (PH-7 household-unit voucher complete implementation)
- L4 GCash offline balance (waiting for Coins.ph development)
- L5 Coins.ph piggyback (Coins.ph compliance 6 months)
- NDRRMC SMS gateway real connection (gateway contract needed)
- Felica SE real device connection (MyNumber card reader needed)

---

## 6. Justification of major decisions

### Q1: Why JP = SE + shelter terminal, while PH = paper + barangay + PRC?

**Answer**: **Because infrastructure + culture differ**.

| Aspect | JP | PH |
|--------|----|----|
| SE penetration | MyNumber card Felica existing | PhilSys ID is paper only |
| Disaster frequency | Once in 30 years → heavy armament OK | 20+/year → light deployment needed |
| Trust anchor | Hardware tamper-resistance | Community + post-recovery reconcile |

### Q2: Why withdraw "world first" expression?

**Answer**: **Since CP-6 v1 doesn't work due to assumption error, claiming "world first" is dishonest**.

Correct expression:
- ❌ Old: "World first disaster-time offline fallback"
- ✅ New: "Disaster-time offline PBM **2-country, 2-design** proposal (JP A+E hybrid / PH DL Protocol)"

### Q3: Why drop the "Lista Bayanihan" name?

**Answer**: Dr. Carmela Reyes' anthropological critique is right:
- Bayanihan is **short-term reciprocity** at heart, ill-suited to long-term institutions
- Risk of romanticized poverty view
- → Changed to "**Disaster Lista (DL) Protocol**" (directly expressing function)

### Q4: Why defer household-unit voucher schema change to R19?

**Answer**: PH-7 household-unit requires `household_id` addition to Citizen model → also affects JP side → if done in R18, **scope explosion**. R18 covers design doc + mock services, schema change handled in R19.

---

## 7. Point reconciliation (Round 17 = PR #18 = auto-demo)

| Agent | Detail | Points |
|-------|--------|--------|
| Engineer | demo.html 600 lines + 14 scenes × 3 languages narration + standalone-ization | +30 |
| Researcher | demo-walkthrough.md (browser-less preview) | +10 |
| Cost Guardian | demo > recording ROI estimation | +5 |

**🏆 R17 MVP**: Engineer (5 rounds running)

---

## 8. Phase completion (R17 → R18 estimated)

| Phase | R17 | R18 (planned) | Diff rationale |
|-------|-----|---------------|----------------|
| Phase 1 | 86% | 86% | Unchanged |
| Phase 2 | 71% | **75%** (+4pt) | M+11 (CP-6) v1 ready → **v2 ready** re-evaluated |
| Phase 3 | 40% | **48%** (+8pt) | M+18 evidence strengthened (CP-6 v2 PH/JP parallel implementation) |

In CP-6 v2, **withdrawing "world first" actually increases content honesty** = greater persuasion at international forums.
