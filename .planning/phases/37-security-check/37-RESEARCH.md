# Phase 37: Full Security Check - Research

**Researched:** 2026-02-25
**Domain:** Security audit & hardening (auth, headers, secrets, dependencies, file uploads)
**Confidence:** HIGH

## Summary

DonorCRM has a solid security foundation from Phase 36's full-stack audit (14 security issues fixed), but several deeper security concerns remain unaddressed. The JWT auth system (SimpleJWT) is well-configured with token rotation and blacklisting already enabled in settings, but the frontend fails to store the rotated refresh token -- meaning refresh token rotation is broken in practice. Security headers are partially configured (HSTS, X-Frame-Options, X-Content-Type-Options present in prod), but Content-Security-Policy is completely absent. No rate limiting exists on any endpoint, including auth. Password validators use Django defaults (minimum 8 chars, no purely-numeric) but lack the "at least 1 number and 1 letter" requirement from user decisions. Dependency scanning has never been run.

The codebase has good defensive patterns already: file upload size limits (10 MB), CSV export sanitization, formula injection stripping on import, null byte removal, field length truncation, owner-scoped querysets on all views, and proper permission classes. The main gaps are systemic hardening (rate limiting, CSP, password policy) rather than code-level vulnerabilities.

**Primary recommendation:** Use DRF's built-in `ScopedRateThrottle` for auth endpoint rate limiting (no new dependencies), add `django-csp` for Content-Security-Policy headers, write a custom password validator for the alphanumeric requirement, and fix the frontend refresh token rotation bug. Run `bandit`, `pip-audit`, and `npm audit` for automated scanning. Produce SECURITY-REPORT.md documenting all findings.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Gap-fill approach from Phase 36 -- focus on what Phase 36 missed, not a full re-audit
- Automated scanning (bandit for Python, npm audit for JS, safety check) PLUS manual code review for logic flaws
- Include infrastructure/deployment security (render.yaml, CORS, security headers, env var hygiene)
- Dependency audit: fix known CVEs AND flag significantly outdated packages that may have unpatched issues
- Fix issues as they're discovered -- no separate discovery phase before fixes
- Produce a final SECURITY-REPORT.md summarizing what was checked, findings, and resolutions
- Each finding gets a severity rating: Critical / High / Medium / Low
- Defer large refactors (e.g., switching auth libraries) to future phases -- only fix issues that don't require major architecture changes
- Add refresh token rotation: new refresh token issued on each use, old one invalidated
- Add rate limiting on authentication endpoints (login, token refresh) -- e.g., 5 failed attempts per minute per IP
- Add basic password policy: minimum 8 characters, at least 1 number and 1 letter
- Tighten token expiry: access token 15 minutes, refresh token 7 days
- Database-level encryption only (Render provides disk encryption at rest) -- no app-level field encryption
- Audit + harden secrets management: verify no secrets in code/git, ensure Render env vars properly scoped, check for leaked keys
- Full file upload security review: all upload endpoints (CSV, XLSX, Smartsheet) checked for path traversal, type spoofing, malicious content
- Add security headers: Content-Security-Policy, HSTS, X-Content-Type-Options, X-Frame-Options via Django SecurityMiddleware

### Claude's Discretion
- Specific rate limiting thresholds and implementation (django-ratelimit vs DRF throttling)
- CSP policy details (which directives, how strict)
- Whether to add CSRF cookie settings or rely on DRF's token auth exemption
- Bandit/safety configuration and which warnings to suppress

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core (Already In Place)
| Library | Version | Purpose | Security Relevance |
|---------|---------|---------|-------------------|
| Django | >=4.2,<5.0 | Backend framework | SecurityMiddleware, password validators, CSRF |
| DRF | >=3.14,<4.0 | REST API | Built-in throttling classes, permission framework |
| djangorestframework-simplejwt | >=5.3,<6.0 | JWT auth | Token rotation, blacklisting, expiry config |
| django-cors-headers | >=4.0,<5.0 | CORS | Origin allowlisting |
| sentry-sdk | >=1.30,<2.0 | Error tracking (prod) | `send_default_pii=False` already set |

### To Add
| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| django-csp | 4.x | Content-Security-Policy headers | No CSP currently; user decision requires it |
| bandit | latest | Python static security analysis | User decision requires automated Python scanning |
| pip-audit | latest | Python dependency CVE scanning | Better than `safety` -- free, open DB, PyPA-maintained |

### Not Needed (Already Built-In)
| Capability | Provided By | Notes |
|------------|-------------|-------|
| Rate limiting | DRF `ScopedRateThrottle` | Built into DRF, no extra dependency |
| npm audit | npm CLI | Built into npm, run `npm audit` in frontend/ |
| Password validation | Django `AUTH_PASSWORD_VALIDATORS` | Custom validator for alphanumeric requirement |
| Security headers (HSTS, X-Frame, etc.) | Django `SecurityMiddleware` | Already in prod.py, just verify configuration |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DRF throttling | django-ratelimit | Extra dependency; decorator-based (less DRF-native). DRF throttling is sufficient and zero-dependency. |
| pip-audit | safety | safety requires paid plan for best DB; pip-audit uses free PyPA advisory DB |
| django-csp | Manual header middleware | django-csp handles nonces, per-view overrides, report-only mode. Worth the dependency. |

**Recommendation: Use DRF throttling** (no new dependency). It integrates natively with DRF views, supports per-view scoping, and uses Django's cache backend. For auth endpoints that use SimpleJWT's built-in views (TokenObtainPairView, TokenRefreshView), we can subclass them and add `throttle_scope`.

**Installation:**
```bash
# Backend (dev dependency for scanning -- not production)
pip install bandit pip-audit

# Backend (production dependency)
pip install django-csp

# Frontend (built-in)
cd frontend && npm audit
```

## Architecture Patterns

### Pattern 1: Auth Endpoint Rate Limiting via DRF ScopedRateThrottle
**What:** Apply per-scope rate limits to login and token refresh endpoints using DRF's built-in throttle.
**When to use:** Auth endpoints that are targets for brute-force attacks.
**Confidence:** HIGH (DRF official documentation)

```python
# config/settings/base.py -- add to REST_FRAMEWORK
REST_FRAMEWORK = {
    # ... existing config ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth': '5/min',         # Login/refresh: 5 per minute per IP
        'password': '3/min',     # Password change: 3 per minute
    },
}

# apps/users/urls_auth.py -- subclass SimpleJWT views to add throttle_scope
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = 'auth'

class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_scope = 'auth'
```

### Pattern 2: Fix Frontend Refresh Token Rotation
**What:** The backend issues a new refresh token on each use (ROTATE_REFRESH_TOKENS=True, BLACKLIST_AFTER_ROTATION=True) but the frontend only stores the new access token, not the new refresh token. After one refresh, the old refresh token is blacklisted and subsequent refreshes fail, logging the user out.
**Confidence:** HIGH (direct code inspection)

```typescript
// frontend/src/api/client.ts -- CURRENT (broken)
const { access } = response.data
localStorage.setItem(ACCESS_TOKEN_KEY, access)

// frontend/src/api/client.ts -- FIXED
const { access, refresh } = response.data
setTokens(access, refresh)  // Store BOTH tokens
```

### Pattern 3: Custom Password Validator
**What:** Django's built-in validators cover min length (8), common passwords, numeric-only, and user-attribute similarity. Need a custom validator for "at least 1 number and 1 letter".
**Confidence:** HIGH (Django docs)

```python
# apps/core/validators.py
import re
from django.core.exceptions import ValidationError

class AlphanumericPasswordValidator:
    """Require at least one letter and one number."""
    def validate(self, password, user=None):
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError('Password must contain at least one letter.')
        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one number.')

    def get_help_text(self):
        return 'Your password must contain at least one letter and one number.'
```

### Pattern 4: CSP Configuration with django-csp
**What:** Add Content-Security-Policy header. DonorCRM is an SPA served from a separate static site (Render), so CSP applies primarily to the Django API responses.
**Confidence:** HIGH (django-csp 4.0 docs)

```python
# config/settings/prod.py
MIDDLEWARE.insert(2, 'csp.middleware.CSPMiddleware')

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        "img-src": ["'self'"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'"],
    },
}
```

**Important nuance:** Since DonorCRM's frontend is a separate static site (not served by Django), CSP on the API server primarily protects the API schema/docs pages and any Django admin pages. The frontend's CSP would need to be set via Render's static site headers configuration in render.yaml, not Django middleware.

### Pattern 5: Security Scanning Commands
**What:** Run automated security scanners and fix findings.
**Confidence:** HIGH (tool documentation)

```bash
# Python static analysis
bandit -r apps/ -f json -o bandit-report.json --severity-level medium

# Python dependency CVE scan
pip-audit --requirement requirements/base.txt --requirement requirements/prod.txt

# Frontend dependency CVE scan
cd frontend && npm audit --audit-level moderate
```

### Anti-Patterns to Avoid
- **Over-restrictive CSP breaking the app:** Start with `CONTENT_SECURITY_POLICY_REPORT_ONLY` to detect violations before enforcing. However, since the Django API doesn't serve the SPA, this is low risk.
- **Rate limiting authenticated users by IP only:** DRF's `ScopedRateThrottle` uses IP for anonymous requests and user ID for authenticated requests, which is correct behavior.
- **Suppressing all bandit warnings globally:** Only suppress false positives with inline `# nosec` comments, not global config excludes (except for test files).
- **Fixing CVEs by pinning to exact versions:** Use range specifiers (>=X.Y.Z) to allow patch updates. Only pin when a specific version is needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom middleware counting requests | DRF `ScopedRateThrottle` | Handles IP tracking, cache backend, rate parsing, 429 responses |
| CSP headers | Manual header injection in middleware | `django-csp` | Handles nonces, per-view overrides, report-only mode, constants |
| Dependency CVE scanning | Manual version checking | `pip-audit` + `npm audit` | Automated DB lookups against advisory databases |
| Python static analysis | Manual code review only | `bandit` + manual review | AST-based analysis catches patterns humans miss |
| Password validation | Custom regex in serializer | Django `AUTH_PASSWORD_VALIDATORS` | Centralized, applies to all password changes, admin included |

**Key insight:** Security hardening should use battle-tested tools, not custom implementations. The main work is configuration and integration, not building new systems.

## Common Pitfalls

### Pitfall 1: Refresh Token Rotation Breaking User Sessions
**What goes wrong:** Backend rotates refresh tokens (issues new one, blacklists old), but frontend doesn't store the new refresh token. After first token refresh, user gets logged out.
**Why it happens:** SimpleJWT's `TokenRefreshView` returns `{access, refresh}` when rotation is enabled, but the frontend interceptor only reads `access`.
**How to avoid:** Store both `access` and `refresh` from the refresh response. This is the single most impactful security bug to fix.
**Warning signs:** Users reporting unexpected logouts after ~15 minutes (access token lifetime).
**Current status:** BROKEN. `frontend/src/api/client.ts` line 106 only stores `access`.

### Pitfall 2: ScopedRateThrottle Requires Cache Backend
**What goes wrong:** DRF throttling uses Django's cache to track request counts. The default `LocMemCache` doesn't share between Gunicorn workers.
**Why it happens:** Each Gunicorn worker has its own memory space, so rate counts aren't shared.
**How to avoid:** In production, Redis is available (Render). Use Redis cache backend for throttle state. If Redis is not enabled (currently commented out in render.yaml), `LocMemCache` still provides per-worker rate limiting which is better than nothing.
**Warning signs:** Rate limits appearing inconsistent between requests (hitting different workers).
**Current status:** Redis is commented out in render.yaml. Rate limiting with LocMemCache will still work per-worker -- acceptable for a small deployment.

### Pitfall 3: CSP Blocking Inline Styles in Django Admin/Swagger
**What goes wrong:** Strict CSP (`style-src: 'self'`) blocks inline styles used by Django admin and drf-spectacular Swagger UI.
**Why it happens:** Django admin and Swagger UI use inline `<style>` tags and `style=` attributes.
**How to avoid:** Either (a) use `EXCLUDE_URL_PREFIXES` in django-csp to exclude `/admin/` and `/api/v1/docs/`, or (b) add `'unsafe-inline'` to `style-src` for those paths. Since these are admin-only, option (a) is simpler.
**Warning signs:** Admin/docs pages render without styling.

### Pitfall 4: Bandit False Positives on Test Files
**What goes wrong:** Bandit flags hardcoded passwords in test fixtures, assert statements, and test helper functions.
**Why it happens:** Test files intentionally contain test credentials and patterns that look like security issues.
**How to avoid:** Exclude test directories: `bandit -r apps/ --exclude "*/tests/*"`
**Warning signs:** High finding count dominated by test file issues.

### Pitfall 5: npm audit Noise from Dev Dependencies
**What goes wrong:** `npm audit` reports vulnerabilities in devDependencies that don't affect production.
**Why it happens:** Dev dependencies (build tools, test frameworks) often have vulnerabilities that don't impact the shipped application.
**How to avoid:** Use `npm audit --omit=dev` for production-relevant scan, but still run full audit and triage dev dependency issues separately.
**Warning signs:** Many moderate/low findings in eslint plugins, vite, etc.

### Pitfall 6: API Schema/Docs Exposed in Production
**What goes wrong:** `/api/v1/schema/`, `/api/v1/docs/`, and `/api/v1/redoc/` are currently accessible without authentication, potentially exposing API structure to attackers.
**Why it happens:** drf-spectacular views have no permission classes by default.
**How to avoid:** Add `IsAuthenticated` (or `IsAdmin`) permission to schema views in production, or disable them entirely.
**Warning signs:** Anonymous access to full API schema.

## Code Examples

### Current Auth Configuration (Already Good)
```python
# config/settings/base.py -- SimpleJWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),     # Already correct per user decision
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),        # Already correct per user decision
    'ROTATE_REFRESH_TOKENS': True,                      # Already enabled
    'BLACKLIST_AFTER_ROTATION': True,                    # Already enabled
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### Current Security Headers (prod.py -- Already Good)
```python
# config/settings/prod.py -- already configured
SECURE_BROWSER_XSS_FILTER = True              # X-XSS-Protection (deprecated but harmless)
SECURE_CONTENT_TYPE_NOSNIFF = True             # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = 'DENY'                       # X-Frame-Options: DENY
SECURE_SSL_REDIRECT = True                     # Redirect HTTP to HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True                   # Secure flag on session cookie
CSRF_COOKIE_SECURE = True                      # Secure flag on CSRF cookie
SECURE_HSTS_SECONDS = 31536000                 # HSTS: 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### File Upload Security Review Checklist
```
All upload endpoints (10 total) use:
  - MAX_UPLOAD_SIZE = 10 MB check          [VERIFIED in all views]
  - MultiPartParser only                    [VERIFIED - explicit parser_classes]
  - Admin-only permissions                  [VERIFIED - IsAdmin on RE/MPD imports]
  - CSV null byte stripping                 [VERIFIED in decode_csv_bytes()]
  - Field length truncation (10,000 chars)  [VERIFIED in _sanitize_field()]
  - SHA256 dedup (RE imports)               [VERIFIED in check_duplicate_import()]
  - Formula injection stripping (MPD)       [VERIFIED - FORMULA_INJECTION_CHARS]
  - CSV export sanitization                 [VERIFIED - sanitize_csv_value() in all exports]

Missing:
  - File extension validation on MPD import [PARTIAL - accepts CSV/XLSX by design, but no reject of .exe/.js]
  - Content-type validation (MIME check)    [MISSING - only extension check on CSV imports]
  - XLSX macro/embedded content check       [MISSING - openpyxl parses data only, low risk]
```

### Secrets Management Audit Status
```
.env file:       In .gitignore [VERIFIED]
.env.example:    Contains only placeholder values [VERIFIED]
render.yaml:     SECRET_KEY uses generateValue: true [VERIFIED]
                 DATABASE_URL uses fromDatabase [VERIFIED]
                 No hardcoded secrets [VERIFIED]
base.py:         SECRET_KEY from config() with insecure default [NOTE: dev only]
                 DB_PASSWORD from config() [VERIFIED]
                 EMAIL_HOST_PASSWORD from config() [VERIFIED]
.gitignore:      Covers *.pem, *.key, secrets.json, credentials.json, .mcp.json [VERIFIED]
Git history:     Need to verify no secrets committed in past (git log search)
```

### Current Password Validators
```python
# Django defaults -- covers:
# 1. UserAttributeSimilarityValidator -- password != email/name
# 2. MinimumLengthValidator -- min 8 chars (default)
# 3. CommonPasswordValidator -- blocks "password123" etc.
# 4. NumericPasswordValidator -- blocks all-numeric passwords

# MISSING: "at least 1 number and 1 letter" per user decision
# FIX: Add custom AlphanumericPasswordValidator to list
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `safety check` (PyUp) | `pip-audit` (PyPA) | 2022+ | Free, open advisory DB, PyPA-maintained |
| `SECURE_BROWSER_XSS_FILTER` | Deprecated | Chrome 78+ (2019) | Still harmless to include, but CSP is the real protection |
| Manual CSP header strings | `django-csp` 4.0 with constants | 2024 | Type-safe constants, nonce support, per-view control |
| Django 6.0 built-in CSP | Coming soon | Django 6.0 (not released) | DonorCRM on Django 4.2 -- use django-csp for now |
| `django-ratelimit` decorator | DRF built-in throttling | Always available | No extra dependency for DRF projects |

**Deprecated/outdated:**
- `SECURE_BROWSER_XSS_FILTER`: X-XSS-Protection header is deprecated by all major browsers. CSP replaces it. Keep the setting (harmless) but don't rely on it.
- `safety` free tier: Increasingly limited. `pip-audit` is the standard choice for open-source projects.

## Detailed Findings by Area

### 1. Auth & Session Security

**Token expiry (Already correct):**
- Access: 15 minutes (matches user decision)
- Refresh: 7 days (matches user decision)
- Dev overrides: 1 hour access, 30 days refresh (acceptable for development)

**Refresh token rotation (BROKEN on frontend):**
- Backend: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` -- correctly configured
- `token_blacklist` app installed -- correct
- Frontend bug: `client.ts` line 106 only stores `access` from refresh response, ignoring new `refresh` token
- Impact: After first token refresh, old refresh token is blacklisted, user gets logged out on next access token expiry
- Fix: Store `response.data.refresh` alongside `response.data.access` in the interceptor

**Rate limiting (MISSING):**
- No throttle classes configured in REST_FRAMEWORK settings
- No rate limiting on `/api/v1/auth/login/` or `/api/v1/auth/refresh/`
- Recommendation: DRF `ScopedRateThrottle` with `'auth': '5/min'`

**Password policy (PARTIAL):**
- Django defaults provide: min 8 chars, no all-numeric, no common passwords, no similar-to-user-attributes
- Missing: "at least 1 number and 1 letter" per user decision
- Fix: Custom `AlphanumericPasswordValidator` in `apps/core/validators.py`

**Logout (GOOD):**
- `LogoutView` blacklists refresh token on logout
- Exception handling returns 400 for invalid tokens

### 2. Security Headers

**Present in prod.py (GOOD):**
- HSTS (1 year, subdomains, preload)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- SSL redirect with proxy header
- Secure cookies (session + CSRF)

**Missing (TO ADD):**
- Content-Security-Policy -- needs django-csp
- Referrer-Policy -- not configured (Django 4.2 doesn't set by default)
- Permissions-Policy -- not configured (optional but recommended)

**Frontend headers (PARTIAL):**
- render.yaml sets `Cache-Control: no-cache` on frontend
- No CSP, Referrer-Policy, or Permissions-Policy on static site
- Fix: Add security headers to render.yaml frontend `headers` section

### 3. Infrastructure & Deployment

**render.yaml (GOOD):**
- SECRET_KEY generated by Render (not hardcoded)
- DATABASE_URL from database service
- CORS_ALLOWED_ORIGINS restricted to frontend origin
- Separate frontend/backend services

**Concerns:**
- API docs (schema, swagger, redoc) accessible without auth in production
- Health check endpoint (`/api/v1/health/`) has no auth (acceptable for load balancers)
- Dev settings have `CORS_ALLOW_ALL_ORIGINS = True` (acceptable for dev only)
- Redis commented out -- rate limiting will use LocMemCache (per-worker, acceptable)

### 4. File Upload Security

**10 upload endpoints reviewed:**

| Endpoint | Permission | Size Check | Extension Check | Content Validation |
|----------|-----------|------------|-----------------|-------------------|
| ContactImportView | IsAdmin | 10 MB | .csv only | UTF-8 decode |
| FundImportView | IsAdmin | 10 MB | .csv only | UTF-8-sig decode |
| EntityImportView | IsAdmin | 10 MB | .csv only | UTF-8-sig decode |
| RESolicitorImportView | IsAdmin | 10 MB | None (raw bytes) | decode_csv_bytes() |
| REConstituentImportView | IsAdmin | 10 MB | None (raw bytes) | decode_csv_bytes() |
| REGiftImportView | IsAdmin | 10 MB | None (raw bytes) | decode_csv_bytes() |
| RERecurringGiftImportView | IsAdmin | 10 MB | None (raw bytes) | decode_csv_bytes() |
| MPDImportView | IsAdmin | 10 MB | None (format detection) | PK\x03\x04 magic bytes |
| GenericContactImportView | IsStaffOrAbove | 10 MB | None (raw bytes) | decode_csv_bytes() |
| GenericDonationImportView | IsStaffOrAbove | 10 MB | None (raw bytes) | decode_csv_bytes() |

**Findings:**
- All enforce 10 MB limit (GOOD)
- All require authentication + appropriate role (GOOD)
- No files saved to disk -- all parsed in memory (GOOD for path traversal)
- RE imports use `decode_csv_bytes()` with null byte stripping (GOOD)
- CSV imports check `.csv` extension; RE/generic imports don't check extension (LOW risk -- they'll fail to parse non-CSV)
- MPD import detects XLSX via PK magic bytes (GOOD)
- No MIME type validation (LOW risk -- content is always parsed, not executed)
- openpyxl XLSX parsing: data-only, no macro execution (GOOD)

### 5. CSRF Considerations

DonorCRM uses JWT auth (not session auth), so CSRF protection is handled differently:
- DRF's `SessionAuthentication` performs CSRF checks; `JWTAuthentication` does not (by design)
- `CSRF_COOKIE_SECURE = True` in prod (for any admin/session usage)
- `CsrfViewMiddleware` is in middleware stack (protects Django admin)
- SPA + JWT means CSRF is not an attack vector for API endpoints (tokens are in Authorization header, not cookies)

**Recommendation:** No CSRF changes needed. Current setup is correct for JWT-based SPA.

## Open Questions

1. **Git history secrets scan**
   - What we know: Current .env is in .gitignore, render.yaml uses generated values
   - What's unclear: Whether secrets were ever committed in early project history
   - Recommendation: Run `git log --all -S "password" --oneline` and similar searches during implementation. If found, rotate affected credentials.

2. **API docs in production**
   - What we know: `/api/v1/schema/`, `/api/v1/docs/`, `/api/v1/redoc/` are accessible
   - What's unclear: Whether these are intentionally public for API consumers or an oversight
   - Recommendation: Restrict to authenticated users (`IsAuthenticated` permission) unless there's a specific need for public docs. The planner should include a task for this.

3. **Render static site CSP headers**
   - What we know: render.yaml supports custom headers on the static site
   - What's unclear: Exact CSP directives needed for the React SPA (which CDN assets, inline styles from libraries)
   - Recommendation: Start with `CONTENT_SECURITY_POLICY_REPORT_ONLY` on frontend, audit violations, then enforce. This may need to be iterative.

4. **Redis for rate limiting**
   - What we know: Redis is commented out in render.yaml to save costs
   - What's unclear: Whether the user wants to re-enable Redis for rate limiting
   - Recommendation: Use LocMemCache (per-worker) for now. Document that Redis would improve rate limiting accuracy if enabled in future.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all settings, views, models, and frontend code
- [DRF Throttling Documentation](https://www.django-rest-framework.org/api-guide/throttling/) -- ScopedRateThrottle configuration
- [django-csp 4.0 Documentation](https://django-csp.readthedocs.io/en/latest/configuration.html) -- CSP configuration
- [Django Password Validation](https://docs.djangoproject.com/en/4.2/topics/auth/passwords/#module-django.contrib.auth.password_validation) -- Custom validator pattern
- Phase 36 Audit Report (`.planning/phases/36-full-stack-audit/36-AUDIT-REPORT.md`) -- What was already fixed

### Secondary (MEDIUM confidence)
- [pip-audit PyPI](https://pypi.org/project/pip-audit/) -- Dependency scanning tool
- [Bandit Documentation](https://bandit.readthedocs.io/) -- Python security scanner
- [npm audit Documentation](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities/) -- Frontend dependency scanning
- [Safety vs pip-audit comparison](https://sixfeetup.com/blog/safety-pip-audit-python-security-tools) -- Tool comparison

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or official documentation

## Metadata

**Confidence breakdown:**
- Auth/session hardening: HIGH -- direct code inspection, SimpleJWT docs verified
- Security headers: HIGH -- Django SecurityMiddleware well-documented, django-csp docs current
- Rate limiting: HIGH -- DRF throttling is built-in, well-documented
- File upload security: HIGH -- all 10 endpoints inspected, patterns verified
- Dependency scanning: HIGH -- tool documentation is straightforward
- CSP policy details: MEDIUM -- exact directives for SPA may need iteration
- Secrets in git history: LOW -- need to scan, can't determine pre-research

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days -- stable tools and patterns)
