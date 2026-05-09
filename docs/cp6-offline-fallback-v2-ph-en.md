# CP-6 v2 (Philippines) — Disaster Lista (DL) Protocol

> **Created**: 2026-05-09 (Round 18) / **Replaces**: [`cp6-offline-fallback.md`](./cp6-offline-fallback.md) (v1)
> **Reference**: Strategy Meetings #16 + #17 ([`strategy-2026-05-round17.md`](./strategy-2026-05-round17.md))
> **Name origin**: At Strategy Meeting #17, Dr. Carmela Reyes (UP anthropologist) criticized the "Lista Bayanihan" name as risking **a romanticized view of poverty** → renamed to **"Disaster Lista (DL) Protocol"**.
>
> 🇯🇵 Japanese original: [`cp6-offline-fallback-v2-ph.md`](./cp6-offline-fallback-v2-ph.md)

---

## 1. Design principles

JP works on **hardware tamper-resistance**, but PH has:
- No SE-equivalent national ID (PhilSys is paper-based)
- National uniform shelter-terminal deployment is unrealistic on government budget
- BUT **Filipino community trust (lista culture)** already operates as social infrastructure

→ Three layers: **community trust + paper + post-recovery reconcile**. **No SE used**.

---

## 2. Architecture (3 layers)

```
[Layer 1] Paper voucher (laminated, water-resistant)
              ─ distributed to opt-in 4Ps recipients in peacetime
              ─ typhoon-season (June–Nov) only — ~PHP 50M/year
              ─ household-unit voucher (primary recipient photo + member count)

[Layer 2] Disaster Lista (DL) ─ digitized sari-sari informal credit
              ─ does NOT intervene in normal peacetime operations
              ─ activates only during NDRRMC Code Red declaration
              ─ sari-sari opt-in
              ─ disaster-only PHP 200/household/day credit limit

[Layer 3] Barangay + Red Cross witness
              ─ barangay hall (42K nationwide) ledger management
              ─ 3-tier delegated authority: captain → kagawad → tanod (mitigates Padrino risk)
              ─ PRC (Philippine Red Cross) volunteer must be present
              ─ door-to-door visits executed by PRC
```

> **NOT implemented in Round 18 (deferred to R20+)**:
> - L4 GCash offline balance (Coins.ph development needs 12–18 months)
> - L5 Coins.ph piggyback (compliance review needs 6 months)

---

## 3. Layer details

### Layer 1: Paper voucher (laminated)

| Item | Detail |
|------|--------|
| **Distribution** | 4Ps recipients who opt in (estimated 10–20%) |
| **Period** | Typhoon season June–November (6 months/year) |
| **Issue cost** | PHP 8/sheet (print PHP 5 + laminate PHP 3) |
| **Total cost** | 4.4M × 15% × 6 months = ~PHP 32M/year |
| **Voucher content** | Household ID HMAC + primary recipient photo + member count + monthly cap (PHP 1,400 4Ps standard) + ECDSA signature |
| **Validity** | Issue month only (30-day grace if NDRRMC Code Red active) |
| **Collection** | Received by sari-sari/barangay, scanned & ingested to contract after recovery |

### Layer 2: Disaster Lista (DL)

| Item | Detail |
|------|--------|
| **Activation** | NDRRMC declares Code Red (received via SMS gateway) |
| **Eligible stores** | Opt-in sari-sari + Mercury Drug, etc. |
| **Credit limit** | PHP 200/household/day (Aling Maria's recommendation, monthly accumulation PHP 6,000) |
| **Recording** | (a) Store owner's handwritten lista book (b) Recipient household ID + photo ID confirmation (c) Within 1 week of recovery, batch-submitted to contract via DSWD |
| **Anti-fraud** | 1 day × 1 household × 1 sari-sari uniqueness, 3-strike rule (3 violations = sari-sari excluded) |
| **Payout timing** | Sari-sari can choose **weekly batch** or **same-day immediate** payout (R18 provides both adapters) |

### Layer 3: Barangay + Red Cross

| Item | Detail |
|------|--------|
| **Delegated authority** | Captain → kagawad (sub-leader) → tanod (security) 3-tier (succession when captain evacuates) |
| **Witness mandatory** | At least 1 PRC volunteer must be present (independent verification of Padrino political bias) |
| **Door-to-door** | PRC + barangay staff visit homes per 4Ps roster (children + elderly households) |
| **Handwritten ledger** | Daily aggregation at barangay hall: household ID + distribution content + photo |
| **After recovery** | Ledger photographed → sent to DSWD → batched into contract |

---

## 4. Data flow (typhoon scenario)

### 4.1 Peacetime (typhoon season starts in May)

```
DSWD ──→ paper vouchers distributed to opt-in recipients (15% target)
                Monthly distribution, photo ID + signed voucher
sari-sari + Mercury Drug opt-in confirmation
Barangay hall delegated-authority training + PRC coordination confirmation
```

### 4.2 Typhoon approaching (PAGASA Cat 3+ alert)

```
PAGASA ──→ NDRRMC ──→ Code Red declare (target LGU)
                          ↓
            SMS gateway (¥50K/month) reception
                          ↓
        services/ndrrmc_alert.py notifies PBM contract
                          ↓
            DL mode activates: vouchers immediately valid + sari-sari can accept DL
```

### 4.3 During disaster (0–7 days)

```
Recipient ──→ sari-sari (if walkable)
                Show voucher + photo ID match
                Owner records in lista book (household ID + items + amount)
                Same-day or weekly batch payout to sari-sari in PHPC

Recipient ──→ barangay hall (PRC witnessing)
                Show voucher → record in handwritten ledger
                On-site supplies distribution (DSWD reserves)

PRC + barangay ──→ door-to-door (households unable to walk)
                     Receive voucher + photo + distribute supplies
                     Record in ledger
```

### 4.4 After recovery (8–30 days)

```
Barangay ──→ photograph ledger → DSWD ──→ contract batch
sari-sari ──→ photograph lista book → DSWD ──→ contract batch
All redemptions consolidated to consumed mapping → integrity check → JPYC payout
```

### 4.5 Yolanda-class (Cat 5+) exception

```
Cat 5+ → sari-sari themselves evacuate / collapse
→ DL Protocol unable to function
→ NDRRMC direct distribution phase activates
→ DSWD + AFP (national army) + PRC distribute supplies directly
→ After recovery, PBM monthly cap "carried over as unused" to next month (recipient suffers no loss)
```

---

## 5. CP-1..CP-7 alignment

| CP | v2 PH enforcement |
|----|-------------------|
| CP-1 | governor.revokeProgram() (same as normal ops) |
| CP-2 | 4Ps roster + barangay approval + photo ID (human + paper double-check) |
| CP-3 | PHPC peg ops (BSP supervision) |
| CP-4 | HMAC household ID, raw PSN absent |
| CP-5 | **5% operational tolerance + post-recovery audit** (#17 PH-6, honestly stated) |
| CP-6 | **The core of this v2** |
| CP-7 | Monthly cap (PHP 1,400/household/month) |

---

## 6. 11 adoption items → implementation map

| #16/#17 ID | Content | This doc section |
|-----------|---------|------------------|
| PH-1 ✏️ | 3-layer DL Protocol | §2 architecture |
| PH-2 ✏️ | lista_adapter (opt-in + disaster-only) | §3 Layer 2 |
| PH-3 ✅ | barangay_endpoint (3-tier delegation) | §3 Layer 3 |
| PH-4 ✏️ | NDRRMC SMS + PRC API reception | §4.2 |
| PH-5 ✅ | Paper voucher opt-in + typhoon season | §3 Layer 1 |
| PH-6 ✅ | CP-5 5% operational tolerance | §5 CP-5 |
| PH-7 ✏️ | Household-unit voucher | §3 Layer 1 (household ID + primary recipient photo + member count) |
| PH-8 ✅ | DSWD MC + BSP NoL document | Separate handoff-packages/dswd/ |
| PH-9 🆕 | Barangay 3-tier + mandatory PRC witness | §3 Layer 3 |
| PH-10 🆕 | Immediate vs weekly batch dual-support | §3 Layer 2 (both adapters) |
| PH-11 🆕 | Name "DL Protocol" | This doc throughout |
| PH-12 🆕 | Yolanda class out of scope | §4.5 |

---

## 7. Annual cost estimate

| Item | Cost |
|------|------|
| Paper voucher print + laminate (15% opt-in × 6 months) | PHP 32M (~¥80M) |
| SMS gateway (NDRRMC alert reception) | PHP 0.6M (~¥1.5M) |
| PRC operational agreement + training | PHP 5M (~¥12M) |
| Barangay 3-tier delegation training | PHP 3M (~¥7M) |
| Sari-sari photo ID equipment (opt-in 5K stores) | PHP 5M (~¥12M) |
| **Total** | **PHP 45M/year (~¥112M/year)** |

JICA application's 24-month PHP 90M roughly fits the scale of national DL Protocol deployment for 4Ps.

---

## 8. Implementation roadmap

| Phase | Content | Status |
|-------|---------|--------|
| **R18** (this round) | Design doc (this file) + 4 services mock + tests | ✅ in progress |
| R19 | Citizen.household_id schema + 4Ps multi-locale loader extension | next |
| R20 | NDRRMC SMS gateway real connection (real gateway contract needed) | pending external |
| R21 | Coins.ph PHPC sandbox connection | pending external |
| R22+ | Quezon City 1-barangay 5-household pilot | pending all-party agreement |

---

## 9. Comparison with JP v2

| Aspect | JP v2 (A+E hybrid) | PH v2 (DL Protocol) |
|--------|---------------------|---------------------|
| Trust anchor | Hardware (Felica SE) | Community + paper + post-recovery reconcile |
| Authentication strength | Mechanically strict | 5% operational tolerance + audit |
| Deployment cost | High (¥7-10B 5-year plan) | Low (¥112M/year) |
| Disaster-time ops | Nationally uniform | Barangay + PRC hybrid |
| Expected disaster frequency | Once every 30 years → heavy armament OK | 20+/year → light deployment essential |
| Yolanda-class exception | National framework handles | Switches to NDRRMC direct distribution |

→ Same problem ─ different contexts ─ different solutions. Two designs each optimized for its own society, **honestly presented without "world first" claims**.
