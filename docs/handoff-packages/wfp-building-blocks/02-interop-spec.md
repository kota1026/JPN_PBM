# Donor-PBM × Building Blocks Interoperability Protocol (Draft v0.1)

> **Status**: Draft, sandbox spec only. Real protocol must be co-designed with WFP team.

## 1. Architecture

```
[JPN-PBM Donor side]                              [Building Blocks beneficiary side]
                                                   ─ existing $300M+ infra
[donor (KYC tier 0-3)]
   ↓ AML 3-source cross-check
   ↓ tier_policy enforced
[donation event on PBM contract]
                                                   [refugee with UNHCR ProGres + iris]
   ↓ federated PID attestation
   ↓ ─────────────────────────→ Building Blocks verifies PID
                                  via existing iris check
                                                   ↓ distribution event
[consumed-state cross-check] ←─── recorded on Building Blocks chain
   ↓
[donor dashboard] shows
- k=50-aggregated, country-level
- "your USDC 100 → 3.3 households in Yemen Sa'ada via Building Blocks"
```

## 2. Federated PID Attestation

Both systems must agree that:
- `pid_jpn_pbm = HMAC(K_jpn_pbm, progres_id)` is computed by Building Blocks side
- `pid_bb = HMAC(K_bb, progres_id)` already exists in Building Blocks
- For each beneficiary, BB **attests** to JPN-PBM: "this `pid_jpn_pbm` corresponds to an active ProGres ID and has consumed X amount this month"

Cryptographic shape:

```
{
  "pid_jpn_pbm": "abc123...",
  "country_of_residence": "YE",
  "region": "Sa'ada",
  "status": "active",
  "consumed_this_month_usdc_centi": 25000,
  "month_index": 202606,
  "attested_at": 1718000000,
  "bb_signature": "...",       // Building Blocks attestation key
  "bb_signer": "wfp-yemen-attestor-001"
}
```

JPN-PBM verifies `bb_signature` against published WFP-BB public keys (rotated quarterly).

## 3. Double-distribution prevention

The critical interop concern: same beneficiary may receive from both donor pools simultaneously, exceeding their monthly cap.

Solution: **consumed-state sync** at distribution time.

```python
# JPN-PBM Donor-PBM contract logic (psuedocode)
def distribute_to_beneficiary(pid_jpn, amount):
    # 1. Get BB's consumed state for this beneficiary
    bb_consumed = building_blocks_adapter.get_consumed(pid_jpn)
    
    # 2. Compute total across both systems
    total = own_consumed[pid_jpn] + bb_consumed
    
    # 3. Cap is shared (e.g., $50/household/month)
    if total + amount > shared_cap:
        raise CapExceededError()
    
    # 4. Distribute + notify BB
    pbm.transfer(supplier, amount)
    building_blocks_adapter.notify_consumed(pid_jpn, amount)
```

## 4. Failure modes

| Scenario | Handling |
|----------|----------|
| BB API unreachable (network) | CP-6 v2 offline mode: paper voucher fallback |
| BB attestation signature invalid | Reject, alert security team |
| consumed-state out of sync | Reconcile every 24h, alert on discrepancy >5% |
| BB rotates signing key | Pre-published rotation schedule, 90-day grace |

## 5. Open questions for WFP team

- Does Building Blocks support outbound attestation API today? (We assume no, but suspect could be added quickly)
- Is iris verification real-time or batched? (Affects sync cadence)
- What's BB's current double-distribution prevention with other UN agencies?
- Would WFP allow JPN-PBM to call into a UN-internal API, or must we be UN-procured first?

## 6. Mock implementation

In R21, we shipped `services/donor_wallet.py` with a stub Building Blocks adapter for testing. Real adapter (R22+) requires WFP technical contact.
