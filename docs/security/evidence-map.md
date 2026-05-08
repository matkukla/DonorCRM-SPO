# Evidence Map

Maps DonorCRM controls to the assertions an auditor or customer security
review typically asks for. Each row points at the file, command, or
external evidence that demonstrates the control is in place.

**Scope confirmed 2026-05-07:** US-based donors only. No card data
stored. Frameworks formally in scope: state breach-notification laws
(50 states baseline). Frameworks not formally in scope but that this
document is structured to support if a future audit requires them:
SOC 2 (CC6/CC7 controls), and the encryption posture asserted by
typical enterprise customer security questionnaires.

## Cryptography

| Control | Implementation | Evidence |
|---------|----------------|----------|
| AES-256 for sensitive data at rest | AES-256-GCM v1 envelope; 32-byte keys | [crypto-architecture.md](crypto-architecture.md), [apps/core/encryption.py](../../apps/core/encryption.py), tests in [test_encryption.py](../../apps/core/tests/test_encryption.py) |
| Authenticated encryption (tamper detection) | GCM mode; `InvalidTag` on flipped byte | `TestTamperDetection` tests in [test_encryption.py](../../apps/core/tests/test_encryption.py) |
| Random nonces, no reuse | 96-bit nonce per write from `os.urandom`; tests assert two encryptions of identical plaintext differ | `test_two_encryptions_of_same_plaintext_differ` |
| Key rotation procedure | Documented annual rotation | [key-management.md](key-management.md) |
| Algorithm rotation supported | Versioned envelope (`v1:` prefix); `decrypt_str` handles legacy Fernet read path | `TestLegacyFernetReadPath` |
| Re-encryption tooling | `python manage.py rotate_pii_encryption --all` — idempotent, resumable | [rotate_pii_encryption.py](../../apps/core/management/commands/rotate_pii_encryption.py), [test_rotate_pii_encryption.py](../../apps/core/tests/test_rotate_pii_encryption.py) |
| Key custody — current | Render env var `DJANGO_PII_ENCRYPTION_KEYS`; 1Password mirror | [key-management.md](key-management.md) |
| Key custody — planned | KMS-backed envelope encryption (Phase 5) | Encryption-rollout doc |

## Transport security

| Control | Implementation | Evidence |
|---------|----------------|----------|
| TLS 1.3 at edge | Render-managed; verified via curl | [tls-evidence.md](tls-evidence.md) |
| TLS 1.2+ minimum | TLS 1.0/1.1 rejected by Render edge | [tls-evidence.md](tls-evidence.md) |
| HSTS, 1-year+ | `SECURE_HSTS_*` in [config/settings/prod.py](../../config/settings/prod.py); Render edge sets 10-year HSTS on static site | [tls-evidence.md](tls-evidence.md), [render.yaml](../../render.yaml) |
| HTTPS redirect | `SECURE_SSL_REDIRECT=True` | [config/settings/prod.py](../../config/settings/prod.py) |
| App ↔ DB TLS | `ssl_require=True`, configurable `DB_SSLMODE` (default `require`, target `verify-full`) | [config/settings/prod.py](../../config/settings/prod.py) |
| App ↔ DB TLS startup verification | `pg_stat_ssl` query at boot; refuses to start if TLS missing or <1.2 | [apps/core/db_tls_check.py](../../apps/core/db_tls_check.py), [apps/core/apps.py](../../apps/core/apps.py) |
| Strong cipher suite | Negotiated `TLS_AES_256_GCM_SHA384` | curl evidence in [tls-evidence.md](tls-evidence.md) |

## Application-layer hardening

| Control | Implementation | Evidence |
|---------|----------------|----------|
| Strong session/CSRF cookies | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | [config/settings/prod.py](../../config/settings/prod.py) |
| Strict Content-Security-Policy | django-csp + render.yaml static site headers | [config/settings/prod.py](../../config/settings/prod.py), [render.yaml](../../render.yaml) |
| Other security headers | `X-Frame-Options=DENY`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` | Same |
| SECRET_KEY safety check | Refuses to boot in prod with default or short key | [config/settings/prod.py](../../config/settings/prod.py) |
| Brute-force protection | django-axes installed; lockout in prod | base.py + axes config |
| Sentry PII scrubbing | `send_default_pii=False` (further scrubbing in Phase 6) | [config/settings/prod.py](../../config/settings/prod.py) |

## Access control & authentication

| Control | Implementation | Evidence |
|---------|----------------|----------|
| Role-based authorization | 4 roles (admin, missionary, supervisor, coach) with object-level permissions | [apps/core/permissions.py](../../apps/core/permissions.py) |
| Owner-scoped data | `get_visible_user_ids()` is the central scoping choke point | Same |
| JWT auth | `simplejwt` with refresh token blacklist | [config/settings/base.py](../../config/settings/base.py) |
| Password hashing | Django default (Argon2 fallback to PBKDF2) | Default config |
| View-As audit | Admin/supervisor view-as logged | [apps/core/middleware.py](../../apps/core/middleware.py), [apps/core/audit.py](../../apps/core/audit.py) |

## Logging & monitoring

| Control | Implementation | Evidence |
|---------|----------------|----------|
| Structured security audit log | `audit_event` channel `security.audit` | [apps/core/audit.py](../../apps/core/audit.py) |
| Login success/failure logged | django-axes signals into audit log | base.py |
| Crypto operations audited | `crypto.reencrypt.batch`, `crypto.reencrypt.complete`, `db.tls.check` events | rotate_pii_encryption + db_tls_check |
| Error tracking | Sentry with PII off | prod.py |
| Append-only PII access log | Phase 6 — pending |

## Backups

| Control | Implementation | Evidence |
|---------|----------------|----------|
| Automated daily Postgres backups | Render-managed | Render dashboard |
| Off-provider archive | GPG symmetric AES-256, uploaded to B2 | [backup-runbook.md](backup-runbook.md) |
| Quarterly restore-tested | Checklist + log | [restore-test-checklist.md](restore-test-checklist.md) |
| Application-layer encryption survives backup | Encrypted columns are ciphertext in any backup tarball | crypto-architecture.md |

## Vulnerability management

| Control | Implementation | Status |
|---------|----------------|--------|
| Dependency CVE scan | `pip-audit` / GitHub Dependabot | In CI (existing) |
| Static security scan | `bandit` | In CI (existing — `.github/workflows/security.yml`) |
| Secret scan | GitHub secret scanning | Enabled at the repo level |
| Penetration test | Not yet scheduled | Recommend annual |

## Open evidence gaps

| Gap | Phase | Priority |
|-----|-------|----------|
| Append-only PII access log with retention | Phase 6 — ✅ shipped 2026-05-08 ([apps/core/models.py::DataAccessLog](../../apps/core/models.py), [access_log_middleware.py](../../apps/core/access_log_middleware.py), [purge_expired_data](../../apps/core/management/commands/purge_expired_data.py)) | done |
| KMS-backed key custody | Phase 5 | medium (enterprise-customer-asked) |
| Blind-index for `email`, `phone` | Phase 3B | medium |
| Penetration test report | Phase 7 | medium |
| Quarterly TLS posture re-verification process | Phase 4 | low (ad-hoc today) |

## Verification cadence

- **Per release**: CI security scans run; encryption tests must pass.
- **Quarterly**: TLS evidence refresh, restore test, key backup verification.
- **Annual**: Key rotation, this evidence map review, pen test.
