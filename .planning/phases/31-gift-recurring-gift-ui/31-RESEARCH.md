# Phase 31: Gift & Recurring Gift UI - Research

**Researched:** 2026-02-23
**Domain:** React frontend UI refactoring -- renaming Donations/Pledges to Gifts/Recurring Gifts, rebuilding list/detail pages against new backend models, adding solicitor credit slide-in panel
**Confidence:** HIGH

## Summary

This phase is a comprehensive frontend UI refactoring. The backend models (Gift, RecurringGift, GiftCredit) and API endpoints are already complete from Phase 30. The frontend still references old Donation/Pledge terminology, types, API paths, and data shapes everywhere. The work involves: (1) creating new API layer + hooks for Gift/RecurringGift endpoints, (2) rewriting list pages with updated columns and filters, (3) building a gift detail slide-in panel with solicitor credit breakdown, (4) merging the Contact detail "Donations" and "Pledges" tabs into a single "Gifts" tab, (5) renaming dashboard labels, (6) creating backend CSV export endpoints for Gift/RecurringGift, and (7) updating routes and sidebar navigation.

The key complexity is the data shape mismatch between old Donation/Pledge models (dollar amounts as strings, donation_type, payment_method, thanked status) and new Gift/RecurringGift models (cents-based amounts with `amount_dollars` computed field, no donation_type/payment_method/thanked fields, but has `description` and solicitor credits). The Gift model is simpler than Donation -- no payment method, no thanked status, no donation type -- while adding GiftCredit for solicitor attribution. The RecurringGift model has expanded status choices (Active/Held/Completed/Cancelled/Terminated) and frequencies (8 options vs 4) compared to old Pledge.

**Primary recommendation:** Create new `api/gifts.ts` and `hooks/useGifts.ts` modules from scratch matching the actual Gift/RecurringGift serializer shapes, then rewrite pages to use them. Do NOT try to adapt old donation/pledge modules -- the data shapes are too different.

<user_constraints>
## User Constraints (from CONTEXT.md — REVISED 2026-02-23)

**CRITICAL: NO RENAME.** All user-facing text stays as "Donations" and "Pledges". The frontend rewires to Gift/RecurringGift API endpoints but keeps all visible labels, URL paths, and CSV headers as-is.

### Locked Decisions
- **NO RENAME** -- All user-facing text stays as "Donations" and "Pledges" (sidebar, page titles, breadcrumbs, buttons, empty states)
- **NO URL RENAME** -- Frontend URL paths stay as /donations and /pledges
- **NO CSV RENAME** -- CSV export filenames and column headers stay as-is (donations.csv, "Date", etc.)
- **NO DASHBOARD LABEL CHANGES** -- Keep "Recent Donations", "Total Donated", "Pledged Monthly Support", etc.
- Credits shown on donation detail view only (not in list page columns)
- Simple table layout: Solicitor Name | Amount | Percentage
- Donation detail opens as a slide-in panel (matching existing User Drilldown pattern)
- Hide credits section entirely when a donation has no solicitor credits
- Donations list: Donor Name | Amount | Date | Fund | Description
- Pledges list: Donor Name | Amount | Frequency | Status | Start Date | Fund
- Same filter set as old pages, same labels
- No fund filter added (keep existing filter set)
- Clicking a donation row opens the slide-in detail panel; donor name is a link to contact page
- Late Pledges section kept as placeholder with "Late detection coming soon" text

### Claude's Discretion
- Exact slide-in panel layout and styling (should match existing drilldown patterns)
- Loading states and error handling for donation detail fetch
- Pledges filter set (status, frequency filters -- follow existing patterns)
- Empty state messages on list pages
- Whether to use a single "Donations" contact tab with two sections or keep two separate tabs

### Deferred Ideas (OUT OF SCOPE)
- Late recurring gift detection (requires fulfillment tracking or date-based heuristic) -- future phase
- Fund filter on Donations list page -- potential future enhancement
- Actual rename of UI terminology from Donations/Pledges to Gifts/Recurring Gifts -- future decision
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-GIFT-01 | Rename "Donations" to "Gifts" across sidebar, page titles, and components | Sidebar.tsx navItems array, Dashboard.tsx stat cards, all page headers, insights sidebar labels |
| UI-GIFT-02 | Rename "Pledges" to "Recurring Gifts" across sidebar, page titles, and components | Sidebar.tsx navItems array, NeedsAttention.tsx, SupportProgress.tsx, GivingSummaryCard.tsx labels |
| UI-GIFT-03 | Gifts list page with existing filters updated for Gift model fields | New api/gifts.ts types, useFilterParams with gift filter parsers, GiftFilterSet backend fields |
| UI-GIFT-04 | Recurring Gifts list page with existing filters updated for RecurringGift model fields | RecurringGiftFilterSet has status + frequency filters, extended status/frequency enums |
| UI-GIFT-05 | Gift detail view showing solicitor credit breakdown | Sheet slide-in panel pattern from UserDrilldownPanel, GiftCredit model with solicitor name + amount |
| UI-GIFT-06 | Contact detail Gifts tab showing gifts linked to that contact | Contact backend already has /contacts/:id/donations/ and /contacts/:id/pledges/ endpoints returning Gift/RecurringGift serializers |
| UI-GIFT-07 | Update CSV exports to use Gift/RecurringGift data | New backend export views needed (gifts app has no export_views.py yet), ExportCSVButton component pattern |
| DASH-02 | Dashboard summary cards and charts updated to query Gift/RecurringGift instead of Donation/Pledge | Backend already returns Gift data via dashboard service; frontend labels need renaming only |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | UI framework | Already in use |
| React Router v6 | 6.x | Routing | Already in use, needed for /gifts and /recurring-gifts routes |
| TanStack React Query | 5.x | Data fetching + caching | Already in use for all API hooks |
| nuqs | latest | URL state management | Already in use via useFilterParams |
| shadcn/ui | latest | UI components (Sheet, Table, Card, Badge) | Already in use for all UI |
| Radix UI | latest | Sheet primitive (slide-in panel) | Already in use via shadcn/ui Sheet |
| @tanstack/react-table | 8.x | Table with column definitions | Already in use via DataTable |
| Lucide React | latest | Icons | Already in use |
| date-fns | latest | Date formatting | Already in use |
| Recharts | latest | Dashboard charts | Already in use |
| Axios | latest | HTTP client | Already in use via apiClient |

### No New Dependencies
This phase requires zero new npm packages. Everything needed is already installed and in use.

## Architecture Patterns

### Current Project Structure (relevant files)
```
frontend/src/
├── api/
│   ├── donations.ts     # OLD -- to be replaced by gifts.ts
│   ├── pledges.ts       # OLD -- to be replaced by gifts.ts
│   ├── dashboard.ts     # Types already use Gift terminology (RecentGift, etc.)
│   └── contacts.ts      # getContactDonations/getContactPledges endpoints
├── hooks/
│   ├── useDonations.ts  # OLD -- to be replaced by useGifts.ts
│   ├── usePledges.ts    # OLD -- to be replaced by useGifts.ts
│   ├── useContacts.ts   # useContactDonations/useContactPledges
│   ├── useDashboard.ts  # Already fetches Gift data
│   └── useFilterParams.ts  # donationFilterParsers, pledgeFilterParsers
├── pages/
│   ├── donations/       # OLD -- to become pages/gifts/
│   │   ├── DonationList.tsx
│   │   ├── DonationDetail.tsx
│   │   └── DonationForm.tsx
│   ├── pledges/         # OLD -- to become pages/recurring-gifts/
│   │   ├── PledgeList.tsx
│   │   ├── PledgeDetail.tsx
│   │   └── PledgeForm.tsx
│   ├── contacts/
│   │   └── ContactDetail.tsx  # Has Donations and Pledges tabs
│   ├── Dashboard.tsx    # Uses RecentDonations, LateDonations, SupportProgress
│   └── insights/        # Pages reference donation/pledge terminology
├── components/
│   ├── layout/Sidebar.tsx     # "Donations" and "Pledges" nav items
│   ├── dashboard/
│   │   ├── RecentDonations.tsx  # Title says "Recent Donations"
│   │   ├── LateDonations.tsx    # Title says "Late Donations"
│   │   ├── SupportProgress.tsx  # References "pledges"
│   │   ├── NeedsAttention.tsx   # "Late Pledges" section
│   │   ├── GivingSummaryCard.tsx # "Recurring Pledges" label
│   │   └── MonthlyGiftsCard.tsx # Already uses "Gifts" terminology
│   └── shared/
│       ├── ExportCSVButton.tsx  # Reusable CSV download component
│       └── FilterBar.tsx        # Filter bar with export integration
├── lib/
│   └── filter-presets.ts  # donationPresets, pledgePresets
└── App.tsx               # Routes: /donations, /pledges paths
```

### Pattern 1: Gift Detail Slide-in Panel (Sheet)
**What:** Use the existing shadcn/ui Sheet component for the gift detail slide-in, matching the UserDrilldownPanel pattern exactly.
**When to use:** When user clicks a gift row in the gifts list page.
**Example:**
```typescript
// Source: existing UserDrilldownPanel.tsx pattern
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"

interface GiftDetailPanelProps {
  open: boolean
  giftId: string | null
  onClose: () => void
}

export function GiftDetailPanel({ open, giftId, onClose }: GiftDetailPanelProps) {
  const { data: gift, isLoading } = useGift(giftId)

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        {isLoading ? (
          <div className="space-y-6">
            {/* Skeleton loading */}
          </div>
        ) : gift ? (
          <div className="space-y-6">
            <SheetHeader>
              <SheetTitle>{formatCurrency(gift.amount_dollars)}</SheetTitle>
              <SheetDescription>
                from {gift.donor_contact_name} on {formatLocalDate(gift.gift_date)}
              </SheetDescription>
            </SheetHeader>
            {/* Gift details */}
            {/* Solicitor credits table (conditionally rendered) */}
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
```

### Pattern 2: API Layer with Gift Types
**What:** New TypeScript interfaces matching the actual Gift serializer output.
**Key difference from old Donation:** Amount is in cents (`amount_cents`) with computed `amount_dollars` as a string. No `donation_type`, `payment_method`, or `thanked` fields. Has `description` instead of `notes`.
**Example:**
```typescript
// Source: apps/gifts/serializers.py GiftSerializer
export interface Gift {
  id: string
  donor_contact: string
  donor_contact_name: string
  fund: string | null
  external_gift_id: string
  amount_cents: number
  amount_dollars: string  // Decimal from serializer
  gift_date: string
  description: string
  created_at: string
  updated_at: string
}

// For the detail view with credits
export interface GiftWithCredits extends Gift {
  credits: GiftCredit[]
}

export interface GiftCredit {
  id: string
  solicitor: string
  solicitor_name: string  // Needs backend serializer update
  amount_cents: number
  amount_dollars: string
}
```

### Pattern 3: Filter Parsers for New Models
**What:** New filter parser definitions matching backend GiftFilterSet and RecurringGiftFilterSet.
**Example:**
```typescript
// Matching apps/gifts/filters.py GiftFilterSet fields
export const giftFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  donor_contact: parseAsString,
  fund: parseAsString,
  gift_date_after: parseAsString,
  gift_date_before: parseAsString,
  min_amount: parseAsString,
  max_amount: parseAsString,
  owner: parseAsString,
  ordering: parseAsString,
}

// Matching apps/gifts/filters.py RecurringGiftFilterSet fields
export const recurringGiftFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  donor_contact: parseAsString,
  fund: parseAsString,
  status: parseAsString,
  frequency: parseAsString,
  ordering: parseAsString,
}
```

### Pattern 4: Contact Gifts Tab (Combined)
**What:** Single "Gifts" tab in ContactDetail with two sections: one-time gifts table and recurring gifts table.
**Example:**
```typescript
<TabsTrigger value="gifts">
  Gifts ({(gifts?.length || 0) + (recurringGifts?.length || 0)})
</TabsTrigger>
<TabsContent value="gifts">
  <Card>
    <CardHeader>
      <CardTitle>One-Time Gifts</CardTitle>
    </CardHeader>
    <CardContent>
      {/* gifts table */}
    </CardContent>
  </Card>
  <Card className="mt-4">
    <CardHeader>
      <CardTitle>Recurring Gifts</CardTitle>
    </CardHeader>
    <CardContent>
      {/* recurring gifts table */}
    </CardContent>
  </Card>
</TabsContent>
```

### Anti-Patterns to Avoid
- **Reusing old Donation/Pledge type interfaces:** Gift has fundamentally different fields (no donation_type, payment_method, thanked). Create fresh types.
- **Dollar amount confusion:** Gift amounts are in cents (amount_cents integer) with amount_dollars as computed Decimal string. Never parse amount_cents as dollars.
- **Old URL aliases:** The backend has `/donations/` and `/pledges/` as backward-compatible aliases to `/gifts/`. Frontend should use `/gifts/` and `/gifts/recurring/` exclusively.
- **Separate solicitor credits API call:** Need to ensure the gift detail endpoint includes credits. Currently the GiftSerializer does NOT include credits -- this needs a backend enhancement or a separate endpoint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slide-in panel | Custom overlay/portal | shadcn/ui Sheet component | Already has accessibility, animation, keyboard handling |
| URL filter state | Manual useState + URL sync | nuqs useQueryStates via useFilterParams | Already handles serialization, browser history, type safety |
| CSV download | Custom fetch + blob handling | ExportCSVButton component | Already handles loading state, Content-Disposition parsing, error toasts |
| Data table with pagination | Custom table rendering | DataTable component with @tanstack/react-table ColumnDef | Already handles loading, pagination, row clicks |
| Currency formatting | Manual string manipulation | formatCurrency helper (already duplicated in many files) | Consistent Intl.NumberFormat usage |
| Date formatting | new Date() parsing | formatLocalDate from lib/utils | Handles UTC date-only string bug |

**Key insight:** Every UI pattern needed for this phase already exists in the codebase. The work is adapting existing patterns to new data shapes and terminology, not building new UI primitives.

## Common Pitfalls

### Pitfall 1: Amount Format Mismatch
**What goes wrong:** Old Donation.amount is a decimal string ("100.00"). New Gift.amount_dollars is also a decimal string but Gift.amount_cents is an integer. Forms that create gifts need to convert dollar input to cents.
**Why it happens:** The Gift model stores cents but displays dollars.
**How to avoid:** Use `amount_dollars` for display (it comes pre-computed from the serializer). For create/update, convert user dollar input to cents: `Math.round(parseFloat(dollarValue) * 100)`.
**Warning signs:** Amounts displaying as 100x too large or too small.

### Pitfall 2: GiftSerializer Missing Credits
**What goes wrong:** The current GiftSerializer does not include `credits` (solicitor credit breakdown). The gift detail panel needs this data.
**Why it happens:** Phase 30 created basic CRUD serializers but didn't add a "detail with credits" serializer.
**How to avoid:** Create a GiftDetailSerializer that includes credits with nested GiftCreditSerializer. Add a credits endpoint or enhance the detail view serializer.
**Warning signs:** Gift detail panel always shows "No solicitor credits" even for imported RE gifts.

### Pitfall 3: Backend Search/Ordering Missing
**What goes wrong:** The current GiftFilterSet and RecurringGiftFilterSet don't have search (text search by donor name) or ordering support. The old DonationList and PledgeList pages use `search` filter.
**Why it happens:** Phase 30 created minimal filter sets.
**How to avoid:** Add SearchFilter and OrderingFilter backends to GiftListCreateView and RecurringGiftListCreateView, with search_fields=['donor_contact__first_name', 'donor_contact__last_name', 'description'].
**Warning signs:** Search box does nothing, sort columns don't work.

### Pitfall 4: Export Endpoints Don't Exist
**What goes wrong:** There are no CSV export endpoints for gifts or recurring gifts. The old /donations/export/csv/ and /pledges/export/csv/ were part of the deleted donation/pledge apps.
**Why it happens:** Phase 30 focused on backend service cutover, not export views.
**How to avoid:** Create new export_views.py in apps/gifts/ following the exact pattern from apps/contacts/export_views.py (Echo class, StreamingHttpResponse, sanitize_csv_value).
**Warning signs:** Export CSV buttons return 404.

### Pitfall 5: UTC Date Display Bug
**What goes wrong:** Date-only strings like "2026-02-01" parsed by `new Date()` display as Jan 31 in US timezones.
**Why it happens:** JavaScript parses YYYY-MM-DD as UTC midnight.
**How to avoid:** Always use `formatLocalDate()` from `@/lib/utils.ts` for date-only fields (gift_date, start_date). This is already documented in project MEMORY.md.
**Warning signs:** Gift dates appearing one day off.

### Pitfall 6: RecurringGift Extended Enums
**What goes wrong:** Old Pledge had 4 statuses (active/paused/completed/cancelled) and 4 frequencies (monthly/quarterly/semi_annual/annual). RecurringGift has 5 statuses (active/held/completed/cancelled/terminated) and 8 frequencies (monthly/quarterly/semi_annually/annually/bimonthly/biweekly/weekly/irregular).
**Why it happens:** Gift models are RE-compatible with more options.
**How to avoid:** Create complete label maps matching all RecurringGiftStatus and RecurringGiftFrequency values. Note: frequency key is `semi_annually` (not `semi_annual`).
**Warning signs:** Unknown status/frequency values showing raw enum strings.

### Pitfall 7: Stale React Query Cache Keys
**What goes wrong:** Changing from "donations" to "gifts" query keys means old cached data won't invalidate properly if any code still uses old keys.
**Why it happens:** Incremental changes that forget to update all invalidation calls.
**How to avoid:** Use new query keys consistently: ["gifts", params], ["gifts", id], ["recurring-gifts", params], etc. Search for all "donations" and "pledges" query key usages.
**Warning signs:** Stale data after mutations, data not refreshing.

### Pitfall 8: Old Import/Export Page References
**What goes wrong:** The ImportExport page and ExportCard components may still reference donation export functions from api/imports.ts.
**Why it happens:** Phase 30 removed old import views but export references may linger.
**How to avoid:** Check apps/imports/views.py for remaining export endpoints. The api/imports.ts `exportDonations()` function calls `/imports/export/donations/` which may return 404/410 now.
**Warning signs:** Export buttons on Import/Export page failing silently.

## Code Examples

### Gift List API Call Pattern
```typescript
// Source: existing pattern from api/donations.ts adapted for Gift model
export async function getGifts(params: Record<string, string> = {}): Promise<PaginatedResponse<Gift>> {
  const response = await apiClient.get<PaginatedResponse<Gift>>("/gifts/", { params })
  return response.data
}
```

### Gift Detail with Credits (Backend Enhancement Needed)
```python
# Source: pattern needed in apps/gifts/serializers.py
class GiftCreditReadSerializer(serializers.ModelSerializer):
    solicitor_name = serializers.CharField(source='solicitor.normalized_name', read_only=True)
    amount_dollars = serializers.DecimalField(
        source='amount_dollars', read_only=True, max_digits=12, decimal_places=2
    )

    class Meta:
        model = GiftCredit
        fields = ['id', 'solicitor', 'solicitor_name', 'amount_cents', 'amount_dollars']

class GiftDetailSerializer(GiftSerializer):
    credits = GiftCreditReadSerializer(many=True, read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True, default=None)

    class Meta(GiftSerializer.Meta):
        fields = GiftSerializer.Meta.fields + ['credits', 'fund_name']
```

### CSV Export View Pattern
```python
# Source: pattern from apps/contacts/export_views.py
class GiftExportCSVView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Gift.objects.select_related('donor_contact', 'fund').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(donor_contact__owner=user)
        filterset = GiftFilterSet(request.query_params, queryset=qs)
        filtered_qs = filterset.qs[:10000]

        filename = f'gifts_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            yield writer.writerow(['Donor Name', 'Amount', 'Gift Date', 'Fund', 'Description'])
            for gift in filtered_qs:
                yield writer.writerow([
                    sanitize_csv_value(gift.donor_contact.full_name),
                    str(gift.amount_dollars),
                    gift.gift_date.isoformat(),
                    sanitize_csv_value(gift.fund.name if gift.fund else ''),
                    sanitize_csv_value(gift.description or ''),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

### Sidebar Navigation Update
```typescript
// Source: existing Sidebar.tsx pattern
const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: <LayoutDashboard className="h-5 w-5" /> },
  { label: "Contacts", href: "/contacts", icon: <Users className="h-5 w-5" /> },
  { label: "Gifts", href: "/gifts", icon: <DollarSign className="h-5 w-5" /> },
  { label: "Recurring Gifts", href: "/recurring-gifts", icon: <FileText className="h-5 w-5" /> },
  { label: "Tasks", href: "/tasks", icon: <CheckSquare className="h-5 w-5" /> },
  // ...
]
```

### Dashboard Label Renames
```typescript
// RecentDonations.tsx -> RecentGifts.tsx (rename component)
<CardTitle>Recent Gifts</CardTitle>
<CardDescription>Latest gifts received</CardDescription>

// NeedsAttention.tsx Late Pledges section
// Replace Late Pledge count/list with placeholder:
<div className="p-4 bg-amber-50 ...">
  <span className="font-medium text-amber-900">Late detection coming soon</span>
</div>

// SupportProgress.tsx
<CardTitle>Monthly Support</CardTitle>

// Dashboard stat cards
<StatCard title="Recent Gifts" ... />
<StatCard title="Active Recurring Gifts" ... />
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Donation model (decimal amount) | Gift model (cents-based, amount_dollars property) | Phase 27/30 | All amount handling must use amount_dollars or convert cents |
| Pledge model (4 statuses, 4 frequencies) | RecurringGift model (5 statuses, 8 frequencies) | Phase 27 | Label maps must be expanded |
| /api/v1/donations/ endpoint | /api/v1/gifts/ endpoint (donations/ still works as alias) | Phase 30 | Frontend should use /gifts/ path exclusively |
| Separate Donations/Pledges tabs on contact | Single "Gifts" tab with two sections | Phase 31 (this phase) | UI simplification |
| Donation detail as full page | Gift detail as slide-in panel | Phase 31 (this phase) | New UI pattern for gifts |
| donation_type + payment_method fields | description field only | Phase 27 | Simpler gift data, no type/payment filters |

**Deprecated/outdated:**
- `api/donations.ts`: Will be replaced by `api/gifts.ts`
- `api/pledges.ts`: Will be replaced by `api/gifts.ts` (shared module)
- `hooks/useDonations.ts`: Will be replaced by `hooks/useGifts.ts`
- `hooks/usePledges.ts`: Will be replaced by `hooks/useGifts.ts`
- `donationFilterParsers` / `pledgeFilterParsers`: Will be replaced by gift/recurring gift parsers
- `pages/donations/` directory: Will be replaced by `pages/gifts/`
- `pages/pledges/` directory: Will be replaced by `pages/recurring-gifts/`

## Backend Gaps to Address

These backend changes are needed to support the frontend:

### 1. Gift Detail Serializer with Credits
The current `GiftSerializer` does not include solicitor credits. Need a `GiftDetailSerializer` that nests `GiftCredit` objects with solicitor name.

### 2. Search Support on Gift/RecurringGift Views
The current views use DjangoFilterBackend only. Need to add `SearchFilter` with `search_fields` for donor name search, and `OrderingFilter` for column sorting.

### 3. CSV Export Endpoints
No export endpoints exist for Gift or RecurringGift. Need:
- `GET /api/v1/gifts/export/csv/` -- filtered gift export
- `GET /api/v1/gifts/recurring/export/csv/` -- filtered recurring gift export

### 4. Owner Filter on GiftFilterSet
The current `GiftFilterSet` filters by `donor_contact` and `fund` but not by `owner` (contact owner). Admin users need to filter by owner like the old donation list.

### 5. Fund Name in Gift List Response
The current `GiftSerializer` includes `fund` (UUID) but not the fund name. List page needs fund name for display.

## Comprehensive File Change Map

### Files to CREATE (new)
| File | Purpose |
|------|---------|
| `frontend/src/api/gifts.ts` | Gift + RecurringGift types, API functions |
| `frontend/src/hooks/useGifts.ts` | React Query hooks for Gift + RecurringGift |
| `frontend/src/pages/gifts/GiftList.tsx` | Gifts list page |
| `frontend/src/pages/gifts/GiftDetailPanel.tsx` | Slide-in gift detail with credits |
| `frontend/src/pages/gifts/GiftForm.tsx` | Gift create/edit form |
| `frontend/src/pages/recurring-gifts/RecurringGiftList.tsx` | Recurring gifts list page |
| `frontend/src/pages/recurring-gifts/RecurringGiftDetail.tsx` | Recurring gift detail page |
| `frontend/src/pages/recurring-gifts/RecurringGiftForm.tsx` | Recurring gift create/edit form |
| `apps/gifts/export_views.py` | Backend CSV export views |

### Files to MODIFY (rename labels, update imports)
| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Replace /donations and /pledges routes with /gifts and /recurring-gifts |
| `frontend/src/components/layout/Sidebar.tsx` | Rename nav items to "Gifts" and "Recurring Gifts" |
| `frontend/src/hooks/useFilterParams.ts` | Add giftFilterParsers, recurringGiftFilterParsers |
| `frontend/src/lib/filter-presets.ts` | Replace donationPresets/pledgePresets with giftPresets/recurringGiftPresets |
| `frontend/src/pages/contacts/ContactDetail.tsx` | Merge Donations+Pledges tabs into single "Gifts" tab |
| `frontend/src/hooks/useContacts.ts` | Rename useContactDonations -> useContactGifts, etc. |
| `frontend/src/api/contacts.ts` | Rename getContactDonations -> getContactGifts (keeping same endpoint paths since backend uses same URLs) |
| `frontend/src/pages/Dashboard.tsx` | Update stat card labels, component names |
| `frontend/src/components/dashboard/RecentDonations.tsx` | Rename to RecentGifts, update labels |
| `frontend/src/components/dashboard/LateDonations.tsx` | Update to show "Late detection coming soon" placeholder |
| `frontend/src/components/dashboard/SupportProgress.tsx` | Change title to "Monthly Support" |
| `frontend/src/components/dashboard/NeedsAttention.tsx` | Update Late Pledges section label |
| `frontend/src/components/dashboard/GivingSummaryCard.tsx` | Rename "Recurring Pledges" to "Recurring Gifts" |
| `frontend/src/components/dashboard/MonthlyGiftsCard.tsx` | Already uses "Gifts" -- update description text |
| `apps/gifts/serializers.py` | Add GiftDetailSerializer with credits, fund_name |
| `apps/gifts/views.py` | Add search/ordering, use detail serializer for retrieve |
| `apps/gifts/filters.py` | Add owner filter, search support |
| `apps/gifts/urls.py` | Add export CSV URL patterns |

### Files to DELETE (old, replaced)
| File | Reason |
|------|--------|
| `frontend/src/api/donations.ts` | Replaced by api/gifts.ts |
| `frontend/src/api/pledges.ts` | Replaced by api/gifts.ts |
| `frontend/src/hooks/useDonations.ts` | Replaced by hooks/useGifts.ts |
| `frontend/src/hooks/usePledges.ts` | Replaced by hooks/useGifts.ts |
| `frontend/src/pages/donations/` (directory) | Replaced by pages/gifts/ |
| `frontend/src/pages/pledges/` (directory) | Replaced by pages/recurring-gifts/ |

### Insights Pages -- Label-Only Updates
| File | Change |
|------|--------|
| `frontend/src/pages/insights/DonationsByMonthYear.tsx` | Title: "Gifts by Month/Year" |
| `frontend/src/pages/insights/MonthlyCommitments.tsx` | Title: "Monthly Recurring Gifts" or keep as "Monthly Commitments" |
| `frontend/src/pages/insights/LateDonations.tsx` | Title update, reference recurring gifts |
| `frontend/src/components/layout/Sidebar.tsx` insightsItems | "Donations by Month/Year" -> "Gifts by Month/Year", "Late Donations" -> "Late Gifts" |

## Open Questions

1. **GiftCredit Serializer -- Solicitor Name Display**
   - What we know: GiftCredit model stores solicitor FK. Solicitor model has `normalized_name` field. The GiftSerializer currently does not include credits.
   - What's unclear: Whether to use `normalized_name` ("Last, First" format) or format it as "First Last" for display.
   - Recommendation: Use `normalized_name` as-is since it's the canonical solicitor name from RE imports. The "Last, First" format is standard in fundraising contexts.

2. **Gift Create/Edit Form -- Amount Conversion**
   - What we know: Old DonationForm sends dollar amounts. Gift API expects `amount_cents` (integer).
   - What's unclear: Whether to add an `amount_dollars` write field to the serializer or handle conversion client-side.
   - Recommendation: Handle conversion client-side in the form: `amount_cents: Math.round(parseFloat(dollarInput) * 100)`. This keeps the API consistent.

3. **Old Route Redirects**
   - What we know: Users may have bookmarked /donations or /pledges URLs.
   - What's unclear: Whether to add redirects from old paths to new paths.
   - Recommendation: Add React Router `<Navigate>` redirects from /donations -> /gifts and /pledges -> /recurring-gifts for backward compatibility.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `apps/gifts/models.py` -- Gift, GiftCredit, RecurringGift, RecurringGiftCredit model definitions
- Codebase analysis: `apps/gifts/serializers.py` -- Current GiftSerializer and RecurringGiftSerializer output shapes
- Codebase analysis: `apps/gifts/filters.py` -- GiftFilterSet and RecurringGiftFilterSet available filter fields
- Codebase analysis: `apps/gifts/views.py` -- Current API view configurations
- Codebase analysis: `apps/gifts/urls.py` -- API URL patterns (/gifts/, /gifts/recurring/)
- Codebase analysis: `config/api_urls.py` -- Backend URL routing including aliases
- Codebase analysis: All frontend files listed in Architecture Patterns section

### Secondary (MEDIUM confidence)
- Project decisions from STATE.md -- Phase 27-30 accumulated context on model design choices
- CONTEXT.md locked decisions -- UI terminology and layout specifications

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, zero new dependencies
- Architecture: HIGH - All patterns exist in codebase (Sheet panel, FilterBar, DataTable, CSV export)
- Pitfalls: HIGH - Identified from direct code analysis of old vs new model differences
- Backend gaps: HIGH - Verified by reading current serializers/views/filters vs requirements

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable -- this is internal codebase refactoring, no external dependency risk)
