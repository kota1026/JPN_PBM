# Strategy Meeting #14 — The last mile before external dependencies (Round 15)

> **Created**: 2026-05-09 (round 15)
> **Topic**: After Round 14, "core + runnable + shippable" was complete. Round 15 makes sure that the moment real RPC / real GCash / real iPhone / real DSWD integrations land, **a single switch** flips them all into production state — by building adapter layers, mocks, and specs.
> **Output**: 6 items adopted + 1 strategy doc translated.
> **Translated**: 2026-05-09 (round 16)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round14.md`](./strategy-2026-05-round14.md)

---

## 0. Motivation — why "adapter layer" first

Implementations through Round 14 were pure-functional Python + in-process mocks. What happens when we switch to the real thing:

| Domain | Current (R14) | Real-world migration | Risks |
|--------|---------------|----------------------|-------|
| Blockchain | Python `sol_simulator.py` mimics EVM | Polygon Mumbai → web3.py against real RPC | RPC instability, signature differences, out-of-gas |
| GCash payments | Frontend mock UUID | GCash Sandbox API → real HTTPS | Rate limits, error handling |
| iPhone scanner | Verified on desktop Chrome | Real iPhone Safari (iOS 17+) BarcodeDetector or ZXing | iOS BarcodeDetector versions that don't support EAN-13 |
| ID linkage | PhilSys mock OAuth | Real PhilSys API + LandBank ATM card linkage | PSN format conversion, 4Ps roster matching |
| JICA application | v1 English draft | Pre-screening conversation → v2 revision | LoIs not collected / budget rationale insufficient |

**Writing the adapter layer first** = the system is in a state where switching to real backend is a single env var flip.
This means **the day external resources arrive = the day production deployment is possible**.

## 1. Adopted (6 items, implemented in parallel)

| # | Agent | Proposal | Implementation | Impact |
|---|-------|----------|----------------|--------|
| **T1** | Stablecoin Architect | Polygon chain adapter | `backend/app/services/chain_adapter.py` + tests | Zero code change to switch after RPC URL is provided |
| **T2** | Stablecoin Architect | GCash sandbox adapter | `backend/app/services/gcash_adapter.py` + tests | Single env var to flip after Coins.ph contact |
| **T3** | Engineer | iPhone scanner hardening + manual test checklist | `frontend/scanner.js` patch + `docs/scanner-iphone-test-checklist.md` | iOS 16/17 graceful degradation |
| **T4** | Stablecoin Architect | LandBank ATM bridge mock + spec | `backend/app/services/landbank_bridge.py` + `docs/landbank-bridge-spec.md` + tests | Bolt-on to existing 4Ps disbursement flow |
| **T5** | Researcher | JICA application v1.1 (LoI templates + DPG evidence) | `docs/handoff-packages/jica/04-letters-of-intent-templates.md` + `05-dpg-self-assessment-evidence.md` | Ready to display in pre-screening conversation |
| **T6** | Researcher | Round 13 strategy meeting translation | `docs/strategy-2026-05-round13-en.md` | Maintain i18n lag at 1 |

## 2. Adapter design principles

All three adapters (chain / gcash / landbank) follow the same structure:

```python
class XxxBackend(Protocol):
    """Interface. Common to real and mock."""
    def some_op(self, ...) -> ...: ...

class MockXxxBackend:
    """Returns shape-compatible responses even in sandbox."""

class RealXxxBackend:
    """Calls real API/RPC. Starts only if env vars are set."""

def get_backend() -> XxxBackend:
    """env var picks mock or real. Default = mock."""
```

This means:
- Tests always use Mock (CI green doesn't break)
- Production deployment changes a single env var
- Phased rollout (some mock / some real) is also possible

## 3. JICA application v1 → v1.1 improvements

To make JICA pre-screening "ready to pass" immediately:

- **LoI (Letter of Intent) templates**: 5 letters for JPYC / Coins.ph / Tokyo Innovation Base / Quezon City / DSWD. Addressed to actual role-holders, 1 page each, with signature blocks.
- **DPG Standard 9 indicator evidence appendix**: Each indicator points to a specific repository file/commit URL. JICA reviewers can verify "running evidence" with one click.
- **Budget line item rationale**: Each item in the ¥65M / 24-month budget gets its pricing basis (e.g., AWS CloudHSM ¥62,500/month, Quantstamp audit ~¥6M, etc.).

## 4. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 230+ passed (R14 214 → R15 +tbd)
✓ verify(all) all green

$ bash scripts/build_handoff_package.sh jica
→ /tmp/jpn-pbm-handoff-jica-2026-05-09.zip (includes LoI templates + DPG evidence)
```

## 5. Point Reconciliation (Round 14 = PR #15)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | T1 multi-locale loader + T2 PH POS SDK + T5 handoff zip + verify mode | **+30** |
| **Researcher** | T3 R12 translation + T4 whitepaper §6.4 + T5 12 handoff files | **+30** |
| Stablecoin Architect | T2 GCash mock design review | +15 |
| Cost Guardian | handoff package size management | +10 |
| Red Team | DSWD Tagalog cover letter review | +10 |
| Purpose Guardian | audit trail consistency check | +10 |
| Legal | Data Privacy Act document organization | +10 |
| Others | Standby +5 |

🥇 **MVP**: Engineer & Researcher tied (+30). After Engineer ran 4 consecutive MVP rounds (R11–R14), Researcher caught up in Round 14.

## 6. Round 16 candidates (only real-diplomacy domains remain)

What's doable in the sandbox is **truly final** by Round 15. Next:

1. JICA pre-screening conversation → v2 revision
2. Polygon Mumbai testnet real RPC URL acquisition → start `chain_adapter.py:RealChainBackend`
3. Coins.ph contact → GCash sandbox API key → start `gcash_adapter.py:RealGCashBackend`
4. iPhone 13 / 15 real-device scanner verification
5. 4-party MoU agreement with DSWD / Quezon City LGU
6. Whitepaper v1.0 finalization (currently v0.1 draft) and OECD/BIS/MAS sharing

## 7. Phase Completion (R14 → R15 estimated)

| Phase | R14 | R15 (estimated) |
|-------|-----|------------------|
| Phase 1 | 86% | 86% (unchanged, awaiting M+0) |
| Phase 2 | 71% | 71% (M+1 evidence reinforced but status remains ready) |
| Phase 3 | 40% | 40% (zero real diplomacy, so unchanged) |

The effect of Round 15 is in **"responsiveness when external is unlocked"**, not in the **percentage figures**. That is operational quality that doesn't show up in numbers.
