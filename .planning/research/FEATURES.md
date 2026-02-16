# Feature Research

**Domain:** Smartsheet Import, List Page Filtering, Quality Audit
**Researched:** 2026-02-16
**Confidence:** HIGH

## Feature Landscape

### Category 1: Smartsheet File Import with Column Mapping

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| **Excel (.xlsx) + CSV file upload** | Smartsheet exports are .xlsx by default, CSV as fallback. Users expect both formats. | LOW | Existing `MultiPartParser` in import views; add openpyxl for .xlsx |
| **Column mapping UI with dropdown selects** | Smartsheet column names never match CRM fields. Every import tool (Salesforce, HubSpot, Airtable) shows source-to-target mapping. Users expect to see their Excel headers paired with dropdowns of CRM fields. | MEDIUM | Backend must expose field schema per import type; frontend needs new ColumnMapper component |
| **Data preview after mapping** | Users need to verify that "Full Name" correctly mapped to `full_name` before committing. Show first 5-10 rows with mapped columns. | LOW | Reuse existing CSVPreviewTable pattern; feed it mapped data instead of raw CSV |
| **Row-level validation with error CSV download** | When row 42 has an invalid email, user needs to know which row and what's wrong. Existing pattern already does this for SPO imports. | LOW | Reuse ImportRowError model and error CSV download; no new work |
| **File format detection** | Detect .xlsx vs .csv automatically from file content (magic bytes), not just extension. Users rename files. | LOW | Check `PK` magic bytes for .xlsx, fall back to CSV parsing |
| **Formula injection prevention on import** | Cells starting with `=`, `+`, `-`, `@` must be sanitized. Existing exports have this (services.py:521), but imports do NOT. Security table stakes. | LOW | Add FORMULA_PREFIXES check to Smartsheet parser, matching existing export sanitization |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends On |
|---------|-------------------|------------|------------|
| **Auto-detect column mappings** | Fuzzy match "Email Address" to `email`, "First Name" to `first_name`. Saves 80% of manual mapping work for common headers. Uses difflib.SequenceMatcher with pattern dictionaries. | LOW-MEDIUM | Column mapping UI must exist first; auto-detect populates dropdowns with suggestions |
| **Mapping confidence indicators** | GREEN checkmark for high-confidence matches (>0.8), YELLOW for medium (>0.6), RED for low/unmapped. User immediately sees what needs attention. | LOW | Auto-detect must return confidence scores |
| **Save/reuse column mapping templates** | Users importing from same Smartsheet repeatedly save hours. Store in localStorage keyed by import type. | MEDIUM | Column mapping UI must exist; localStorage persistence layer |
| **Import type selection in Smartsheet flow** | User picks "Contacts", "Donations", "Pledges" as the target type. Different types have different target fields. | LOW | Backend field schema endpoint must support all 4 types |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Multi-sheet Excel import** | "My Smartsheet export has multiple tabs" | Tab selection UI adds complexity; user confusion about which tab maps to which type; error surface multiplies | **Document single-sheet export.** Most Smartsheet exports are single-sheet. Show clear error: "This file has 3 sheets. Please export a single sheet." |
| **Drag-and-drop column mapping** | "I want to drag Excel columns onto CRM fields" | HIGH implementation cost with @dnd-kit. Accessibility nightmare (keyboard, screen reader, mobile). Dropdown mapping covers 100% of use cases with 30% of the effort. | **Dropdown selects per row.** Source column name displayed as label, target field as dropdown. Same result, fully accessible, less code. |
| **Import undo/rollback** | "What if I import wrong data?" | Requires transaction history, unclear semantics (what if data was already edited after import?), database complexity | **Validate-first workflow** (already built). Preview mapped data, validate all rows, show errors. Only commit after user confirms. |
| **Formula/computed column import** | "My Excel has formulas that calculate totals" | Excel formulas don't transfer -- openpyxl with `data_only=True` reads computed values. Evaluating formulas is a security risk. | **Import evaluated values only.** Use `load_workbook(data_only=True)`. Document that formulas import as their last-calculated values. |
| **Real-time import progress bar** | "Show me 37% complete" | WebSocket/SSE infrastructure for <2 second operations. Imports for typical missionary data (500-2000 rows) complete in under 2 seconds. | **Spinner with "Importing X rows..."** Already implemented in ImportDialog. Add Celery with progress only when files exceed 5000 rows. |

---

### Category 2: Comprehensive List Page Filters

**Current state of each list page:**

| Page | Current Filters | Current Pattern | What's Missing |
|------|----------------|-----------------|----------------|
| **ContactList** | search, status dropdown, needs_thank_you toggle | URL params via useSearchParams, server-side via DjangoFilterBackend | Date range (created_at, last_gift_date), group filter, owner filter (admin), amount range (total_given) |
| **DonationList** | search, donation_type dropdown, thanked dropdown | URL params via useSearchParams, server-side via DjangoFilterBackend | Date range (date), amount range (amount), payment_method dropdown, fund filter |
| **JournalList** | NONE (just a card grid) | No filtering, no search, no URL params | Search by name, date range (created_at), is_archived toggle. NOTE: JournalList is a card grid, not a table -- filter pattern needs to work with grid layout. |
| **PledgeList** | status dropdown, is_late toggle | URL params via useSearchParams | Search by donor name, frequency filter, amount range, date range (start_date) |
| **Transactions (Insights)** | date_from/date_to via useState | Component state (NOT URL params -- bug). Loses state on refresh. | Convert to URL params. Add donation_type, payment_method, amount range, donor search. |

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| **Date range filter (start + end)** | Time-based data (donations, journals, transactions) universally needs date filtering. Every financial app has this. | MEDIUM | New DateRangePicker component using existing react-day-picker; backend already supports `__gte`/`__lte` lookups |
| **Amount range filter (min/max)** | Donations and pledges need financial filtering. "Show me all donations over $500." | LOW | Two number inputs; backend `amount__gte`/`amount__lte` via django-filter |
| **Status/category dropdown filters** | ContactList has status, DonationList has type/thanked. Extend to all pages with consistent UX. | LOW | Existing DropdownMenu pattern in ContactList and DonationList; replicate to JournalList, PledgeList |
| **Clear all filters button** | When 4+ filters are active, users need one-click reset. | LOW | Reset all URL params to defaults; show only when filters are active |
| **Filter state in URL params (all pages)** | Filters must survive refresh, be bookmarkable, be shareable. Transactions page currently uses useState -- this is a bug. | LOW | Convert Transactions page from useState to useSearchParams; JournalList needs URL params added |
| **Search on all list pages** | Text search by name/email/donor is expected on every list. JournalList has no search. | LOW | Backend `search_fields` already configured for most views; add to JournalList backend and frontend |
| **Server-side filtering for all pages** | Client-side filtering breaks at 100+ items. All filtering must go through API. JournalList currently loads all journals client-side. | MEDIUM | JournalList backend needs `filterset_fields` extended; ensure all queries include `select_related`/`prefetch_related` |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends On |
|---------|-------------------|------------|------------|
| **Filter presets (quick buttons)** | "Needs Thank You", "This Month", "Late Pledges", "Stalled Contacts" -- one-click common filter combinations. Reduces cognitive load for daily workflows. | LOW | Filter infrastructure must exist; presets are just pre-configured URL params |
| **Active filter summary badges** | "5 filters applied: Status=Donor, Date=Last 30 days..." above the table. Users forget what's active. | LOW | Read from URL params, render Badge components |
| **Export filtered results to CSV** | Download only what you see after filtering. "Export my filtered donor list." | LOW | Reuse existing CSV export; pass current filter params to export endpoint |
| **Group filter for contacts** | Filter contacts by group membership. "Show me all contacts in my 'Church Partners' group." | MEDIUM | Backend needs M2M filter through `groups` table; may need custom FilterSet |
| **Owner filter (admin only)** | Admin filters contacts/donations by missionary. "Show me John's contacts." | LOW | Backend: add `owner` to admin-only FilterSet. Frontend: show owner dropdown only for admin role. SECURITY: must NOT be accessible to non-admin users (PITFALL from EDGE_CASE_AUDIT.md 2.2) |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Advanced query builder (AND/OR logic)** | "I want contacts who are donors AND gave >$500 OR are in group X" | Overwhelming UI for 90% of users. Massive implementation cost. Creates usability issues (users build broken queries). | **Stacked filters with implicit AND.** Covers 95% of use cases. Status=Donor + Amount>500 implicitly ANDs. |
| **Saved filters to database** | "Save my filter combinations across devices" | Requires new UserPreference model, migrations, API endpoints. URL params are already shareable and bookmarkable. | **URL params are the save mechanism.** Users can bookmark filtered views. Browser sync handles cross-device. |
| **Multi-select dropdowns for all filters** | "I want to see Donors AND Major Donors at once" | Complicates URL param serialization, backend query logic, and UI state management. Marginal value. | **Single-select dropdowns for v1.3.** If user feedback demands multi-select, add for highest-demand filters only in v1.4. |
| **Client-side column sorting** | "Let me sort by clicking column headers" | Breaks pagination. If server returns page 1 of 500 results sorted by date, client-side re-sorting only re-sorts those 20 rows. Misleading. | **Server-side ordering** via `OrderingFilter` (already configured in most backend views). Add sort controls to frontend that pass `ordering` param. |

---

### Category 3: Quality Audit (Security, Dark Mode, Code Quality, Performance)

**Current state of issues (from EDGE_CASE_AUDIT.md):**

| Issue | Severity | Category | Lines to Fix |
|-------|----------|----------|-------------|
| Journal grid N+1 queries (351 queries/page) | CRITICAL | Performance | ~40 lines |
| ListAPIView permission bypass | CRITICAL | Security | ~10 lines |
| Cross-user contact access in stage events | CRITICAL | Security | 1 line |
| 59 hardcoded color instances across 13 files | HIGH | Dark Mode | ~59 replacements |
| Float arithmetic in monthly_equivalent | MODERATE | Code Quality | ~5 lines |
| Stats not updated on donation edit | MODERATE | Data Integrity | ~3 lines |
| Dashboard GET side effect | MODERATE | UX | ~10 lines |
| No frontend route guards for roles | HIGH | Security/UX | ~20 lines |

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| **Fix ListAPIView permission bypass** | Any authenticated user can view other users' donations/pledges by UUID. Active security vulnerability. Must fix before adding filters (filters would widen the attack surface). | LOW | Fix `get_queryset()` in ContactDonationsView, ContactPledgesView, ContactJournalEventsView to scope by owner |
| **Fix cross-user contact access in stage events** | Any user can link another user's contact to their journal. 1-line fix. | LOW | Change line 221 in journals/serializers.py to `Contact.objects.get(id=contact_id, owner=user)` |
| **Dark mode color audit -- fix hardcoded colors** | 59 hardcoded color instances (bg-blue-50, text-green-700, border-red-200, etc.) across 13 files. These render invisible or unreadable in dark mode. Toggle exists, but new features break in dark mode. | MEDIUM | Scan all .tsx files; replace hardcoded colors with semantic Tailwind classes (bg-blue-50 -> bg-blue-50 dark:bg-blue-950/50) or CSS variables |
| **WCAG contrast compliance in dark mode** | WCAG 2.1 SC 1.4.3 requires 4.5:1 contrast for normal text, 3:1 for large text/UI. Dark mode must meet same standard. Not optional -- accessibility requirement. | MEDIUM | Depends on fixing hardcoded colors first; then test contrast ratios with WebAIM Contrast Checker |
| **Fix N+1 queries in journal grid** | 351 queries per page load with 50 contacts. Will become unusable at scale. Must fix before adding journal filters (filters increase query load). | MEDIUM | Add `prefetch_related('stage_events', 'decisions')` to JournalContactListCreateView.get_queryset(); rewrite serializer to use prefetched data |
| **File size limits on upload endpoints** | No `DATA_UPLOAD_MAX_MEMORY_SIZE` configured. 50MB upload crashes server (512MB Render free tier). Must fix before adding Smartsheet import. | LOW | Add `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` to settings; add explicit size check in views |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends On |
|---------|-------------------|------------|------------|
| **Fix float arithmetic in monthly_equivalent** | Penny discrepancies in dashboard totals. Not a crash, but missionary sees $83.32 instead of $83.33. Trust issue. | LOW | Replace `float(self.amount) * multiplier` with `Decimal(str(self.amount)) * Decimal(str(multiplier))` in pledges/models.py |
| **Frontend route guards for roles** | read_only user navigates to /contacts/new, fills out form, submits, gets 403. Wasted time. | LOW | Check `user.role` in router config; redirect or show "not authorized" before rendering forms |
| **Fix dashboard GET side effect** | Events marked as "seen" on every GET request, before user actually reads them. | LOW | Move `mark_events_as_not_new()` to separate POST endpoint |
| **React Error Boundary** | Unhandled error = white screen, no recovery. Users must refresh. | LOW | Add Error Boundary at app root with fallback UI |
| **Fix donation edit stat refresh** | Finance user corrects $500 to $50, contact stats stay stale until next donation. | LOW | Remove `if not created: return` guard in donations/signals.py |
| **CSV export formula sanitization** | Exported CSVs with unsanitized data are a CSV injection vector. Import sanitizes, export doesn't. | LOW | Prefix `=`, `+`, `-`, `@` in export functions (5 lines) |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Automated visual regression testing** | "Catch dark mode regressions in CI" | Significant setup cost (Playwright screenshots, baseline management, flaky tests). Overkill for 13 files with hardcoded colors. | **Manual dark mode checklist per PR.** Toggle dark mode, screenshot each affected page. Add to PR template: "Tested in dark mode? Y/N" |
| **Full OWASP penetration test** | "We should do a security audit" | Professional pentest costs $5-20k, overkill for a missionary CRM with <200 users. | **Targeted audit of known issues** from EDGE_CASE_AUDIT.md. Fix the 3 security vulnerabilities identified. Add `ruff` for code quality. Run `bandit` for Python security linting. |
| **Performance profiling infrastructure** | "Set up APM monitoring" | New Relic/Datadog costs money, adds complexity. Most performance issues are known N+1 patterns. | **Django Debug Toolbar in dev.** Profile specific endpoints before and after filter changes. Measure query count, not response time. |

---

## Feature Dependencies

```
SMARTSHEET IMPORT CHAIN:
File size limits (audit) ──must precede──> File Upload (new)
    └──requires──> File format detection (.xlsx/.csv)
        └──requires──> Backend field schema endpoint (new)
            └──requires──> Column Mapping UI (new)
                └──requires──> Data preview with mapped columns
                    └──requires──> Validation (reuse existing)
                        └──requires──> Import execution (reuse existing)
                            └──enhances──> Auto-detect mapping (optional)

FILTER CHAIN:
Permission bypass fix (audit) ──must precede──> Backend filter expansion
    └──requires──> Extended filterset_fields per view
        └──requires──> FilterBar component (new, reusable)
            └──requires──> DateRangePicker component (new)
            └──requires──> URL param sync on all pages
                └──enhances──> Filter presets (optional)
                └──enhances──> Active filter badges (optional)
                └──enhances──> Export filtered results (optional)

QUALITY AUDIT CHAIN:
Security fixes (permission bypass, cross-user access) ──must precede──> Filter expansion
N+1 query fixes ──must precede──> Journal filters (filters increase query load)
File size limits ──must precede──> Smartsheet import
Dark mode hardcoded colors fix ──must precede──> New UI components
    (otherwise new components inherit broken dark mode pattern)

CROSS-CHAIN DEPENDENCIES:
Hardcoded color fixes (audit) ──must precede──> Column Mapping UI + FilterBar
    (new components must use correct semantic classes from the start)
Permission bypass fix (audit) ──must precede──> Owner filter for admin
    (adding owner filter before fixing permissions widens attack surface)
```

### Dependency Notes

- **Security fixes MUST precede filter expansion:** Adding an `owner` field to FilterSet before fixing the ListAPIView permission bypass would create a new privilege escalation vector. Fix permissions first, then add filters.
- **N+1 fixes MUST precede journal filters:** Journal grid already runs 351 queries. Adding filters without `prefetch_related` would make performance worse. Fix queries first.
- **File size limits MUST precede Smartsheet import:** Importing a 50MB Excel file without limits crashes the server. Set limits before the upload endpoint exists.
- **Dark mode fixes MUST precede new UI components:** New components (ColumnMapper, FilterBar, DateRangePicker) must use semantic color classes. If existing code has hardcoded colors, developers copy the broken pattern. Fix the codebase first, then build new components using the correct pattern.
- **Auto-detect enhances Column Mapping:** Optional feature that pre-fills dropdown selections. Mapping UI works without it (just empty dropdowns), but auto-detect makes it much faster.
- **Filter presets enhance FilterBar:** Quick buttons are just pre-built URL param sets. FilterBar must exist first.

---

## MVP Definition

### Launch With (v1.3)

**Smartsheet Import (P1):**
- [ ] **Excel/CSV file upload with format detection** -- Users export from Smartsheet as .xlsx or .csv; both must work
- [ ] **Column mapping UI with dropdown selects** -- Show source column name, dropdown of target CRM fields, per row
- [ ] **Auto-detect common mappings** -- Fuzzy match "Email" to email, "First Name" to first_name; pre-fill dropdowns
- [ ] **Preview mapped data (first 10 rows)** -- Show what the import will look like before committing
- [ ] **Formula injection prevention on import** -- Sanitize cells starting with `=`, `+`, `-`, `@`

**Comprehensive Filters (P1):**
- [ ] **Date range filter component** -- Reusable start/end date picker using existing react-day-picker
- [ ] **Amount range filter (min/max)** -- Two number inputs for financial filtering
- [ ] **Extended status/category filters per page** -- ContactList: group, owner (admin). DonationList: payment_method, fund. PledgeList: frequency, donor search
- [ ] **Fix Transactions page to use URL params** -- Convert from useState to useSearchParams (currently a bug)
- [ ] **Add filters to JournalList** -- Search, date range, is_archived. Convert card grid to support filters.
- [ ] **Clear all filters button** -- Show when any filter is active; reset all params

**Quality Audit (P1):**
- [ ] **Fix ListAPIView permission bypass** -- Scope get_queryset() by owner for non-admin users
- [ ] **Fix cross-user contact access** -- Add owner check in stage event creation
- [ ] **Fix 59 hardcoded dark mode colors** -- Replace with semantic Tailwind classes across 13 files
- [ ] **Fix N+1 queries in journal grid** -- Add prefetch_related, rewrite serializer
- [ ] **Add file size limits to upload endpoints** -- DATA_UPLOAD_MAX_MEMORY_SIZE setting + view-level check
- [ ] **WCAG contrast verification for dark mode** -- Test all pages with contrast checker

### Add After Validation (v1.x)

- [ ] **Save/reuse column mapping templates** -- Trigger: users report repetitive mapping work for same Smartsheet format
- [ ] **Filter presets ("Needs Thank You", "This Month", "Stalled")** -- Trigger: user feedback on common filter combinations
- [ ] **Export filtered results to CSV** -- Trigger: users request "download what I'm seeing"
- [ ] **Active filter summary badges** -- Trigger: user confusion about which filters are active
- [ ] **Frontend route guards for roles** -- Trigger: read_only users hitting 403 errors
- [ ] **Fix float arithmetic in monthly_equivalent** -- Trigger: users report penny discrepancies

### Future Consideration (v2+)

- [ ] **Multi-sheet Excel import** -- Why defer: Most Smartsheet exports are single-sheet; complexity outweighs value
- [ ] **Drag-drop column mapping** -- Why defer: HIGH cost, accessibility challenges; dropdown mapping sufficient
- [ ] **Advanced filter query builder (AND/OR)** -- Why defer: Overwhelming for most users; stacked AND covers 95%
- [ ] **Saved filters (backend persistence)** -- Why defer: URL params already bookmarkable; new model not justified
- [ ] **Real-time import progress** -- Why defer: Imports <2s for typical data; add only when Celery needed for >5k rows
- [ ] **Import undo/rollback** -- Why defer: Validate-first prevents mistakes; undo semantics unclear

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| Fix permission bypass | CRITICAL | LOW | P0 | Audit (first) |
| Fix cross-user contact access | CRITICAL | LOW | P0 | Audit (first) |
| File size limits | HIGH | LOW | P0 | Audit (first) |
| Fix N+1 journal queries | HIGH | MEDIUM | P0 | Audit (first) |
| Dark mode hardcoded colors | HIGH | MEDIUM | P1 | Audit |
| WCAG contrast verification | HIGH | MEDIUM | P1 | Audit |
| Column mapping UI | HIGH | MEDIUM | P1 | Import |
| Excel/CSV file upload | HIGH | LOW | P1 | Import |
| Auto-detect mappings | HIGH | LOW-MEDIUM | P1 | Import |
| Date range filters | HIGH | MEDIUM | P1 | Filters |
| Amount range filters | MEDIUM | LOW | P1 | Filters |
| Extended status filters | HIGH | LOW | P1 | Filters |
| Fix Transactions URL params | MEDIUM | LOW | P1 | Filters |
| JournalList filters | MEDIUM | MEDIUM | P1 | Filters |
| Clear all filters | MEDIUM | LOW | P1 | Filters |
| Save column mappings | MEDIUM | MEDIUM | P2 | Post-v1.3 |
| Filter presets | MEDIUM | LOW | P2 | Post-v1.3 |
| Export filtered results | MEDIUM | LOW | P2 | Post-v1.3 |
| Active filter badges | LOW | LOW | P2 | Post-v1.3 |
| Route guards for roles | MEDIUM | LOW | P2 | Post-v1.3 |
| Float arithmetic fix | LOW | LOW | P2 | Post-v1.3 |
| Drag-drop mapping | MEDIUM | HIGH | P3 | v2+ |
| Advanced query builder | LOW | HIGH | P3 | v2+ |
| Multi-sheet import | LOW | HIGH | P3 | v2+ |

**Priority key:**
- **P0:** Fix before building new features -- security/performance prerequisites
- **P1:** Must have for v1.3 launch -- core functionality defining the milestone
- **P2:** Should have, add when possible -- enhances core, low cost
- **P3:** Nice to have, future consideration -- high cost or low ROI

---

## User Workflows

### Smartsheet Import Workflow

```
1. Admin navigates to Import Center (/admin/imports)
2. Clicks "Smartsheet Import" tile (new, alongside existing SPO tiles)
3. Selects import type: Contacts, Donations, or Pledges
4. Uploads .xlsx or .csv file (drag-drop or click-to-browse)
5. System parses headers, auto-detects column mappings
6. User reviews mapping UI:
   - Left column: Excel header names with sample data
   - Right column: Dropdown of CRM fields (auto-filled with suggestions)
   - Confidence indicators: green/yellow/red per row
   - User adjusts any incorrect mappings
7. Clicks "Preview" -- sees first 10 rows with mapped column names
8. Clicks "Validate" -- system checks all rows, reports errors
9. If errors: downloads error CSV, fixes source file, re-uploads
10. If clean: clicks "Import" -- data committed to database
11. Sees import summary: X created, Y updated, Z errors
```

### Filter Workflow (Contacts Example)

```
1. User navigates to Contacts (/contacts)
2. Sees filter bar: Search | Status | Group | Date Range | Needs Thank You
3. Selects Status = "Donor" -- URL updates to /contacts?status=donor
4. Sets Date Range = "Last 30 days" -- URL: /contacts?status=donor&last_gift_date__gte=2026-01-17
5. Active filter badges appear: "Status: Donor" "Last Gift: Last 30 days"
6. Table updates with server-side filtered results
7. User bookmarks URL -- filter state persists
8. User clicks "Clear Filters" -- URL resets to /contacts
9. User shares URL with admin -- admin sees same filtered view
```

### Quality Audit Workflow

```
Phase 1: Automated scan
  - Run ruff check on Python code
  - Grep for hardcoded color classes in .tsx files
  - Profile query counts on list endpoints with Django Debug Toolbar

Phase 2: Fix security issues
  - Fix permission bypass in 3 views (get_queryset owner scoping)
  - Fix cross-user access in stage events (1 line)
  - Add file size limits to settings and views

Phase 3: Fix dark mode
  - Replace 59 hardcoded colors across 13 files
  - Test each page in dark mode, screenshot for verification
  - Check contrast ratios with WebAIM Contrast Checker

Phase 4: Fix performance
  - Add prefetch_related to journal grid queries
  - Profile before/after to verify improvement (351 queries -> <10)
```

---

## Competitor Feature Analysis

| Feature | Smartsheet Native Export | Salesforce Data Import | Flatfile/CSVBox | Our Approach |
|---------|------------------------|----------------------|-----------------|--------------|
| **Column mapping** | No mapping (exports to raw format) | Auto-detect + manual override | AI-powered mapping + manual | Auto-detect with dropdown override (best of both, no AI cost) |
| **File formats** | .xlsx, .csv | CSV only | CSV, XLSX, TSV, JSON | .xlsx + .csv (matches Smartsheet exports) |
| **Preview** | N/A (export only) | First 10 rows | First 100 rows with statistics | First 10 rows with mapped columns (sufficient for validation) |
| **Error handling** | N/A | Error CSV download | Inline errors + downloadable report | Row-level errors with downloadable CSV (already built, reuse) |
| **Validation** | N/A | Real-time during mapping | Streaming validation | Two-step: Validate all -> Import (prevents partial imports) |
| **Date filters** | Built-in calendar + presets | Calendar widget + "Last 7/30/90 days" | N/A (not a list tool) | Date range picker + future: preset buttons |
| **Amount filters** | Number range slider | Min/max inputs | N/A | Min/max number inputs (simple, explicit) |
| **Filter persistence** | Saved views (backend) | Saved views (backend) | N/A | URL params (bookmarkable, shareable, zero backend cost) |
| **Dark mode** | OS-level sync | Manual toggle | N/A | Manual toggle with WCAG compliance (fixing 59 hardcoded colors) |

---

## Existing Code Reuse Map

Features that can be built by extending existing patterns vs. features requiring new code.

| Feature | Reuse | New Code | Effort |
|---------|-------|----------|--------|
| Excel file upload | Existing MultiPartParser, file validation pattern | openpyxl parsing, format detection | 30% reuse |
| Column mapping UI | Existing Dialog, Select, Card components from Radix | ColumnMapper, FieldMappingRow components | 20% reuse |
| Import execution | Existing parse_contacts_csv, import_contacts, ImportRun, ImportRowError | Transform layer (mapped data -> CSV format) | 80% reuse |
| Date range filter | Existing react-day-picker, Popover components | DateRangePicker wrapper, URL param integration | 60% reuse |
| Contact filters | Existing DjangoFilterBackend, search_fields, URL param pattern | Extend filterset_fields, add FilterBar UI | 70% reuse |
| Donation filters | Existing DjangoFilterBackend, search_fields, URL param pattern | Extend filterset_fields, add date/amount inputs | 70% reuse |
| Journal filters | Existing DjangoFilterBackend (backend), Card grid (frontend) | Add FilterBar to card grid layout, URL param sync | 40% reuse |
| Dark mode fixes | Existing Tailwind dark: prefix, CSS variables | Replace 59 hardcoded classes, no new architecture | 90% reuse (find-replace) |
| Permission fixes | Existing get_queryset() pattern in ContactListCreateView | Add owner scoping to 3 views | 95% reuse (copy pattern) |
| N+1 query fixes | Existing prefetch_related pattern (used elsewhere) | Add prefetches, rewrite serializer methods | 50% reuse |

---

## Sources

### Smartsheet Import & Column Mapping
- [Inside CSVBox: How Column Mapping Really Works](https://blog.csvbox.io/inside-csvbox-column-mapping/) -- Column mapping UI patterns
- [Designing An Attractive Data Importer -- Smashing Magazine](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/) -- Import UX best practices
- [CSV Import Best Practices -- Benedict Roeser](https://benedictroeser.de/2021/03/csv-import-best-practices/) -- Error handling, validation flow
- [Best UI Patterns for File Uploads -- CSVBox](https://blog.csvbox.io/file-upload-patterns/) -- Drag-drop upload widget patterns
- [Data Prep UI Guide -- Adobe Experience Platform](https://experienceleague.adobe.com/en/docs/experience-platform/data-prep/ui/mapping) -- Enterprise mapping UI reference

### List Filtering Patterns
- [Using React Router searchParams to manage filter state](https://cgarethc.medium.com/using-react-router-searchparams-to-manage-filter-state-for-a-list-e515e8e50166) -- URL param filter pattern
- [Managing Filters In the URL in React -- Trustica](https://trustica.cz/en/blog/2025/11/20/url-params-functions/) -- Practical React filter guide (Nov 2025)
- [Complete guide for query parameter filtering in React](https://gist.github.com/tapinambur0508/71a9b7c34a4117a1a5d96eb2761278b6) -- Implementation reference
- [Why URL state matters -- LogRocket](https://blog.logrocket.com/url-state-usesearchparams/) -- URL as single source of truth
- [Filter Reference -- django-filter 25.2](https://django-filter.readthedocs.io/en/stable/ref/filters.html) -- DateFromToRangeFilter, NumberFilter
- [Filtering -- Django REST framework](https://www.django-rest-framework.org/api-guide/filtering/) -- DjangoFilterBackend integration

### Dark Mode & Accessibility
- [Offering a Dark Mode Doesn't Satisfy WCAG Contrast](https://www.boia.org/blog/offering-a-dark-mode-doesnt-satisfy-wcag-color-contrast-requirements) -- Both modes must meet WCAG
- [WCAG Issue #2889: Dark mode and contrast criterion](https://github.com/w3c/wcag/issues/2889) -- If auto-applied, both themes must pass
- [Tailwind Contrast Checker -- TWColors](https://tailwindcolor.tools/tailwind-contrast-checker) -- Tailwind-specific contrast tool
- [InclusiveColors: WCAG accessible palette for Tailwind](https://www.inclusivecolors.com/) -- Systematic color pairing

### Security Audit
- [Django REST Framework -- OWASP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Django_REST_Framework_Cheat_Sheet.html) -- DRF security patterns
- [Django Security -- OWASP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html) -- Django security checklist
- [CSV Injection -- OWASP](https://owasp.org/www-community/attacks/CSV_Injection) -- Formula injection prevention

---
*Feature research for: DonorCRM v1.3 -- Smartsheet Import, Filters & Polish*
*Researched: 2026-02-16*
