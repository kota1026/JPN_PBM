# CP-6 v2 (Japan) — MyNumber Felica SE + Shelter Terminal Hybrid

> **Created**: 2026-05-09 (Round 18) / **Replaces**: [`cp6-offline-fallback.md`](./cp6-offline-fallback.md) (v1)
> **Reference**: Strategy Meetings #16 + #17 ([`strategy-2026-05-round17.md`](./strategy-2026-05-round17.md))
>
> 🇯🇵 Japanese original: [`cp6-offline-fallback-v2-jp.md`](./cp6-offline-fallback-v2-jp.md)

---

## 1. What v1 got wrong

| v1 assumption | Reality (Tokyo Inland Earthquake scenario) |
|---------------|--------------------------------------------|
| Retailer POS continues operating | Power loss disables POS for 0–7 days |
| Shop staff present | Staff also evacuated |
| Paper receipt rolls available | Supply chain disrupted |

→ **POS doesn't survive the middle of a disaster**. POS-dependent design is broken.

---

## 2. v2 design principle

> Restart from: **"With zero power and zero connectivity, what authentication system prevents impersonation and double-spending?"**

Three layers:

```
[Layer A] Personal device: MyNumber card (Felica SE)
              ─ tamper-resistant + monotonic counter
              ─ pre-stage "this month's offline allowance"
              ─ recipient always carries

[Layer E] Government endpoint: tablet at evacuation centers
              ─ generator + Starlink mini for satellite uplink
              ─ NFC reader (talks to SE)
              ─ operated by civil servants

[Layer paper] Secondary fallback: paper QR (CP-6a)
              ─ for SE-cardless / SE-broken / unreachable households
              ─ ECDSA-signed printed paper
              ─ shelter staff transcribes to handwritten ledger
```

---

## 3. Layer details

### Layer A: MyNumber card Felica SE

**Premise**: Already distributed to all citizens (90%+ penetration), no new hardware deployment.

| Item | Detail |
|------|--------|
| Hardware | MyNumber card's Felica chip (RC-S960, SE embedded) |
| Peacetime prefund | Monthly write of "this month's offline allowance" to SE (e.g., ¥10,000) |
| Disaster-time | NFC reader (shelter terminal) communicates, SE counter manages remaining |
| Double-spend prevention | SE-internal monotonic counter (tamper-resistant) |
| Power | Card itself needs none (only the reader) |
| Backup | If card is lost, the paper layer (CP-6a) covers |

**Implementation key**: Existing MyNumber Portal v2 OAuth flow needs to add a **"SE prefund write permission"**. This is a JPKI Public Key Infrastructure API extension.

### Layer E: Shelter terminal

**Deployment plan**: 15,000 designated evacuation centers + ~5,000 LGU offices = **~20,000 units nationwide**

| Item | Detail |
|------|--------|
| Hardware | iPad Pro–class tablet + NFC reader + satellite (Starlink mini) + generator (5kVA) |
| Per-unit cost | ~¥250,000 (hardware) + ~¥100,000 (generator) = ¥350,000 |
| National total | ~¥7B (lump sum) or ¥1.4B × 5 years |
| Operator | LGU staff (extension of evacuation-center management) |
| Peacetime use | **Shared with** national health-insurance / certificate-issuance terminals to maintain utilization |

**Critical**: This investment is NOT CP-6-specific. It is justified through **shared use with national health-insurance and certificate-issuance windows**, making it fundable at the LGU budget level.

### Layer paper (CP-6a): Secondary fallback

**Use cases**:
- MyNumber card lost / damaged
- Shelter unreachable, where door-to-door teams (welfare officer + DMAT) deliver in the field
- Battery-dead SE that can't be read

**Spec**:
- ECDSA-signed printed paper QR (laminated for water resistance)
- Monthly distribution (opt-in)
- Shelter / welfare officer transcribes to handwritten ledger → digital ingest after recovery

---

## 4. Data flow (during disaster)

### 4.1 Peacetime prefund (start of month)

```
DSWD/TMG ──→ JPKI API ──→ resident MyNumber card SE
                          monthly offline allowance ¥10,000 written
                          counter = 0 reset
```

### 4.2 Disaster strikes → distribution

```
Citizen (with MyNumber card) ──→ shelter terminal
                                   NFC reads SE
                                   counter ≤ monthly cap?
                                   [✓] supplies dispensed
                                   [✓] SE counter updated
                                   [✓] redemption recorded in terminal local DB
                                   [✓] sent to contract via satellite (immediate or batch)
```

### 4.3 Door-to-door (elderly / infants / mobility-impaired)

```
Welfare officer + DMAT ──→ visited household
                              receives paper QR + face confirmation
                              records in handwritten ledger
                              (scanned + ingested to contract batch after recovery)
```

---

## 5. CP-1..CP-7 alignment

| CP | v2 enforcement |
|----|----------------|
| CP-1 (emergency stop) | Same as normal ops. governor.revokeProgram() |
| CP-2 (eligibility) | Pre-funding to SE + monthly cap = approval evidence |
| CP-3 (peg) | Normal JPYC operations |
| CP-4 (privacy) | SE contains only HMAC PID; raw MyNumber not present |
| CP-5 (no double-spend) | **SE counter (mechanically strict) + on-chain consumed (defense in depth)** |
| CP-6 (disaster) | **The core of this v2** |
| CP-7 (cap) | Monthly cap = SE limit |

---

## 6. Implementation roadmap

| Phase | Content | Status |
|-------|---------|--------|
| **R18** (this round) | `services/se_card_adapter.py` mock + design doc (this file) | ✅ in progress |
| **R19** | Citizen.household_id schema (shared with PH) | next |
| **R20** | JPKI API spec investigation + real SE prefund prototype | pending external |
| **R21+** | Shelter terminal 1-unit field test (Starlink mini + NFC reader) | pending hardware + budget |
| **R25+** | National 20K-unit deployment (5-year plan) | policy decision + budget |

---

## 7. International comparison

| Country | Approach |
|---------|----------|
| **Japan (this proposal)** | A + E hybrid (Felica SE + shelter terminal) |
| Singapore (Project Orchid) | Fully online assumed; no disaster-offline spec |
| EU (Digital Euro pilot) | C (time-limited offline credit) on smartphone |
| BoJ Phase 2 Pilot | A (SE-embedded) extended to general payments |
| Indonesia (BPNT) | IC card + e-warong (the prototype this builds on) |

→ **A + E hybrid is uniquely suited to Japan**, which already has both MyNumber Felica and a national evacuation-center infrastructure. A Japan-specific competitive advantage.

---

## 8. Remaining issues (Round 19+)

1. **JPKI API SE prefund write permission**: Currently JPKI is for personal authentication only; writing is out of scope. Discussion with the Ministry of Internal Affairs and Communications required.
2. **Shelter terminal shared-use institutional design**: National health-insurance / certificate-issuance integration rules
3. **Communication redundancy including Starlink mini**: Always-on satellite cost / licensing
4. **5-year deployment budget**: Total ¥7-10B (20K units × ¥350-500K)
5. **Alternatives for citizens without MyNumber cards** (mostly elderly, ~10%): Paper QR + door-to-door standardization

These are policy / procurement matters. Technical design is complete in this v2.
