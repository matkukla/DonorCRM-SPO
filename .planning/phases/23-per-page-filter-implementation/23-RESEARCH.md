# Phase 23: Per-Page Filter Implementation - Research

**Researched:** 2026-02-18
**Domain:** Wiring Phase 22 filter infrastructure (FilterBar, useFilterParams, backend FilterSets) to remaining list pages
**Confidence:** HIGH

## Summary

Phase 23 completes the filter story started by Phase 22. Phase 22 built the infrastructure: backend FilterSets for 4 models (contacts, donations, pledges, tasks), frontend useFilterParams hook with 5 parser configs, FilterBar/Badge/Presets/ExportCSV components, and wired ContactList as the reference implementation. Phase 23 must wire the remaining 3 DRF-backed list pages (DonationList, PledgeList, JournalList) and the Transactions page to use the shared infrastructure, while adding new filter fields required by FLT-01 through FLT-07.

The primary work divides into three areas: (1) **backend gaps** -- Journals has no FilterSet, no export endpoint, and needs one created; Donations needs `fund` and amount range filters added to its FilterSet; Pledges needs amount range and search-by-donor-name added; the admin owner filter needs implementing in DonationListCreateView.get_queryset() to match the ContactListCreateView pattern. (2) **frontend wiring** -- DonationList, PledgeList, and JournalList all use manual `useSearchParams` instead of `useFilterParams`; they need migrating to the ContactList reference pattern. (3) **new filter controls** -- date range inputs, amount range inputs, fund dropdown, frequency dropdown, payment method dropdown, and admin-only owner dropdown need to be added as `FilterBar` children.

**Primary recommendation:** Follow the ContactList reference pattern exactly for each page. Backend-first: add missing FilterSet fields and the JournalFilterSet + export endpoint. Then frontend: replace `useSearchParams` with `useFilterParams`, wrap filter controls in `FilterBar`, add presets and export CSV. The amount range filters (FLT-02) require new `NumberFilter` with `lookup_expr='gte'/'lte'` on backend and `parseAsString` parsers on frontend. The admin owner filter (FLT-04) stays in `get_queryset()` per Phase 22 security decision but needs a conditional UI dropdown using `useAuth().user.role`.

## Standard Stack

### Core (all existing -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| django-filter | 24.3 (pinned) | Backend queryset filtering | Already installed in Phase 22; provides FilterSet, DateFilter, NumberFilter, CharFilter, BooleanFilter, UUIDFilter |
| nuqs | 2.8.8 | Type-safe URL filter state | Already installed in Phase 22; provides useQueryStates, parseAsString, parseAsBoolean, parseAsInteger |
| @tanstack/react-query | 5.90.17 | Data fetching with filter-aware cache keys | Already in stack; filter objects become query keys |
| date-fns | 4.1.0 | Date preset calculations | Already in stack; used by filter-presets.ts |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui | existing | DropdownMenu, Button, Input, Badge | Filter control dropdowns and toggle buttons |
| lucide-react | existing | Icons for filter controls | Filter, Search, Calendar, DollarSign, etc. |

### No New Dependencies Required
Phase 23 uses only what Phase 22 already installed. All filtering infrastructure is in place.

## Architecture Patterns

### Pattern 1: ContactList Reference Implementation (THE pattern to follow)

**What:** The ContactList page was fully wired in Phase 22-03 and serves as THE reference for all other pages.

**Key elements of the pattern:**

1. Import `useFilterParams` + page-specific parsers
2. Destructure `filters, setFilters, clearAll, activeFilters, toQueryParams`
3. Build `queryParams` from `toQueryParams()` + page_size
4. Pass `queryParams` to data hook (must accept `Record<string, string>`)
5. Render `<FilterBar>` with activeFilters, clearAll, onRemoveFilter, filterLabels, filterValueLabels, presets, exportUrl, exportParams
6. Place filter controls (search, dropdowns, toggles) as FilterBar children
7. Use `setFilters({ [key]: value, page: 1 })` for all filter changes (reset pagination)

**Anti-pattern to avoid:** The current DonationList and PledgeList pages use `useSearchParams` with manual `handleTypeFilter`, `handleThankedFilter`, etc. functions. Each has 20-30 lines of boilerplate that the shared hook eliminates.

### Pattern 2: Backend FilterSet Enhancement

**What:** Adding new filter fields to existing FilterSets.

**When to use:** When a requirement calls for a new filter field (amount range, fund, etc.).

**Steps:**
1. Add the filter field to the `FilterSet` class
2. Add the field name to `Meta.fields`
3. Add matching parser to the frontend page-specific parsers in `useFilterParams.ts`
4. Add corresponding filter control in the page's FilterBar children

**Example -- Adding amount range to DonationFilterSet:**
```python
# apps/donations/filters.py
class DonationFilterSet(django_filters.FilterSet):
    # ... existing fields ...
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    fund = django_filters.UUIDFilter(field_name='fund_id')

    class Meta:
        model = Donation
        fields = [..., 'amount_min', 'amount_max', 'fund']
```

### Pattern 3: Admin-Only Owner Filter (Security Pattern)

**What:** Owner filtering for contacts and donations, restricted to admin users only.

**Where it lives:** In `get_queryset()` of each view, NOT in the FilterSet (Phase 22 security decision).

**Existing implementation (ContactListCreateView):**
```python
# Optional owner filter for admin (intentionally NOT in FilterSet - security)
owner_id = self.request.query_params.get('owner')
if owner_id and user.role == 'admin':
    queryset = queryset.filter(owner_id=owner_id)
```

**Frontend pattern:**
```typescript
// Only show owner dropdown if user is admin
const { user } = useAuth()
{user?.role === 'admin' && (
  <OwnerDropdown
    value={filters.owner}
    onChange={(val) => setFilters({ owner: val, page: 1 })}
  />
)}
```

**Important:** The `owner` param must NOT be in the parser config's `excludedKeys` -- it should show as an active filter badge when set. But the backend ignores it for non-admin users.

### Pattern 4: JournalFilterSet Creation (New FilterSet for Existing View)

**What:** Creating a new FilterSet for the journals app, which Phase 22 skipped (only contacts, donations, pledges, tasks got FilterSets).

**Key considerations:**
- Journal model has: `name`, `deadline`, `is_archived`, `goal_amount`, `owner`
- JournalListCreateView already uses `filterset_fields = ['is_archived']`
- View already has `search_fields = ['name']` for SearchFilter
- View already has special logic: excludes archived by default unless `is_archived` filter is present
- Owner filtering for journals follows the same admin-only security pattern

**The archived-by-default behavior needs careful handling:** The view currently checks `if 'is_archived' not in self.request.query_params` to exclude archived journals. With a FilterSet, this behavior must be preserved. The FilterSet should NOT include `is_archived` as a default filter -- the view's queryset logic should remain as-is.

### Pattern 5: Refactoring API Functions to Accept Record<string, string>

**What:** The ContactList reference pattern passes `Record<string, string>` from `toQueryParams()` directly to the data hook. But the current DonationList and PledgeList use typed filter interfaces (`DonationFilters`, `PledgeFilters`) with manual URLSearchParams building.

**Migration approach:** Change the data hooks (`useDonations`, `usePledges`) to accept `Record<string, string>` like `useContacts` does, then update the API functions (`getDonations`, `getPledges`) to accept a params object and pass it directly to axios, eliminating the manual URLSearchParams building.

**Example:**
```typescript
// Before (DonationList pattern):
const { data } = useDonations({
  page, page_size: PAGE_SIZE, search,
  donation_type: donationType, thanked: thanked === "true" ? true : ...
})

// After (ContactList pattern):
const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
const { data } = useDonations(queryParams)
```

### Recommended Project Structure (new/modified files)

```
apps/
  journals/
    filters.py              # NEW: JournalFilterSet
    export_views.py          # NEW: JournalExportCSVView
  donations/
    filters.py              # MODIFY: add amount_min, amount_max, fund
    views.py                # MODIFY: add admin owner filter in get_queryset
  pledges/
    filters.py              # MODIFY: add amount_min, amount_max
    views.py                # MODIFY: (optional) add SearchFilter for donor name
  journals/
    urls.py                 # MODIFY: add export/csv/ route
    views.py                # MODIFY: use filterset_class instead of filterset_fields
frontend/src/
  hooks/
    useFilterParams.ts      # MODIFY: add journalFilterParsers, add owner/fund/amount parsers
  lib/
    filter-presets.ts       # MODIFY: add journal presets
  pages/
    donations/
      DonationList.tsx      # MODIFY: migrate to useFilterParams + FilterBar
    pledges/
      PledgeList.tsx        # MODIFY: migrate to useFilterParams + FilterBar
    journals/
      JournalList.tsx       # MODIFY: migrate to useFilterParams + FilterBar
  api/
    donations.ts            # MODIFY: change getDonations to accept Record<string, string>
    pledges.ts              # MODIFY: change getPledges to accept Record<string, string>
    journals.ts             # MODIFY: change getJournals to accept Record<string, string>
  hooks/
    useDonations.ts         # MODIFY: change useDonations to accept Record<string, string>
    usePledges.ts           # MODIFY: change usePledges to accept Record<string, string>
    useJournals.ts          # MODIFY: change useJournals to accept Record<string, string>
```

### Anti-Patterns to Avoid

- **Adding owner to FilterSet:** Owner filtering MUST stay in `get_queryset()` gated by role check. Never add `owner` to any FilterSet. This is a locked Phase 22 decision.
- **Mixing useSearchParams and useFilterParams on the same page:** Once a page is migrated, ALL URL state should go through the shared hook. No hybrid approach.
- **Forgetting to reset pagination when filters change:** Every `setFilters` call that changes a filter value MUST include `page: 1` (or `offset: 0` for Transactions). Forgetting this shows page 3 of old results after a new filter is applied.
- **Using `parseAsFloat` or `parseAsInteger` for amount filters:** Amount filter values should be `parseAsString` on the frontend to match the backend's string-based query param parsing. The backend `NumberFilter` handles string-to-number conversion.
- **Not nulling sibling fields in presets:** Presets must explicitly null other filter fields to prevent stacking. This is an established pattern from Phase 22-02.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Amount range filtering | Manual queryset `.filter(amount__gte=X, amount__lte=Y)` | django-filter `NumberFilter(lookup_expr='gte'/'lte')` | Automatic validation, consistent with date range pattern |
| Fund dropdown options | Hard-coded fund list | Backend endpoint to list available funds | Funds are imported dynamically from SPO |
| User list for owner dropdown | Hard-coded user list | Existing `useUsers()` hook + `getUsers()` API | Already implemented, admin-only |
| Per-page manual URL state | Manual `useSearchParams` + `handleXFilter()` per page | `useFilterParams(pageFilterParsers)` | Eliminates 20-30 lines of boilerplate per page |
| CSV export with current filters | Separate export query logic | `ExportCSVButton` with `toQueryParams()` | Guarantees "what you see is what you export" |
| Archived-by-default journal logic | Custom filter logic | Keep existing view.get_queryset() behavior | Already working, don't break it |

**Key insight:** Phase 23 is almost entirely a wiring/replication exercise. The infrastructure exists. The reference implementation exists. The task is to replicate the ContactList pattern to 3 more pages and add the missing filter fields.

## Common Pitfalls

### Pitfall 1: Breaking the Journal Archived-by-Default Behavior
**What goes wrong:** After adding a JournalFilterSet, all journals (including archived) appear in the list.
**Why it happens:** JournalListCreateView has special logic: `if 'is_archived' not in self.request.query_params: queryset = queryset.filter(is_archived=False)`. If the FilterSet processes `is_archived` before this check runs, or if the FilterSet's Meta.fields includes `is_archived` without the view's conditional logic, the behavior breaks.
**How to avoid:** Keep `is_archived` handling in `get_queryset()` as-is. The FilterSet should handle other fields (deadline range, etc.) but NOT override the archived logic. Use `filterset_class` alongside the existing `get_queryset()` archived check -- DjangoFilterBackend applies the FilterSet AFTER `get_queryset()` returns, so the ordering is safe. But do NOT add `is_archived` to the FilterSet's Meta.fields -- let the view handle it manually.
**Warning signs:** Archived journals appearing in the list when no `is_archived` filter is set.

### Pitfall 2: Donations API Hook Signature Mismatch
**What goes wrong:** After migrating DonationList to `useFilterParams`, the donations don't load because the hook/API function expects typed `DonationFilters` but receives `Record<string, string>`.
**Why it happens:** The current `useDonations` hook calls `getDonations(filters)` which builds URLSearchParams manually from a typed interface. The new pattern passes `Record<string, string>` directly to axios params.
**How to avoid:** Refactor `getDonations()` to accept `Record<string, string>` and pass it directly as axios params (like `getContacts` does). Update `useDonations` to accept `Record<string, string>`. Same for pledges and journals.
**Warning signs:** TypeScript errors on `useDonations(queryParams)` because `queryParams` is `Record<string, string>` not `DonationFilters`.

### Pitfall 3: Fund Filter Requires a New API Endpoint
**What goes wrong:** The fund dropdown in DonationList has no data to populate because there's no API endpoint to list funds.
**Why it happens:** The Fund model exists in `apps/imports/models.py` but only has an import endpoint (`/api/v1/imports/funds/`), not a list endpoint.
**How to avoid:** Create a simple read-only fund list endpoint (e.g., `GET /api/v1/funds/` or `GET /api/v1/imports/funds/list/`) that returns `[{id, name}]` for active funds. Or: use a simpler approach -- add `fund` to the DonationFilterSet (already done with UUIDFilter) and on the frontend, show a text input for fund ID instead of a dropdown. A dropdown is nicer UX but requires an endpoint.
**Warning signs:** Empty fund dropdown, or fund filter only works if user types a UUID manually.

### Pitfall 4: Pledge Search by Donor Name Not Supported by DRF SearchFilter
**What goes wrong:** FLT-06 requires "search by donor name" on pledges, but PledgeListCreateView doesn't have `SearchFilter` in its `filter_backends` or `search_fields`.
**Why it happens:** PledgeListCreateView has `filter_backends = [DjangoFilterBackend, filters.OrderingFilter]` -- no `filters.SearchFilter`. The `search` param won't work without it.
**How to avoid:** Add `filters.SearchFilter` to PledgeListCreateView's `filter_backends` and add `search_fields = ['contact__first_name', 'contact__last_name']`. Add `search: parseAsString` to pledgeFilterParsers.
**Warning signs:** Search box on PledgeList does nothing, or returns all pledges regardless of search term.

### Pitfall 5: UTC Date Display Bug on New Date Filter Inputs
**What goes wrong:** Date filter inputs show dates that are off by one day in US timezones.
**Why it happens:** Date-only strings like "2026-02-01" are parsed as UTC midnight by `new Date()`, which displays as Jan 31 in US timezones. This is the known UTC date display bug from MEMORY.md.
**How to avoid:** Date filter inputs use `type="date"` HTML inputs which handle YYYY-MM-DD natively -- they don't parse through `new Date()`. The date values flow as strings through the URL and to the backend without JS Date parsing. The bug only affects DISPLAY of dates (e.g., in filter badges). Use `formatLocalDate()` from `lib/utils.ts` for any date display, not `new Date().toLocaleDateString()`.
**Warning signs:** Filter badge shows "From: 2026-01-31" when the user selected "2026-02-01".

### Pitfall 6: React Query Cache Key Collisions with undefined Values
**What goes wrong:** Changing a filter doesn't trigger a new API call because React Query thinks the cache key hasn't changed.
**Why it happens:** From MEMORY.md: "Global staleTime: 5 min in QueryProvider. Pass clean Record<string, string> (from toQueryParams()) as query keys, not objects with undefined values -- undefined gets stripped by JSON serialization, causing key collisions."
**How to avoid:** Always use `toQueryParams()` to build query params (which strips nulls/undefineds). Pass the same clean object as both the query key and the API params.
**Warning signs:** Changing a filter shows stale data, or requires manual page refresh.

## Code Examples

### Example 1: DonationList Migration (Frontend)

```typescript
// BEFORE (current):
const [searchParams, setSearchParams] = useSearchParams()
const page = parseInt(searchParams.get("page") || "1", 10)
const donationType = searchParams.get("donation_type") as DonationType | undefined
const { data } = useDonations({ page, page_size: PAGE_SIZE, donation_type: donationType, ... })

// AFTER (Phase 23):
const { filters, setFilters, clearAll, activeFilters, toQueryParams } = useFilterParams(donationFilterParsers)
const [searchInput, setSearchInput] = useState(filters.search || "")
useEffect(() => { setSearchInput(filters.search || "") }, [filters.search])
const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
const { data } = useDonations(queryParams)
```

### Example 2: DonationFilterSet Enhancement (Backend)

```python
# apps/donations/filters.py
import django_filters
from apps.donations.models import Donation

class DonationFilterSet(django_filters.FilterSet):
    donation_type = django_filters.CharFilter(field_name='donation_type')
    payment_method = django_filters.CharFilter(field_name='payment_method')
    thanked = django_filters.BooleanFilter(field_name='thanked')
    date_after = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    contact = django_filters.UUIDFilter(field_name='contact_id')
    # NEW for FLT-02:
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    # NEW for FLT-05:
    fund = django_filters.UUIDFilter(field_name='fund_id')

    class Meta:
        model = Donation
        fields = [
            'donation_type', 'payment_method', 'thanked',
            'date_after', 'date_before', 'contact',
            'amount_min', 'amount_max', 'fund',
        ]
```

### Example 3: JournalFilterSet Creation (Backend)

```python
# apps/journals/filters.py
import django_filters
from apps.journals.models import Journal

class JournalFilterSet(django_filters.FilterSet):
    deadline_after = django_filters.DateFilter(field_name='deadline', lookup_expr='gte')
    deadline_before = django_filters.DateFilter(field_name='deadline', lookup_expr='lte')

    class Meta:
        model = Journal
        fields = ['deadline_after', 'deadline_before']
        # NOTE: is_archived is handled in get_queryset(), NOT here
```

### Example 4: Admin Owner Filter in DonationListCreateView (Backend)

```python
# apps/donations/views.py - in DonationListCreateView.get_queryset()
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        queryset = Donation.objects.all()
    else:
        queryset = Donation.objects.filter(contact__owner=user)

    # Admin-only owner filter (matches ContactListCreateView pattern)
    owner_id = self.request.query_params.get('owner')
    if owner_id and user.role == 'admin':
        queryset = queryset.filter(contact__owner_id=owner_id)

    return queryset.select_related('contact', 'pledge')
```

### Example 5: Updated donationFilterParsers (Frontend)

```typescript
// hooks/useFilterParams.ts
export const donationFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  donation_type: parseAsString,
  payment_method: parseAsString,
  thanked: parseAsBoolean,
  date_after: parseAsString,
  date_before: parseAsString,
  amount_min: parseAsString,
  amount_max: parseAsString,
  fund: parseAsString,
  owner: parseAsString,  // admin-only, conditionally rendered
  ordering: parseAsString,
}
```

### Example 6: JournalExportCSVView (Backend)

```python
# apps/journals/export_views.py
import csv
from datetime import datetime
from rest_framework import permissions
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from apps.imports.services import sanitize_csv_value
from apps.journals.filters import JournalFilterSet
from apps.journals.models import Journal

class Echo:
    def write(self, value):
        return value

class JournalExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'admin':
            queryset = Journal.objects.all()
        else:
            queryset = Journal.objects.filter(owner=user)

        if 'is_archived' not in request.query_params:
            queryset = queryset.filter(is_archived=False)

        filterset = JournalFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('owner')[:10000]

        filename = f'journals_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            yield writer.writerow(['Name', 'Goal Amount', 'Deadline', 'Archived', 'Created'])
            for journal in filtered_qs:
                yield writer.writerow([
                    sanitize_csv_value(journal.name),
                    str(journal.goal_amount),
                    journal.deadline or '',
                    'Yes' if journal.is_archived else 'No',
                    journal.created_at.date().isoformat(),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

### Example 7: Fund List Endpoint (Backend, minimal)

```python
# apps/imports/views.py (or a new funds/views.py)
from rest_framework import generics, permissions, serializers
from apps.imports.models import Fund

class FundListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ['id', 'name']

class FundListView(generics.ListAPIView):
    serializer_class = FundListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Return all funds without pagination

    def get_queryset(self):
        return Fund.objects.filter(status='active').order_by('name')
```

## Per-Page Gap Analysis

### DonationList (NEEDS FULL WIRING)

**Current state:** Uses `useSearchParams` manually with `handleTypeFilter`, `handleThankedFilter`, etc. Wrapped in `<Card>`. No FilterBar, no presets, no badges, no export CSV.

**Backend gaps:**
- Missing `amount_min`/`amount_max` NumberFilters (FLT-02)
- Missing `fund` UUIDFilter (FLT-05)
- Missing admin owner filter in `get_queryset()` (FLT-04)
- DonationFilterSet already has: `donation_type`, `payment_method`, `thanked`, `date_after`, `date_before`, `contact`
- SearchFilter already configured with `search_fields` (implicit in DRF)
- Export endpoint already exists at `/api/v1/donations/export/csv/`

**Frontend gaps:**
- Migrate from `useSearchParams` to `useFilterParams(donationFilterParsers)`
- Replace `<Card>` filter wrapper with `<FilterBar>`
- Add date range inputs (FLT-01)
- Add amount range inputs (FLT-02)
- Add payment method dropdown (FLT-05)
- Add fund dropdown (FLT-05) -- needs fund list endpoint
- Add admin owner dropdown (FLT-04)
- Add donation presets (already defined in `filter-presets.ts`)
- Add ExportCSVButton
- Refactor `getDonations()` and `useDonations()` to accept `Record<string, string>`

### PledgeList (NEEDS FULL WIRING)

**Current state:** Uses `useSearchParams` manually with `handleStatusFilter`, `handleLateFilter`. Wrapped in `<Card>`. No FilterBar, no presets, no badges, no export CSV, no search.

**Backend gaps:**
- Missing `amount_min`/`amount_max` NumberFilters (FLT-02)
- Missing `SearchFilter` in `filter_backends` and no `search_fields` (FLT-06)
- PledgeFilterSet already has: `status`, `frequency`, `is_late`, `start_date_after`, `start_date_before`, `contact`
- Export endpoint already exists at `/api/v1/pledges/export/csv/`

**Frontend gaps:**
- Migrate from `useSearchParams` to `useFilterParams(pledgeFilterParsers)`
- Replace `<Card>` filter wrapper with `<FilterBar>`
- Add search input for donor name (FLT-06)
- Add date range inputs for start_date (FLT-01)
- Add amount range inputs (FLT-02)
- Add frequency dropdown (FLT-06)
- Add pledge presets (already defined in `filter-presets.ts`)
- Add ExportCSVButton
- Add `search` and `amount_min`/`amount_max` to `pledgeFilterParsers`
- Refactor `getPledges()` and `usePledges()` to accept `Record<string, string>`

### JournalList (NEEDS FULL WIRING)

**Current state:** Uses card grid layout (not DataTable). No FilterBar, no presets, no badges, no export CSV. Very minimal -- just loads journals with `useJournals()`.

**Backend gaps:**
- No FilterSet (currently uses `filterset_fields = ['is_archived']`)
- No export endpoint
- Need JournalFilterSet with deadline range filters
- Need JournalExportCSVView
- Need to add export route to `apps/journals/urls.py`

**Frontend gaps:**
- Add `journalFilterParsers` to `useFilterParams.ts`
- Create journal presets in `filter-presets.ts`
- Migrate from bare `useJournals()` to `useFilterParams(journalFilterParsers)` + refactored `useJournals(queryParams)`
- Add FilterBar with: search, archived toggle, date range for deadline
- Add ExportCSVButton
- Refactor `getJournals()` and `useJournals()` to accept `Record<string, string>`
- Note: JournalList uses a card grid, not DataTable -- the FilterBar sits above the grid, same pattern works

### Transactions (ALREADY PARTIALLY WIRED)

**Current state:** Already uses `useFilterParams(transactionFilterParsers)` and `<FilterBar>` from Phase 22-03 FLT-08 fix. Has date range filter inputs.

**What's left:** Transactions is effectively complete for Phase 23 scope. It already has:
- URL-based filter state via `useFilterParams`
- FilterBar with date range inputs
- Active filter badges and clear-all

**Possible enhancements (LOW priority):**
- Add presets (e.g., "This Month", "Last 30 Days")
- Transactions uses a custom insights endpoint, not DRF pagination, so no backend FilterSet changes needed

## Requirement-to-Implementation Mapping

| Requirement | Backend Change | Frontend Change | Pages Affected |
|-------------|---------------|-----------------|----------------|
| FLT-01: Date range filtering | Already done (Phase 22-01 FilterSets) | Add date inputs to FilterBar children | Donations, Pledges, Journals (Transactions done) |
| FLT-02: Amount range filtering | Add NumberFilter(gte/lte) to DonationFilterSet + PledgeFilterSet | Add amount_min/max inputs, add parsers | Donations, Pledges |
| FLT-03: Contact group filter | Already done (ContactFilterSet has `group`) | Already wired in ContactList (Phase 22-03) | Contacts (DONE) |
| FLT-04: Admin owner filter | Add owner check to DonationListCreateView.get_queryset() | Add conditional owner dropdown (useAuth + useUsers) | Contacts (done), Donations |
| FLT-05: Payment method + fund | `payment_method` already in FilterSet; add `fund` UUIDFilter + fund list endpoint | Add dropdowns for both | Donations |
| FLT-06: Pledge frequency + donor search | `frequency` already in FilterSet; add SearchFilter to view | Add frequency dropdown, search input | Pledges |
| FLT-07: Journal name/date/archived | Create JournalFilterSet, keep archived logic in view | Add search, date range, archived toggle | Journals |

## State of the Art

| Phase 22 Built | Phase 23 Extends | Net New Work |
|----------------|------------------|--------------|
| 4 backend FilterSets | Add fields to Donation+Pledge FilterSets, create Journal FilterSet | ~3 FilterSet modifications + 1 new |
| 5 parser configs | Add fields to donation+pledge+journal parsers | ~3 parser config updates |
| FilterBar + components | Wire to 3 more pages | Replication, not creation |
| ContactList reference | DonationList, PledgeList, JournalList wiring | Follow established pattern |
| 4 CSV export endpoints | Add Journal export endpoint | 1 new export view |
| Presets for 3 pages | Add Journal presets | 1 new preset set |

## Open Questions

1. **Fund filter: dropdown vs text input?**
   - What we know: There's no fund list endpoint. Fund model exists in `apps/imports/models.py` with `name` and `external_id` fields. Donations have a FK to Fund.
   - What's unclear: How many funds typically exist (10? 100? 1000?) and whether a dropdown is practical.
   - Recommendation: Create a simple fund list endpoint (no pagination, return all active funds). If <100 funds (likely for a missionary CRM), a dropdown is the right UX. This is a small endpoint (~10 lines).

2. **Should JournalList switch from card grid to DataTable?**
   - What we know: JournalList uses a card grid (`grid gap-4 md:grid-cols-2 lg:grid-cols-3`). All other list pages use DataTable.
   - What's unclear: Whether the card layout should be preserved for visual appeal or migrated for consistency.
   - Recommendation: Keep the card grid. FilterBar works above any layout. The journals page is more of a dashboard/overview than a data table -- cards are better UX here. Just add FilterBar above the grid.

3. **Transactions page: add presets?**
   - What we know: Transactions already has FilterBar with date range. It uses a custom insights endpoint with offset pagination, not DRF.
   - What's unclear: Whether adding presets (This Month, Last 30 Days, YTD) to Transactions is in scope for Phase 23.
   - Recommendation: Add simple date presets to Transactions as a nice-to-have. Low effort since the infrastructure is already wired.

4. **Admin owner filter: contacts AND donations, or just contacts?**
   - What we know: FLT-04 says "Admin can filter contacts and donations by owner (missionary)". ContactListCreateView already has the owner filter in get_queryset(). DonationListCreateView does not.
   - What's unclear: Whether the owner filter for donations should filter by `contact__owner` (which contact's owner is this missionary) or something else.
   - Recommendation: Add `contact__owner_id` filter to DonationListCreateView.get_queryset(), matching the Contact pattern. This lets an admin see "all donations received by Missionary X's contacts."

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All FilterSets, views, frontend pages, hooks, API files, models examined directly
- Phase 22 RESEARCH.md, 22-01-SUMMARY.md, 22-02-SUMMARY.md, 22-03-SUMMARY.md -- infrastructure documentation
- ContactList.tsx reference implementation -- the exact pattern to replicate

### Secondary (MEDIUM confidence)
- django-filter 24.3 documentation (NumberFilter, DateFilter, BooleanFilter, CharFilter, UUIDFilter)
- nuqs 2.8.8 (parseAsString, parseAsBoolean, parseAsInteger, useQueryStates)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and in use. No new dependencies.
- Architecture: HIGH -- Reference implementation exists (ContactList). Pattern is proven and documented.
- Per-page gap analysis: HIGH -- Every file examined, every gap identified with specific file paths.
- Pitfalls: HIGH -- Based on actual codebase analysis, known bugs (MEMORY.md), and Phase 22 decisions.
- Open questions: MEDIUM -- Fund endpoint and JournalList layout are design decisions needing user input.

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable domain, replication of existing patterns)
