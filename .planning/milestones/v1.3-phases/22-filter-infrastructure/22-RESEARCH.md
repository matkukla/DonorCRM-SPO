# Phase 22: Filter Infrastructure - Research

**Researched:** 2026-02-17
**Domain:** Django REST Framework filtering with django-filter + React URL state management
**Confidence:** HIGH

## Summary

Phase 22 builds a reusable, server-side filter system across all list pages (Contacts, Donations, Pledges, Tasks) with URL persistence, filter presets, active filter badges, clear-all functionality, and filtered CSV export. The codebase already has partial filtering -- every list view uses `DjangoFilterBackend` with `filterset_fields` for basic exact-match filters, and every frontend list page reads/writes `useSearchParams` for URL state. The gap is: (1) no date range filters on the backend, (2) each frontend page hand-rolls its own filter state logic with no shared abstraction, (3) no filter presets, (4) no "clear all" button, (5) no active filter summary badges, (6) no filtered CSV export on list pages, and (7) the Transactions page stores filters in React state (`useState`) instead of URL params (the FLT-08 bug).

The approach is to upgrade django-filter from 23.5 to 24.3 (pinned, NOT 25.2), create custom `FilterSet` classes per model, build a reusable `useFilterParams` hook + `FilterBar` component on the frontend, and add CSV export endpoints that reuse the same filtered querysets.

**Primary recommendation:** Upgrade django-filter to 24.3, replace `filterset_fields` with explicit `FilterSet` classes on all list views, build a shared `useFilterParams` hook using `nuqs` for type-safe URL state, create a reusable `<FilterBar>` component, and add `/export/csv/` endpoints per resource that apply the same filters.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| django-filter | 24.3 (pinned) | Server-side queryset filtering with DRF integration | Already installed (23.5), needs upgrade; NOT 25.2 which requires Django 5.2+ |
| djangorestframework | 3.14.0 | REST API framework (existing) | Already in stack, provides filter_backends infrastructure |
| nuqs | latest (2.x) | Type-safe URL search params state management for React | Replaces manual useSearchParams boilerplate; has React Router v6 adapter |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | 4.1.0 (existing) | Date range preset calculations | Already installed; used in `lib/date-presets.ts` |
| react-router-dom | 6.30.3 (existing) | URL routing with search params | Already in stack; nuqs wraps it via adapter |
| @tanstack/react-query | 5.90.17 (existing) | Data fetching with filter-aware cache keys | Already in stack; filter objects become query keys |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nuqs | Manual useSearchParams | nuqs adds ~5KB but eliminates 200+ lines of boilerplate across 5 pages; type-safe parsers prevent bugs |
| Custom FilterSet classes | `filterset_fields` (current) | Custom classes needed for date ranges, choice labels, and owner-scoped filters; `filterset_fields` only does exact match |
| StreamingHttpResponse for CSV | In-memory StringIO (current) | Streaming needed for large datasets (>1000 rows); small exports can stay in-memory |

**Installation:**
```bash
# Backend
pip install 'django-filter==24.3'

# Frontend
cd frontend && npm install nuqs
```

## Architecture Patterns

### Backend: Custom FilterSet per Model

Currently all views use `filterset_fields = ['status', 'thanked']` which only supports exact-match filtering. Phase 22 replaces these with explicit `FilterSet` classes that support date ranges, multiple choice values, and owner-scoped filters.

**Pattern:**
```python
# apps/donations/filters.py
import django_filters
from apps.donations.models import Donation

class DonationFilterSet(django_filters.FilterSet):
    """Reusable filter for donations list."""
    date_after = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    donation_type = django_filters.CharFilter(field_name='donation_type')
    payment_method = django_filters.CharFilter(field_name='payment_method')
    thanked = django_filters.BooleanFilter(field_name='thanked')

    class Meta:
        model = Donation
        fields = ['donation_type', 'payment_method', 'thanked', 'date_after', 'date_before']
```

Then in the view:
```python
class DonationListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DonationFilterSet  # replaces filterset_fields
```

### Backend: CSV Export Endpoint Pattern

Add export endpoints that reuse the same `FilterSet` + queryset logic:

```python
# apps/donations/views.py
class DonationExportCSVView(APIView):
    """GET: Export filtered donations as CSV."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Reuse the same queryset logic from list view
        user = request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)

        # Apply filters using the same FilterSet
        filterset = DonationFilterSet(request.query_params, queryset=queryset)
        queryset = filterset.qs.select_related('contact', 'pledge')

        # Stream CSV
        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            yield writer.writerow(['Date', 'Contact', 'Amount', ...])
            for donation in queryset:
                yield writer.writerow([...])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="donations_{date}.csv"'
        return response
```

### Frontend: nuqs Adapter Setup

Wrap `BrowserRouter` with `NuqsAdapter`:

```typescript
// App.tsx
import { NuqsAdapter } from 'nuqs/adapters/react-router/v6'

function App() {
  return (
    <ThemeProvider>
      <NuqsAdapter>
        <BrowserRouter>
          {/* ... routes ... */}
        </BrowserRouter>
      </NuqsAdapter>
    </ThemeProvider>
  )
}
```

### Frontend: Shared useFilterParams Hook

```typescript
// hooks/useFilterParams.ts
import { useQueryStates, parseAsString, parseAsInteger, parseAsBoolean } from 'nuqs'

export function useFilterParams<T extends Record<string, unknown>>(
  parsers: Record<string, ReturnType<typeof parseAsString>>,
) {
  const [filters, setFilters] = useQueryStates(parsers, {
    shallow: false, // trigger React Query refetch
  })

  const clearAll = () => {
    const cleared = Object.fromEntries(
      Object.keys(parsers).map(key => [key, null])
    )
    setFilters(cleared)
  }

  const activeFilters = Object.entries(filters).filter(
    ([key, value]) => value !== null && key !== 'page'
  )

  return { filters, setFilters, clearAll, activeFilters }
}
```

### Frontend: FilterBar Component

```typescript
// components/shared/FilterBar.tsx
interface FilterBarProps {
  activeFilters: [string, unknown][]
  onClearAll: () => void
  presets?: FilterPreset[]
  onApplyPreset?: (preset: FilterPreset) => void
  onExportCSV?: () => void
  children: React.ReactNode  // filter controls (dropdowns, date pickers)
}
```

### Recommended Project Structure (new/modified files)
```
apps/
  contacts/
    filters.py          # NEW: ContactFilterSet
  donations/
    filters.py          # NEW: DonationFilterSet
  pledges/
    filters.py          # NEW: PledgeFilterSet
  tasks/
    filters.py          # NEW: TaskFilterSet
frontend/src/
  hooks/
    useFilterParams.ts  # NEW: shared filter URL state hook
  components/shared/
    FilterBar.tsx        # NEW: reusable filter bar with badges/clear/presets
    FilterBadge.tsx      # NEW: individual active filter badge
    FilterPresets.tsx    # NEW: preset dropdown component
    ExportCSVButton.tsx  # NEW: CSV export button component
  lib/
    filter-presets.ts   # NEW: preset definitions (Needs Thank You, This Month, etc.)
```

### Anti-Patterns to Avoid
- **Storing filters in useState alongside URL params:** Use URL params as THE single source of truth. The Transactions page bug (FLT-08) is exactly this anti-pattern -- it uses `useState` for dateFrom/dateTo instead of `useSearchParams`.
- **Per-page filter boilerplate:** Every page currently hand-rolls `handleStatusFilter`, `handleTypeFilter`, etc. Extract into the shared hook.
- **Exposing owner field in FilterSet for non-admin users:** Owner-scoping MUST happen in `get_queryset()` before filters are applied. Never add `owner` to a public FilterSet.
- **Building CSV export as separate query logic:** Export endpoints MUST apply the same FilterSet as the list endpoint to guarantee "what you see is what you export."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL search param parsing & serialization | Manual URLSearchParams manipulation per page | nuqs `useQueryStates` with typed parsers | Type safety, null handling, batched updates, history mode control |
| Date range filtering on backend | Custom `get_queryset()` date parsing (current pattern in DonationListCreateView) | django-filter `DateFilter` with `lookup_expr='gte'`/`'lte'` | Automatic validation, consistent param naming, works with FilterSet |
| Boolean filter parsing ("true"/"false" strings) | Manual `searchParams.get("thanked") === "true"` | nuqs `parseAsBoolean` / django-filter `BooleanFilter` | Handles null vs false correctly on both sides |
| Filter preset date calculations | Inline date arithmetic | Extend existing `lib/date-presets.ts` | Already has startOfMonth, lastQuarter, ytd presets |
| CSV formula injection prevention | Custom sanitization per export | Reuse existing `sanitize_csv_value()` from `apps/imports/services.py` | Already implemented and tested (Phase 21, QAL-12) |

**Key insight:** The codebase already has 80% of the building blocks -- DjangoFilterBackend is globally configured, every view has `filter_backends`, every frontend page uses `useSearchParams`, date-fns presets exist, CSV sanitization exists. This phase is primarily about consolidation and enhancement, not greenfield development.

## Common Pitfalls

### Pitfall 1: django-filter 24.3 Breaking Changes (RangeWidget Suffixes)
**What goes wrong:** django-filter 24.3 changed `RangeWidget` suffixes from `_0`/`_1` to `_min`/`_max`. If you use `DateFromToRangeFilter`, the query params change from `?date_0=X&date_1=Y` to `?date_min=X&date_max=Y`.
**Why it happens:** Upgrade from 23.5 to 24.3 introduces this breaking change.
**How to avoid:** Use individual `DateFilter` fields with explicit `lookup_expr` instead of `DateFromToRangeFilter`. This gives full control over param names (`date_after`, `date_before`) and avoids the suffix issue entirely.
**Warning signs:** Tests passing locally with 23.5, failing after upgrade to 24.3.

### Pitfall 2: Filtered CSV Export Returns Unfiltered Data
**What goes wrong:** User applies filters, sees 50 results, clicks "Export CSV," gets 5,000 rows (the full unfiltered dataset).
**Why it happens:** Export endpoint builds its own queryset without applying the FilterSet, or applies filters to a different queryset.
**How to avoid:** Extract queryset-building into a shared method. Both list and export endpoints call `self._get_filtered_queryset(request)` which applies FilterSet.
**Warning signs:** Export endpoint has its own `Donation.objects.all()` call without FilterSet application.

### Pitfall 3: nuqs + React Query Cache Key Mismatch
**What goes wrong:** User changes filter, URL updates, but data doesn't refresh. Or: data refreshes but with stale filters.
**Why it happens:** React Query cache keys use the filter object, but nuqs updates URL asynchronously. If the query key doesn't include the parsed filter values, stale data persists.
**How to avoid:** Pass the nuqs filter state object directly as part of the React Query key: `queryKey: ["donations", filters]`. Use `shallow: false` in nuqs options to ensure React re-renders.
**Warning signs:** Changing a filter causes a brief flash of old data, or requires manual page refresh.

### Pitfall 4: Permission Bypass via Filter Params
**What goes wrong:** Regular staff user accesses `?owner=<admin_uuid>` and sees other users' contacts.
**Why it happens:** FilterSet exposes `owner` field without role check. DRF's `filter_backends` apply AFTER queryset is built, so if `get_queryset()` scopes by owner but FilterSet overrides that scope, data leaks.
**How to avoid:** NEVER include `owner` in a public FilterSet. Admin-only filters must be in a separate FilterSet or gated with a role check. Always verify: `get_queryset()` scopes data first, then FilterSet further narrows.
**Warning signs:** No role-based test for filter param access.

### Pitfall 5: Transactions Page State Migration (FLT-08)
**What goes wrong:** Transactions page uses `useState` for `dateFrom`/`dateTo` and `offset` -- these are NOT reflected in URL params. Bookmarking or sharing the URL loses filter state.
**Why it happens:** Transactions page was built with a different pagination pattern (offset-based) and never migrated to URL-based state.
**How to avoid:** Migrate Transactions to use `useFilterParams` hook + `useSearchParams` for all state, matching the pattern used by all other list pages.
**Warning signs:** Transactions page has `const [dateFrom, setDateFrom] = useState("")` instead of reading from URL.

## Code Examples

### Example 1: ContactFilterSet (Backend)
```python
# apps/contacts/filters.py
import django_filters
from apps.contacts.models import Contact

class ContactFilterSet(django_filters.FilterSet):
    """Filter contacts by status, needs_thank_you, owner (admin only), date ranges."""
    status = django_filters.CharFilter(field_name='status')
    needs_thank_you = django_filters.BooleanFilter(field_name='needs_thank_you')
    last_gift_after = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='gte')
    last_gift_before = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='lte')
    group = django_filters.CharFilter(field_name='groups__id')

    class Meta:
        model = Contact
        fields = ['status', 'needs_thank_you', 'last_gift_after', 'last_gift_before', 'group']
```

### Example 2: Filter Preset Definitions (Frontend)
```typescript
// lib/filter-presets.ts
import { startOfMonth, endOfMonth, subDays, format } from 'date-fns'

export interface FilterPreset {
  id: string
  label: string
  description: string
  getParams: () => Record<string, string | null>
}

export const contactPresets: FilterPreset[] = [
  {
    id: 'needs-thank-you',
    label: 'Needs Thank You',
    description: 'Contacts with unthanked donations',
    getParams: () => ({ needs_thank_you: 'true', status: null }),
  },
  {
    id: 'this-month',
    label: 'This Month',
    description: 'Contacts with gifts this month',
    getParams: () => ({
      last_gift_after: format(startOfMonth(new Date()), 'yyyy-MM-dd'),
      last_gift_before: format(endOfMonth(new Date()), 'yyyy-MM-dd'),
    }),
  },
]

export const pledgePresets: FilterPreset[] = [
  {
    id: 'late-pledges',
    label: 'Late Pledges',
    description: 'Active pledges past due date',
    getParams: () => ({ is_late: 'true', status: 'active' }),
  },
  {
    id: 'stalled',
    label: 'Stalled',
    description: 'Active pledges with no payment in 60+ days',
    getParams: () => ({ status: 'active', is_late: 'true' }),
  },
]
```

### Example 3: nuqs-based useFilterParams Hook (Frontend)
```typescript
// hooks/useFilterParams.ts
import { useQueryStates, parseAsString, parseAsBoolean, parseAsInteger } from 'nuqs'

// Page-specific parser definitions
export const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  needs_thank_you: parseAsBoolean,
  last_gift_after: parseAsString,
  last_gift_before: parseAsString,
  group: parseAsString,
}

export function useContactFilters() {
  const [filters, setFilters] = useQueryStates(contactFilterParsers)

  const clearAll = () => {
    setFilters({
      page: 1,
      search: null,
      status: null,
      needs_thank_you: null,
      last_gift_after: null,
      last_gift_before: null,
      group: null,
    })
  }

  const activeFilterCount = Object.entries(filters)
    .filter(([key, val]) => key !== 'page' && val !== null)
    .length

  return { filters, setFilters, clearAll, activeFilterCount }
}
```

### Example 4: Filtered CSV Export Endpoint (Backend)
```python
# apps/contacts/views.py
class ContactExportCSVView(APIView):
    """GET: Export filtered contacts as CSV."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Same queryset logic as ContactListCreateView
        user = request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)

        # Apply same FilterSet
        filterset = ContactFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs

        # Reuse existing export function
        from apps.imports.services import export_contacts_csv
        csv_content = export_contacts_csv(filtered_qs)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="contacts_export.csv"'
        return response
```

## State of the Art

| Old Approach (Current) | Current Approach (Phase 22) | Impact |
|------------------------|-----------------------------|--------|
| `filterset_fields = ['status', 'thanked']` | Custom `FilterSet` classes with date ranges, lookup exprs | Supports date range, boolean, choice filters properly |
| Manual `useSearchParams` per page | nuqs `useQueryStates` with typed parsers | Type-safe, batched URL updates, null handling |
| No filter presets | Preset dropdown with predefined filter combinations | One-click common workflows |
| No active filter badges | `<FilterBadge>` components showing active filters | Users always know what's filtered |
| No clear-all button | `clearAll()` in shared hook | One-click reset to unfiltered state |
| No filtered CSV export | Export endpoints apply same FilterSet | "What you see is what you export" |
| Transactions page uses useState for filters | All pages use URL params | Bookmarkable, shareable filter state |

**Deprecated/outdated:**
- django-filter 23.5: Must upgrade to 24.3 for date filter improvements and bug fixes. Do NOT upgrade to 25.2 (requires Django 5.2+, project runs 4.2.11).

## Existing Codebase Inventory

### Pages that need filter infrastructure (5 pages):

| Page | Current Filters | Missing | URL State |
|------|----------------|---------|-----------|
| ContactList | status, needs_thank_you, search | date range, group, owner (admin), presets, badges, clear-all, CSV export | Yes (useSearchParams) |
| DonationList | donation_type, thanked, search | date range, payment_method, presets, badges, clear-all, CSV export | Yes (useSearchParams) |
| PledgeList | status, is_late | frequency, date range, presets, badges, clear-all, CSV export | Yes (useSearchParams) |
| TaskList | status, priority, task_type, search | date range, presets, badges, clear-all, CSV export | Yes (useSearchParams) |
| Transactions | date_from, date_to | FLT-08 bug: uses useState not URL params; needs badges, clear-all, CSV export | NO (useState bug) |

### Backend filter infrastructure already in place:
- `DjangoFilterBackend` is globally configured in `REST_FRAMEWORK.DEFAULT_FILTER_BACKENDS`
- Every list view has `filter_backends = [DjangoFilterBackend, ...]`
- Every list view has `filterset_fields` (basic exact-match)
- Pagination via `StandardPagination` (25 per page)

### CSV export infrastructure already in place:
- `sanitize_csv_value()` in `apps/imports/services.py`
- `export_contacts_csv()` and `export_donations_csv()` in `apps/imports/services.py`
- `StreamingHttpResponse` pattern in `apps/insights/export_views.py`
- `Echo` pseudo-buffer class in `apps/insights/export_views.py`

## Filter Preset Specifications (from Requirements FLT-10)

| Preset | Page(s) | Filters Applied |
|--------|---------|-----------------|
| Needs Thank You | Contacts, Donations | `needs_thank_you=true` (contacts) or `thanked=false` (donations) |
| This Month | Contacts, Donations | date >= startOfMonth(now), date <= endOfMonth(now) |
| Late Pledges | Pledges | `is_late=true`, `status=active` |
| Stalled | Pledges | `status=active`, `is_late=true` (same as Late Pledges but semantically different label) |

## Open Questions

1. **Should the Transactions page be migrated to use DRF pagination?**
   - What we know: Transactions uses offset/limit pagination via a custom insights service, not DRF's built-in pagination. Other pages use DRF PageNumberPagination.
   - What's unclear: Whether to migrate Transactions to standard DRF pagination or just fix the URL state bug.
   - Recommendation: Fix URL state bug only (FLT-08). Full pagination migration is out of scope for this phase.

2. **Should nuqs be adopted or keep using manual useSearchParams?**
   - What we know: nuqs eliminates ~200 lines of boilerplate across 5 pages, provides type safety, has React Router v6 adapter. Trade-off is a new dependency (~5KB).
   - What's unclear: Whether the team prefers minimal dependencies.
   - Recommendation: Adopt nuqs. The per-page boilerplate reduction is significant and it prevents the exact category of bugs FLT-08 represents (state desynchronization).

3. **Export row limit for CSV?**
   - What we know: Current StreamingHttpResponse exports have no row limit. For large datasets, this could be slow.
   - What's unclear: Maximum expected dataset size in production.
   - Recommendation: Set a 10,000 row limit on CSV exports with a clear message if exceeded. Use `StreamingHttpResponse` for memory efficiency.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All views, models, frontend pages, existing filters, CSV export infrastructure
- django-filter 24.3 changelog: [GitHub CHANGES.rst](https://github.com/carltongibson/django-filter/blob/main/CHANGES.rst)
- nuqs docs: [nuqs.dev/docs/adapters](https://nuqs.dev/docs/adapters) - React Router v6 adapter confirmed

### Secondary (MEDIUM confidence)
- [django-filter 24.3 documentation](https://django-filter.readthedocs.io/en/stable/)
- [DRF filtering docs](https://www.django-rest-framework.org/api-guide/filtering/)
- [nuqs React Advanced 2025 presentation](https://www.infoq.com/news/2025/12/nuqs-react-advanced/)
- [Pitfalls research](../../research/PITFALLS_V1.3_SMARTSHEET_FILTERS.md) - especially Pitfalls 7, 8, 11

### Tertiary (LOW confidence)
- django-filter 25.2 Django version requirement (verified via search, but exact release note not fetched)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified, versions confirmed, existing codebase analyzed
- Architecture: HIGH - Based on existing codebase patterns, extending rather than replacing
- Pitfalls: HIGH - Prior pitfalls research exists, verified against codebase state
- Filter presets: MEDIUM - Preset definitions match requirements but exact UX needs design
- nuqs adoption: MEDIUM - Library verified but not yet used in this codebase

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable domain, django-filter 24.3 is a stable release)
