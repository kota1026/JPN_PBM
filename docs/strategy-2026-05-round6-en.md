# Strategy Meeting #6 — Phase 2 Defense Layer + Bridge to Phase 3

> **Created**: 2026-05-02 / **Format**: 11-Agent Strategic Decision Protocol v1.0
> **Topic**: Sol-compatible ECDSA was completed in Round 6. Before moving to Phase 3 (Polygon production), solidify key management, contract equivalence, and migration design
> **Output**: 5 functional implementations + harness expansion + Strategy Meeting #2 English translation
> **Translated**: 2026-05-02 (round 9)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round6.md`](./strategy-2026-05-round6.md)

---

## 1. Adopted (5 items)

| # | Proposal | Implementation | Impact |
|---|----------|----------------|--------|
| **A** | ECDSA key rotation path | `services/key_management.py` + `/treasury/keys/rotation` | env multi-key + active toggle + verify against all keys → revoke by env removal |
| **B** | Sol contract Python simulator | `services/sol_simulator.py` + `cross_check_with_offchain` | Test contract behavior fully before Polygon production deploy |
| **C** | PostgreSQL-compatible migrations | `migrations/__init__.py` + `/treasury/migrations/status` | Alembic-style (numbered + idempotent + dialect dispatch) for SQLite/PostgreSQL |
| **D** | E2E expansion | `e2e/tests/flagship-flow.spec.ts` 3 added | OAuth radio + multi-year view + keys/migrations audit endpoints |
| **E** | Strategy Meeting #2 translation | `docs/strategy-2026-05-round2-en.md` | MAS forum sharing (2nd of 5) |

## 2. ECDSA Key Rotation Design

```
ENV (Phase 2 migration example):
  JPN_PBM_GOVERNOR_PRIVKEYS=key_2027,key_2026,key_2025  # newest first
  JPN_PBM_GOVERNOR_ACTIVE_IDX=0                          # newest is active
  JPN_PBM_KEY_GRACE_DAYS=90

  - sign with active / verify by trying all keys → old-key signatures pass during grace
  - remove old key from env → instant revoke
```

`verify_against_any_governor` tries all registered keys, so 2-3 generations max in production.

## 3. Sol Simulator vs Real Contract

| Aspect | Sol (`redeemBatch`) | Python simulator | Equivalent |
|--------|---------------------|-------------------|------------|
| Single failure → revert all | Solidity revert | `SolRevert` raise | ✅ |
| nonce | `consumed[pid][month]` mapping | dict[(pid, month)] | ✅ |
| approved store | `approvedStores[msg.sender]` | set | ✅ |
| signature verify | `ecrecover == governor` | `verify_coupon_eip191` | ✅ keccak256 compat |
| grace | `expires_at + 30 days` | `GRACE_DAYS_SEC` | ✅ |
| payout | `jpyc.transfer(store, amount)` | `store_balances[s] += amount` | ✅ |

## 4. Verification

```
$ bash scripts/verify.sh all
[verify:pytest] 123 passed in 4.62s ✓
[verify:seed]   ✓ / [verify:sol]    ✓ / [verify:front]  ✓
✓ verify(all) all green
```

100 → 123 tests pass (+23):
- key_rotation: 8 cases
- sol_simulator: 9 cases
- migrations: 6 cases

## 5. Point Reconciliation (Round 6)

| Agent | Detail | Total |
|-------|--------|-------|
| **Stablecoin Architect** | **Full A + B (Sol simulator) design** | **+30** |
| Engineer | C migrations + D E2E expansion | +20 |
| Researcher | E Strategy Meeting #2 translation | +15 |
| Cost Guardian | C migrations idempotency check | +10 |
| Red Team | A rotation risk scenario picking | +10 |
| Purpose Guardian | A old-key reject design check | +10 |
| CTO | B simulator Ethereum ABI compat check | +10 |
| Others | Pending | +5 each |

🥇 **MVP**: Stablecoin Architect (+30) — solved Phase 3 production deploy compatibility risk in two stages (A key rotation + B simulator).
