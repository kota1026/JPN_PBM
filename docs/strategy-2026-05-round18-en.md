# Strategy Meeting #18 — Round 19 ─ Completing remaining sandbox-doable items

> **Created**: 2026-05-09 (round 19)
> **Topic**: Complete the 5 items deferred from Round 18 that are sandbox-doable
> **Format**: Short session (skipping the long council since #16/#17 ran consecutively)
> **Output**: 5 adoptions (the externally-independent items among R18 deferred)
> **Translated**: 2026-05-09 (round 20)
>
> 🇯🇵 Japanese original: [`strategy-2026-05-round18.md`](./strategy-2026-05-round18.md)

---

## 0. Round 18 backlog inventory

Of the 6 items R18 marked "deferred to R19+", sandbox-doable are:

| # | Item | Sandbox? | Reason |
|---|------|---------|--------|
| 1 | Citizen.household_id schema (PH-7 full impl) | ✅ | Internal schema change only |
| 2 | NDRRMC SMS gateway real connection | ❌ | Gateway contract needed |
| 3 | Coins.ph PHPC sandbox connection | ❌ | Coins.ph compliance 6 months |
| 4 | GCash offline balance | ❌ | Coins.ph development 12-18 months |
| 5 | Felica SE real device | ❌ | JPKI API + MyNumber reader needed |
| 6 | Shelter terminal field test | ❌ | Starlink + NFC + generator needed |

→ **Only #1 is implementable**. Plus i18n / docs updates.

## 1. Adopted (5 items)

| # | Proposal | Owner | Impact |
|---|----------|-------|--------|
| **T1** | `Citizen.household_id` schema + full household-unit voucher impl | Engineer | PH-7 closed, JP can also use |
| **T2** | `seed/ph/citizens.json` revision + household links (8 recipients → 5 households) | Engineer + Researcher | Household-unit demo enabled |
| **T3** | CP-6 v2 docs translation (jp + ph) | Researcher | International forum sharing preparation |
| **T4** | R17 strategy meeting translation (R18 minutes, CP-6 v2 council record) | Researcher | i18n lag + international expansion |
| **T5** | JICA application v1.2 revision (CP-6 v2 reflection + Round 18 adoptions + R17 council) | Researcher | Real diplomacy prep |

## 2. T1 (household schema) design

### 2.1 Model change

```python
# backend/app/models/citizen.py
class Citizen(Base):
    pid: ... (existing)
    name: ...
    address: ...
    ward: ...
    dob: ...
    gender: ...
    # 🆕 R19 (#17 PH-7 adoption)
    household_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # household_id = HMAC(primary recipient's PSN/My Number)
    # Same household members share the same household_id
    # JP can keep individual-unit if household_id = pid (1 person 1 household) for backward compat
```

### 2.2 Auto migration

```python
# backend/app/db.py:_PENDING_COLUMNS
("citizens", "household_id", "VARCHAR(64)", "NULL"),
```

### 2.3 Service layer

New `services/household.py`:
- `get_household_members(household_id)` ─ list members of the same household
- `household_aggregate_eligibility(household_id, program)` ─ household-unit eligibility
- `is_household_voucher(voucher)` ─ determine if voucher is household-unit or individual

`lista_adapter` / `barangay_endpoint` already accept **household_id as string argument**, so no code change ─ the caller side (R20+) just passes the right id.

### 2.4 PH seed revision

```json
// 8 recipients → 5 households grouping
{
  "psn": "PH-0001", "household_id": "HH-001-santos", ...
  "psn": "PH-0001-A", "household_id": "HH-001-santos", ... (child 1)
  "psn": "PH-0001-B", "household_id": "HH-001-santos", ... (child 2)
  "psn": "PH-0002", "household_id": "HH-002-reyes", ...
  ...
}
```

JP side (`seed/citizens.json`) is **unchanged for backward compatibility** (household_id unset = individual-unit treatment).

## 3. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 305+ passed (R18 297 → R19 +tbd)
[verify:i18n]   16/17 (round18 latest lag = 1, tolerable)
✓ verify(all) all green
```

## 4. Point Reconciliation (Round 18 = PR #19)

| Agent | Detail | Points |
|-------|--------|--------|
| **Engineer** | 4 mock services impl + demo.html Scene 7-9 revision + all 297 tests green | **+25** |
| **Field Officer Pia + Aling Maria + Roberto + Carmela (new persona collective)** | #16 #17 overturned 4 PH assumptions through field perspective | **+30** |
| Researcher | CP-6 v2 docs 2 + whitepaper §4 revision + strategy meeting minutes | +20 |
| Red Team | v1 "world first" withdrawal proposal + 4 modifications integration | +15 |
| Purpose Guardian | CP-5 honest 5% tolerance documentation | +10 |
| Cost Guardian | PH paper voucher cost estimate rejecting all-distribution case | +10 |

🥇 **R18 MVP**: **New Persona Collective (+30)** ─ Field Officer + Aling Maria + Roberto + Carmela. **Transforming "deskbound council" to "field council"** is R18's core achievement.

## 5. Round 20+ candidates (real diplomacy required)

After R19 completion, only **minor improvements remain in sandbox**:

| Candidate | Required external resource |
|-----------|---------------------------|
| Polygon Mumbai real deployment | RPC URL (Alchemy/Infura) |
| GCash sandbox API integration | Coins.ph contact (post-LoI) |
| iPhone real-device scanner verification | iPhone 13/15 device |
| DSWD 4Ps LandBank integration | DSWD policy agreement |
| JICA pre-screening v3 | JICA conversation |
| NDRRMC SMS gateway real connection | Gateway contract (PHP 50K/mo) |
| Felica SE real device (MyNumber + JPKI) | JPKI API extension (MIC negotiation) |

## 6. Phase completion (R18 → R19 estimated)

| Phase | R18 | R19 (forecast) | Diff |
|-------|-----|----------------|------|
| Phase 1 | 86% | 86% | M+0 still pending |
| Phase 2 | 75% | **77%** (+2pt) | M+11 evidence reinforced (household-unit support) |
| Phase 3 | 48% | **52%** (+4pt) | M+18 international expansion prep (CP-6 v2 EN + JICA v1.2) |

R19's value is **"zero remaining work when external unlocks"**, not numerical progress.
