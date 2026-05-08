# Database Access Controls

## DataAccessLog append-only enforcement

The `core_dataaccesslog` table records every PII-bearing request (see
`apps/core/access_log_middleware.py`). To make the audit trail
tamper-resistant against an attacker who has gained code execution on
the application server, the application's Postgres role should hold
only `INSERT` and `SELECT` on this table — **never** `UPDATE` or
`DELETE`. The `purge_expired_data` retention command runs under a
separate, more privileged role.

The application code already follows this contract (no `.update()` or
`.delete()` callsites on `DataAccessLog` outside the purge command), so
the gap is purely at the database privilege layer.

### Roles

| Role               | Purpose                                  | Privileges on `core_dataaccesslog` |
|--------------------|------------------------------------------|------------------------------------|
| `donorcrm_app`     | Web/worker runtime (current default)     | `INSERT`, `SELECT`                 |
| `donorcrm_purge`   | Nightly retention sweep                  | `INSERT`, `SELECT`, `DELETE`       |
| `donorcrm_admin`   | Schema migrations, manual ops            | All                                |

### Provisioning runbook (Render Postgres)

Run as the database owner (the role created by Render) **after** initial
migrations have created the table:

```sql
-- 1. Create the limited application role and the purge role.
CREATE ROLE donorcrm_app   LOGIN PASSWORD '<from secrets manager>';
CREATE ROLE donorcrm_purge LOGIN PASSWORD '<from secrets manager>';

-- 2. Grant base table access (all tables EXCEPT core_dataaccesslog).
GRANT CONNECT ON DATABASE donorcrm TO donorcrm_app, donorcrm_purge;
GRANT USAGE   ON SCHEMA public      TO donorcrm_app, donorcrm_purge;

GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public
  TO donorcrm_app, donorcrm_purge;

-- 3. Lock down core_dataaccesslog for the app role.
REVOKE UPDATE, DELETE
  ON core_dataaccesslog
  FROM donorcrm_app;

-- 4. Allow new tables added by future migrations to inherit these grants.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLES TO donorcrm_app, donorcrm_purge;

-- 5. Re-revoke for any future re-creation of core_dataaccesslog.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE UPDATE, DELETE ON TABLES FROM donorcrm_app;
```

### Wiring the two `DATABASE_URL`s in `render.yaml`

Wire the web service to `donorcrm_app` and the `donorcrm-purge` cron
to `donorcrm_purge`. The cron entry already exists (added in PR #55);
update its `DATABASE_URL` env var to point at a connection string built
from the `donorcrm_purge` credentials rather than the default
`fromDatabase` block.

```yaml
- type: cron
  name: donorcrm-purge
  envVars:
    - key: DATABASE_URL
      value: "postgres://donorcrm_purge:<purge-password>@<host>/donorcrm"
```

Store the purge-role password in Render as an env-group secret and
reference it via `fromGroup` so it does not appear in source.

### Verifying the lockdown

After provisioning, confirm the app role really is locked down:

```sql
-- Connect as donorcrm_app
SET ROLE donorcrm_app;
DELETE FROM core_dataaccesslog WHERE id = '00000000-0000-0000-0000-000000000000';
-- Expected: ERROR: permission denied for table core_dataaccesslog
```

Re-test once after every schema migration that touches the table —
`ALTER DEFAULT PRIVILEGES` only applies to *future* tables, and
`core_dataaccesslog` already exists when the runbook is first run.

### Rotation

If the `donorcrm_app` password is rotated, the cron job is unaffected
because it has its own credentials. If the `donorcrm_purge` password
is rotated, the cron job must be redeployed with the new value.

### Status

| Item                                              | State        |
|---------------------------------------------------|--------------|
| `purge_expired_data` cron wired in `render.yaml`  | Done (PR #55)|
| Two-role provisioning script run on prod          | TODO         |
| Verification query passes on prod                 | TODO         |

Until the provisioning is complete, the audit log is append-only at the
application layer only. An attacker with the application's DB
credentials can erase audit entries.
