-- =====================================================================
-- DataAccessLog two-role DB lockdown (risk register R2)
-- =====================================================================
-- Purpose: make the PII access log (core_dataaccesslog) tamper-PROOF at the
-- database privilege layer, not just append-only by application convention.
-- After this runs (and the app is repointed to donorcrm_app), an attacker who
-- obtains the application's DB credentials still cannot UPDATE or DELETE audit
-- rows. See docs/security/access-controls.md for the full rationale.
--
-- HOW TO RUN (database is now internal-only — no public access):
--   1. Open Render dashboard -> donorcrm-db -> Connect -> PSQL Command, OR
--      `render psql donorcrm-db`, connecting as the database OWNER role.
--   2. Replace the two '<from secrets manager>' passwords below with strong,
--      unique values stored in your secrets manager (1Password / Render env).
--   3. Run this whole file (\i path/to/this.sql, or paste it).
--   4. Repoint the web service to the limited role and redeploy (CRITICAL):
--        - Generate a connection string for donorcrm_app and set it as the
--          web service DATABASE_URL (Render env, as a secret), replacing the
--          default `fromDatabase` connectionString (which is the OWNER role).
--        - render.yaml note: the app currently uses the owner via
--          `fromDatabase ... property: connectionString`. The lockdown does
--          NOTHING while the app connects as the owner, because a table owner
--          bypasses GRANT/REVOKE.
--   5. Run the VERIFICATION block at the bottom (as donorcrm_app) and confirm
--      the DELETE is denied.
-- =====================================================================

-- 1. Create the limited application role and the purge role.
CREATE ROLE donorcrm_app   LOGIN PASSWORD '<from secrets manager>';
CREATE ROLE donorcrm_purge LOGIN PASSWORD '<from secrets manager>';

-- 2. Base connectivity + table access on everything.
GRANT CONNECT ON DATABASE donorcrm TO donorcrm_app, donorcrm_purge;
GRANT USAGE   ON SCHEMA public      TO donorcrm_app, donorcrm_purge;

GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public
  TO donorcrm_app, donorcrm_purge;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
  TO donorcrm_app, donorcrm_purge;

-- 3. Lock down the audit log for the APP role (purge role keeps DELETE so the
--    retention sweep can still expire old rows).
REVOKE UPDATE, DELETE
  ON core_dataaccesslog
  FROM donorcrm_app;

-- 4. Make future tables (added by later migrations) inherit these grants...
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLES TO donorcrm_app, donorcrm_purge;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO donorcrm_app, donorcrm_purge;

-- 5. ...but keep the app role locked out of any future re-creation of the log.
--    (ALTER DEFAULT PRIVILEGES applies only to tables created AFTER it runs, so
--    re-run step 3 manually after any migration that re-creates the table.)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE UPDATE, DELETE ON TABLES FROM donorcrm_app;

-- =====================================================================
-- VERIFICATION  (run AFTER repointing the app; connect as donorcrm_app)
-- =====================================================================
--   SET ROLE donorcrm_app;
--   DELETE FROM core_dataaccesslog
--     WHERE id = '00000000-0000-0000-0000-000000000000';
--   -- Expected: ERROR: permission denied for table core_dataaccesslog
--   RESET ROLE;
-- =====================================================================
