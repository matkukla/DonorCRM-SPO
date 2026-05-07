# PII Encryption Rollout

This document is the operational runbook for moving DonorCRM donor PII columns
from plaintext to field-level encryption (`apps.core.encryption.EncryptedTextField`).

## Why

Render's managed Postgres provides at-rest disk encryption. That defends only
against physical theft of the storage volume. It does NOT defend:

- a leaked read-only DB credential (analytics pipeline, dev export)
- accidental SQL dumps copied to object storage
- a future SQL-injection or ORM bug that surfaces rows
- snapshots restored into a lower environment

Field-level encryption ensures these egress paths reveal ciphertext only.

## Scope (Phase 1)

Encrypt the following columns on existing models:

| App        | Model              | Columns                                              |
|------------|--------------------|------------------------------------------------------|
| contacts   | Contact            | `phone`, `email`, `address`, `notes`                 |
| gifts      | Gift               | `notes`                                              |
| prayers    | PrayerIntention    | `description`                                        |
| journals   | JournalEntry       | `body`                                               |

Out of scope for Phase 1:
- Searchable indexes (would require a separate hashed blind-index column)
- KMS-backed envelope encryption (Phase 2 — keys live in app env today)
- Field-level encryption of `User.email` (used as login identifier, would
  break django-axes username lockup; defer to Phase 3 with a normalized
  hash column)

## Phase 1 procedure

1. **Generate a key** (locally, do not commit):
   ```bash
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```
2. **Set `PII_ENCRYPTION_KEYS` in Render env** for both web + worker services.
3. **Deploy the app code** with `PII_ENCRYPTION_KEYS` set but BEFORE swapping
   any model field to `EncryptedTextField`. This proves the key is available.
4. **For each column** in the table above, create a Django migration:
   - `AlterField` to swap `TextField` → `EncryptedTextField`
   - A `RunPython` data migration that loops the table in batches of ~500
     rows, reads each value (which `from_db_value` returns as plaintext for
     legacy rows due to the `gAAAAA` sentinel check), and re-saves it. The
     `get_prep_value` path encrypts on write.
   - Mark the migration `atomic = False` so each batch commits independently.
5. **Verify** with `psql`:
   ```sql
   SELECT phone FROM contacts_contact LIMIT 5;
   ```
   Values should start with `gAAAAA…`.
6. **Roll columns one app at a time** so a failed migration impacts a single
   surface, not the entire dataset.

## Key rotation

1. Generate a new key.
2. Set `PII_ENCRYPTION_KEYS="<NEW_KEY>,<OLD_KEY>"` (new first).
3. Deploy. New writes use the new key; old reads still decrypt.
4. Run a management command (`rotate_pii_encryption`) that reads + re-saves
   every encrypted row in batches. (Command not yet written — Phase 1.5.)
5. Once all rows are re-encrypted, remove `<OLD_KEY>` from the env and
   redeploy.

Never delete a key from `PII_ENCRYPTION_KEYS` until you have positive
confirmation that no row remains encrypted under it. A safe guardrail is to
keep the old key for one full rotation cycle (e.g., 90 days) past the
re-encryption sweep.

## Phase 2: KMS envelope encryption

Field-level encryption with keys in app env is defeated by code execution on
the app server. To raise the bar:

- Move the data-encryption keys (DEKs) into AWS KMS / GCP KMS.
- App holds only a key-encryption-key (KEK) reference, not the DEKs.
- Each row stores its own DEK encrypted under KMS; the app calls KMS to
  unwrap the DEK on read.

Cost: ~$1/month per KMS key + per-call API charges. Adds latency on every
read. Worth it for compliance frameworks (SOC 2 + customer requests for KMS).
Track as a separate phase; do NOT block Phase 1 on it.

## Threat model summary

| Threat                                   | Phase 1 (this rollout) | Phase 2 (KMS) |
|------------------------------------------|------------------------|---------------|
| Cold backup theft                        | Defended               | Defended      |
| DB credential leak                       | Defended               | Defended      |
| Accidental SQL dump into object storage  | Defended               | Defended      |
| App-server code execution                | Bypassed               | Defended      |
| Compromised Render account               | Bypassed               | Bypassed*     |

\* unless KMS is in a separate cloud account with break-glass IAM.

## Operational checklist before enabling

- [ ] `PII_ENCRYPTION_KEYS` set in Render web + worker env
- [ ] Key backed up in 1Password / Doppler vault
- [ ] Key recovery procedure documented (who has access, how to restore)
- [ ] Backup runbook updated to call out that backup tarballs are encrypted
- [ ] First migration tested against a Render preview environment
