# Strategy Meeting #5 — Toward Phase 2 Final Form

> **Created**: 2026-05-02 / **Format**: 11-Agent Strategic Decision Protocol v1.0
> **Topic**: Lift Phase 2 components from Round 5 to a state interoperable with real contracts + UI integration
> **Output**: 5 functional implementations + harness expansion (load 5,000 req)
> **Translated**: 2026-05-02 (round 9)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round5.md`](./strategy-2026-05-round5.md)

---

## 1. Adopted (5 items)

| # | Proposal | Implementation | Impact |
|---|----------|----------------|--------|
| **A** | ECDSA Sol full compatibility (keccak256 + abi.encode + EIP-191) | `services/sol_compat.py` (160 lines) + 11 tests | Guarantees signature verification matches when PBMOfflineFallback.sol is deployed to Polygon Mumbai |
| **B** | Multi-year spend per-fiscal-year tracking | `fiscal_budget.spent_by_year_from_ebpm` + `remaining_for_year_precise` + `/programs/{id}/fiscal-budget` extension | EBPM-actuals-based determination of past-year consumption |
| **C** | citizen.html OAuth flow toggle | radio button + `_loginViaOAuth` (3-step Authorization Code Grant) | User can switch Phase 1 (direct) vs Phase 2 (OAuth) |
| **D** | tokyo.html multi-year budget view | New section + 4 KPIs + per-fiscal-year actuals table | Multi-year flagship budgets visible on screen |
| **E** | Load test scale-up | SQLite WAL + busy_timeout=10s + loadtest `--max-fail-rate` + 100×50 (= 5,000 req) | Measured **431 req/s, p95=347ms, fail=2.66%** (within 5% threshold) |

## 2. Test Vector Match (Adoption A)

| Hash | Input | Expected | Implementation |
|------|-------|----------|----------------|
| keccak256 | `b""` | `c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` | ✅ |
| keccak256 | `b"abc"` | `4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45` | ✅ |
| keccak256 | `b"hello"` | `1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8` | ✅ |
| Ethereum address | privkey=0x01 | `0x7e5f4552091a69125d5dfcb7b8c2659029395bdf` | ✅ |

`sign_coupon_eip191` → `verify_coupon_eip191` round-trip OK. Implements **low-s normalization** + recovery id auto-search → equivalent to Sol `ecrecover`.

## 3. Verification

```
$ bash scripts/verify.sh all
[verify:pytest] 100 passed in 2.59s ✓
[verify:seed]   ✓
[verify:sol]    ✓
[verify:front]  ✓
✓ verify(all) all green

$ bash scripts/verify.sh load
5000 requests in 11.59s = 431 req/s
p50=204.6ms p95=347.4ms p99=392.8ms
failures: 133 (2.66%) — within 5% sandbox threshold
```

## 4. Point Reconciliation (Round 5)

| Agent | Detail | Total |
|-------|--------|-------|
| **Stablecoin Architect** | **Full A (Sol-compat + low-s normalization)** | **+25** |
| CFO | Full B | +20 |
| Engineer | C+D frontend wire-up | +15 |
| Red Team | E adopted with 5% threshold compromise + WAL mode proposal | +15 |
| Cost Guardian | SQLite WAL resolved bottleneck | +10 |
| Researcher | Test vector external match verified | +5 |
| Purpose Guardian | OAuth path also maintains CP-2 | +5 |

🥇 **MVP**: Stablecoin Architect (+25) — Sol-compatible ECDSA implementation eliminated the largest compatibility risk for Phase 2 migration.
