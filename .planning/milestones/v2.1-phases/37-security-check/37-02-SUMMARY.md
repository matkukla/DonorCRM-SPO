---
phase: 37-security-check
plan: 02
subsystem: infra
tags: [csp, django-csp, security-headers, render, referrer-policy, permissions-policy]

# Dependency graph
requires:
  - phase: 37-security-check
    provides: "Plan 01 rate limiting and auth hardening"
provides:
  - "Content-Security-Policy on Django API via django-csp middleware"
  - "Referrer-Policy on Django API via SecurityMiddleware"
  - "CSP, Referrer-Policy, Permissions-Policy on frontend static site via render.yaml"
  - "Authenticated API docs in production (schema, swagger, redoc)"
affects: [deployment, render-config]

# Tech tracking
tech-stack:
  added: [django-csp 4.0]
  patterns: [CSP via django-csp CONTENT_SECURITY_POLICY dict, conditional permission_classes based on DEBUG]

key-files:
  created: []
  modified:
    - config/settings/prod.py
    - config/api_urls.py
    - render.yaml
    - requirements/base.txt

key-decisions:
  - "Strict CSP (default-src: 'none') for Django API since it serves JSON, not HTML"
  - "Exclude /admin and /api/v1/docs|redoc from CSP to avoid breaking inline styles/scripts"
  - "Skip Permissions-Policy on Django API (JSON-only); set it on frontend static site instead"
  - "Use specific backend URL (donorcrm-web.onrender.com) in frontend CSP connect-src"
  - "Conditional API docs auth: IsAuthenticated in production, open in development"

patterns-established:
  - "CSP exclusions via EXCLUDE_URL_PREFIXES for admin/docs paths"
  - "Conditional permission_classes pattern: schema_permission = [IsAuthenticated] if not settings.DEBUG else []"

requirements-completed: []

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 37 Plan 02: Security Headers & API Docs Summary

**django-csp with strict CSP for API responses, Referrer-Policy via SecurityMiddleware, frontend security headers in render.yaml, and authenticated API docs in production**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-25T18:31:35Z
- **Completed:** 2026-02-25T18:34:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Installed django-csp 4.0 and configured strict Content-Security-Policy for Django API production responses (default-src: 'none') with exclusions for admin and docs paths
- Set SECURE_REFERRER_POLICY to strict-origin-when-cross-origin in production settings
- Added CSP, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy headers to frontend static site in render.yaml
- Gated API schema/docs/redoc endpoints behind IsAuthenticated in production while keeping them open in development

## Task Commits

Each task was committed atomically:

1. **Task 1: Install django-csp and configure security headers for backend production** - `e99b9f5` (feat)
2. **Task 2: Restrict API docs to authenticated users and add frontend security headers** - `2897aa6` (feat)

## Files Created/Modified
- `requirements/base.txt` - Added django-csp>=4.0,<5.0 dependency
- `config/settings/prod.py` - CSPMiddleware in MIDDLEWARE, CONTENT_SECURITY_POLICY directives, SECURE_REFERRER_POLICY
- `config/api_urls.py` - Conditional IsAuthenticated permission on schema/docs/redoc views
- `render.yaml` - CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy headers on frontend static site

## Decisions Made
- **Strict CSP for API:** Used `default-src: 'none'` since Django serves JSON API responses, not HTML pages. This is the most restrictive possible CSP.
- **CSP exclusions:** Excluded `/admin`, `/api/v1/docs`, and `/api/v1/redoc` via `EXCLUDE_URL_PREFIXES` because Django admin and Swagger UI use inline styles/scripts that would be blocked by strict CSP.
- **No Permissions-Policy on Django API:** Permissions-Policy is a browser-enforced policy for HTML pages. Since Django serves JSON, it's set only on the frontend static site via render.yaml.
- **Frontend CSP allows unsafe-inline styles:** Required because shadcn/ui and Tailwind CSS inject inline styles. This is a necessary trade-off for SPA frameworks.
- **Specific backend URL in frontend CSP:** Used `https://donorcrm-web.onrender.com` in `connect-src` (from render.yaml env vars) rather than a wildcard.
- **Conditional API docs auth:** Used `settings.DEBUG` to conditionally apply `IsAuthenticated` -- keeps docs open for development, restricted in production.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Security headers are configured for both backend (Django) and frontend (Render static site)
- API docs are restricted in production
- Ready for Phase 37 Plan 03 (dependency scanning and security report)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 37-security-check*
*Completed: 2026-02-25*
