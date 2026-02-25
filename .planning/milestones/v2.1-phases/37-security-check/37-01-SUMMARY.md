---
phase: 37-security-check
plan: 01
subsystem: auth
tags: [jwt, rate-limiting, throttling, password-validation, refresh-tokens, drf]

# Dependency graph
requires:
  - phase: 36-full-stack-audit
    provides: "Security audit findings identifying auth gaps"
provides:
  - "DRF ScopedRateThrottle on auth endpoints (5/min production, 100/min dev)"
  - "AlphanumericPasswordValidator requiring letters and numbers"
  - "Fixed refresh token rotation storing both access and refresh tokens"
affects: [37-security-check]

# Tech tracking
tech-stack:
  added: []
  patterns: ["ScopedRateThrottle with throttle_scope on view subclasses", "Custom Django password validator pattern"]

key-files:
  created:
    - "apps/core/validators.py"
    - "apps/core/tests/__init__.py"
    - "apps/core/tests/test_validators.py"
  modified:
    - "apps/users/urls_auth.py"
    - "config/settings/base.py"
    - "config/settings/dev.py"
    - "frontend/src/api/client.ts"

key-decisions:
  - "Used ScopedRateThrottle (not AnonRateThrottle) for per-endpoint control"
  - "Set 100/min dev override to prevent throttling during development"

patterns-established:
  - "Throttled view subclasses: create subclass with throttle_scope, wire in urls"
  - "Custom validators: apps/core/validators.py with tests in apps/core/tests/"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 37 Plan 01: Auth Hardening Summary

**DRF rate limiting on auth endpoints, AlphanumericPasswordValidator with tests, and fixed refresh token rotation in frontend interceptor**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T18:31:34Z
- **Completed:** 2026-02-25T18:33:51Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Auth endpoints (login, refresh) rate-limited to 5 requests/min via ScopedRateThrottle
- Custom AlphanumericPasswordValidator ensures passwords contain both letters and numbers
- Frontend refresh token interceptor now stores both access and refresh tokens, fixing broken rotation
- Dev settings override throttle rates to 100/min for development comfort
- 5 unit tests for password validator all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add auth endpoint rate limiting and custom password validator** - `f11e517` (feat)
2. **Task 2: Fix frontend refresh token rotation bug** - `98a646b` (fix)

**Plan metadata:** `02a592c` (docs: complete plan)

## Files Created/Modified
- `apps/core/validators.py` - AlphanumericPasswordValidator requiring letters and numbers
- `apps/core/tests/__init__.py` - Test package init
- `apps/core/tests/test_validators.py` - 5 unit tests for password validator
- `apps/users/urls_auth.py` - ThrottledTokenObtainPairView and ThrottledTokenRefreshView subclasses
- `config/settings/base.py` - DRF throttle config and custom password validator registration
- `config/settings/dev.py` - Permissive throttle rate override for development
- `frontend/src/api/client.ts` - Fixed refresh token storage in interceptor

## Decisions Made
- Used ScopedRateThrottle (not AnonRateThrottle) for granular per-endpoint control via throttle_scope
- Set 100/min dev override to prevent throttling from interfering during local development
- Placed throttled view subclasses directly in urls_auth.py (co-located with URL patterns) rather than a separate views file

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Auth hardening complete, ready for Plan 02 (security headers and API docs restriction)
- Rate limiting, password policy, and refresh token rotation all functional

## Self-Check: PASSED

- All 4 created files verified on disk
- Both task commits (f11e517, 98a646b) verified in git log

---
*Phase: 37-security-check*
*Completed: 2026-02-25*
