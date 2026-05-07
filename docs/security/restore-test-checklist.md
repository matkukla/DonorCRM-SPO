# Backup Restore Test Checklist

A checklist + results template for the restore tests scheduled in
[backup-runbook.md](backup-runbook.md). The principle: a backup that has
never been restored is not a backup, it's a wish.

Run the **quarterly snapshot test** every 90 days and the **annual
off-provider test** once per year. Fill in a copy of the relevant
template at the bottom of this file (or in `docs/security/restore-tests/`)
each time you run one.

---

## Quarterly: Render snapshot → staging restore

**Goal:** prove that a Render-managed snapshot of production Postgres can
be restored to a working database in under our 4-hour RTO target, and that
DonorCRM functions against the restored data.

**Prerequisites:**
- Render dashboard access for the production workspace
- A staging Postgres instance to restore into. If one doesn't exist
  permanently, provision a temporary one for the test.
- A staging copy of the web service deployed against that DB.
- Smoke-test credentials for the staging app.

**Procedure:**

- [ ] **(00:00)** Note the start time. Open Render → `donorcrm-db` → Backups.
- [ ] Identify the most recent snapshot. Record its timestamp.
- [ ] Click **Restore** and target the staging database. (Read the
      confirmation dialog twice. The wrong target here drops production data.)
- [ ] **(restore start)** Note the restore-start timestamp.
- [ ] Wait for restore to complete. Watch Render's status indicator.
- [ ] **(restore end)** Note the restore-completion timestamp. Compute the
      restore wall time.
- [ ] On the staging web service, set `DATABASE_URL` to the restored DB and
      redeploy. Note the redeploy timestamp.
- [ ] **(deploy end)** Note when the staging service comes up green.
- [ ] Run the smoke tests below. Note the timestamp at which all smoke tests
      pass.
- [ ] **(smoke pass)** This is your full RTO measurement. Compare to the
      4-hour target.

**Smoke tests** (against the restored staging app):

- [ ] Login with a known test-user account succeeds and returns a JWT.
- [ ] `GET /api/v1/contacts/` returns ≥1 row.
- [ ] `GET /api/v1/gifts/` returns ≥1 row.
- [ ] Pick a known contact ID (from production memory or the snapshot
      itself); `GET /api/v1/contacts/{id}/` returns the expected name.
- [ ] Pick a known gift; the amount field matches what you remember.
- [ ] If `Contact.notes` has been migrated to encrypted: pick a contact
      with notes and confirm the value reads as expected (i.e., the
      restored DB has the encryption keys configured correctly via
      `PII_ENCRYPTION_KEYS` env var).
- [ ] The Sentry project receives at least one event from the staging
      deploy (proves the SDK is wired and credentials are still valid).

**Cleanup:**

- [ ] Tear down the staging DB and web service if they were temporary.
- [ ] Document the result below.

---

## Annual: Off-provider GPG dump → fresh DB restore

**Goal:** prove that the encrypted dumps in B2 are recoverable end-to-end
even if Render were entirely unavailable. This defends Scenario C from
the backup runbook (ransomware / Render account compromise).

**Prerequisites:**
- Read access to the Backblaze B2 bucket containing the GPG dumps
- The GPG passphrase from 1Password
- A target Postgres instance that is NOT on Render (e.g., local Docker,
  AWS RDS preview, GCP Cloud SQL trial). Using off-Render is the whole
  point of the test.
- `pg_restore` and `gpg` installed locally

**Procedure:**

- [ ] **(00:00)** Note the start time.
- [ ] List dumps in B2:
      ```bash
      b2 ls donorcrm-offsite-backups | tail
      ```
- [ ] Download the most recent dump:
      ```bash
      b2 download-file-by-name donorcrm-offsite-backups donorcrm-YYYY-MM-DD.dump.gpg ./
      ```
- [ ] Decrypt:
      ```bash
      gpg --decrypt --output donorcrm-YYYY-MM-DD.dump donorcrm-YYYY-MM-DD.dump.gpg
      ```
      Confirm the GPG passphrase from 1Password works.
- [ ] Provision the target Postgres. Note its connection string.
- [ ] Restore:
      ```bash
      pg_restore --no-owner --no-acl --dbname="$TARGET_URL" donorcrm-YYYY-MM-DD.dump
      ```
- [ ] **(restore end)** Note the timestamp.
- [ ] Verify schema:
      ```sql
      \dt
      SELECT count(*) FROM contacts_contact;
      SELECT count(*) FROM gifts_gift;
      ```
      Confirm the table count and row counts match what you'd expect for
      that dump's date.
- [ ] Verify a known PII row reads correctly. If `Contact.notes` is
      encrypted, you'll need the matching `PII_ENCRYPTION_KEYS` from the
      time of the dump — confirm 1Password has it.
- [ ] **Securely destroy local artifacts:**
      ```bash
      shred -u donorcrm-YYYY-MM-DD.dump
      shred -u donorcrm-YYYY-MM-DD.dump.gpg
      ```
- [ ] Tear down the target Postgres.
- [ ] Document the result below.

---

## Annual: Tabletop exercise — Scenario C (ransomware)

**Goal:** prove that the team has a coherent response if Render account
access is lost AND snapshots are deleted simultaneously. This is a
discussion, not a hands-on test — but the discussion exposes gaps.

**Participants:** founders + on-call engineer + (if applicable) any
external advisor with security-incident experience.

**Procedure:**

- [ ] Schedule a 60-minute meeting.
- [ ] Read the runbook's Scenario C steps aloud.
- [ ] For each step, ask:
  - Who has the access/credentials needed?
  - How long does that step actually take?
  - What's the failure mode if that step doesn't work?
- [ ] Specifically validate:
  - [ ] Who has the GPG passphrase and the 1Password vault that holds it?
  - [ ] Who can revoke the compromised Render account? (Render org owner)
  - [ ] How do we communicate the outage to active users? (status page,
        email list, in-app banner — pick the one that survives)
  - [ ] Where would the rebuilt-from-source data come from? (RE / SPO
        upstream — confirm the upstream is still accessible)
- [ ] Note any items where the answer is "I don't know" — those are
      pre-incident gaps to fix BEFORE you need them.
- [ ] Document the session below with the gaps found.

---

## Results log template

Copy this template and fill it in for each test.

```markdown
### Quarterly snapshot test — YYYY-MM-DD

- Snapshot timestamp restored: YYYY-MM-DD HH:MM UTC
- Restore wall time: HH:MM (target: ≤ 4h)
- Smoke tests pass: ✅ / ❌
- Total RTO measured: HH:MM
- Issues found: <list, or "none">
- Action items: <list, or "none">
- Run by: <name>
```

```markdown
### Annual off-provider test — YYYY-MM-DD

- Dump date: YYYY-MM-DD
- Bucket retrieval succeeded: ✅ / ❌
- GPG decryption succeeded: ✅ / ❌
- pg_restore succeeded: ✅ / ❌
- Schema verification passed: ✅ / ❌
- PII decryption (if applicable): ✅ / ❌ / N/A
- Issues found: <list, or "none">
- Action items: <list, or "none">
- Run by: <name>
```

```markdown
### Annual tabletop — YYYY-MM-DD

- Participants: <names>
- Pre-incident gaps identified:
  1. ...
  2. ...
- Action items with owners:
  1. ... (owner: ..., due: ...)
- Run by: <name>
```

---

## Historical results

(append entries here in reverse chronological order)
