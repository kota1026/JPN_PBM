# Para sa: DSWD Region NCR · 4Ps Program Management

**Tungkol sa**: 4Ps Programmable Subsidy (PBM) — panukala para sa closed-alpha pilot sa Quezon City
**Mula sa**: JPN-PBM Project (Tokyo + Manila Twin Pilot)
**Petsa**: 2026-05-09 (draft)

---

Mahal na DSWD team,

Kami ay isang open-source international initiative na pinangunahan mula sa Tokyo, na dinisenyo upang gawing **purpose-bound** ang pamamahagi ng subsidiya gamit ang stablecoin technology. Ang aming sistema ay tumatakbo na sa sandbox sa <https://github.com/kota1026/JPN_PBM>, na may 175+ unit tests, berde sa GitHub Actions CI, at nakapagsagawa na ng 24-item smart-contract self-audit.

Hinihingi namin ang kooperasyon ng DSWD sa **closed-alpha pilot ng 4Ps PBM** sa Quezon City: 5 sambahayan × 5 sari-sari store × 3 buwan. Ang pilot ay gumagamit ng **PHPC** (peso stablecoin ng Coins.ph na inaprubahan ng Bangko Sentral ng Pilipinas sa regulatory sandbox 2024) bilang underlying value layer.

Ano ang pagkakaiba mula sa kasalukuyang cash-based 4Ps:

| Isyu | Kasalukuyang 4Ps (cash) | 4Ps PBM (panukala) |
|------|-------------------------|---------------------|
| Maling paggamit (alak/sigarilyo) | ~5–7% tahimik na nawawala | **Sapilitang nababara** sa MCC (alak = 5921, sigarilyo = 5993) |
| Pamamahagi sa panahon ng bagyo | Tumitigil kapag walang network | **Tuloy-tuloy** sa pre-signed offline QR (CP-6) |
| Reporting lag | 4–8 linggo | **Real-time** k-anonymous KPI dashboard |
| Fraud detection | Manual audit lang | On-chain `consumed[]` mapping na pumipigil sa double-redemption |
| Vendor lock-in | Posible sa proprietary system | **Apache 2.0 open source** — pag-aari ng DSWD ang deployment |

Ano ang hinihingi namin mula sa DSWD:

1. **Magpili ng pilot LGU** (iminumungkahi namin ang **Quezon City**, dahil sa umiiral na ugnayan sa DICT).
2. **Aprubahan ang partisipasyon ng 5 mock na 4Ps households** para sa closed alpha (walang aktwal na pondo ng DSWD habang alpha — gumagamit ng sandbox PHPC).
3. **Magtulungan sa pagbuo ng operational protocol** para sa sari-sari merchant onboarding.
4. **Magbigay ng observer status** sa aming mga test run.

Ano ang makukuha ng DSWD:

- Isang gumagana na 4Ps leakage reduction tool, na-validate sa sandbox bago hawakan ang totoong pera.
- Real-time KPI dashboard na ma-access nang walang raw PII.
- Reference implementation na pwedeng gamitin ng iba pang Southeast Asian welfare ministries.
- Conference contribution credit sa OECD / BIS / MAS.

Ano ang makukuha namin:

- Domain expertise ng DSWD sa operational realities ng 4Ps.
- Pahintulot na lumapit sa Coins.ph at GCash na may basbas ng DSWD.
- Letter of Intent na nagpapalakas sa aming JICA Digital Public Goods application.

Ang detalyadong 4Ps PBM specification ay nasa `02-4ps-pilot-spec.md`. Ang privacy compliance sa Data Privacy Act of 2012 ay dokumentado sa `03-data-privacy.md`.

Nagpapasalamat kami sa pagsasaalang-alang ng DSWD. Magiging karangalan namin ang isang 30-minutong introductory meeting sa inyong convenience.

— JPN-PBM Project Lead
<https://github.com/kota1026/JPN_PBM>
