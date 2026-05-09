# LandBank ATM Bridge Specification (Round 15 — sandbox spec)

> **Status**: Sandbox specification. Real DSWD-LandBank API not yet accessed.
> **Implementation**: [`backend/app/services/landbank_bridge.py`](../backend/app/services/landbank_bridge.py) (mock + protocol stubs).

---

## 1. Why this exists

Philippine 4Ps disbursement currently flows:

```
DSWD → LandBank Cash Card (per household) → ATM withdrawal → cash → sari-sari purchase
```

JPN-PBM cannot replace LandBank in one step. It must **co-exist** during pilot:

```
DSWD ┬→ LandBank Cash Card (existing, ~50% of allowance)
     └→ PBM PHPC wallet (new, ~50% of allowance)
                     ↓
        Eligible-purchase only at approved sari-sari/Mercury Drug
```

The Bridge module enforces:
- (CP-5) **No double disbursement** — if a household is in `pbm_only` mode for month M, no LandBank withdrawal for month M is allowed (and vice versa).
- (CP-6) **Disaster grace** — offline coupon redemptions reconcile after recovery, exceeding caps allowed but logged.
- **Audit trail** — every disbursement-mode change, withdrawal, and redemption is recorded in `bridge_audit_log` for DSWD inspection.

## 2. Modes

| Mode | Description | Use case |
|------|-------------|----------|
| `landbank_only` | All allowance via LandBank cash card | Default for non-pilot households |
| `pbm_only` | All allowance via PBM PHPC | Full pilot participants |
| `split` | Configurable split between LandBank and PBM | Half-pilot for risk mitigation |

Switching modes is allowed only at month boundary (M-1 → M). DSWD field officer signs the change.

## 3. Sequence diagrams

### 3.1 Normal monthly flow (pbm_only)

```
DSWD                  Bridge                     Backend / Chain
 │                      │                              │
 │ set_disbursement_mode│                              │
 │ (psn, M=202608,      │                              │
 │  mode=pbm_only,      │                              │
 │  pbm_amount=140k)    │                              │
 │─────────────────────►│                              │
 │                      │ audit_log: set_mode          │
 │                      │ (state initialized)          │
 │                                                     │
 │                      │              user redeems    │
 │                      │              at sari-sari    │
 │                      │              (PBM contract)  │
 │                      │◄─────────────────────────────│
 │                      │ record_pbm_redemption(...)   │
 │                      │ ✓ within cap → updated state │
```

### 3.2 CP-5 protection (rejected double disbursement)

```
Bridge                                    Citizen
 │ state for (psn, M=202608) = pbm_only    │
 │                                         │
 │                       (someone tries)   │
 │                       ATM withdrawal    │
 │◄────────────────────────────────────────│
 │                                         │
 │ raise ValueError(                       │
 │   "household in pbm_only mode;          │
 │    LandBank withdrawal would be CP-5    │
 │    violation (double-disbursement)")    │
 │                                         │
```

### 3.3 CP-6 disaster grace

```
Citizen                  POS (offline)         Bridge          DSWD
 │  show offline QR        │                     │                │
 │────────────────────────►│ verify sig +        │                │
 │                         │ local nonce check   │                │
 │  receive goods +        │                     │                │
 │  paper receipt          │                     │                │
 │◄────────────────────────│                     │                │
 │                         │                                       
 │                         │ ── Network restored ──                
 │                         │                                       
 │                         │ batch submit                          
 │                         │ to PBM contract                       
 │                         │ (auto-reconcile)                      
 │                                                                 
 │                         At month end:                            
 │                         ──────────────────►│                    
 │                         reconcile_offline_redemptions          
 │                         (psn, M, offline_total)                
 │                                            │ may exceed cap     
 │                                            │ → logged as        
 │                                            │ "offline_overage"  
 │                                            │                    
 │                                            │ DSWD reviews       
 │                                            │ overages ──────────►
```

## 4. API (Python interface)

```python
class LandBankBridge(Protocol):
    def get_household_state(self, *, psn_pid: str, month_index: int)
        -> HouseholdState | None: ...

    def set_disbursement_mode(self, *, psn_pid: str, month_index: int,
                              mode: DisbursementMode,
                              landbank_amount_centavos: int = 0,
                              pbm_amount_centavos: int = 0)
        -> HouseholdState: ...

    def record_landbank_withdrawal(self, *, psn_pid: str, month_index: int,
                                    amount_centavos: int)
        -> HouseholdState: ...

    def record_pbm_redemption(self, *, psn_pid: str, month_index: int,
                               amount_centavos: int)
        -> HouseholdState: ...

    def reconcile_offline_redemptions(self, *, psn_pid: str, month_index: int,
                                       offline_total_centavos: int)
        -> HouseholdState: ...

    def audit_log(self) -> list[BridgeAuditEntry]: ...
```

## 5. Real (DSWD-proxy) backend, Round 16+

DSWD will provide a **proxy API** in front of LandBank. We do not call LandBank
directly because:

1. LandBank API specs are not publicly documented.
2. DSWD legally controls the disbursement schedule.
3. A proxy lets DSWD throttle / kill-switch the integration without touching our code.

Planned proxy endpoints:

| Verb | Path | Purpose |
|------|------|---------|
| GET | `/dswd/proxy/landbank/state?psn=...&month=...` | Read state |
| POST | `/dswd/proxy/landbank/mode` | Set mode (DSWD-signed) |
| GET | `/dswd/proxy/landbank/withdraw-events?psn=...&month=...` | Webhook-poll equivalent |

Authentication: DSWD HMAC + IP allowlist.

## 6. Privacy considerations

- All operations key on **HMAC PSN**, not raw PSN — bridge never sees raw IDs.
- Audit log entries contain HMAC PSN; truncation to 8 chars in display surfaces.
- Cross-LGU operation requires per-LGU bridge instance (no global shared state).

## 7. Test coverage in this round

| Test | Description |
|------|-------------|
| `test_set_mode_*` | mode setter constraints |
| `test_landbank_withdrawal_rejected_in_pbm_only_mode` | CP-5 enforcement |
| `test_pbm_redemption_rejected_in_landbank_only_mode` | CP-5 enforcement |
| `test_split_mode_allows_both_within_limits` | split mode happy path |
| `test_landbank_cap_exceeded_rejected` | cap enforcement |
| `test_offline_reconcile_within_cap` | normal CP-6 reconciliation |
| `test_offline_reconcile_exceeds_cap_logged_but_allowed` | CP-6 grace |
| `test_audit_log_records_each_operation` | audit completeness |

22 tests in [`backend/tests/test_landbank_bridge.py`](../backend/tests/test_landbank_bridge.py), all passing.

## 8. What's NOT covered (Round 16+)

- Actual LandBank API integration (waiting for DSWD proxy spec)
- Cross-month carryover (allowance roll-over across months)
- Multi-LGU sharing / non-NCR pilots
- Reconciliation of a household that **switches mode mid-month** (currently rejected by setter)
