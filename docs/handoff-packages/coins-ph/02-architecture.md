# Architecture: PHPC integration into JPN-PBM (Manila pilot)

## High-level flow

```
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  ① 4Ps recipient (smartphone)│    │  ② Sari-sari merchant        │
│  - PhilSys ID (HMAC PID)     │    │  - QR Ph sticker (no POS)    │
│  - GCash app + 4Ps mini-app  │    │  - Cash drawer                │
│  - PHP balance + PHPC PBM    │    │                              │
└──────────────┬───────────────┘    └──────────────┬───────────────┘
               │                                   │
               │  scan QR Ph (verify MCC, CRC)     │
               │◄─────────────────────────────────►│
               │                                   │
               │  scan product barcode (EAN-13/480)│
               │  ↓ /products/{jan}                │
               │  ↓ estimate eligibility           │
               │                                   │
               │  pay via GCash QR Ph               │
               │  ───────────────────────────────► │
               │       │                           │
               │       ▼                           │
┌──────────────┴──────────┐                        │
│  GCash backend (existing)│                       │
│  ─ self-pay portion      │                       │
│  ─ merchant ack          │                       │
└──────────────────────────┘                       │
                                                   │
        ↓ subsidy portion (PHPC)                   │
                                                   │
┌──────────────────────────────────────────────────┴────┐
│  PBM smart contract on Polygon (PHPC)                 │
│  ─ verify approved store + program eligibility        │
│  ─ unwrap PHPC, transfer to merchant wallet           │
│  ─ emit Spent event for EBPM                          │
└────────────────────────────────────────────────────────┘
```

## Why this architecture

| Concern | Solution |
|---------|----------|
| Sari-sari has no POS | Recipient's smartphone runs the scanner; QR Ph sticker + paper-receipt-fallback |
| Tingi (loose goods) has no barcode | MCC fallback within monthly cap (`cap_no_barcode_centavos`) |
| Liquor / tobacco at "grocery" stores | MCC blacklist (5921 / 5993 / 5813 / 7995) hard-coded in `item_eligibility.py` |
| Typhoon / flood network outage | CP-6 pre-signed offline coupons (30-day validity, ECDSA on `ethSignedDigest`) |
| BSP regulatory anchor | PHPC is BSP-approved; PBM only **wraps** PHPC, no new issuance event |
| Privacy (Data Privacy Act 2012) | HMAC(PSN) pseudonymization; k-anonymity in EBPM exports |

## Coins.ph integration touchpoints

| Touchpoint | Status | What we need |
|-----------|--------|--------------|
| PHPC token contract address | Mainnet (live) | Address for testnet allocation |
| GCash QR Ph generation API | Live | Sandbox API key |
| EMV QR Ph compliance | Spec available (BSP 2019-859) | Joint review of our parser |
| Custodial settlement rails (PHPC ↔ PHP bank deposit) | Live | Same as existing Coins.ph product |
| Merchant onboarding (sari-sari sign-up) | Coins.ph existing channel | Our pilot piggybacks on this |
