# Key Management Runbook

**Scope:** the AES-256 keys used for field-level PII encryption.
**Env var:** `DJANGO_PII_ENCRYPTION_KEYS` (Render web service).

> Phase 5 (KMS-backed envelope encryption) will move key custody from env
> vars to AWS KMS or Vault; this runbook covers the env-var era.

## Key format

Comma-separated typed entries:

```
aes256:<32-byte-urlsafe-base64>[,aes256:<previous-key>][,fernet:<legacy-key>]
```

- The **first entry** is the current write key. New writes use it.
- Subsequent entries are read-only fallbacks — needed to decrypt rows that
  were last written under an older key.
- `fernet:` entries decrypt rows from before the AES-256-GCM upgrade
  (algorithm rotation, not just key rotation). Removed once
  `rotate_pii_encryption --all` confirms no rows remain in the legacy
  format.

## Mint a new key

```bash
python -c "from apps.core.encryption import generate_aes256_key; print(generate_aes256_key())"
# → aes256:<43-char-base64>
```

The key material is 32 bytes from `os.urandom`. Treat the printed value
as a credential: never commit, paste, or echo to a shared channel.

## Where to store the active set

| Location | Purpose |
|----------|---------|
| Render web service env var `DJANGO_PII_ENCRYPTION_KEYS` | Live runtime |
| 1Password / Bitwarden vault item "DonorCRM PII keys" | Operator-recoverable copy. Loss of all copies = unrecoverable PII loss. |
| Sealed envelope (paper, fireproof safe) | Last-resort recovery for the founder/owner. |

**Do not** store in: source repository, GitHub Actions secrets that aren't
strictly needed, customer-shared docs, Slack, or email.

## Rotate a key (annual cadence; recommended)

1. Mint a new aes256 key.
2. Render dashboard → DonorCRM web → Environment → edit
   `DJANGO_PII_ENCRYPTION_KEYS`. Prepend the new key, keep the prior key
   as the second entry. Save (triggers redeploy).
3. After the deploy goes healthy, run on the Render shell:
   ```bash
   python manage.py rotate_pii_encryption --all
   ```
   The command logs `crypto.reencrypt.batch` and `crypto.reencrypt.complete`
   audit events. Wait for completion.
4. Verify by sampling: `psql ... -c "SELECT notes FROM contacts_contact LIMIT 5"`
   and confirm every row's prefix is `v1:`.
5. Wait at least 24 hours (lets ongoing connections drain). Then remove the
   prior key from the env var, save, redeploy.
6. Update the 1Password item with the new key and the date. Keep the
   prior key archived for 90 days as paranoia recovery, then destroy.

## Algorithm upgrade (Fernet → AES-256-GCM, completed 2026-05-07)

The same procedure with one twist: the *first* entry is the new aes256 key,
the *second* is the legacy `fernet:<…>` key. After `rotate_pii_encryption`
sweeps, the legacy key can be removed.

## Disaster scenarios

### Lost the active key (env var wiped, no backup)

- Encrypted columns become unreadable. There is no decryption path.
- Mitigation: 1Password backup. If that's also lost: restore from a
  backup that pre-dates the loss (which still has decryptable rows under
  whatever key WAS active at backup time). The keys for that backup must
  be stored alongside it (sealed envelope archive recommended).

### Suspected key compromise

1. Mint a new key, prepend it. Redeploy.
2. Run `rotate_pii_encryption --all`.
3. Remove the compromised key from env var. Redeploy.
4. Note: rows that were *exfiltrated* before rotation remain decryptable
   by the attacker. Rotation does not make that go away — only KMS-backed
   envelope encryption (Phase 5) reduces ongoing exposure of new rows
   when an app-server compromise is suspected.

### Key file recovered through `git log` of a deleted commit

Treat as full compromise. Follow the suspected-compromise procedure
*and* rewrite history of any branch that ever contained the secret
(`git filter-repo`), force-push, force-rotate any GitHub deploy keys,
audit who has clones.

## Audit evidence

The application logs every batch re-encryption via
`apps.core.audit.audit_event`. Render's log retention is the source of
record; for evidence requiring longer retention, forward
`event=crypto.reencrypt.*` lines to a write-once destination
(S3 + Object Lock recommended).

## Cadence summary

| Action | Cadence | Owner |
|--------|---------|-------|
| Routine key rotation | Annual | Engineering |
| Verify 1Password backup matches Render env | Quarterly | Engineering |
| Restore-test from backup with archived key | Quarterly | Per [restore-test-checklist.md](restore-test-checklist.md) |
| Re-mint after personnel change with key access | On-event | Engineering |
| Key compromise drill (tabletop) | Annual | Engineering + ops |
