# Phase 37: Full Security Check - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Comprehensive security audit and hardening of the DonorCRM application, focusing on gaps not covered by Phase 36's full-stack audit. Phase 36 handled basic security items (safe param parsing, write route guards, import parser hardening). This phase goes deeper into auth, sessions, secrets, infrastructure, dependencies, and file uploads. Fixes issues as they're found and produces a final security report.

</domain>

<decisions>
## Implementation Decisions

### Audit scope & depth
- Gap-fill approach from Phase 36 — focus on what Phase 36 missed, not a full re-audit
- Automated scanning (bandit for Python, npm audit for JS, safety check) PLUS manual code review for logic flaws
- Include infrastructure/deployment security (render.yaml, CORS, security headers, env var hygiene)
- Dependency audit: fix known CVEs AND flag significantly outdated packages that may have unpatched issues

### Findings handling
- Fix issues as they're discovered — no separate discovery phase before fixes
- Produce a final SECURITY-REPORT.md summarizing what was checked, findings, and resolutions
- Each finding gets a severity rating: Critical / High / Medium / Low
- Defer large refactors (e.g., switching auth libraries) to future phases — only fix issues that don't require major architecture changes

### Auth & session hardening
- Add refresh token rotation: new refresh token issued on each use, old one invalidated
- Add rate limiting on authentication endpoints (login, token refresh) — e.g., 5 failed attempts per minute per IP
- Add basic password policy: minimum 8 characters, at least 1 number and 1 letter
- Tighten token expiry: access token 15 minutes, refresh token 7 days

### Data protection
- Database-level encryption only (Render provides disk encryption at rest) — no app-level field encryption
- Audit + harden secrets management: verify no secrets in code/git, ensure Render env vars properly scoped, check for leaked keys
- Full file upload security review: all upload endpoints (CSV, XLSX, Smartsheet) checked for path traversal, type spoofing, malicious content
- Add security headers: Content-Security-Policy, HSTS, X-Content-Type-Options, X-Frame-Options via Django SecurityMiddleware

### Claude's Discretion
- Specific rate limiting thresholds and implementation (django-ratelimit vs DRF throttling)
- CSP policy details (which directives, how strict)
- Whether to add CSRF cookie settings or rely on DRF's token auth exemption
- Bandit/safety configuration and which warnings to suppress

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow OWASP guidelines and Django security best practices.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 37-security-check*
*Context gathered: 2026-02-25*
