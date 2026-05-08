# Incident Response Runbook

**Scope:** suspected or confirmed compromise of DonorCRM, its data, or any
subsystem (Render, Sentry, B2 backups, GitHub).
**Owner:** founder / engineering lead.
**Audience:** anyone who detects an incident; auditors evaluating SOC 2
CC7.4 (incident response).

> Goal of this document: minimize time-to-decision during an incident.
> When you are paged at 2am, the steps below should be sufficient to
> contain damage without consulting a lawyer or another doc.

## Severity tiers

| Tier | Trigger | Response time | Examples |
|------|---------|---------------|----------|
| **SEV-0** | Active exfiltration in progress, or confirmed unauthorized access to PII | <30 min from detection | DB credential confirmed leaked, anomalous bulk-export pattern in audit log |
| **SEV-1** | Suspected compromise but not confirmed; or auth bypass available | <2 hours | Sentry shows unauthenticated 200s on protected endpoints, suspicious login bursts that defeat rate limit |
| **SEV-2** | Vulnerability disclosed; not yet exploited | <24 hours | Critical CVE in a dependency, security review finding |
| **SEV-3** | Hardening gap with low immediate risk | <7 days | Misconfigured env var, expired cert, deprecated dependency |

## Phase 1 — Detect

Sources to check daily / on-page:

- Sentry alerts
- Render service health page
- `axes.AccessLog` — login failures
- `security.audit` log channel — auth events, view-as activations, crypto
  rotations
- Render Postgres metrics — connection count anomaly, query latency spike
- GitHub secret-scanning notifications
- External: vendor vulnerability advisories (Render, Sentry, Django release notes)

When a tier-0/1 signal hits, **start the timer** (note wall clock; the
timeline matters for breach-notification deadlines).

## Phase 2 — Contain

The goal is to **stop the bleeding**, not yet to fix the root cause.

### If a credential is suspected leaked

1. **Rotate the credential immediately.**
   - DB password: Render dashboard → donorcrm-db → Settings → Reset password.
   - `SECRET_KEY`: Render dashboard → donorcrm-web → Environment → regenerate. (Will invalidate all JWTs and sessions.)
   - `DJANGO_PII_ENCRYPTION_KEYS`: see [key-management.md](key-management.md) suspected-compromise procedure.
   - `BLIND_INDEX_KEYS`: same procedure, separate vault.
   - GitHub deploy keys / PATs: GitHub → Settings → revoke.
2. **Force re-authentication for all users.**
   - Run `python manage.py blacklist_all_tokens` (or simplejwt's flush) on the Render shell.
3. **Review audit log for actions taken under the compromised credential.**
   - `grep "actor_id=<suspect-uuid>" security.audit` in Render logs.

### If an attacker is actively in the system

1. **Disable the affected user account** if known: admin → user → Active=False.
2. **Take the affected service offline** if SEV-0 and credential rotation is insufficient: Render dashboard → Suspend service. This breaks production but is sometimes the right call.
3. **Capture evidence before remediation**: screenshot Sentry traces, copy relevant audit-log lines to a forensics folder. Don't wipe logs.

### If a backup or PII export was leaked

1. Confirm whether the leaked artifact contained encrypted columns.
   Per [crypto-architecture.md](crypto-architecture.md), donor PII fields
   are AES-256-GCM ciphertext in any DB dump or backup tarball — this
   matters for the safe-harbor analysis.
2. If the artifact predates field-level encryption (rare; check artifact's
   created_at vs encryption-rollout commit dates), assume plaintext PII
   exposure and proceed to Phase 4 (Notify).

## Phase 3 — Eradicate & Recover

1. **Identify the root cause.** Don't skip this — patching only the
   exploited path leaves siblings open.
2. **Patch.** Code fix + dependency upgrade + configuration change.
3. **Verify.** Re-test the exploit path. Add a regression test where
   feasible.
4. **Restore from clean backup** if data integrity is uncertain. Use
   the procedure in [backup-runbook.md](backup-runbook.md).
5. **Re-enable services** that were taken offline. Confirm health checks.
6. **Inform users that the incident is resolved**, even if you don't
   disclose details.

## Phase 4 — Notify (if applicable)

### Threshold for state breach notification

US state breach laws generally require notification when:

- Personal information was acquired by an unauthorized person, AND
- The information was not encrypted (or the encryption keys were also compromised), AND
- The exposure could reasonably result in identity theft or financial harm.

DonorCRM scope (US-only, no card data per 2026-05-07 confirmation):
state laws (all 50) define "personal information" as **name + identifier**
where the identifier is SSN, driver's license, financial account, medical
info, etc. **Donor PII as we collect it** (name + email + phone + address +
gift history) typically does NOT trigger most state breach laws on its
own — but consult counsel before relying on this.

### If you must notify

Required steps within the deadline (most states: 30-60 days):

1. **Inform counsel** (engage a privacy attorney; pre-arrange this).
2. **Inform the State AG** in any state where ≥500 affected residents (varies; counsel will advise).
3. **Inform affected donors** — letter or email per state requirements.
4. **Inform any required third parties**: your insurance carrier (cyber
   policy), Render security team, processor partners.

### Communication templates

Drafts of incident notification letters and AG cover letters live in
`docs/security/incident-templates/` (TODO: write these before they're needed).

## Phase 5 — Post-mortem

Within 7 days of resolution:

1. Write a blameless post-mortem in `docs/security/incidents/YYYY-MM-DD-<slug>.md`:
   - Detection: what tipped you off, time to detect.
   - Contain: actions taken, time to contain.
   - Eradicate: root cause, fix.
   - Notify: who was told, when.
   - Lessons: what defenses would have prevented this earlier.
   - Action items: with owners and due dates.
2. Review at the next engineering check-in.
3. Update this runbook if any step was unclear or missing.
4. If applicable, update the [evidence-map.md](evidence-map.md) with new
   controls.

## Contacts

| Role | Person | Channel |
|------|--------|---------|
| Engineering on-call | <fill in> | <fill in> |
| Privacy counsel | <fill in> | <fill in> |
| Cyber-insurance carrier | <fill in> | <fill in> |
| Render support | <support@render.com> | https://render.com/support |
| Sentry support | <support@sentry.io> | https://sentry.io/support |

## Drills

- **Tabletop annually.** Pick a SEV-1 scenario (e.g. "leaked DB password posted to GitHub") and walk through this runbook with the team. Time each phase. Note any gaps.
- **Backup restore quarterly.** Per [restore-test-checklist.md](restore-test-checklist.md). Document the actual restore time as your RTO baseline.
- **Key rotation rehearsal annually.** Mint a new PII key, rotate, sweep, retire. Time how long the sweep takes on production-scale data.
