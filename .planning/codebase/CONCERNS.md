# Codebase Concerns

**Analysis Date:** 2026-01-24

## Tech Debt

**Celery Tasks Disabled in Production:**
- Issue: Background worker and Celery Beat services are commented out in `render.yaml` (lines 55-108) to reduce hosting costs. Scheduled tasks are non-functional.
- Files: `/home/matkukla/projects/DonorCRM/render.yaml`, `/home/matkukla/projects/DonorCRM/config/celery.py`
- Impact: At-risk donor detection (`detect_at_risk_donors`), late pledge checking (`check_late_pledges`), and weekly summary emails do not run in production. Users won't receive alerts or notifications.
- Fix approach: Create a worker-as-container solution or implement polling mechanism in web service. Alternatively, use a free tier service like Heroku Scheduler or AWS Lambda for periodic tasks.

**Hardcoded Production Hostname:**
- Issue: Git commit `9c00a69` mentions "hardcoded host for now" - indicates temporary solution in place.
- Files: `config/settings/` (likely dev.py or prod.py settings)
- Impact: Production deployment may be fragile or not scaling to multiple instances.
- Fix approach: Verify ALLOWED_HOSTS and CORS configuration properly source from environment variables. Current implementation in `base.py` lines 19-20 and 193-197 appears correct but hostname may be hardcoded elsewhere.

**Console Email Backend in Development:**
- Issue: `EMAIL_BACKEND` defaults to `django.core.mail.backends.console.EmailBackend` in `config/settings/base.py` (line 216).
- Files: `/home/matkukla/projects/DonorCRM/config/settings/base.py`
- Impact: Emails are logged to console instead of sent. Email testing doesn't validate actual delivery. Production must set proper backend via env vars.
- Fix approach: Use SendGrid, AWS SES, or other production email service. Ensure EMAIL_BACKEND is properly configured in prod settings.

## Known Issues

**Exception Handling Too Broad:**
- Instances: `/home/matkukla/projects/DonorCRM/apps/users/views_auth.py`, `/home/matkukla/projects/DonorCRM/apps/dashboard/tasks.py`, `/home/matkukla/projects/DonorCRM/apps/core/email.py`
- Problem: `except Exception` and `except BaseException` catch all errors without specific handling or logging context.
- Impact: Bugs silently fail. Difficult to debug production issues. Generic error messages don't help users.
- Workaround: Current logging catches some errors, but specific exception types should be caught.

**Bare Except in Email Service:**
- File: `/home/matkukla/projects/DonorCRM/apps/core/email.py` (lines 42-45)
- Problem: HTML email template rendering silently fails with bare `except` block. No specific error type caught.
- Impact: If HTML template is missing, system silently falls back. No visibility into template errors.

## Security Considerations

**Secret Key Default is Insecure:**
- Risk: `SECRET_KEY` in `config/settings/base.py` (line 14) defaults to `'django-insecure-change-me-in-production'` if env var not set.
- Files: `/home/matkukla/projects/DonorCRM/config/settings/base.py`
- Current mitigation: Render.yaml generates SECRET_KEY at deployment via `generateValue: true` (line 37).
- Recommendations: Add pre-deployment check to ensure SECRET_KEY is not default value. Consider using a secrets management system for local development.

**Email Credentials Stored in Environment:**
- Risk: Email authentication credentials (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD) stored as plain env vars in `config/settings/base.py` (lines 220-221).
- Files: `/home/matkukla/projects/DonorCRM/config/settings/base.py`, `.env.example`
- Current mitigation: Only used for SMTP connections. Not exposed in API responses.
- Recommendations: Use OAuth2 for email providers instead of plain credentials. Rotate credentials regularly.

**CORS Hardcoded Origins in Render:**
- Risk: `CORS_ALLOWED_ORIGINS` hardcoded for single frontend in `render.yaml` (line 43): `https://donorcrm-frontend.onrender.com`.
- Files: `/home/matkukla/projects/DonorCRM/render.yaml`
- Impact: If frontend domain changes, CORS breaks and frontend can't communicate with API. No flexibility for staging/preview environments.
- Recommendations: Use environment variable `CORS_ALLOWED_ORIGINS` instead. Support comma-separated origins for multiple deployments.

**JWT Token Configuration:**
- Risk: Access token lifetime is 15 minutes (config/settings/base.py line 181). Short expiry is good, but refresh token is 7 days and can be rotated.
- Files: `/home/matkukla/projects/DonorCRM/config/settings/base.py` (lines 180-190)
- Current mitigation: ROTATE_REFRESH_TOKENS enabled, tokens blacklisted after rotation.
- Recommendations: Implement token refresh endpoint rate limiting to prevent brute force attacks.

**Database Connection Pool Exposed:**
- Risk: Production database pool settings visible in code (`config/settings/prod.py` lines 50-55) with hardcoded values.
- Files: `/home/matkukla/projects/DonorCRM/config/settings/prod.py`
- Impact: Pool sizes not tuned for actual database capacity. No flexibility for scaling.
- Recommendations: Make POOL_SIZE and MAX_OVERFLOW configurable via environment variables.

## Performance Bottlenecks

**Denormalized Statistics Without Caching:**
- Problem: Contact model has denormalized fields (total_given, gift_count, etc.) in `apps/contacts/models.py` (lines 58-74).
- Files: `/home/matkukla/projects/DonorCRM/apps/contacts/models.py`, `/home/matkukla/projects/DonorCRM/apps/contacts/models.py` (lines 138-167)
- Cause: `update_giving_stats()` method recalculates all statistics on every donation. No caching of expensive aggregations.
- Improvement path: Use database-level triggers or materialized views. Cache dashboard aggregations for 1 hour. Batch statistics updates via Celery.

**Task Iterator Without Chunking:**
- Problem: Large-scale Celery tasks use `.iterator()` but don't chunk work efficiently.
- Files: `/home/matkukla/projects/DonorCRM/apps/contacts/tasks.py` (line 41), `/home/matkukla/projects/DonorCRM/apps/pledges/tasks.py` (line 28)
- Cause: Iterating 100K+ records in single task will timeout or consume excessive memory.
- Improvement path: Split large tasks into sub-tasks using Celery chains or implement pagination with N records per task.

**CSV Import Memory Usage:**
- Problem: Large CSV files loaded entirely into memory in `apps/imports/services.py` and `apps/imports/views.py`.
- Files: `/home/matkukla/projects/DonorCRM/apps/imports/views.py` (line 63), `/home/matkukla/projects/DonorCRM/apps/imports/services.py`
- Cause: `file.read().decode('utf-8')` loads entire file. No streaming.
- Improvement path: Use pandas chunked reading or implement streaming CSV parser. Process rows one at a time without loading entire file.

**Bulk Create Without Conflict Handling:**
- Problem: `Contact.objects.bulk_create()` in import doesn't handle duplicate email constraint.
- Files: `/home/matkukla/projects/DonorCRM/apps/imports/tasks.py` (lines 100, 127)
- Cause: Duplicate emails fail silently or raise IntegrityError without graceful handling.
- Improvement path: Use `bulk_create(..., ignore_conflicts=True)` or implement upsert logic. Return detailed error report.

**N+1 Query in At-Risk Donor Detection:**
- Problem: Potential N+1 queries in `detect_at_risk_donors()` when creating events.
- Files: `/home/matkukla/projects/DonorCRM/apps/contacts/tasks.py` (lines 30-55)
- Cause: Event creation in loop (line 43) likely makes individual database writes.
- Improvement path: Use `bulk_create()` to create all events in single query. Batch events by user.

## Fragile Areas

**CSV Import Validation Logic:**
- Files: `/home/matkukla/projects/DonorCRM/apps/imports/services.py` (451 lines - largest file in codebase)
- Why fragile: Complex validation with multiple date formats (line 26), custom regex for emails (line 29), type coercions. Hard to maintain regex patterns and add new fields.
- Safe modification: Add comprehensive test cases for edge cases (invalid dates, special characters, empty values). Use library like `phonenumbers` for phone validation instead of regex.
- Test coverage: `apps/imports/tests/test_services.py` (229 lines) - good coverage but needs more edge case testing.

**Celery Task Status Tracking:**
- Files: `/home/matkukla/projects/DonorCRM/apps/imports/tasks.py` (lines 17-30)
- Why fragile: Progress tracking uses cache with 1-hour TTL. Cache miss means lost progress. No database persistence.
- Safe modification: Use Django ORM to persist ImportJob records. Store status in database instead of cache.
- Test coverage: Missing tests for cache expiry and progress tracking.

**Email Service Generic Exception Handling:**
- Files: `/home/matkukla/projects/DonorCRM/apps/core/email.py` (170 lines)
- Why fragile: Silent failures on template rendering errors (line 44). No detailed error reporting.
- Safe modification: Log full stack trace. Return specific error types. Add email service abstraction to mock in tests.
- Test coverage: No visible tests for email service.

**Role-Based Access Control String Matching:**
- Files: `/home/matkukla/projects/DonorCRM/apps/contacts/views.py` (lines 54-56)
- Why fragile: Access checks use hardcoded role strings `'admin'`, `'finance'`, `'read_only'`.
- Safe modification: Create Role enum or permission classes. Use Django's permission system. Add model for roles.
- Test coverage: Tests exist but don't comprehensively test all role combinations.

**Contact Status Automatic Update:**
- Files: `/home/matkukla/projects/DonorCRM/apps/contacts/models.py` (lines 160-162)
- Why fragile: Contact status automatically updated to DONOR on first donation. No control over this behavior.
- Safe modification: Remove automatic status change or add override flag. Let staff explicitly change status.
- Test coverage: Likely not tested.

## Scaling Limits

**Single Redis Instance for Celery:**
- Current capacity: Single Redis instance (render.yaml line 106 commented out).
- Limit: No Redis in production - all async tasks disabled. When enabled, single instance limits throughput.
- Scaling path: Use AWS ElastiCache or managed Redis. Implement Redis clustering for failover. Use RabbitMQ as alternative broker.

**Database Connection Pool Sizing:**
- Current capacity: POOL_SIZE=20, MAX_OVERFLOW=30 (prod.py line 51-52) = 50 max connections.
- Limit: Render free PostgreSQL plan limits connections. With multiple gunicorn workers, connections exhaust quickly.
- Scaling path: Use PgBouncer for connection pooling. Migrate to managed PostgreSQL with higher limits. Reduce connection per worker.

**Gunicorn Worker Count:**
- Current capacity: Default gunicorn workers (likely 2-4 on Render).
- Limit: Render free tier doesn't specify. Concurrent users limited by worker count and response time.
- Scaling path: Configure workers via environment variable. Use auto-scaling groups. Implement request queuing.

**CSV Import Batch Size:**
- Current capacity: Batch size 100 contacts per bulk_create (imports/tasks.py line 91).
- Limit: Large imports (10K+ records) may timeout or memory-exhaust.
- Scaling path: Reduce batch to 50, implement progress updates more frequently. Use Celery sub-tasks.

## Dependencies at Risk

**Celery Disabled Risk:**
- Risk: Celery 5.3+ has breaking changes. Code expects Celery to be present but it's disabled.
- Impact: If re-enabled, may encounter compatibility issues. Code not actively tested.
- Migration plan: Run full integration tests when re-enabling Celery. Pin version `celery>=5.3,<6.0` in requirements.

**Django Dependency Narrow Range:**
- Risk: `Django>=4.2,<5.0` (requirements/base.txt line 2) locked to 4.2. Django 5.0 has significant changes.
- Impact: When upgrading to Django 5.0+, may need updates to models, admin, or ORM calls.
- Migration plan: Test against Django 5.0 in staging. Gradual migration of deprecated patterns (async views, etc.).

**drf-spectacular Version:**
- Risk: `drf-spectacular>=0.27,<1.0` (requirements/base.txt line 19) - younger library, may have breaking changes.
- Impact: API schema generation may break. Documentation tools may not work.
- Migration plan: Pin to specific version tested in CI. Monitor release notes.

## Missing Critical Features

**No Audit Trail for Financial Data:**
- Problem: No audit logging for donations, pledges, or contact deletions. Can't track who changed what.
- Blocks: Compliance, financial reporting, dispute resolution.
- Priority: HIGH - required for nonprofit operations.

**No Soft Delete for Contacts:**
- Problem: Contact deletions are permanent. No recovery. Violates data retention requirements.
- Blocks: GDPR compliance (right to be forgotten requires permanent deletion), but also need retention for financial records.
- Priority: HIGH - implement soft delete + configurable retention period.

**No Backup Strategy Documented:**
- Problem: No documented backup mechanism for production database.
- Blocks: Disaster recovery. Data loss risk unmitigated.
- Priority: HIGH - Render provides automated backups but not documented in code.

**No Rate Limiting on Import Endpoints:**
- Problem: CSV import endpoints have no rate limiting. User could spam uploads.
- Blocks: DoS vulnerability. Unprotected file upload endpoints.
- Priority: MEDIUM - add request throttling to import views.

**No Activity Logging for User Actions:**
- Problem: No way to see who accessed which contacts/donations. Privacy and security risk.
- Blocks: Audit trail, compliance reporting.
- Priority: MEDIUM - add middleware to log API access.

## Test Coverage Gaps

**Celery Tasks Not Tested:**
- Untested: `apps/contacts/tasks.py`, `apps/pledges/tasks.py`, `apps/dashboard/tasks.py`, `apps/imports/tasks.py`.
- Files: All task files lack corresponding test files.
- Risk: Scheduled jobs fail silently in production. No visibility into failures.
- Priority: HIGH - add integration tests for all periodic tasks.

**Email Service Not Tested:**
- Untested: `apps/core/email.py` - no test file visible.
- Files: `/home/matkukla/projects/DonorCRM/apps/core/email.py`
- Risk: Email failures silent. Template errors undetected. Email list changes break silently.
- Priority: HIGH - add tests for email sending, template rendering, error cases.

**CSV Service Edge Cases:**
- Untested: Date parsing with unusual formats, large files, special characters, malformed CSV.
- Files: `/home/matkukla/projects/DonorCRM/apps/imports/services.py`
- Risk: Import fails for valid but unexpected data. No error messages.
- Priority: MEDIUM - add edge case tests.

**Permission Classes Not Comprehensively Tested:**
- Untested: `IsContactOwnerOrReadAccess`, `IsStaffOrAbove` custom permissions across all endpoints.
- Files: `apps/core/permissions.py` (not visible in exploration).
- Risk: Unauthorized access possible. Role-based access breaks silently.
- Priority: HIGH - add permission tests for all view combinations.

**Frontend API Error Handling:**
- Untested: API client error handling, token refresh failures, network timeouts.
- Files: `frontend/src/api/client.ts`
- Risk: Frontend crashes on API errors. No graceful fallback.
- Priority: MEDIUM - add error boundary tests and API mock tests.

---

*Concerns audit: 2026-01-24*
