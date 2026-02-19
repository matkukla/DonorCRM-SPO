# Phase 20: Security & Performance Fixes - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 7 known security vulnerabilities and performance bugs (QAL-01, QAL-02, QAL-05, QAL-06, QAL-07, QAL-08, QAL-09) before new features are built. This is a purely corrective phase — no new user-facing features, just making existing features secure and performant.

</domain>

<decisions>
## Implementation Decisions

### Permission scoping (QAL-01, QAL-02)
- Silent filter approach: non-admin users' querysets are scoped to their own data automatically — no 403 errors, no information leakage
- Admin users continue to see all data across all missionaries (unscoped querysets)
- Stage event cross-user access (QAL-02): Claude's discretion on whether to return validation error or silent "not found"

### File upload limits (QAL-06)
- Max file size: 10 MB
- Enforcement: both client-side (instant feedback) and server-side (safety net)
- Rejection UX: toast notification — "File too large (max 10 MB)"
- File type restriction: size only for now — type restrictions deferred to Smartsheet import phase (24-25)

### Route guards (QAL-08)
- Admin-only pages: Analytics dashboard AND Import Center
- Non-admin behavior: redirect to home page (not a permission denied page)
- Admin nav items: hidden entirely from non-admin sidebar (not grayed out)
- Direct URL access (bookmarked/shared admin links): redirect to home WITH a brief toast explaining they don't have access

### Dashboard side-effect (QAL-09)
- When to mark events as "seen": Claude's discretion based on current dashboard implementation
- Visual indicators for unseen events: Claude's discretion based on current UI

### Float arithmetic (QAL-07)
- Fix code to use Decimal for pledge monthly_equivalent calculations
- Run a data migration to recalculate all existing pledge values (fix + migration, not forward-only)

### N+1 queries (QAL-05)
- Just make it fast — fix with prefetch_related, get under 10 queries
- No user-facing loading state changes needed

### Claude's Discretion
- Stage event cross-user rejection pattern (validation error vs silent not-found)
- Dashboard "seen" marking mechanism (explicit action, separate POST, or auto-after-render)
- Whether unseen events need visual distinction in the dashboard UI
- Technical implementation of all query optimizations
- Exact toast message wording for route guard redirects

</decisions>

<specifics>
## Specific Ideas

- No special caution needed for missionaries — these are all bug fixes that should just work better
- File type restrictions deliberately deferred to Phase 24-25 (Smartsheet import)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-security-performance-fixes*
*Context gathered: 2026-02-17*
