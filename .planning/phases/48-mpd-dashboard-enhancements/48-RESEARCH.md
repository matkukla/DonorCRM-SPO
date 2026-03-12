# Phase 48: MPD Dashboard Enhancements - Research

**Researched:** 2026-03-12
**Domain:** Django REST API extension + React dashboard component enhancement
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Monthly Average tile position:** First tile in a 4-column grid (`md:grid-cols-4`). Final order: Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining.
- **No new endpoint for tile:** Add `monthly_average` to existing `/api/v1/imports/mpd/me/` response.
- **Admin MPD Overview table column order:** Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining.
- **No new endpoint for overview:** Add `monthly_average` to existing `/api/v1/imports/mpd/overview/` response.
- **Admin section placement:** Below the missionary's own MPD tiles on the dashboard.
- **Admin visibility guard:** `user?.role === "admin"` (frontend); `IsAdmin` permission class (backend, already applied to `MPDOverviewView`).
- **Admin always sees admin section:** Admin overview renders regardless of whether admin has personal MPD data.
- **No timestamp shown:** No data-currency label on tiles or section headers.
- **No-data behavior unchanged:** MPD section stays hidden when `has_data` is false; no empty state added.

### Claude's Discretion

- Exact Tailwind grid class for 4-col responsiveness (e.g., `sm:grid-cols-2 md:grid-cols-4`).
- Whether `MPDStatsInline` is renamed or the 4th card is added inline.
- Skeleton loading state for the admin table section.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MPD-01 | Dashboard displays a "Monthly Average" tile in the MPD Financial Overview section showing average monthly giving | `MPDSnapshot.monthly_average` field exists on the model; backend simply needs to include it in `MPDMyDataView` response dict; frontend adds a new Card in `MPDStatsInline` and updates the grid to 4-col |
| MPD-02 | Dashboard displays an MPD Overview section visible only to admin role, showing org-wide MPD health metrics from Smartsheet data | `MPDOverviewView` already exists with `IsAdmin` permission; add `monthly_average` to per-missionary dict; `MPDOverviewTable` already renders via TanStack Table — add column following the existing decimal-sorting pattern |
</phase_requirements>

---

## Summary

Phase 48 is a surgical enrichment of the existing MPD infrastructure — no new models, no new endpoints, no new pages. The `MPDSnapshot` model already stores `monthly_average` as a `DecimalField`; it was simply never surfaced in the two API views or the frontend components.

The backend work is two small dict additions: one field in `MPDMyDataView.get()` and one field in the per-missionary dict inside `MPDOverviewView.get()`. Both follow the existing `str(snapshot.field) if snapshot.field is not None else None` pattern used for every other DecimalField in these views.

The frontend work is three changes: (1) expand `MPDStatsInline` from 3 to 4 cards with Monthly Average first, (2) update the Dashboard grid wrapper from `md:grid-cols-3` to `sm:grid-cols-2 md:grid-cols-4`, and (3) add an admin-gated section below the personal MPD block that renders `MPDOverviewTable` (with a new Monthly Average column) when `user?.role === "admin"`. Type interfaces in `mpd.ts` need one new optional field each.

**Primary recommendation:** Follow the verbatim patterns already in the codebase — same decimal-to-string serialisation on the backend, same `columnHelper.accessor` + numeric `sortingFn` on the frontend. No new abstractions needed.

---

## Standard Stack

### Core (already in use — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django REST Framework | current (project) | `APIView` + `Response` for backend views | Project standard for all API endpoints |
| TanStack Table v8 | current (project) | `createColumnHelper`, sortable columns in `MPDOverviewTable` | Already used in `MPDOverviewTable`; add column following same pattern |
| React Query (`@tanstack/react-query`) | current (project) | `useQuery` in `useMPDMyData` / `useMPDOverview` hooks | Already wired; no hook changes needed |
| shadcn/ui Card | current (project) | `Card`, `CardHeader`, `CardContent`, `CardTitle` | All existing MPD tiles use this pattern |
| Tailwind CSS | current (project) | Responsive grid classes | `sm:grid-cols-2 md:grid-cols-4` follows project convention |

**Installation:** No new packages required.

---

## Architecture Patterns

### Existing MPD Data Flow

```
MPDSnapshot model (monthly_average DecimalField, already populated by mpd_services.py)
  |
  v
MPDMyDataView.get()  ------>  /api/v1/imports/mpd/me/   ------>  useMPDMyData()  ------>  MPDStatsInline + Dashboard grid
MPDOverviewView.get() -----> /api/v1/imports/mpd/overview/ ----> useMPDOverview() -----> MPDOverviewTable
```

### Pattern 1: Backend — DecimalField to string serialisation

**What:** All DecimalFields on `MPDSnapshot` are serialised as strings to avoid floating-point loss. `None` maps to `null`.

**When to use:** Every financial field added to either response dict.

```python
# Source: apps/imports/views.py, existing MPDMyDataView and MPDOverviewView
'monthly_average': str(snapshot.monthly_average) if snapshot.monthly_average is not None else None,
```

### Pattern 2: Frontend — TanStack Table decimal column with null-last sort

**What:** `columnHelper.accessor` with a custom `sortingFn` that parses string decimals, treating `null`/empty as sorting last.

**When to use:** Every financial column in `MPDOverviewTable` that holds a `string | null` value.

```typescript
// Source: frontend/src/components/mpd/MPDOverviewTable.tsx (existing current_mpd_cap column)
columnHelper.accessor("monthly_average", {
  header: ({ column }) => (
    <button
      className="flex items-center gap-2 hover:text-foreground cursor-pointer"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      Monthly Average
      <ArrowUpDown className="h-4 w-4" />
    </button>
  ),
  cell: (info) => formatMPDCurrency(info.getValue()),
  sortingFn: (rowA, rowB, columnId) => {
    const a = rowA.getValue<string | null>(columnId)
    const b = rowB.getValue<string | null>(columnId)
    if (a === null && b === null) return 0
    if (a === null) return 1
    if (b === null) return -1
    const numA = parseFloat(a)
    const numB = parseFloat(b)
    if (isNaN(numA) && isNaN(numB)) return 0
    if (isNaN(numA)) return 1
    if (isNaN(numB)) return -1
    return numA - numB
  },
}),
```

### Pattern 3: Fragment-children Card component

**What:** `MPDStatsInline` renders `<>...</>` Fragment children — the parent Dashboard div provides the grid. Adding a 4th card prepends the Monthly Average card before the existing three.

**When to use:** The component interface must add `monthlyAverage?: string | null` as a new prop.

```typescript
// Source: frontend/src/components/mpd/MPDStatsInline.tsx (existing pattern, extend for 4th card)
interface MPDStatsInlineProps {
  monthlyAverage: string | null | undefined   // NEW — add first
  currentMpdCap: string | null | undefined
  latestRollForwardBalance: string | null | undefined
  monthsRemainingRf: string | undefined
}
```

### Pattern 4: Admin-only dashboard section guard

**What:** Sections that should only render for admins follow `user?.role === "admin"` inline checks. The admin MPD overview section should render after the personal MPD section and is always shown to admins, independent of whether admin has personal MPD data.

```typescript
// Source: frontend/src/pages/Dashboard.tsx (existing pattern, ~line 54)
// Admin section structure:
{user?.role === "admin" && (
  <div className="space-y-2">
    <h2 className="text-lg font-semibold">MPD Overview</h2>
    <MPDOverviewTable />
  </div>
)}
```

Note: `MPDOverviewTable` already handles its own loading/error/empty states internally — no skeleton wrapper needed at the Dashboard level. The component renders a card with pulse skeletons for the loading state (lines 144-151 of `MPDOverviewTable.tsx`).

### Recommended Change Locations

```
Backend:
  apps/imports/views.py
    MPDMyDataView.get()     — add monthly_average to response dict
    MPDOverviewView.get()   — add monthly_average to per-missionary dict

Frontend:
  frontend/src/api/mpd.ts
    MPDMyDataResponse       — add monthly_average?: string | null
    MPDMissionaryOverview   — add monthly_average?: string | null

  frontend/src/components/mpd/MPDStatsInline.tsx
    — add monthlyAverage prop; prepend Monthly Average Card

  frontend/src/components/mpd/MPDOverviewTable.tsx
    — add monthly_average column (2nd position, after user_name)

  frontend/src/pages/Dashboard.tsx
    — grid: md:grid-cols-3 -> sm:grid-cols-2 md:grid-cols-4
    — pass mpdData.monthly_average to MPDStatsInline
    — add admin-gated MPDOverviewTable section below personal MPD block
```

### Anti-Patterns to Avoid

- **Do not add a new endpoint.** Both `monthly_average` additions go into existing endpoints. Adding new routes creates unnecessary surface area.
- **Do not import `useMPDOverview` at the Dashboard level.** `MPDOverviewTable` already calls the hook internally. Importing it again at the Dashboard level would cause double-fetching.
- **Do not guard the admin section with `!isViewingOther`.** The CONTEXT.md decision is that the admin overview section always renders for admins. The existing `{!isViewingOther && (...)}` wrapper is on the personal MPD section — the admin section sits outside (or after) that block.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decimal-to-currency display | Custom formatter | `formatMPDCurrency()` in `frontend/src/api/mpd.ts` | Already handles null, NaN, Intl.NumberFormat USD formatting |
| Null-last numeric sort for string decimals | Custom comparator | Copy existing `sortingFn` pattern from `current_mpd_cap` column | Handles null, NaN, and numeric edge cases already validated in production |
| Sortable table header button | Custom button | Copy existing `ArrowUpDown` header pattern from `MPDOverviewTable` | Consistent with all other sortable columns |
| Table loading skeleton | Custom skeleton | `MPDOverviewTable` already renders `[...Array(5)].map(...)` pulse skeletons | Don't add a second loading layer at Dashboard level |

---

## Common Pitfalls

### Pitfall 1: Column insertion order in TanStack Table

**What goes wrong:** New `monthly_average` column inserted at wrong position — appearing after MPD Cap instead of before it. The column order in the `columns` array in `useMemo` determines display order.

**Why it happens:** The CONTEXT decision says column order must be Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining. The `monthly_average` accessor must be the second entry in the array.

**How to avoid:** Insert the new `columnHelper.accessor("monthly_average", ...)` block between `user_name` and `current_mpd_cap` in the `columns` array.

**Warning signs:** Visual inspection — if Monthly Average appears as the last column rather than second, the array order is wrong.

### Pitfall 2: Missing `monthly_average` in `MPDStatsInline` prop interface

**What goes wrong:** Adding the card in the JSX without updating the TypeScript interface causes a TS error or runtime undefined.

**Why it happens:** The interface is defined at the top of the file and the prop must be explicitly declared to flow through.

**How to avoid:** Update the `MPDStatsInlineProps` interface first, then add the card JSX.

### Pitfall 3: Admin section hidden behind `!isViewingOther` guard

**What goes wrong:** Admin cannot see the MPD Overview section when they are not viewing another user, or the section disappears correctly but the intent was "always show for admin."

**Why it happens:** The personal MPD block is wrapped in `{!isViewingOther && (...)}`. If the admin section JSX is placed inside that block, it will vanish when an admin is viewing another user's dashboard. Per CONTEXT, the admin section should always render for admins regardless of view state.

**How to avoid:** Place the admin overview section in a separate sibling block outside the `{!isViewingOther}` guard. The recommended structure:

```tsx
{/* Personal MPD — hidden when viewing as another user */}
{!isViewingOther && ( /* existing personal MPD tiles */ )}

{/* Admin MPD Overview — always visible to admin */}
{user?.role === "admin" && ( /* MPDOverviewTable */ )}
```

### Pitfall 4: Snapshot missing `monthly_average` data

**What goes wrong:** `monthly_average` is a nullable DecimalField — some snapshots may have `null`. The backend already handles this with the `if snapshot.monthly_average is not None else None` pattern. The frontend `formatMPDCurrency(null)` returns `"--"`. No special case needed.

**Why it happens:** Smartsheet may not include the Monthly Average column for all rows, so the import service stores `null`.

**How to avoid:** Use the same null-guard pattern in both views. Already established — just follow the pattern.

---

## Code Examples

Verified patterns from existing source files:

### Backend: MPDMyDataView response dict (current, 3 fields)

```python
# Source: apps/imports/views.py, MPDMyDataView.get()
return Response({
    'has_data': True,
    'current_mpd_cap': str(snapshot.current_mpd_cap) if snapshot.current_mpd_cap is not None else None,
    'latest_roll_forward_balance': str(snapshot.latest_roll_forward_balance) if snapshot.latest_roll_forward_balance is not None else None,
    'months_remaining_rf': snapshot.months_remaining_rf,
})
```

`monthly_average` is added using the same pattern.

### Backend: MPDOverviewView per-missionary dict (current, 4 fields)

```python
# Source: apps/imports/views.py, MPDOverviewView.get()
missionaries.append({
    'user_id': str(user.id),
    'user_name': user.full_name,
    'current_mpd_cap': str(snapshot.current_mpd_cap) if snapshot.current_mpd_cap is not None else None,
    'latest_roll_forward_balance': str(snapshot.latest_roll_forward_balance) if snapshot.latest_roll_forward_balance is not None else None,
    'months_remaining_rf': snapshot.months_remaining_rf,
})
```

`monthly_average` is inserted after `user_name` to match the intended display column order.

### Frontend: Dashboard MPD grid (current, 3-col)

```tsx
// Source: frontend/src/pages/Dashboard.tsx ~line 297-312
<div className="grid gap-3 md:grid-cols-3">
  <MPDStatsInline
    currentMpdCap={mpdData.current_mpd_cap}
    latestRollForwardBalance={mpdData.latest_roll_forward_balance}
    monthsRemainingRf={mpdData.months_remaining_rf}
  />
</div>
```

Updated to `sm:grid-cols-2 md:grid-cols-4` with `monthlyAverage={mpdData.monthly_average}` prop added.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| 3 MPD tiles (MPD Cap, Roll Forward Balance, Months Remaining) | 4 MPD tiles (Monthly Average first) | No breaking changes — additive only |
| Admin MPD Overview visible only on dedicated import/analytics page | Admin MPD Overview also visible on Dashboard | Improved admin discoverability |

**Deprecated/outdated:** Nothing deprecated by this phase.

---

## Open Questions

1. **`MPDStatsInline` rename vs. extend**
   - What we know: Component is named for 3 inline stats; adding a 4th changes its character.
   - What's unclear: Whether a rename like `MPDFinancialStats` is worth the refactor.
   - Recommendation: Extend in-place (add the prop, add the card). A rename is cosmetic and adds file churn without behavior change. Leave renaming to a future cleanup phase.

2. **Responsive grid on narrow screens**
   - What we know: Current grid is `md:grid-cols-3`. At `sm` breakpoint (640px), cards stack.
   - What's unclear: Exact breakpoint preference.
   - Recommendation: Use `sm:grid-cols-2 md:grid-cols-4`. On small screens (< 640px), single column; on sm (640-767px), 2 columns; on md+ (768px+), 4 columns. This is a Claude's Discretion item.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest apps/imports/tests/test_mpd_views.py -x --no-cov` |
| Full suite command | `pytest apps/imports/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MPD-01 | `GET /api/v1/imports/mpd/me/` returns `monthly_average` field | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_my_data_includes_monthly_average -x --no-cov` | ❌ Wave 0 |
| MPD-01 | `GET /api/v1/imports/mpd/me/` returns `monthly_average: null` when snapshot has no value | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_my_data_monthly_average_null -x --no-cov` | ❌ Wave 0 |
| MPD-02 | `GET /api/v1/imports/mpd/overview/` returns `monthly_average` in each missionary entry | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_overview_includes_monthly_average -x --no-cov` | ❌ Wave 0 |
| MPD-02 | `GET /api/v1/imports/mpd/overview/` is forbidden for non-admin users | unit | `pytest apps/imports/tests/test_mpd_views.py::test_mpd_overview_admin_only -x --no-cov` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest apps/imports/tests/test_mpd_views.py -x --no-cov`
- **Per wave merge:** `pytest apps/imports/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `apps/imports/tests/test_mpd_views.py` — covers MPD-01 and MPD-02 backend assertions
- [ ] No factory file exists for `MPDSnapshot` or `MPDUpload` — tests must use `Model.objects.create()` directly (pattern from `apps/imports/tests/test_views.py`)

*(Frontend is React/Vite with no test runner configured in this project — frontend changes are verified manually via the browser. No frontend test gaps to address.)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `apps/imports/views.py` — `MPDMyDataView` and `MPDOverviewView` implementations
- Direct code inspection: `apps/imports/models.py` — `MPDSnapshot.monthly_average` field confirmed present
- Direct code inspection: `frontend/src/components/mpd/MPDStatsInline.tsx` — exact prop interface and Card pattern
- Direct code inspection: `frontend/src/components/mpd/MPDOverviewTable.tsx` — TanStack Table column definitions and sortingFn pattern
- Direct code inspection: `frontend/src/api/mpd.ts` — `MPDMyDataResponse` and `MPDMissionaryOverview` interfaces
- Direct code inspection: `frontend/src/pages/Dashboard.tsx` — admin check pattern, MPD section location (~line 293)
- Direct code inspection: `apps/imports/urls.py` — route names confirmed (`mpd-my-data`, `mpd-overview`)

### Secondary (MEDIUM confidence)

- N/A — all findings from direct source inspection, no external research needed.

### Tertiary (LOW confidence)

- N/A

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — direct code inspection of existing working components
- Architecture: HIGH — patterns are verbatim copies of existing working code
- Pitfalls: HIGH — derived from actual code structure (column array order, guard placement)
- Test gaps: HIGH — confirmed by listing test directory contents

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable internal codebase; no external dependency changes expected)
