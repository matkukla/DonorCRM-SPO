# Phase 36: Full-Stack Audit - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Comprehensive audit of the entire DonorCRM codebase across 5 dimensions: security, performance, code quality, UI/UX, and API consistency. Fix issues as found, produce a summary report, and create a human testing checklist. This phase does NOT add new features — it hardens what exists.

</domain>

<decisions>
## Implementation Decisions

### Audit scope
- Full codebase — all Django apps and the entire React frontend, not just v2.0 code
- Fix all issues found inline (don't just report)
- For large/risky changes: Claude uses judgment — fix if safe, document if risky
- Produce a summary report at the end listing findings, fixes, and remaining items

### Known tech debt (fix first)
- Fix all 6 items from v2.0 milestone audit before broader review:
  1. IMP-05: ImportBatch duplicate status not persisted to DB
  2. UI-GIFT-03: Gift amount filter dollar/cents unit mismatch
  3. NeedsAttention.tsx `|| true` workaround
  4. MODEL-01-08 checkboxes unchecked in REQUIREMENTS.md
  5. useREImport missing `['prayers']` cache invalidation
  6. useREImport wrong cache key `['recurringGifts']` vs `['recurring-gifts']`

### Security audit
- OWASP top 10 review on all endpoints
- Permission scoping verified on every API view
- Input validation checked on all import parsers
- Not pen-test depth — focused on real attack surface

### Performance audit
- Full stack profiling: N+1 queries, missing indexes, select_related/prefetch_related gaps
- Frontend bundle size assessment and code splitting opportunities
- Caching strategy review
- API response time patterns and connection pooling

### Code quality
- Dead code removal (unused imports, functions, components)
- Inconsistent pattern unification (error handling, serializer style)
- Type safety gaps closed
- Add tests for critical untested paths (auth, imports, data integrity)

### UI/UX audit
- Dark mode coverage on ALL pages (not just v2.0)
- Basic accessibility: color contrast (4.5:1), keyboard nav on interactive elements, ARIA labels on icons/buttons
- Desktop only — no responsive/mobile testing
- Create structured human testing checklist for 19 pending manual verification items from phase verifications

### API consistency
- Full API review: error response formats, endpoint naming conventions, serializer field naming
- Pagination patterns, HTTP status codes, content types
- CORS headers review

### Claude's Discretion
- Prioritization order within each dimension (which files to audit first)
- How to split the audit into plans/tasks for parallel execution
- Whether to batch small fixes or commit each individually
- Test framework and assertion style for new tests

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the undiscussed areas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 36-full-stack-audit*
*Context gathered: 2026-02-24*
