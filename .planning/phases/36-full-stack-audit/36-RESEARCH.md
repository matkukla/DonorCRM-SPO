# Phase 36: Full-Stack Audit - Research

**Researched:** 2026-02-24
**Domain:** Full-stack code audit (security, performance, quality, UI/UX, API consistency)
**Confidence:** HIGH

## Summary

DonorCRM has accumulated significant code across 34 phases spanning milestones v1.0 through v2.0, with 12 Django apps, a React/Vite frontend, and ~97 executed plans. This phase is a hardening audit -- no new features, only finding and fixing issues across 5 dimensions: security, performance, code quality, UI/UX, and API consistency.

Two prior audit documents provide a strong starting point: the **EDGE_CASE_AUDIT.md** (2026-02-11, pre-v2.0) identified 16 issues ranked by risk, and the **v2.0-MILESTONE-AUDIT.md** (2026-02-23) found 6 specific tech debt items. Many edge case issues from the earlier audit have been addressed in v2.0 code (e.g., cross-user contact access in journals is now owner-scoped, CSV export sanitization exists via `sanitize_csv_value()`, file size limits are enforced, ErrorBoundary and ProtectedRoute with role guards exist). However, several items remain open and new patterns introduced in v2.0 need review.

**Primary recommendation:** Structure the audit as fix-first (6 known tech debt items), then systematic sweep by dimension (security, performance, quality, UI/UX, API), fixing issues inline as found. Produce a summary report and human testing checklist at the end.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Full codebase -- all Django apps and the entire React frontend, not just v2.0 code
- Fix all issues found inline (don't just report)
- For large/risky changes: Claude uses judgment -- fix if safe, document if risky
- Produce a summary report at the end listing findings, fixes, and remaining items
- Fix all 6 items from v2.0 milestone audit before broader review:
  1. IMP-05: ImportBatch duplicate status not persisted to DB
  2. UI-GIFT-03: Gift amount filter dollar/cents unit mismatch
  3. NeedsAttention.tsx `|| true` workaround
  4. MODEL-01-08 checkboxes unchecked in REQUIREMENTS.md
  5. useREImport missing `['prayers']` cache invalidation
  6. useREImport wrong cache key `['recurringGifts']` vs `['recurring-gifts']`
- OWASP top 10 review on all endpoints
- Permission scoping verified on every API view
- Input validation checked on all import parsers
- Not pen-test depth -- focused on real attack surface
- Full stack profiling: N+1 queries, missing indexes, select_related/prefetch_related gaps
- Frontend bundle size assessment and code splitting opportunities
- Dead code removal (unused imports, functions, components)
- Inconsistent pattern unification (error handling, serializer style)
- Type safety gaps closed
- Add tests for critical untested paths (auth, imports, data integrity)
- Dark mode coverage on ALL pages (not just v2.0)
- Basic accessibility: color contrast (4.5:1), keyboard nav on interactive elements, ARIA labels on icons/buttons
- Desktop only -- no responsive/mobile testing
- Create structured human testing checklist for 19 pending manual verification items
- Full API review: error response formats, endpoint naming conventions, serializer field naming
- Pagination patterns, HTTP status codes, content types
- CORS headers review

### Claude's Discretion
- Prioritization order within each dimension (which files to audit first)
- How to split the audit into plans/tasks for parallel execution
- Whether to batch small fixes or commit each individually
- Test framework and assertion style for new tests

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-01 | Full-stack audit covering security (OWASP top 10, auth, permission scoping), performance (N+1 queries, missing indexes, bundle size), code quality (dead code, type safety, inconsistent patterns), UI/UX (accessibility, dark mode, responsive), and API consistency across all v2.0 code paths | All 5 audit dimensions fully researched with specific findings per dimension below |
</phase_requirements>

## Standard Stack

### Core (Already In Place)
| Library | Version | Purpose | Audit Relevance |
|---------|---------|---------|-----------------|
| Django | 4.2.x | Backend framework | OWASP review, permission checks, query optimization |
| DRF | 3.14.x | REST API | Permission classes, serializer consistency, error formats |
| django-filter | 24.3 | Filtering | Filter field correctness (e.g., amount_cents bug) |
| React | 19.x | Frontend | Component audit, error boundaries, accessibility |
| TanStack Query | 5.x | Data fetching | Cache key consistency, stale time, invalidation |
| Tailwind CSS | 3.4.x | Styling | Dark mode class coverage |
| Vite | 7.x | Build tool | Bundle analysis, code splitting |
| pytest | 7.4.x | Testing | Test coverage, new tests for critical paths |

### Audit-Specific Tools (No Installation Needed)
| Tool | Purpose | How to Use |
|------|---------|------------|
| `django.test.utils.override_settings` | Test security settings | Already in test infrastructure |
| `vite build --report` / `npx vite-bundle-visualizer` | Bundle analysis | Run during frontend audit |
| Django `assertNumQueries` | N+1 detection | Use in new performance tests |
| Browser DevTools | Dark mode, a11y inspection | For human testing checklist items |

## Architecture Patterns

### Audit Organization Pattern
```
Phase 36 Audit Structure:
Wave 0: Fix 6 known tech debt items from v2.0 milestone audit
Wave 1: Security audit (OWASP, permissions, input validation)
Wave 2: Performance audit (queries, indexes, bundle)
Wave 3: Code quality audit (dead code, patterns, types, tests)
Wave 4: UI/UX audit (dark mode, accessibility)
Wave 5: API consistency audit (error formats, naming, pagination)
Wave 6: Summary report + human testing checklist
```

### Permission Scoping Pattern (Existing)
Every view in the codebase follows one of these patterns:
```python
# Pattern 1: Queryset-level scoping (most views)
def get_queryset(self):
    if user.role in ['admin', 'finance', 'read_only']:
        return Model.objects.all()
    return Model.objects.filter(owner=user)

# Pattern 2: Object-level permission class
permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

# Pattern 3: Mixed (queryset + permission class)
permission_classes = [IsAuthenticated, IsContactOwnerOrReadAccess]
# Plus queryset scoping in get_queryset()
```

### Error Response Pattern (Inconsistent -- needs unification)
```python
# Pattern A: DRF exception (automatic format)
raise ValidationError({'field': 'error'})  # -> {"field": ["error"]}

# Pattern B: Manual Response with 'detail'
Response({'detail': 'Not found.'}, status=404)

# Pattern C: Manual Response with 'error'
Response({'error': 'Invalid format.'}, status=400)
```

### Anti-Patterns to Avoid During Audit
- **Overly aggressive fixes**: Don't refactor working code for style preferences. Fix actual bugs and consistency issues.
- **Breaking API contracts**: Don't rename response fields that the frontend depends on. Add, don't replace.
- **Silently changing behavior**: Every fix should be documented in the summary report with before/after.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bundle analysis | Custom scripts | `npx vite-bundle-visualizer` | Standard tool, visual output |
| N+1 query detection | Manual log reading | `assertNumQueries` in tests + Django Debug Toolbar | Reliable, reproducible |
| Accessibility testing | Manual color checks | Browser DevTools Lighthouse audit | Standard, covers WCAG |
| Dead code detection | Manual search | TypeScript compiler strict mode + ESLint unused imports | Catches import-level issues |

## Common Pitfalls

### Pitfall 1: Fixing Edge Case Audit Items That Were Already Fixed
**What goes wrong:** The EDGE_CASE_AUDIT.md (2026-02-11) predates v2.0 code. Many items were addressed during phases 27-34.
**Why it happens:** Audit doc references old file paths (e.g., `pledges/models.py`, `donations/views.py`) that no longer exist.
**How to avoid:** Cross-reference each edge case item against current code before attempting fixes. The following items from EDGE_CASE_AUDIT.md have been addressed:
- 1.3 (Cross-user contact access in journals): Fixed in serializers.py line 231 -- now checks `owner=user`
- 1.5 (`is_staff` vs `role`): Check if `admin_summary` now uses `IsAdmin` permission class -- YES, it uses `permission_classes=[IsAuthenticated, IsAdmin]`
- 3.1 (Float money arithmetic): RecurringGift.monthly_equivalent now uses Decimal throughout (gifts/models.py lines 303-316)
- 5.1 (Dashboard GET side effect): Fixed -- `MarkEventsSeenView` is a separate POST endpoint (dashboard/views.py lines 37-47)
- 6.1 (CSV file size limit): Fixed -- `MAX_UPLOAD_SIZE = 10 * 1024 * 1024` and `DATA_UPLOAD_MAX_MEMORY_SIZE` in settings
- 6.3 (CSV export sanitization): Fixed -- `sanitize_csv_value()` exists and is used in all export views
- 7.2 (Frontend route guards): Partially fixed -- `ProtectedRoute` with `requiredRole` exists but only applied to admin routes, not write routes
- 7.3 (Error Boundary): Fixed -- `ErrorBoundary` from `react-error-boundary` wraps the app
**Warning signs:** If you see file paths referencing `donations/` or `pledges/` apps, those have been removed (replaced by `gifts/`).

### Pitfall 2: Breaking StreamingHttpResponse with Exceptions
**What goes wrong:** StreamingHttpResponse generators silently swallow exceptions after headers are sent.
**Why it happens:** Once streaming starts, Python can't send a new HTTP status code.
**How to avoid:** Ensure all data validation happens before the streaming generator starts. This is already correct in the codebase but should be verified during the audit.

### Pitfall 3: Unvalidated int() Casts on Query Parameters
**What goes wrong:** `int(request.query_params.get('days', 30))` raises ValueError for non-numeric input, causing 500 errors.
**Where it occurs:** Multiple locations:
- `apps/dashboard/views.py` lines 104, 163, 164, 219 (LateDonationsView, RecentGiftsView, MonthlyGiftsView)
- `apps/insights/views.py` lines 89, 118, 136, 171, 172 (DonationsByYearView, LateDonationsView, FollowUpsView, TransactionsView)
- `apps/tasks/views.py` line 123 (UpcomingTasksView)
**How to avoid:** Use the `get_safe_int_param()` pattern already present in `apps/insights/views.py` line 47-53. Apply it everywhere.

### Pitfall 4: Cache Key Mismatches After Query Invalidation
**What goes wrong:** `useREImport.onSuccess` invalidates `['recurringGifts']` but `useGifts.ts` uses `['recurring-gifts']`. Stale data remains.
**Why it happens:** No single source of truth for query key constants. Each hook defines its own strings.
**How to avoid:** During audit, create a query key constants file or verify all invalidation calls match their corresponding query hooks.

## Code Examples

### Known Tech Debt Fix 1: ImportBatch Duplicate Status Persistence
```python
# File: apps/imports/re_services.py (lines 223-224, 605-606, 1086-1087, 1476-1477)
# BEFORE:
existing.status = ImportBatchStatus.DUPLICATE
return existing

# AFTER:
existing.status = ImportBatchStatus.DUPLICATE
existing.save(update_fields=['status'])
return existing
```

### Known Tech Debt Fix 2: Gift Amount Filter Dollar/Cents Conversion
```python
# File: apps/gifts/filters.py (lines 15-16)
# BEFORE:
min_amount = django_filters.NumberFilter(field_name='amount_cents', lookup_expr='gte')
max_amount = django_filters.NumberFilter(field_name='amount_cents', lookup_expr='lte')

# AFTER: Use method filter to multiply by 100
min_amount = django_filters.NumberFilter(method='filter_min_amount')
max_amount = django_filters.NumberFilter(method='filter_max_amount')

def filter_min_amount(self, queryset, name, value):
    return queryset.filter(amount_cents__gte=int(value * 100))

def filter_max_amount(self, queryset, name, value):
    return queryset.filter(amount_cents__lte=int(value * 100))
```

### Known Tech Debt Fix 3: NeedsAttention || true Workaround
```typescript
// File: frontend/src/components/dashboard/NeedsAttention.tsx (line 36)
// BEFORE:
const hasItems = overdueTaskCount > 0 || thankYouCount > 0 || true /* always show late pledges placeholder */

// AFTER: Remove workaround, show based on actual conditions or remove the late pledges section
const hasItems = overdueTaskCount > 0 || thankYouCount > 0
```

### Known Tech Debt Fix 4: useREImport Cache Invalidation
```typescript
// File: frontend/src/hooks/useImports.ts (lines 89-96)
// BEFORE:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['importBatches'] })
  queryClient.invalidateQueries({ queryKey: ['contacts'] })
  queryClient.invalidateQueries({ queryKey: ['gifts'] })
  queryClient.invalidateQueries({ queryKey: ['recurringGifts'] })  // WRONG key
  // MISSING: prayers invalidation
},

// AFTER:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['importBatches'] })
  queryClient.invalidateQueries({ queryKey: ['contacts'] })
  queryClient.invalidateQueries({ queryKey: ['gifts'] })
  queryClient.invalidateQueries({ queryKey: ['recurring-gifts'] })  // FIXED key
  queryClient.invalidateQueries({ queryKey: ['prayers'] })  // ADDED
  queryClient.invalidateQueries({ queryKey: ['dashboard'] })
},
```

### Safe int() Parameter Parsing Pattern
```python
# Already exists in apps/insights/views.py -- apply everywhere
def get_safe_int_param(request, key, default, min_val=1, max_val=1000):
    """Safely parse integer query parameter with bounds."""
    try:
        value = int(request.query_params.get(key, default))
    except (ValueError, TypeError):
        return default
    return max(min_val, min(value, max_val))
```

## Detailed Findings by Audit Dimension

### 1. Security Findings

**Permission scoping status (all views checked):**

| App | View | Permission | Queryset Scoped | Status |
|-----|------|-----------|-----------------|--------|
| contacts | ContactListCreateView | IsStaffOrAbove | Yes (owner filter) | OK |
| contacts | ContactDetailView | IsContactOwnerOrReadAccess | Yes | OK |
| contacts | ContactGiftsView | IsContactOwnerOrReadAccess | Yes | OK |
| contacts | ContactRecurringGiftsView | IsContactOwnerOrReadAccess | Yes | OK |
| contacts | ContactTasksView | IsAuthenticated | Yes (owner filter) | OK |
| contacts | ContactEmailsView | IsAuthenticated | Yes (owner filter) | OK |
| contacts | ContactSearchView | IsAuthenticated | Yes (owner filter) | OK |
| contacts | ContactJournalsView | IsContactOwnerOrReadAccess | Yes | OK |
| contacts | ContactPrayerIntentionsView | IsContactOwnerOrReadAccess | Yes | OK |
| contacts | ContactJournalEventsView | IsContactOwnerOrReadAccess | Yes | OK |
| gifts | GiftListCreateView | IsAuthenticated | Yes (owner filter) | OK |
| gifts | GiftDetailView | IsAuthenticated | Yes (owner filter) | OK |
| gifts | RecurringGiftListCreateView | IsAuthenticated | Yes | OK |
| gifts | RecurringGiftDetailView | IsAuthenticated | Yes | OK |
| prayers | All views | IsAuthenticated | Yes (via _owner_scoped_queryset) | OK |
| journals | All views | IsAuthenticated/IsOwnerOrAdmin | Yes (journal__owner filter) | OK |
| tasks | All views | IsAuthenticated/IsOwnerOrAdmin | Yes (owner filter) | OK |
| events | All views | IsAuthenticated | Yes (user filter) | OK |
| groups | All views | IsAuthenticated/IsOwnerOrAdmin | Yes | OK |
| imports | RE import views | IsAdmin | N/A (admin only) | OK |
| imports | Legacy imports | IsAdmin/IsFinanceOrAdmin | N/A | OK |
| dashboard | All views | IsAuthenticated | Yes (user-scoped services) | OK |
| insights | Admin views | IsAdmin | N/A (admin only) | OK |
| users | Admin views | IsAdmin | N/A | OK |

**Remaining security items to verify:**
1. **Unvalidated int() casts** -- 11 instances across dashboard/views.py, insights/views.py, tasks/views.py cause 500 on malformed input
2. **Import parser input validation** -- RE services handle encoding detection but need review for edge cases (malformed CSV, extremely long values, null bytes)
3. **CORS configuration** -- Only explicit origins allowed (good), but verify production values are correct
4. **JWT token handling** -- Token refresh race condition across browser tabs (per-page `isRefreshing` flag). Low severity since single-user app.
5. **Rate limiting** -- No rate limiting on auth endpoints. Low risk for small deployment but should be noted.

### 2. Performance Findings

**N+1 Query Risks (current codebase):**
1. **Journal grid** -- Already fixed with `prefetch_related` in `JournalContactListCreateView.get_queryset()` (lines 203-216)
2. **Dashboard `get_support_progress()`** -- Loads all active RecurringGifts into Python to sum `monthly_equivalent` (line 120: `sum(rg.monthly_equivalent for rg in active_recurring)`). Should use SQL aggregation with CASE/WHEN for frequency multipliers.
3. **Dashboard `get_giving_summary()`** -- Same pattern: loads active RecurringGifts into Python (line 200)
4. **MPDOverviewView** -- Queries MPDSnapshot per user in a loop (lines 697-712). Should use a single query with `Distinct` on user.
5. **Journal analytics `pipeline_breakdown`** -- Uses Subquery for latest stage per JournalContact, which is fine for small datasets but could benefit from a materialized current_stage field at scale.

**Missing Indexes (to verify):**
- Gift model has good indexes: `(donor_contact, gift_date)`, `(gift_date,)`, `(external_gift_id,)`
- RecurringGift has: `(donor_contact, status)`, `(status, -created_at)`
- Contact model: verify index on `needs_thank_you` (used in dashboard queries)
- PrayerIntention: verify index on `status` (used in filtered queries)

**Frontend Bundle:**
- No code splitting configured in `vite.config.ts` (bare minimum config)
- Large dependencies: recharts, @dnd-kit, @tanstack/react-table, react-day-picker
- All pages loaded eagerly via direct imports in App.tsx (no React.lazy)
- Recommend: Add `React.lazy()` for heavy pages (JournalDetail, ImportExport, AdminAnalytics, PrayerList)
- Recommend: Run `npx vite-bundle-visualizer` to identify actual chunk sizes

### 3. Code Quality Findings

**Dead code candidates:**
- `apps/imports/services.py` -- Contains `export_contacts_csv()` and `export_gifts_csv()` functions that may be superseded by the new `export_views.py` files in contacts and gifts apps
- `apps/imports/tasks.py` -- `import_contacts_async` references Celery which is disabled. The function exists but is dormant.
- `apps/core/exceptions.py` -- `PledgeFulfillmentError` references removed Pledge model
- Legacy shim files: `frontend/src/api/donations.ts`, `frontend/src/api/pledges.ts`, `frontend/src/hooks/useDonations.ts`, `frontend/src/hooks/usePledges.ts` -- check if these are still re-export shims or dead code

**Inconsistent patterns:**
1. **Error response format**: Some views use `{'detail': '...'}`, others use `{'error': '...'}`. DRF's default uses `{'detail': '...'}`.
2. **Serializer definition location**: `FundListSerializer` is defined inline in `imports/views.py` instead of in a serializers module. `ImportBatchListView` hand-builds dicts instead of using a serializer.
3. **Admin role checking**: Most views check `user.role == 'admin'`, but journal analytics `admin_summary` uses `IsAdmin` permission class (correct). All are consistent now.
4. **Owner scoping logic**: Some views check `user.role not in ['admin', 'finance', 'read_only']`, others check `user.role == 'admin'` or `user.role != 'admin'`. The finance/read_only visibility rules are inconsistent across apps.

**Type safety:**
- Backend: Python type hints are sparse. Not a priority for this audit but could be noted.
- Frontend: TypeScript is well-used. Main gaps are `unknown` types in some API response interfaces (e.g., `[key: string]: unknown` in REImportResponse).

**Test coverage gaps (critical paths without tests):**
- `apps/gifts/` -- No test files found (tests/__init__.py and factories.py exist but no test_*.py)
- `apps/prayers/` -- No test directory
- `apps/imports/re_services.py` -- No tests for the 4 RE import functions (most complex code in the project)
- `apps/dashboard/services.py` -- `test_services.py` exists but only as a pyc cache artifact, no source
- Permission scoping tests -- No tests verify that staff users can't see other users' data

### 4. UI/UX Findings

**Dark mode:**
- ThemeProvider correctly toggles `dark` class on `<html>` element
- Uses Tailwind's `dark:` variant system (standard approach)
- Need to audit: all pages for missing `dark:` prefixes, especially on:
  - Prayer focus mode (custom chapel-style amber styling)
  - Import result banners
  - Admin analytics pages (charts, heatmaps)
  - Styleguide page
  - Form inputs and placeholders

**Accessibility:**
- WCAG 4.5:1 contrast ratio needs verification across color themes
- Keyboard navigation: `@dnd-kit` provides keyboard support for drag-and-drop
- ARIA labels: Need audit on icon-only buttons (sidebar, toolbar, action buttons)
- Focus management: Dialog components use Radix UI which handles focus trapping
- Screen reader: Table components need `aria-label` and `scope` attributes

**Route guards:**
- `ProtectedRoute` with `requiredRole` exists and works for admin routes
- Write operations (create/edit forms) are NOT guarded -- `read_only` users can navigate to `/contacts/new`, `/donations/new`, etc. and fill out forms before getting a 403 on submit
- Import/export page (`/import-export`) has no role guard but individual API endpoints are admin-only

### 5. API Consistency Findings

**Error response formats (inconsistent):**
| Pattern | Usage | Count |
|---------|-------|-------|
| `{'detail': '...'}` | DRF convention, most views | ~30+ |
| `{'error': '...'}` | Insights views | ~8 |
| DRF auto-format `{'field': ['error']}` | Serializer validation | All serializers |

**Endpoint naming:**
- Mostly consistent REST convention: `/api/v1/{resource}/` for list, `/api/v1/{resource}/{id}/` for detail
- Backward compatibility aliases: `/donations/` -> gifts, `/pledges/` -> gifts (correct)
- RE import endpoints: `/imports/re/constituents/`, `/imports/re/solicitors/`, etc. (consistent)
- Action endpoints: Inconsistent -- some use sub-paths (`/contacts/{id}/thank/`), some use separate resources (`/events/{id}/mark-read/`)

**Pagination:**
- StandardPagination (25 per page) applied globally via DRF settings
- Some views override with `pagination_class = None` (FundListView, ContactJournalsView, TodaysFocusView)
- Consistent `PageNumberPagination` usage throughout

**HTTP status codes:**
- Mostly correct. 201 for creates, 204 for deletes, 400 for validation, 404 for not found
- 410 Gone correctly used for removed legacy endpoints
- Dashboard `GivingSummaryView` does `int(year)` without try/except -- could 500

**Content types:**
- JSON renderer only in DRF settings (good -- no browser API exposure)
- CSV exports use `StreamingHttpResponse` with `text/csv` (correct)

## Open Questions

1. **Frontend bundle size baseline**
   - What we know: No code splitting, eager loading of all pages, large deps (recharts, dnd-kit)
   - What's unclear: Actual bundle size. Is it a problem or acceptable for a small internal app?
   - Recommendation: Run `npx vite-bundle-visualizer` during audit. Add lazy loading only if bundle > 500KB gzipped.

2. **Test coverage target**
   - What we know: pytest config targets 80% via `--cov-fail-under=80`. Unknown if this currently passes.
   - What's unclear: Current actual coverage percentage. Which critical paths are untested.
   - Recommendation: Run `pytest --cov=apps` to get baseline before adding tests. Prioritize permission scoping and import pipeline tests.

3. **Contact `needs_thank_you` index**
   - What we know: Dashboard queries filter on this field. No explicit index seen in model.
   - What's unclear: Whether Django auto-creates an index for BooleanField or if this is a query plan issue.
   - Recommendation: Check with `EXPLAIN ANALYZE` during performance audit. Add index if sequential scan detected.

4. **Legacy shim files**
   - What we know: `donations.ts`, `pledges.ts`, `useDonations.ts`, `usePledges.ts` kept as compatibility layers per Phase 31 decisions
   - What's unclear: Whether any code still imports from these shims or if they're fully dead
   - Recommendation: Check import references during code quality audit. Remove if unused.

## Edge Case Audit Cross-Reference

Items from EDGE_CASE_AUDIT.md (2026-02-11) status in current codebase:

| # | Issue | Status | Evidence |
|---|-------|--------|----------|
| 1.1 | Journal grid N+1 | FIXED | `JournalContactListCreateView` has `prefetch_related` (journals/views.py:203-216) |
| 1.2 | Decision update race | OPEN | No `select_for_update()` in `DecisionSerializer.update()` -- low priority for single-user |
| 1.3 | Cross-user contact in journals | FIXED | `Contact.objects.get(id=contact_id, owner=user)` (journals/serializers.py:231) |
| 1.4 | Analytics unbounded data | OPEN | Journal analytics still return full result sets. Low priority. |
| 1.5 | `is_staff` vs `role` | FIXED | `admin_summary` now uses `IsAdmin` permission class (journals/views.py:551-552) |
| 2.1 | update_giving_stats() race | N/A | Donations model replaced by Gift. Gift signals may have same pattern -- check. |
| 2.2 | ListAPIView permission bypass | FIXED | Contact sub-resource views now have queryset-level owner scoping |
| 3.1 | Float money arithmetic | FIXED | RecurringGift.monthly_equivalent uses Decimal (gifts/models.py:303-316) |
| 3.2 | record_fulfillment() race | N/A | Pledge model removed. RecurringGift has no fulfillment tracking. |
| 3.3 | Stats not updated on edit | CHECK | Gift model uses signals -- verify signal handles both create and update |
| 3.4 | Unvalidated int() casts | OPEN | Still present in dashboard/views.py and tasks/views.py |
| 5.1 | Dashboard GET side effect | FIXED | MarkEventsSeenView is separate POST endpoint |
| 5.2 | Dashboard redundant queries | OPEN | `get_support_progress()` and `get_giving_summary()` load all RecurringGifts into Python |
| 6.1 | CSV file size limit | FIXED | MAX_UPLOAD_SIZE enforced in all import views |
| 6.2 | Async import skips signals | DORMANT | Celery disabled, function exists but unused |
| 6.3 | CSV export sanitization | FIXED | `sanitize_csv_value()` used in all export views |
| 7.1 | Multi-tab token refresh | OPEN | Per-page `isRefreshing` flag. Low priority. |
| 7.2 | Frontend route guards | PARTIAL | ProtectedRoute exists but write routes not guarded for read_only users |
| 7.3 | Error Boundary | FIXED | `react-error-boundary` wraps app root |
| 7.4 | Double-submit mutations | CHECK | Need per-component audit of mutation buttons |

## Recommended Plan Structure

### Wave 0: Known Tech Debt (1 plan, ~6 tasks)
Fix the 6 items from v2.0 milestone audit. These are small, well-defined fixes.

### Wave 1: Security Audit (1 plan, ~4-5 tasks)
1. Fix all unvalidated `int()` casts (apply `get_safe_int_param` pattern)
2. Verify Gift signal handles updates (not just creates)
3. Add write-route guards to ProtectedRoute for read_only users
4. Review import parser edge cases (malformed CSV, null bytes, oversized values)
5. CORS and rate limiting review (document findings)

### Wave 2: Performance Audit (1 plan, ~4 tasks)
1. Fix `get_support_progress()` and `get_giving_summary()` to use SQL aggregation
2. Fix MPDOverviewView N+1 query
3. Frontend bundle analysis and lazy loading for heavy routes
4. Check for missing database indexes (needs_thank_you, prayer status)

### Wave 3: Code Quality (1 plan, ~5 tasks)
1. Remove dead code (PledgeFulfillmentError, dormant Celery imports, unused shims)
2. Unify error response format to `{'detail': '...'}` everywhere
3. Move inline serializers to proper modules
4. Add critical tests (permission scoping, RE import pipeline, gift signals)
5. Clean up type safety gaps in frontend

### Wave 4: UI/UX Audit (1 plan, ~3 tasks)
1. Dark mode sweep across all pages (identify missing `dark:` prefixes)
2. Accessibility pass (ARIA labels, keyboard nav, contrast)
3. Compile human testing checklist from all phase verifications

### Wave 5: API Consistency + Report (1 plan, ~3 tasks)
1. Standardize error response formats
2. Review and document API naming conventions
3. Write final audit summary report

**Total: ~5-6 plans, ~25-30 tasks**

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all Django app views, models, serializers, and frontend components
- `.planning/v2.0-MILESTONE-AUDIT.md` -- authoritative source for 6 known tech debt items
- `.planning/EDGE_CASE_AUDIT.md` -- comprehensive prior audit with 16 ranked issues

### Secondary (MEDIUM confidence)
- Django 4.2 documentation for permission class behavior (ListAPIView + object permissions)
- DRF documentation for error response format conventions

## Metadata

**Confidence breakdown:**
- Known tech debt: HIGH -- items are precisely documented with file locations and line numbers
- Security: HIGH -- all views inspected, permission patterns verified
- Performance: HIGH -- query patterns identified through direct code inspection
- Code quality: HIGH -- dead code and inconsistencies found through systematic search
- UI/UX: MEDIUM -- dark mode and accessibility need live browser verification, not just code review
- API consistency: HIGH -- all endpoints inspected for response format patterns

**Research date:** 2026-02-24
**Valid until:** Indefinite (audit of existing codebase, not dependent on external libraries)
