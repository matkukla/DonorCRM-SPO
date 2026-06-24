# R2 cutover — run the app as the least-privilege `donorcrm_app` role

Completes risk **R2**: after this, the running application connects as
`donorcrm_app`, which has full DML on every table **except** it cannot
`UPDATE`/`DELETE` `core_dataaccesslog`. An attacker who steals the app's DB
credentials can no longer erase the audit trail.

**Prerequisite:** [sql/dataaccesslog-role-lockdown.sql](sql/dataaccesslog-role-lockdown.sql)
has already been run (the `donorcrm_app` / `donorcrm_purge` roles exist).

## Why migrations move out of the deploy

`donorcrm_app` has DML grants but **not** table ownership, so it cannot run
schema migrations (`ALTER TABLE`, etc.). It must not own the tables either —
a table owner bypasses the `REVOKE`, which would defeat the lockdown. So:

- **Runtime (gunicorn)** → `donorcrm_app` (least privilege).
- **Migrations** → the database **owner**, run manually (no longer in the
  build). `render.yaml` reflects this: `migrate` is removed from `buildCommand`
  and `DATABASE_URL` is `sync: false` (set as a dashboard secret).

## Cutover steps — order matters (do in a low-traffic window)

1. **Build the runtime connection string.** Take the owner's *internal*
   connection string (Render → `donorcrm-db` → Connect → Internal Database URL)
   and swap the user/password for the `donorcrm_app` credentials:
   `postgresql://donorcrm_app:<app-password>@<internal-host>/donorcrm`
2. **Set it as a dashboard secret FIRST.** Render → `donorcrm-web` →
   Environment → set `DATABASE_URL` to that string. Do this **before** the new
   `render.yaml` deploys — `sync: false` means Render keeps the dashboard value,
   but only if one exists (an unset value would crash boot).
3. **Deploy the `render.yaml` change** (merge the branch / sync the blueprint).
   The build no longer migrates; the runtime now uses `donorcrm_app`.
4. **Confirm the app is healthy** (`/api/v1/health/`, log in, load the dashboard).
5. **Verify the lockdown** from inside the web service (it connects as
   `donorcrm_app`, so no IP allow-list change needed). Render → `donorcrm-web`
   → Shell:
   ```bash
   python manage.py dbshell -- -c \
     "DELETE FROM core_dataaccesslog WHERE id='00000000-0000-0000-0000-000000000000';"
   # Expected: ERROR: permission denied for table core_dataaccesslog
   ```
   (Or `python manage.py shell` → run the DELETE via `django.db.connection`.)
   A normal `SELECT count(*) FROM core_dataaccesslog;` should still succeed.

### Rollback (if anything breaks)

Set `DATABASE_URL` back to the owner's internal connection string in the
dashboard and redeploy. The app returns to owner-role operation immediately;
nothing is lost. (Or revert the `render.yaml` `DATABASE_URL` to the
`fromDatabase` block.)

## Migrations from now on

Run migrations **as the owner**, not on deploy:

```bash
# Render -> donorcrm-web -> Shell (or any shell on Render's network)
DATABASE_URL='<owner internal connection string>' python manage.py migrate
```

Run this **before** (or as part of) any deploy that ships a new migration, so
the schema is current before the `donorcrm_app` runtime serves it.

- New tables created by an owner-run migration **auto-grant** DML to
  `donorcrm_app` (via the `ALTER DEFAULT PRIVILEGES` set in the lockdown script).
- If a future migration ever re-creates or alters `core_dataaccesslog`, re-run
  the `REVOKE UPDATE, DELETE ON core_dataaccesslog FROM donorcrm_app;` afterward.
