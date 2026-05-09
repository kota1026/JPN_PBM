# Sari-sari & Retail Merchant Onboarding Playbook

> For Quezon City Innovation Office field team
> Time: ~30 minutes per merchant
> Required: smartphone or laptop, printed Tagalog handout, QR Ph sticker (provided)

## 1. Pre-meeting (5 minutes)

- Confirm the merchant has GCash QR Ph already (~80%+ in QC have one).
- Confirm the merchant has a smartphone (~90%+).
- Print the Tagalog handout (`../dswd/01-cover-letter-tl.md`).

## 2. Pitch (10 minutes, Tagalog)

Talking points:

1. **What this is**: 4Ps PBM — a way for 4Ps recipients to buy from your sari-sari with subsidy applied automatically, paid to you in PHPC (which Coins.ph converts to PHP for free).
2. **What changes for you**: Almost nothing. You display one extra QR sticker on your wall. Customers scan with their phones. You get paid directly via Coins.ph just like any other GCash transaction.
3. **What you do not change**: Your prices, your products, your normal cash transactions — all unchanged.
4. **What this gives you**: 4Ps recipients prefer your store because they get subsidy here. More foot traffic.
5. **What we ask**: 30 minutes today + ~5 minutes per pilot transaction during the 3 months.

## 3. On-site setup (10 minutes)

| Step | Action |
|------|--------|
| 1 | Provide and stick the **QR Ph sticker** (printed with merchant_id, MCC, name) on a visible wall location. |
| 2 | Demonstrate one mock transaction with a project-staff phone (the demo runs `frontend/ph/citizen.html` against a local instance). |
| 3 | Walk through what an offline (CP-6) transaction looks like — paper receipt issued, queued, settled later. |
| 4 | Confirm the merchant's GCash account ID for routing PHPC payouts. |
| 5 | Sign a **simple participation form** (not a binding contract during alpha — voluntary). |

## 4. Post-meeting (5 minutes)

- Take photo of the QR sticker installed (for the field log).
- Add merchant to the approved store list via the LGU's authorized field officer (calls `/treasury/approved-stores` POST or via Coins.ph's merchant onboarding API).
- Add to the WhatsApp group for ongoing support.

## 5. Frequently asked questions (Tagalog answer prepared)

**Q: Anong gagawin ko kapag walang internet?**

A: Pwede pa ring tumanggap ng pre-issued QR coupons mula sa customer. I-scan, mag-print ng resibo, at i-save sa phone — kapag bumalik ang internet, mag-sumite tayo ng batch para magkaroon ng PHPC payment.

**Q: Mawawala ba ang PHPC kapag bumagsak ang Coins.ph?**

A: Hindi. Lahat ng transaksyon ay naka-record sa Polygon (open blockchain) — kahit mawala ang Coins.ph (which won't happen — they're BSP-regulated), pwede mong i-redeem ang PHPC sa ibang Polygon DEX.

**Q: Kakailanganin ko bang kumuha ng POS scanner?**

A: Hindi. Ang customer ang mag-scan gamit ang sarili nilang phone. Wala kang need bilhing kasangkapan.

**Q: Magkano ang fee?**

A: Walang fee mula sa amin. Ang Coins.ph PHPC → PHP conversion ay nasa standard rates nila (madalas 0% para sa registered merchants).

**Q: Anong mangyayari kung tinatangkang bumili ang customer ng alak/sigarilyo?**

A: Awtomatikong ire-reject ng app. Hindi mo na kailangang i-judge ang customer — siyang sistema ang nag-de-decide.

## 6. Approved store entry format (technical)

When the field officer adds a merchant to the on-chain approved list, the entry contains:

```json
{
  "id": "ph-store-aling-maria-qc",
  "name": "Aling Maria's Sari-Sari Store",
  "city": "Quezon City",
  "mcc": 5411,
  "qr_ph_id": "MERCHANT-MARIA-QC-001"
}
```

This format matches `seed/ph/stores.json` so the same on-chain `setApprovedStore(true)` call works.
