# Data Privacy Act of 2012 (RA 10173) Compliance Brief

> Compiled for DSWD review of JPN-PBM 4Ps pilot
> National Privacy Commission (NPC) framework alignment

## 1. Lawful basis for processing

The 4Ps PBM pilot processes personal data under **lawful contractual / vital interest grounds** (RA 10173 §12), supplemented by **explicit consent** (§13) recorded immutably:

- Each citizen explicitly consents at PhilSys OAuth time.
- Consent text + scope + timestamp + IP-hash + UA-hash are persisted in the `consent_logs` table immediately when the OAuth `authorize/consent` POST succeeds.
- Source: [`backend/app/routers/philsys_oauth.py`](../../../backend/app/routers/philsys_oauth.py) lines marking the `db.add(ConsentLog(...))` write.

## 2. Pseudonymization at the boundary

PSN (PhilSys number) is **never persisted** in the application database. Only the HMAC-SHA256 of the PSN, keyed by a treasury-controlled secret, reaches downstream:

```python
# backend/app/services/privacy.py
def pseudonymize(maina_or_psn: str) -> str:
    return hmac.new(SECRET, maina_or_psn.encode(), hashlib.sha256).hexdigest()
```

This satisfies §11(b) — *"data is processed in such a manner that the data subject is no longer identifiable, and any subsequent processing cannot identify them, without additional information that is held separately and protected"*.

## 3. Aggregate exports — k-anonymity

EBPM analytics exports apply machine-enforced k-anonymity (k=5):

- Demographic cells with fewer than 5 citizens are suppressed entirely.
- Aggregations over time, ward, age band, etc., respect the k threshold.
- Source: [`backend/app/services/ebpm.py`](../../../backend/app/services/ebpm.py) `K_THRESHOLD = 5`.

This addresses §13 (sensitive personal information) — derivable demographic detail is bounded.

## 4. Data subject rights (§16)

| Right | Implementation |
|-------|----------------|
| Information | Cover letter + this document + on-chain transparency |
| Access | Citizen UI shows their own redemption history |
| Object / Rectification | Via DSWD's existing 4Ps grievance channel |
| Erasure | HMAC PID is irreversible; explicit DSWD instruction triggers exclusion from new programs |
| Data portability | All exports in JSON / CSV format |
| Lodge a complaint | Via NPC standard channel |

## 5. Security of processing (§20–§24)

- **Encryption in transit**: HTTPS to backend; ECDSA secp256k1 for offline coupons.
- **Encryption at rest**: PostgreSQL column-level for sensitive fields (Phase 3); SQLite alpha runs in dedicated DSWD test environment.
- **Access control**: OAuth Bearer + role-based; raw PII access limited to DSWD officers via consent log audit.
- **Audit trail**: Every state-changing function emits an immutable on-chain event.
- **Incident response**: 72-hour NPC notification per §38 if a breach affects 100+ data subjects.

## 6. Data sharing & cross-border

| Direction | What | Lawful basis |
|-----------|------|--------------|
| 4Ps PBM → DSWD | Aggregate KPIs (k-anonymous) | Existing 4Ps reporting mandate |
| 4Ps PBM → Coins.ph | PHPC settlement metadata only (no PII, no PSN, only merchant_id + amount) | Contractual processor relationship per §15 |
| 4Ps PBM → JICA | Anonymized aggregate research data, with consent override | Standard project reporting |
| 4Ps PBM → Tokyo (project lead) | Operational logs (no PII, only HMAC PIDs) | Service-provider relationship |
| **No data leaves the Philippines** in raw or PII form | (§22 cross-border restrictions) | Compliant by design |

## 7. NPC registration

- The Pilot Operator (corporate vehicle TBD) will register as a Personal Information Controller with the NPC prior to alpha launch.
- DSWD remains the primary controller; the project is a Personal Information Processor under contractual instruction.

## 8. Specific compliance evidence in repository

| Requirement | File / Function |
|-------------|----------------|
| Consent log | `backend/app/models/consent.py:ConsentLog` |
| HMAC pseudonymization | `backend/app/services/privacy.py:pseudonymize()` |
| k-anonymity enforcement | `backend/app/services/ebpm.py:K_THRESHOLD` |
| OAuth consent screen (Tagalog/English) | `backend/app/routers/philsys_oauth.py:authorize()` |
| Audit on every state change | All routers emit indexed events |
| Test coverage of consent log writes | `backend/tests/test_philsys_oauth.py:test_consent_writes_consent_log` |
