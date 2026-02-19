# Phase 26: Contact Owner Filter UI - Research

**Researched:** 2026-02-19
**Domain:** Frontend filter UI (React + shadcn/ui), mirroring existing DonationList pattern
**Confidence:** HIGH

## Summary

This phase adds an admin-only "Owner" dropdown to the ContactList FilterBar, closing the FLT-04 gap for contacts. The DonationList already implements this exact pattern (added in Phase 23), and the ContactList backend **already supports the `owner` query parameter** in both `ContactListCreateView.get_queryset()` and `ContactExportCSVView.get()`. The work is therefore **frontend-only**: add the `owner` parser to `contactFilterParsers`, add the dropdown UI to `ContactList.tsx`, update the contact presets to null the new `owner` field, and add `owner` to `filterLabels`.

The backend owner filter is intentionally kept out of `ContactFilterSet` (security decision from Phase 22-01) and handled in `get_queryset()` with an explicit `user.role == 'admin'` check. This means the frontend sends `?owner=<userId>` as a query param, and the backend applies it only for admin users. This pattern is already working for both the contact list API and the contact CSV export endpoint.

**Primary recommendation:** Mirror the DonationList owner dropdown pattern exactly -- the backend is already complete, this is a pure frontend task touching 3 files.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nuqs | (existing) | URL query state management | Already used by `useFilterParams` hook |
| shadcn/ui DropdownMenu | (existing) | Dropdown UI component | Already used for all filter dropdowns |
| @tanstack/react-query | (existing) | Data fetching (`useUsers` hook) | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | (existing) | Date formatting in presets | Already used in `filter-presets.ts` |

### Alternatives Considered
None. This is a direct pattern replication -- no architectural decisions needed.

## Architecture Patterns

### Pattern 1: Admin-Only Owner Filter (DonationList Reference Implementation)

**What:** An owner dropdown that is conditionally rendered only for admin users, fetching the user list via the existing `useUsers` hook.

**When to use:** Any list page where admin needs to filter by contact/data owner.

**Reference:** `frontend/src/pages/donations/DonationList.tsx` lines 362-384

```tsx
// 1. Import useAuth and useUsers at top of file
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"

// 2. In component body, derive isAdmin and fetch users
const { user } = useAuth()
const isAdmin = user?.role === "admin"
const { data: usersData } = useUsers()

// 3. In FilterBar children, conditionally render dropdown
{isAdmin && usersData && (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="secondary" size="sm" className="gap-2">
        <Filter className="h-4 w-4" />
        {filters.owner
          ? usersData.find((u) => String(u.id) === filters.owner)?.full_name || "Owner"
          : "All Owners"}
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent>
      <DropdownMenuItem onClick={() => setFilters({ owner: null, page: 1 })}>
        All Owners
      </DropdownMenuItem>
      {usersData.map((u) => (
        <DropdownMenuItem key={u.id} onClick={() => setFilters({ owner: String(u.id), page: 1 })}>
          {u.full_name}
        </DropdownMenuItem>
      ))}
    </DropdownMenuContent>
  </DropdownMenu>
)}
```

### Pattern 2: Filter Parser Registration

**What:** Add `owner: parseAsString` to the page's filter parsers so nuqs manages it in the URL.

**Reference:** `frontend/src/hooks/useFilterParams.ts` lines 73-87 (donationFilterParsers)

```typescript
// contactFilterParsers currently (lines 62-71):
export const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  needs_thank_you: parseAsBoolean,
  last_gift_after: parseAsString,
  last_gift_before: parseAsString,
  group: parseAsString,
  ordering: parseAsString,
}

// After change -- add owner:
export const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  needs_thank_you: parseAsBoolean,
  last_gift_after: parseAsString,
  last_gift_before: parseAsString,
  group: parseAsString,
  ordering: parseAsString,
  owner: parseAsString,       // <-- NEW
}
```

### Pattern 3: Preset Nulling for New Filter Fields

**What:** Every preset's `getParams()` must explicitly set new filter fields to `null` to prevent filter stacking between presets.

**Reference:** `frontend/src/lib/filter-presets.ts` -- donation presets null `owner` (lines 51-60)

```typescript
// Current contact presets:
export const contactPresets: FilterPreset[] = [
  {
    id: "needs-thank-you",
    label: "Needs Thank You",
    description: "Contacts with unthanked donations",
    getParams: () => ({
      needs_thank_you: "true",
      status: null,
      last_gift_after: null,
      last_gift_before: null,
      // MUST ADD: owner: null,
    }),
  },
  // ... same for "this-month" preset
]
```

### Pattern 4: FilterBar Label Registration

**What:** The `filterLabels` prop maps URL param keys to human-readable badge labels. The `filterValueLabels` prop maps raw values to display text.

**Reference:** `DonationList.tsx` lines 208-219

```tsx
filterLabels={{
  // ... existing keys ...
  owner: "Owner",  // <-- add this
}}
```

For the owner filter, the badge value resolves via FilterBar's default `String(value)`, which would show the user ID. To show the owner's name in the badge, we could add a `filterValueLabels` entry for `owner`, but the DonationList does NOT do this -- it just shows the ID. This is a minor UX detail the planner can decide on.

### Anti-Patterns to Avoid
- **Adding owner to ContactFilterSet:** The owner filter is intentionally NOT in the django-filters FilterSet for security reasons (Phase 22-01 decision). It's handled in `get_queryset()` with explicit role checking. Do NOT add it to `ContactFilterSet`.
- **Creating a new API endpoint for users:** The `useUsers` hook already fetches all users. Do NOT create a separate endpoint.
- **Forgetting to null `owner` in presets:** This causes filter stacking where switching presets doesn't clear the owner filter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL state management | Custom URL parsing | nuqs `parseAsString` in `contactFilterParsers` | Already integrated, type-safe |
| User list fetching | Custom API call | `useUsers()` hook | Already cached via React Query |
| Admin role checking | Custom middleware | `useAuth().user?.role === "admin"` | Already available from AuthProvider |
| CSV export with owner | New export endpoint | Existing `ContactExportCSVView` | Already handles `?owner=` param |

**Key insight:** The entire backend is already complete. The `ContactListCreateView` and `ContactExportCSVView` both already parse `?owner=<id>` and apply it for admin users. This is purely a frontend UI task.

## Common Pitfalls

### Pitfall 1: Forgetting to Null Owner in Contact Presets
**What goes wrong:** User selects an owner, then clicks a preset. The owner filter persists because the preset doesn't null it, showing filtered results the user doesn't expect.
**Why it happens:** New filter fields need to be explicitly nulled in every preset's `getParams()`.
**How to avoid:** Add `owner: null` to every preset in `contactPresets` array.
**Warning signs:** After clicking a preset, the "Owner" filter badge still appears.

### Pitfall 2: Owner Filter Badge Shows Raw UUID
**What goes wrong:** The filter badge shows the user's UUID instead of their name because `filterValueLabels` doesn't map owner IDs to names.
**Why it happens:** The DonationList currently has this same issue -- it doesn't provide `filterValueLabels` for `owner`.
**How to avoid:** Optionally, build a `filterValueLabels.owner` map from `usersData` to map user IDs to `full_name`. This is an enhancement beyond what DonationList does.
**Warning signs:** Badge reads "Owner: 550e8400-e29b-41d4-a716-446655440000" instead of "Owner: John Smith".

### Pitfall 3: Non-Admin User Sees Empty Dropdown
**What goes wrong:** The `useUsers()` hook returns data even for non-admin users (it fetches `/users/`), but the backend ignores the `owner` param for non-admins.
**Why it happens:** The dropdown is conditionally rendered with `isAdmin &&`, so this is already handled. But if the condition is wrong, non-admins see a non-functional dropdown.
**How to avoid:** Use `user?.role === "admin"` exactly as DonationList does.
**Warning signs:** Staff users see an "All Owners" dropdown that does nothing.

### Pitfall 4: Missing Imports
**What goes wrong:** Build error from missing `useAuth` or `useUsers` imports in ContactList.tsx.
**Why it happens:** ContactList currently doesn't import these -- they must be added.
**How to avoid:** Add both imports: `useAuth` from `@/providers/AuthProvider` and `useUsers` from `@/hooks/useUsers`.
**Warning signs:** TypeScript compilation errors.

## Code Examples

### Complete Change Set for ContactList.tsx

```tsx
// ADD these imports:
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"

// ADD in component body (after useNavigate):
const { user } = useAuth()
const isAdmin = user?.role === "admin"

// ADD after markThankedMutation:
const { data: usersData } = useUsers()

// ADD "owner" to filterLabels prop:
filterLabels={{
  search: "Search",
  status: "Status",
  needs_thank_you: "Needs Thank You",
  last_gift_after: "Gift From",
  last_gift_before: "Gift To",
  group: "Group",
  ordering: "Sort",
  owner: "Owner",           // NEW
}}

// ADD owner dropdown as last child of FilterBar (before </FilterBar>):
{isAdmin && usersData && (
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="secondary" size="sm" className="gap-2">
        <Filter className="h-4 w-4" />
        {filters.owner
          ? usersData.find((u) => String(u.id) === filters.owner)?.full_name || "Owner"
          : "All Owners"}
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent>
      <DropdownMenuItem onClick={() => setFilters({ owner: null, page: 1 })}>
        All Owners
      </DropdownMenuItem>
      {usersData.map((u) => (
        <DropdownMenuItem key={u.id} onClick={() => setFilters({ owner: String(u.id), page: 1 })}>
          {u.full_name}
        </DropdownMenuItem>
      ))}
    </DropdownMenuContent>
  </DropdownMenu>
)}
```

### Complete Change for contactFilterParsers

```typescript
export const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  needs_thank_you: parseAsBoolean,
  last_gift_after: parseAsString,
  last_gift_before: parseAsString,
  group: parseAsString,
  ordering: parseAsString,
  owner: parseAsString,  // NEW
}
```

### Complete Change for contactPresets

```typescript
export const contactPresets: FilterPreset[] = [
  {
    id: "needs-thank-you",
    label: "Needs Thank You",
    description: "Contacts with unthanked donations",
    getParams: () => ({
      needs_thank_you: "true",
      status: null,
      last_gift_after: null,
      last_gift_before: null,
      owner: null,              // NEW
    }),
  },
  {
    id: "this-month",
    label: "This Month",
    description: "Contacts with gifts this month",
    getParams: () => ({
      last_gift_after: fmt(startOfMonth(new Date())),
      last_gift_before: fmt(endOfMonth(new Date())),
      status: null,
      needs_thank_you: null,
      owner: null,              // NEW
    }),
  },
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No owner filter on contacts | Backend ready, no frontend UI | Phase 22-23 | FLT-04 partially closed (donations only) |
| Owner in FilterSet | Owner in get_queryset() for security | Phase 22-01 decision | Admin-only enforcement at view level |

**Deprecated/outdated:** None. All patterns are current.

## Open Questions

1. **Owner badge display value**
   - What we know: The DonationList shows the raw user ID in the owner filter badge (no `filterValueLabels` mapping for owner). This is a known minor UX issue.
   - What's unclear: Should Phase 26 fix this for contacts (and potentially donations too), or match the current DonationList behavior exactly?
   - Recommendation: Match DonationList behavior for consistency. If badge display is improved, do it as a separate follow-up for both pages.

2. **Group filter interaction**
   - What we know: ContactList has a `group` filter in its parsers but no visible dropdown for it in the UI (it's in `filterLabels` but no dropdown widget). The owner filter should be independent of this.
   - What's unclear: Nothing -- they're orthogonal filters.
   - Recommendation: No action needed. The group filter is a separate concern.

## Files to Change

| File | Change | Lines Affected |
|------|--------|----------------|
| `frontend/src/hooks/useFilterParams.ts` | Add `owner: parseAsString` to `contactFilterParsers` | ~1 line added after line 70 |
| `frontend/src/pages/contacts/ContactList.tsx` | Add imports, isAdmin check, useUsers hook, owner dropdown, filterLabels entry | ~25 lines added |
| `frontend/src/lib/filter-presets.ts` | Add `owner: null` to both contact presets | 2 lines added |

**No backend changes needed.** The `ContactListCreateView.get_queryset()` (lines 67-69) and `ContactExportCSVView.get()` (lines 39-40) already handle `?owner=<id>` for admin users.

## Sources

### Primary (HIGH confidence)
- `frontend/src/pages/donations/DonationList.tsx` -- reference implementation of admin owner dropdown (lines 362-384)
- `frontend/src/pages/contacts/ContactList.tsx` -- current state, no owner filter
- `frontend/src/hooks/useFilterParams.ts` -- filter parser definitions (contactFilterParsers vs donationFilterParsers)
- `frontend/src/lib/filter-presets.ts` -- preset nulling pattern
- `apps/contacts/views.py` -- backend owner filter already implemented (lines 67-69)
- `apps/contacts/export_views.py` -- CSV export owner filter already implemented (lines 39-40)
- `apps/contacts/filters.py` -- confirms owner NOT in FilterSet (by design)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- exact pattern already exists in DonationList, copy-paste with adaptation
- Pitfalls: HIGH -- identified from existing code patterns and Phase 22/23 prior decisions

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable -- internal codebase pattern replication)
