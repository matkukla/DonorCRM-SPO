# Data Retention Policy

**Scope:** US-based donors only (no GDPR; CCPA may apply if California donors).
**Owner:** engineering.
**Audience:** auditors, customer security questionnaires, internal ops.

> Each row below maps a data class to:
>   - **Retain for**: how long we keep it after creation OR after the
>     trigger event named in the Trigger column, whichever applies.
>   - **Trigger**: the event after which the retention clock starts. If
>     blank, the clock starts at row creation.
>   - **Delete how**: hard-delete via the named mechanism. Soft-delete is
>     not retention — it leaves PII addressable.

## Retention table

| Data class | Retain for | Trigger | Delete how |
|------------|-----------|---------|------------|
| Active donor records (`Contact`, related `Gift`, `RecurringGift`, `JournalContact`) | Indefinite while in active relationship | n/a — see deletion-on-request below | Manual via admin `/backstage/` or owner UI |
| Soft-deleted contact (`is_merged=True`) | 1 year after merge | `created_at` of `ContactMergeLog` | `purge_expired_data` |
| Stage events (`JournalStageEvent`) | Lifetime of the parent contact | n/a | Cascades on contact delete |
| Prayer intentions (`PrayerIntention`) | Lifetime of the parent contact | n/a | Cascades on contact delete |
| Auth audit log (`security.audit` channel, login events) | 1 year | event timestamp | Render log retention + log export rotation |
| **PII access log (`DataAccessLog` — Phase 6)** | **1 year** | event timestamp | `purge_expired_data` |
| `axes.AccessAttempt` rows | 90 days | `attempt_time` | `axes_reset` Django command, scheduled |
| Outstanding JWT tokens (`OutstandingToken`) | Until expiry | issuance | simplejwt blacklist cleanup |
| Blacklisted JWT tokens (`BlacklistedToken`) | 30 days post-blacklist | `blacklisted_at` | simplejwt cleanup |
| Sentry events | 90 days | Sentry-managed | Sentry retention setting |
| Render service logs | 7 days (Render Basic plan) | log emission | Auto-rotated by Render |
| Render Postgres point-in-time recovery | 7 days (Basic plan) | snapshot time | Render-managed |
| Off-provider GPG'd backups (B2) | 30 days | backup creation | B2 lifecycle rule |
| Import batch records (`ImportBatch`) | 1 year | `created_at` | `purge_expired_data` |

## Deletion on request

A donor or staff member can request deletion at any time. Process:

1. Verify the request comes from the data subject (or their authorized agent
   under CCPA, where applicable). Don't delete on email request from an
   unverified address.
2. Hard-delete the `Contact` row via admin or by running the deletion
   workflow. Cascades to gifts, journal events, prayer intentions.
3. Note the `actor_id` in the access log — the deletion event itself is
   audit-logged.
4. **Do NOT delete** the corresponding `DataAccessLog` rows. They reference
   the deleted contact by internal ID only; no PII remains in the log
   after the contact row is gone.
5. Confirm completion in writing within 45 days (CCPA timeline) or 30 days
   for non-California requests as a courtesy.

## Sensitive data not stored

For the record, DonorCRM does NOT collect or store:

- Credit card numbers, expirations, CVVs
- Social Security Numbers
- Bank account or routing numbers
- Driver's license / state ID numbers
- Medical or health records
- EU residents' personal data (per scope confirmation)

If any of the above is ever pasted into a free-text field by a user, treat
as an incident per [incident-response.md](incident-response.md) and purge
the row.

## Backup retention vs. deletion-on-request

Render's automated backups (7 days) and the off-provider B2 backups
(30 days) may retain a deleted donor's row in ciphertext form for the
backup retention window. This is **acceptable under CCPA** as long as:

- The data is encrypted at rest (it is — field-level AES-256-GCM ensures
  any backup contains ciphertext for sensitive fields; volume encryption
  + GPG covers the rest).
- The backup is not used to restore the deleted record.

If a backup is ever restored, the deletion request must be re-applied
immediately on the restored data.

## Purge cadence

- **`purge_expired_data` runs nightly** via a Render cron job (TODO: wire
  the cron). Logs `event=retention.purge.complete` per data class with
  counts.
- **Audit logs are retention-checked weekly** as a separate command so a
  long-running purge doesn't block.

## Review cadence

Review this policy:

- Annually as part of security review.
- Whenever a new model field collects PII.
- Whenever a regulatory framework is added to scope (e.g. SOC 2 audit
  scheduled, GDPR scope expansion).

## File map

| Concern | Path |
|---------|------|
| Purge command | [apps/core/management/commands/purge_expired_data.py](../../apps/core/management/commands/purge_expired_data.py) |
| Retention configuration | `RETENTION_DAYS` constants in the same file |
| Backup retention | [backup-runbook.md](backup-runbook.md) |
| Restore tests | [restore-test-checklist.md](restore-test-checklist.md) |
| Incident response (deletion under breach) | [incident-response.md](incident-response.md) |
