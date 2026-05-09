# Strategy Meeting #13 — Manila Phase 1 completion + Submission packages (Round 14)

> **Created**: 2026-05-09 (round 14)
> **Topic**: Round 13 finished the "core" of the Manila spec. Round 14 makes Manila **runnable** (POS SDK + seed loader) and **shippable** (submission zip + video scripts).
> **Output**: 5 items adopted + 1 strategy doc translated.
> **Translated**: 2026-05-09 (round 15)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round13.md`](./strategy-2026-05-round13.md)

---

## 0. Round 13 (PR #14 draft) gaps

| Item | Status |
|------|--------|
| ✅ PH seed (`seed/ph/*.json`) | Done |
| ✅ PhilSys OAuth Mock | Done |
| ✅ EMV QR Ph parser | Done |
| ✅ JICA application v1 | Done |
| ❌ **PH seed not actually loaded into the DB** (loader read JP only) | Round 14 |
| ❌ **PH POS SDK** (GCash QR Ph integration anticipated) | Round 14 |
| ❌ Whitepaper §6 referred only to JP | Round 14 |
| ❌ Submission zips for JICA / Coins.ph / DSWD | Round 14 |
| ❌ Round 12 strategy meeting translation (i18n still 11/12) | Round 14 |

→ Round 14 brings Manila Phase 1 to a runnable + shippable state.

## 1. Adopted (5 items)

| # | Agent | Proposal | Implementation | Impact |
|---|-------|----------|----------------|--------|
| **T1** | Engineer | multi-locale seed loader | `seed/loader.py` + `--locale jp\|ph` | PH 8 households + 25 products + 8 stores + 2 programs loadable into DB |
| **T2** | Stablecoin Architect | PH POS SDK + GCash QR Ph integration | `sdk/python/jpn_pbm_pos_ph/` (~200 lines) + tests | Sari-sari / Mercury Drug merchant onboarding ready |
| **T3** | Researcher | Round 12 strategy meeting translation | `docs/strategy-2026-05-round12-en.md` | i18n full coverage (12/12) |
| **T4** | Researcher | Manila section in whitepaper §6 | `docs/whitepaper-2026.md` | Consistency for JICA/MAS/BIS submission |
| **T5** | Engineer | Submission zip package builder | `scripts/build_handoff_package.sh` + `docs/handoff-packages/{jica,coins-ph,dswd,quezon-city}/` | "Send this" set is ready |

## 2. multi-locale seed loader design

`backend/migrations/__init__.py` (existing seed loader) reads `seed/*.json` directly.
This was extended to also read `seed/<locale>/*.json`.

```python
def load_seed(db, *, locale: str = "jp") -> dict:
    """Load seed/{locale}/*.json (existing jp keeps top-level paths) into DB.

    locale='jp' uses existing paths (seed/citizens.json), unchanged for compat.
    locale='ph' uses new paths (seed/ph/citizens.json).
    """
```

**Compatibility**: `locale='jp'` is default = existing behavior. `/seed/load` API unchanged.
`/seed/load?locale=ph` triggers PH load.

CP-1 (emergency stop) compatibility: existing `dropAndReseed` logic preserved, locale mixing forbidden.

## 3. PH POS SDK design

Same shape as JP `sdk/python/jpn_pbm_pos/` (created in R3):

```
sdk/python/jpn_pbm_pos_ph/
├── __init__.py       # public API: PosClient class
├── client.py         # HTTPS client to /api/*
├── qr_ph.py          # QR Ph payload verify (services/qr_ph reuse)
└── examples/
    └── sari_sari_simulation.py  # 4Ps redemption simulation
```

Main APIs:
- `client.scan_merchant_qr(payload)` → MerchantInfo
- `client.scan_product_barcode(jan)` → ProductInfo
- `client.estimate_cart(items, store)` → CartEstimate (subsidy included)
- `client.pay(cart_id, payment_method='gcash_qrph')` → PaymentResult

GCash integration is **mock**. Real GCash sandbox API after Coins.ph contact in Round 15+.

## 4. Submission zip packages

Each recipient needs different documents, so each has its own dir:

```
docs/handoff-packages/
├── jica/
│   ├── README.md  ← cover for recipient
│   ├── 01-application.md  → docs/jica-application-draft-en.md
│   ├── 02-whitepaper.md   → docs/whitepaper-2026.md
│   ├── 03-pitch.md        → docs/pitch-deck.md (English)
│   ├── 04-audit.md        → auto-generated audit report
│   ├── 05-license.md      → LICENSE
│   └── 06-fork-guide.md   → docs/fork-guide.md
├── coins-ph/
│   ├── README.md
│   ├── 01-letter.md       ← short technical paper
│   ├── 02-architecture.md → docs/architecture.md
│   ├── 03-cp6.md          → docs/cp6-offline-fallback.md
│   └── 04-qr-ph-spec.md   ← QR Ph compatible implementation proof
├── dswd/
│   ├── README.md
│   ├── 01-cover-letter-tagalog.md  ← Tagalog/English guide
│   ├── 02-4ps-pilot-spec.md        ← prog-4ps-2026 spec excerpt
│   └── 03-data-privacy.md          ← Data Privacy Act 2012 alignment
└── quezon-city/
    ├── README.md
    ├── 01-cover-letter.md
    ├── 02-pilot-spec-quezon.md
    └── 03-merchant-onboarding.md   ← sari-sari onboarding playbook
```

`scripts/build_handoff_package.sh <target>` generates the zip:
```
$ bash scripts/build_handoff_package.sh jica
→ /tmp/jpn-pbm-handoff-jica-2026-05-09.zip (application + whitepaper + audit + ...)
```

## 5. Verification target

```
$ bash scripts/verify.sh all
[verify:pytest] 200+ passed (R13 195 → R14 +tbd)
✓ verify(all) all green

$ bash scripts/build_handoff_package.sh jica
→ jpn-pbm-handoff-jica-*.zip (6 documents)

$ # POST /seed/load?locale=ph injects PH 8 households + 25 products + 2 programs
```

## 6. Point Reconciliation (Round 13 = PR #14)

| Agent | Detail | Total |
|-------|--------|-------|
| **Engineer** | T2 PhilSys OAuth + T3 EMV QR Ph parser + roadmap update | **+30** |
| Researcher | T1 PH seed + T4 JICA application + T5 R11 translation | +30 |
| Stablecoin Architect | T2 design review (symmetry with myna_oauth) | +15 |
| Cost Guardian | JICA budget ¥65M breakdown refinement | +10 |
| Red Team | CRC-16 tampering test addition request | +10 |
| Purpose Guardian | DPG Standard 9 indicator self-assessment organization | +10 |
| Legal | Data Privacy Act 2012 alignment review | +10 |
| Others | Standby +5 |

🥇 **MVP**: Engineer & Researcher tied (+30) — single round delivered 5 items including the JICA application as an external-facing document.

## 7. Round 15 Candidates (real diplomacy / real device required)

Round 14 is genuinely **the last** for sandbox-only progress. Round 15+ requires:

1. **Polygon Mumbai actual deploy** (RPC URL)
2. **GCash sandbox API** real-mock integration (assumes Coins.ph contact made)
3. **iPhone real-device scanner test** (Web BarcodeDetector iOS 17 verification)
4. **DSWD 4Ps real LandBank ATM flow integration** (policy agreement)
5. **JICA pre-screening conversation** results reflected in v2 application

## 8. Phase Completion Trajectory (R13 → R14 estimated)

| Phase | R13 | R14 (estimated) | Diff rationale |
|-------|-----|-----------------|----------------|
| Phase 1 | 86% | 86% | Unchanged |
| Phase 2 | 71% | 71% | Unchanged |
| Phase 3 | 40% | **40-60%** | Submission package ready raises external readiness |

M+18 (whitepaper) status unchanged (real diplomacy still zero, so still "ready"),
but evidence_files appended with Manila section.
