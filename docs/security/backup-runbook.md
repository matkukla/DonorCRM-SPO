# Backup & Disaster Recovery Runbook

DonorCRM stores donor PII and gift history. A complete loss of the production
database would be a catastrophic event for the missionaries and donors who
depend on it. This runbook defines what we back up, how often, who restores,
how long it takes, and how we test that the procedure actually works.

## RPO / RTO targets (Phase 1)

| Metric | Target | Rationale |
|--------|--------|-----------|
| RPO    | ≤ 24h  | Render Standard Postgres takes daily snapshots; one lost day of donor edits is recoverable from sources (RE / SPO / MPD CSVs) by re-running the import pipeline. |
| RTO    | ≤ 4h   | Single-app, single-region deploy. Restore = Render snapshot rollback + Render dashboard re-deploy + smoke tests. |

These targets must be tightened before any contractual SLA is offered to
external orgs. Phase 2 should drive RPO ≤ 1h via WAL archiving and RTO ≤ 1h
via a warm standby.

## What is backed up (Phase 1)

| Asset                       | Mechanism                              | Retention | Off-provider copy |
|-----------------------------|----------------------------------------|-----------|-------------------|
| Production Postgres         | Render daily snapshots                 | 7 days    | Manual quarterly dump (see below) |
| Source-of-truth import CSVs | RE / SPO / MPD upload archive (S3 ext) | Indefinite | N/A (source is upstream system)   |
| Application code + config   | Git (GitHub)                           | Indefinite | GitHub                            |
| Render env vars             | Render dashboard                       | N/A       | 1Password (`DonorCRM Production`) vault item |
| PII encryption keys         | `PII_ENCRYPTION_KEYS` env var          | N/A       | 1Password vault, restricted to admins |

What is NOT backed up:
- Sentry breadcrumbs (Sentry handles its own retention)
- Frontend static assets (rebuilt from Git on demand)
- User session state (intentionally ephemeral; users re-login)

## Recovery scenarios

### Scenario A — accidental row deletion

1. Identify the affected rows + approximate deletion time.
2. Open Render → Postgres service → Backups.
3. Download the snapshot from immediately before the deletion.
4. Restore to a *staging* database (NEVER overwrite prod).
5. Run a targeted SQL export of the affected rows from the staging DB.
6. Insert/update those rows back into prod via a `manage.py` script.
7. Audit the changes via the security audit log.

### Scenario B — full DB corruption / region outage

1. Open Render → Postgres service → Backups → "Restore snapshot".
2. Choose the most recent good snapshot (default: previous day).
3. Wait for the restore to complete (typical: 10–30 min for our size).
4. Render automatically updates the `DATABASE_URL` env var on the linked web
   service. Trigger a redeploy of the web + worker services.
5. Run smoke tests:
   - Login as a known test user.
   - List contacts (should return rows).
   - View a known gift (should match expected amount).
   - Confirm Sentry receives an event from the redeployed service.
6. Communicate restore + data-loss window to active users via in-app banner +
   email. Be specific about the cutoff time.

### Scenario C — ransomware / malicious DROP

If an attacker has DB credentials, snapshot rollback is sufficient. If an
attacker has Render account access, they may have deleted snapshots too.
This is why off-provider backups exist (below). In that scenario:

1. Revoke the compromised Render account immediately.
2. Restore from the most recent off-provider dump (worst case: ~90 days old).
3. Trigger a fresh import from upstream RE / SPO sources to rebuild the data
   gap.
4. Force-rotate all secrets (SECRET_KEY, PII_ENCRYPTION_KEYS, JWT-signing,
   email creds, Sentry DSN). Invalidate all JWTs by rotating
   SIMPLE_JWT_SIGNING_KEY.
5. Force-logout all users (next request fails JWT verification → re-login).
6. Open a postmortem in `docs/incidents/`.

## Off-provider backup procedure (manual, quarterly)

Until automated, run this on the first business day of each quarter:

```bash
# From an admin laptop with Render CLI authenticated:
render psql --service donorcrm-db --command "" > /dev/null  # warm up

DATE=$(date +%Y-%m-%d)
render psql --service donorcrm-db --command "\copy (SELECT * FROM pg_stat_database) TO STDOUT" > /dev/null

# Take a logical dump:
PGPASSWORD="$(render env get DATABASE_URL | grep -o ':[^@]*@' | tr -d ':@')"
pg_dump "$(render env get DATABASE_URL)" --no-owner --no-acl --format=custom \
  --file="donorcrm-${DATE}.dump"

# Encrypt and upload to a separate cloud account (Backblaze B2):
gpg --symmetric --cipher-algo AES256 --output "donorcrm-${DATE}.dump.gpg" \
    "donorcrm-${DATE}.dump"
b2 upload-file donorcrm-offsite-backups "donorcrm-${DATE}.dump.gpg" \
   "donorcrm-${DATE}.dump.gpg"

# Verify upload, delete local plaintext:
shred -u "donorcrm-${DATE}.dump"
```

The B2 bucket has Object Lock enabled with a 1-year retention rule —
backups cannot be deleted by a compromised credential before the retention
window expires.

## Restore-test schedule

A backup that has never been restored is a wish, not a backup.

| Cadence    | Scope                                      | Owner |
|------------|--------------------------------------------|-------|
| Quarterly  | Restore latest Render snapshot to staging, run smoke tests | Engineering on-call |
| Annually   | Restore an off-provider GPG dump to a fresh DB, run smoke tests | Engineering on-call |
| Annually   | Tabletop exercise of Scenario C (ransomware) | Founders + Engineering |

Record each restore test in `docs/security/restore-tests.md` (date,
snapshot id, time-to-restore, issues found).

## Open items (Phase 2)

- [ ] Automate the quarterly off-provider dump via a scheduled job.
- [ ] Add WAL archiving to drop RPO from 24h to ≤ 1h.
- [ ] Document a warm-standby region for RTO ≤ 1h.
- [ ] Add a `manage.py verify_backup` command that restores the latest snapshot
      to a temporary DB, runs schema checksum + row count assertions, and
      tears it down.
