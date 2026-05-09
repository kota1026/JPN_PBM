# Strategy Meeting #15 — Video recording packet (Round 16)

> **Created**: 2026-05-09 (round 16)
> **Topic**: After Round 15 completed "responsiveness when external is unlocked", Round 16 prepares **video material** that can be deployed simultaneously to JICA / TMG / DSWD / Quezon City / international forums.
> **Output**: 6 items adopted (4 video scripts + recording guide + 1 strategy doc translation)
> **Translated**: 2026-05-09 (round 18)

> 🇯🇵 Original Japanese: [`docs/strategy-2026-05-round15.md`](./strategy-2026-05-round15.md)

---

## 0. Why video in Round 16

In Round 1 we created `docs/video-script.md` (Tokyo 4-min version), but the following 14 rounds added:

- Manila twin pilot (4Ps + sari-sari + GCash + Tagalog UI)
- Hybrid eligibility + smartphone barcode scan
- CP-6 disaster fallback (since revised in v2 as of R18)
- Adapter layer (chain / gcash / landbank)
- JICA application + LoI templates + DPG evidence

These are **not yet captured in video material**. Once real diplomacy starts, "watch this 5-minute video before the 30-minute meeting" becomes a critical workflow, so we prepared 4 audience-targeted video scripts.

## 1. Adopted (6 items)

| # | Agent | Proposal | Implementation |
|---|-------|----------|----------------|
| **T0** | Researcher | Video script index | `docs/video-scripts/README.md` |
| **T1** | Researcher | 5-min pitch JP (politicians/executives) | `docs/video-scripts/01-pitch-5min-jp.md` |
| **T2** | Engineer | 15-min tech deep-dive JP | `docs/video-scripts/02-tech-deep-15min-jp.md` |
| **T3** | Researcher | 90-sec international SNS / OECD teaser EN | `docs/video-scripts/03-international-90sec-en.md` |
| **T4** | Researcher + Field | 5-min Manila pilot bilingual TL/EN | `docs/video-scripts/04-manila-pilot-5min-tl-en.md` |
| **T5** | Engineer | Recording / editing / publishing guide | `docs/video-scripts/05-recording-production-guide.md` |
| **T6** | Researcher | Round 14 strategy meeting translation | `docs/strategy-2026-05-round14-en.md` |

## 2. Subsequent pivot (R16 → R17)

After T0 was completed, the user noted: "実際に収録できないと意味ないね" (without actual recording, this is meaningless). Round 16 was paused at T0; the remaining T1-T5 scripts were not authored. Round 17 instead pivoted to "auto-playing demo page" (`frontend/demo.html`), which became the actual usable artifact.

The R16 video script README is preserved as a future-ready scaffold; if a Loom recording operator becomes available, the demo.html scene structure can be reused as a video script directly.

## 3. Point Reconciliation (Round 15 = PR #16)

| Agent | Detail | Total |
|-------|--------|-------|
| **Stablecoin Architect** | T1 chain + T2 gcash adapter (Mock + Real protocol + factory) | **+30** |
| Engineer | T1/T2/T3 series implementation integration + iOS hardening | +25 |
| Researcher | T5/T6 LoI templates + DPG evidence + R13 translation | +20 |
| Purpose Guardian | T4 LandBank CP-5/CP-6 enforcement design | +15 |
| Red Team | Pointed out silent fallback prohibition | +10 |
| Cost Guardian | gcash adapter idempotency requirement | +10 |
| Legal | LandBank bridge audit log format review | +10 |
| Others | Standby +5 |

🥇 **MVP**: Stablecoin Architect (+30) — first MVP since Round 5/6, implementing 3 adapters under unified protocol.

## 4. Round 17 candidate (post-R16 pivot)

Auto-playing demo page (`frontend/demo.html`) replacing video scripts:
- Self-contained HTML, no recording needed
- 14 scenes × ~5 min, JP/EN/TL toggle
- Pause / rewind / direct-jump
- Better than video for technical audiences (interactive)
