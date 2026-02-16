# Architecture Research: v1.3 Integration Architecture

**Domain:** DonorCRM Milestone v1.3 -- Smartsheet Import, Comprehensive Filters, Quality Audit
**Researched:** 2026-02-16
**Confidence:** HIGH (based on complete codebase review of existing patterns)

**Note:** This supersedes SMARTSHEET_ARCHITECTURE.md with deeper integration analysis based on full codebase review.

---

## System Overview: What Changes vs What Stays

```
EXISTING (UNCHANGED)                   NEW / MODIFIED
===========================            ===========================

Backend Django Apps                    Backend Changes
+---------------------------+          +---------------------------+
| imports/                  |          | imports/                  |
|   models.py  (ImportRun,  |          |   services.py  +ADD:      |
|   ImportRowError, Fund)   |          |     parse_smartsheet()    |
|   services.py (CSV parse  |          |     auto_detect_mappings()|
|     + import functions)   |          |   views.py  +ADD:         |
|   views.py (per-type      |          |     SmartsheetUploadView  |
|     import views)         |          |     SmartsheetImportView  |
|   tasks.py (async)        |          |     FieldMetadataView     |
+---------------------------+          +---------------------------+
| contacts/views.py         |          | contacts/views.py MODIFY: |
|   ContactListCreateView   |          |   Extend filterset_fields |
|   (status, needs_thank_you|          |   (owner, date ranges,    |
|    search, owner manual)  |          |    group via filterset)    |
+---------------------------+          +---------------------------+
| donations/views.py        |          | donations/views.py MODIFY:|
|   DonationListCreateView  |          |   Add amount range,       |
|   (type, method, thanked, |          |   fund, owner filters     |
|    date range manual)     |          +---------------------------+
+---------------------------+          | journals/views.py MODIFY: |
| pledges/views.py          |          |   Add owner filter for    |
|   PledgeListCreateView    |          |   admin, extend filterset |
|   (status, freq, is_late) |          +---------------------------+
+---------------------------+

Frontend React                         Frontend Changes
+---------------------------+          +---------------------------+
| components/shared/        |          | components/shared/  +ADD: |
|   DataTable.tsx            |          |   FilterBar.tsx           |
+---------------------------+          |   ActiveFilters.tsx       |
| components/imports/        |          +---------------------------+
|   ImportCard.tsx            |          | components/imports/ +ADD: |
|   ImportDialog.tsx          |          |   SmartsheetWizard.tsx   |
|   SPOImportTile.tsx         |          |   ColumnMapper.tsx      |
|   CSVPreviewTable.tsx       |          |   FieldMappingRow.tsx   |
+---------------------------+          +---------------------------+
| pages/contacts/            |          | pages/ MODIFY:           |
|   ContactList.tsx           |          |   ContactList.tsx        |
| pages/donations/           |          |   DonationList.tsx       |
|   DonationList.tsx          |          |   JournalList.tsx        |
| pages/pledges/             |          |   Transactions.tsx       |
|   PledgeList.tsx            |          |   ImportCenter.tsx       |
+---------------------------+          +---------------------------+
```

---

## Component Architecture: New vs Modified

### Backend -- NEW Components

| Component | File | Type | Responsibility |
|-----------|------|------|----------------|
| `SmartsheetUploadView` | `imports/views.py` | APIView | Accept Excel/CSV upload, parse headers, return headers + preview rows + auto-detected mappings |
| `SmartsheetImportView` | `imports/views.py` | APIView | Accept file + confirmed column mapping, transform rows, delegate to existing import services |
| `FieldMetadataView` | `imports/views.py` | APIView | Return available target fields and their metadata (required, type, validation) for mapping UI |
| `parse_smartsheet_file()` | `imports/services.py` | Service function | Parse Excel (openpyxl) or CSV file, extract headers and preview rows |
| `auto_detect_mappings()` | `imports/services.py` | Service function | Fuzzy-match uploaded headers to DonorCRM fields using difflib.SequenceMatcher |
| `apply_column_mapping()` | `imports/services.py` | Service function | Transform Smartsheet rows to internal format using user-confirmed mapping |

### Backend -- MODIFIED Components

| Component | File | Modification | Risk |
|-----------|------|-------------|------|
| `ContactListCreateView` | `contacts/views.py` | Change `filterset_fields` from list to dict with lookup types; add `owner`, `created_at__gte/lte`, `last_gift_date__gte/lte`; remove manual `owner` and `group` filtering from `get_queryset()` and move to filterset | LOW -- existing filters preserved, made declarative |
| `DonationListCreateView` | `donations/views.py` | Extend `filterset_fields` to dict with `amount__gte/lte`, `fund`; move manual `start_date`/`end_date`/`contact` filters into filterset | LOW -- replaces manual code with declarative equivalent |
| `JournalListCreateView` | `journals/views.py` | Add `owner` filter (admin only); extend `filterset_fields` for `is_archived`, `owner` | LOW -- additive change |
| `PledgeListCreateView` | `pledges/views.py` | Add `fund`, `contact__owner` (admin only) to filterset; add search fields | LOW -- additive change |
| `ImportRun` model | `imports/models.py` | Add `import_source` CharField (choices: 'csv', 'smartsheet', default='csv') to distinguish import origins | LOW -- nullable/default field, no migration risk |

### Frontend -- NEW Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `FilterBar` | `components/shared/FilterBar.tsx` | Reusable horizontal filter bar with composable child slots for search, dropdowns, date pickers, toggle buttons; manages URL param sync |
| `ActiveFilters` | `components/shared/ActiveFilters.tsx` | Badge row showing currently active filters with clear-individual and clear-all actions |
| `SmartsheetWizard` | `components/imports/SmartsheetWizard.tsx` | Multi-step dialog: (1) upload file, (2) map columns, (3) preview + validate, (4) confirm import |
| `ColumnMapper` | `components/imports/ColumnMapper.tsx` | Column mapping interface: list of source columns with dropdown target selectors and confidence indicators |
| `FieldMappingRow` | `components/imports/FieldMappingRow.tsx` | Single mapping row: source column name, target field Select, confidence badge (HIGH/MEDIUM/LOW) |
| `useSmartsheetImport` | `hooks/useSmartsheetImport.ts` | React Query mutation hooks for upload and import steps |
| Smartsheet API functions | `api/imports.ts` | New functions: `uploadSmartsheet()`, `importSmartsheet()`, `getFieldMetadata()` |

### Frontend -- MODIFIED Components

| Component | File | Modification | Scope |
|-----------|------|-------------|-------|
| `ContactList.tsx` | `pages/contacts/` | Replace inline filter Card with FilterBar component; add owner dropdown (admin only), date range pickers, group filter; add ActiveFilters badge row | MEDIUM -- restructure filter section, preserve DataTable usage |
| `DonationList.tsx` | `pages/donations/` | Replace inline filter Card with FilterBar; add date range pickers, amount range inputs, payment method dropdown, fund filter | MEDIUM -- same restructure pattern |
| `JournalList.tsx` | `pages/journals/` | Add FilterBar with owner filter (admin only), search, archived toggle; convert card grid to sortable list for filter integration | MEDIUM -- layout change from grid to list+filters |
| `PledgeList.tsx` | `pages/pledges/` | Add FilterBar wrapping existing status/late filters; add frequency filter, fund filter, search | LOW -- wrap existing filters in FilterBar |
| `Transactions.tsx` | `pages/insights/` | Replace inline filter Card with FilterBar; add donation type, payment method, thanked filters alongside existing date range | LOW -- additive |
| `TaskList.tsx` | `pages/tasks/` | Wrap existing filters in FilterBar for visual consistency | LOW -- cosmetic wrap |
| `ImportCenter.tsx` | `pages/admin/` | Add "Smartsheet Import" tile alongside SPO tiles; add new section header | LOW -- additive tile |

---

## Data Flow

### Smartsheet Import Flow (Two-Phase)

```
Phase 1: Upload + Header Extraction
========================================
User selects .xlsx or .csv file
    |
    v (multipart POST)
SmartsheetUploadView.post()
    |
    +-> Validate file extension (.xlsx, .csv)
    +-> Validate file size (<10MB)
    +-> Detect format (magic bytes: PK = xlsx, else csv)
    |
    +-> If xlsx: openpyxl.load_workbook(read_only=True, data_only=True)
    |   Extract ws[1] headers, first 5 data rows
    |
    +-> If csv: csv.DictReader with utf-8-sig encoding
    |   Extract fieldnames, first 5 rows
    |
    +-> auto_detect_mappings(headers, import_type)
    |   Fuzzy match each header to known field patterns
    |   Return confidence: HIGH (>0.8), MEDIUM (>0.6), LOW
    |
    v
Return JSON:
{
  headers: ["First Name", "Last Name", "Email", ...],
  preview_rows: [{...}, {...}, ...],  // first 5 rows
  suggested_mappings: {
    "First Name": { field: "first_name", confidence: "HIGH" },
    "E-mail": { field: "email", confidence: "MEDIUM" },
    ...
  }
}

Phase 2: Confirmed Import
========================================
User confirms/adjusts mappings in UI, re-sends SAME file
    |
    v (POST with file + mapping JSON)
SmartsheetImportView.post()
    |
    +-> Parse file again (same logic as Phase 1)
    +-> Apply column_mapping to transform rows
    |   { "First Name": "first_name", "E-mail": "email", ... }
    |
    +-> For each row: remap source columns to target fields
    +-> Validate formula injection (=, +, -, @ prefixes)
    +-> Serialize transformed rows to CSV-format string
    |
    +-> Delegate to EXISTING parse function:
    |   parse_contacts_csv(csv_string, user)
    |   OR parse_donations_csv(csv_string, user)
    |
    +-> Delegate to EXISTING import function:
    |   import_contacts(valid_records, user)
    |   OR import_donations(valid_records)
    |
    +-> Create ImportRun with import_source='smartsheet'
    |
    v
Return standard import result:
{
  created_count: N,
  updated_count: N,
  error_count: N,
  errors: [...first 20...],
  import_run_id: "uuid"
}
```

**Key design decision:** The Smartsheet import transforms data INTO the existing CSV-compatible format, then delegates to existing parse/import functions. This avoids duplicating validation logic, error handling, and ImportRun audit trail creation. The file is re-uploaded in Phase 2 rather than using temp file storage -- this is simpler (no temp file management, cache TTL, cleanup) and Smartsheet files are typically <10MB so re-upload takes <2 seconds.

### Filter State Flow (All List Pages)

```
URL (single source of truth)
    |
    v (useSearchParams reads)
FilterBar component renders filter controls
    |  initialized from URL params on mount
    |
    v (user changes filter)
handleFilterChange()
    |
    +-> Update URL params via setSearchParams()
    +-> Reset page to 1
    |
    v (URL change triggers re-render)
useSearchParams re-reads params
    |
    v
React Query hook called with new params
    |
    v (API request)
GET /api/contacts/?status=donor&owner=123&created_at__gte=2025-01-01
    |
    v (DjangoFilterBackend)
ContactListCreateView.get_queryset()
    |
    +-> Owner-scoping applied FIRST (non-admin sees only own)
    +-> DjangoFilterBackend applies declared filters
    +-> SearchFilter applies search across configured fields
    +-> OrderingFilter applies sort
    |
    v
Return paginated, filtered JSON
    |
    v
DataTable renders filtered results
ActiveFilters shows badges for active filters
```

**Critical constraint:** `get_queryset()` MUST scope by owner BEFORE DjangoFilterBackend runs. The existing pattern already does this correctly (line 55-63 in `contacts/views.py`). The `owner` filter parameter in filterset_fields is admin-only and lets admins filter within the "all contacts" queryset. A non-admin user sending `?owner=other_user_id` gets an empty result because DjangoFilterBackend filters are applied WITHIN the already-scoped queryset.

---

## Reusable FilterBar Component Architecture

### Design Principles

1. **URL params as single source of truth** -- no separate useState for filter values
2. **Composable** -- each filter is a child element that pages customize
3. **Consistent** -- same visual treatment across all list pages
4. **Backward compatible** -- existing filter behavior preserved, just unified UI

### Component API

```typescript
// components/shared/FilterBar.tsx
interface FilterBarProps {
  children: React.ReactNode  // Filter control slots
}

// Usage in ContactList.tsx
<FilterBar>
  <FilterBar.Search
    placeholder="Search by name or email..."
    paramKey="search"
  />
  <FilterBar.Select
    paramKey="status"
    label="Status"
    options={statusOptions}
  />
  <FilterBar.Select
    paramKey="owner"
    label="Assigned To"
    options={userOptions}
    adminOnly  // Only renders for admin users
  />
  <FilterBar.DateRange
    paramKeyFrom="created_at__gte"
    paramKeyTo="created_at__lte"
    label="Created"
  />
  <FilterBar.Toggle
    paramKey="needs_thank_you"
    label="Needs Thank You"
    icon={Heart}
  />
</FilterBar>
<ActiveFilters />  // Shows badges for active filters
```

### Implementation Pattern

```typescript
// Each sub-component reads/writes URL params directly
function FilterBarSearch({ paramKey, placeholder }: SearchProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [inputValue, setInputValue] = useState(
    searchParams.get(paramKey) || ""  // Initialize from URL
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (inputValue) {
      params.set(paramKey, inputValue)
    } else {
      params.delete(paramKey)
    }
    params.set("page", "1")
    setSearchParams(params)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input value={inputValue} onChange={...} placeholder={placeholder} />
      <Button type="submit" variant="secondary">Search</Button>
    </form>
  )
}
```

### Per-Page Filter Configurations

| Page | Search | Status | Owner (admin) | Date Range | Type/Method | Amount | Toggle | Group |
|------|--------|--------|--------------|------------|-------------|--------|--------|-------|
| ContactList | name, email | contact status | yes | created_at, last_gift_date | -- | -- | needs_thank_you | group |
| DonationList | donor name | -- | yes | date | donation_type, payment_method | amount range | thanked | -- |
| PledgeList | donor name | pledge status | yes | -- | frequency | -- | is_late | fund |
| JournalList | journal name | -- | yes | created_at | -- | -- | is_archived | -- |
| TaskList | task title | task status | -- | -- | task_type, priority | -- | -- | -- |
| Transactions | -- | -- | -- | date range | donation_type, payment_method | -- | thanked | -- |

---

## Backend Filter Architecture

### Current State Analysis

The codebase uses three different filter patterns across list views:

1. **Declarative filterset_fields list (ContactList, DonationList, PledgeList):** `filterset_fields = ['status', 'needs_thank_you']` -- cleanest pattern
2. **Manual get_queryset filtering (ContactList owner/group, DonationList date/contact):** Hand-written `if request.query_params.get('owner')` blocks
3. **No filtering (JournalList):** Only search and ordering

**Target state:** Migrate ALL filtering to declarative `filterset_fields` dict syntax. This eliminates manual query param parsing, provides automatic validation, and generates OpenAPI schema entries.

### Migration: ContactListCreateView

```python
# BEFORE (contacts/views.py lines 49-75)
class ContactListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'created_at', 'last_gift_date', 'total_given']
    ordering = ['last_name', 'first_name']
    filterset_fields = ['status', 'needs_thank_you']  # Simple list

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)

        # MANUAL: owner filter for admin
        owner_id = self.request.query_params.get('owner')
        if owner_id and user.role == 'admin':
            queryset = queryset.filter(owner_id=owner_id)

        # MANUAL: group filter
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

        return queryset.select_related('owner')


# AFTER
class ContactListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'created_at', 'last_gift_date', 'total_given']
    ordering = ['last_name', 'first_name']
    filterset_fields = {
        'status': ['exact'],
        'needs_thank_you': ['exact'],
        'owner': ['exact'],              # replaces manual owner filter
        'groups': ['exact'],             # replaces manual group filter (M2M)
        'created_at': ['gte', 'lte'],    # NEW: date range
        'last_gift_date': ['gte', 'lte'],# NEW: date range
    }

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)
        # Manual filters REMOVED -- now handled by filterset_fields
        return queryset.select_related('owner')
```

**Security note:** The `owner` filter in filterset_fields does NOT create a permission bypass because `get_queryset()` already scopes to `owner=user` for non-admins. DjangoFilterBackend filters are applied WITHIN the queryset returned by `get_queryset()`, not in place of it.

### Migration: DonationListCreateView

```python
# AFTER
class DonationListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']
    filterset_fields = {
        'donation_type': ['exact'],
        'payment_method': ['exact'],
        'thanked': ['exact'],
        'date': ['gte', 'lte'],           # replaces manual start_date/end_date
        'amount': ['gte', 'lte'],          # NEW: amount range
        'contact': ['exact'],              # replaces manual contact filter
        'fund': ['exact'],                 # NEW: fund filter
        'contact__owner': ['exact'],       # NEW: admin filter by contact owner
    }

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)
        # Manual date/contact filters REMOVED
        return queryset.select_related('contact', 'pledge')
```

**API param change:** Frontend currently sends `start_date` and `end_date`. After migration, params become `date__gte` and `date__lte`. The frontend hook must be updated to match. This is a breaking change for any bookmarked URLs with date filters -- acceptable because the old params will simply be ignored (no filter applied) rather than erroring.

---

## Smartsheet Import: Integration with Existing Pipeline

### Critical Design Decision: Transform, Don't Duplicate

The existing import pipeline has separate parse functions per type, each with specific validation logic:

- `parse_contacts_csv()` -- 80 lines of validation (required fields, email format, dedup, length limits)
- `parse_donations_csv()` -- 130 lines of validation (amount parsing, date parsing, contact lookup, external_id dedup)
- `parse_funds_csv()` -- 70 lines of validation (fund_id, name, status enum)
- `parse_entities_csv()` -- 80 lines of validation (entity_id, name splitting, email format)
- `parse_transactions_csv()` -- 110 lines of validation (FK batch validation, strict mode)
- `parse_pledges_csv()` -- 130 lines of validation (FK validation, enum validation)

The Smartsheet import MUST NOT duplicate these. Instead, it transforms uploaded data into the format these parsers expect, then calls them.

### Import Type Detection

The Smartsheet wizard limits import to contact and donation types (the most common Smartsheet use case). SPO-specific types (funds, entities, transactions, pledges) remain CSV-only because they have fixed column formats.

```python
SMARTSHEET_IMPORT_TYPES = {
    'contacts': {
        'target_fields': {
            'first_name': {'required': True, 'type': 'text', 'max_length': 150},
            'last_name': {'required': True, 'type': 'text', 'max_length': 150},
            'email': {'required': False, 'type': 'email'},
            'phone': {'required': False, 'type': 'text', 'max_length': 20},
            'street_address': {'required': False, 'type': 'text', 'max_length': 255},
            'city': {'required': False, 'type': 'text', 'max_length': 100},
            'state': {'required': False, 'type': 'text', 'max_length': 50},
            'postal_code': {'required': False, 'type': 'text', 'max_length': 20},
            'country': {'required': False, 'type': 'text', 'max_length': 100},
            'notes': {'required': False, 'type': 'text'},
        },
        'parse_function': 'parse_contacts_csv',
    },
    'donations': {
        'target_fields': {
            'contact_email': {'required': False, 'type': 'email', 'group': 'contact_id'},
            'contact_first_name': {'required': False, 'type': 'text', 'group': 'contact_id'},
            'contact_last_name': {'required': False, 'type': 'text', 'group': 'contact_id'},
            'amount': {'required': True, 'type': 'decimal'},
            'date': {'required': True, 'type': 'date'},
            'donation_type': {'required': False, 'type': 'enum'},
            'payment_method': {'required': False, 'type': 'enum'},
            'external_id': {'required': False, 'type': 'text'},
            'notes': {'required': False, 'type': 'text'},
        },
        'parse_function': 'parse_donations_csv',
    },
}
```

### File Format Handling

```python
import io
import csv
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def parse_smartsheet_file(uploaded_file):
    """
    Parse uploaded file (Excel or CSV), return headers and preview rows.

    Args:
        uploaded_file: Django UploadedFile object

    Returns:
        dict with 'headers', 'preview_rows', 'row_count'

    Raises:
        ValidationError for invalid/unsupported files
    """
    # File size check
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError(
            f'File size ({uploaded_file.size // 1024 // 1024}MB) exceeds '
            f'maximum of {MAX_FILE_SIZE // 1024 // 1024}MB.'
        )

    filename = uploaded_file.name.lower()
    content = uploaded_file.read()

    if filename.endswith('.xlsx'):
        return _parse_excel(content)
    elif filename.endswith('.csv'):
        return _parse_csv(content)
    else:
        raise ValidationError(
            'Unsupported file type. Please upload .xlsx or .csv files.'
        )


def _parse_excel(content: bytes) -> dict:
    """Parse Excel file using openpyxl in read-only mode."""
    try:
        wb = load_workbook(
            filename=io.BytesIO(content),
            read_only=True,   # Memory-efficient streaming
            data_only=True    # Read values, not formulas
        )
    except (InvalidFileException, Exception) as e:
        raise ValidationError(f'Invalid Excel file: {str(e)}')

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise ValidationError('File is empty.')

    headers = [str(cell).strip() if cell is not None else '' for cell in rows[0]]
    # Remove empty trailing headers
    while headers and not headers[-1]:
        headers.pop()

    preview = rows[1:6]  # First 5 data rows

    return {
        'headers': headers,
        'preview_rows': [
            {headers[i]: (str(cell).strip() if cell is not None else '')
             for i, cell in enumerate(row) if i < len(headers)}
            for row in preview
        ],
        'row_count': len(rows) - 1,
    }


def _parse_csv(content: bytes) -> dict:
    """Parse CSV file with BOM handling."""
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValidationError('File encoding error. Please use UTF-8.')

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationError('CSV file is empty or has no headers.')

    headers = list(reader.fieldnames)
    preview = []
    row_count = 0
    for i, row in enumerate(reader):
        row_count += 1
        if i < 5:
            preview.append(dict(row))

    return {
        'headers': headers,
        'preview_rows': preview,
        'row_count': row_count,
    }
```

### Auto-Detection Algorithm

```python
from difflib import SequenceMatcher

FIELD_PATTERNS = {
    'first_name': ['first', 'fname', 'first name', 'firstname', 'given name'],
    'last_name': ['last', 'lname', 'last name', 'lastname', 'surname', 'family name'],
    'email': ['email', 'e-mail', 'email address', 'e mail'],
    'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone number', 'phone #'],
    'street_address': ['address', 'street', 'street address', 'address line', 'mailing address'],
    'city': ['city', 'town'],
    'state': ['state', 'province', 'region', 'st'],
    'postal_code': ['zip', 'postal', 'postal code', 'zipcode', 'zip code'],
    'country': ['country', 'nation'],
    'notes': ['notes', 'comments', 'remarks', 'memo'],
    'amount': ['amount', 'gift', 'donation', 'gift amount', 'donation amount', 'total'],
    'date': ['date', 'gift date', 'donation date', 'posted date', 'received date'],
    'contact_email': ['donor email', 'contact email', 'giver email'],
    'contact_first_name': ['donor first', 'contact first', 'giver first'],
    'contact_last_name': ['donor last', 'contact last', 'giver last'],
    'donation_type': ['type', 'gift type', 'donation type'],
    'payment_method': ['method', 'payment', 'payment method', 'payment type'],
    'external_id': ['id', 'external id', 'reference', 'ref', 'transaction id'],
}


def auto_detect_mappings(uploaded_headers, import_type):
    """
    Fuzzy match uploaded headers to DonorCRM fields.
    Returns dict: { uploaded_header: { field, confidence } }
    """
    # Get valid target fields for this import type
    valid_fields = set(SMARTSHEET_IMPORT_TYPES[import_type]['target_fields'].keys())

    mappings = {}
    used_fields = set()  # Prevent duplicate mappings

    for header in uploaded_headers:
        if not header.strip():
            continue

        header_lower = header.lower().strip()
        best_match = None
        best_score = 0

        for field, patterns in FIELD_PATTERNS.items():
            if field not in valid_fields or field in used_fields:
                continue

            for pattern in patterns:
                # Exact match
                if header_lower == pattern:
                    best_score = 1.0
                    best_match = field
                    break

                score = SequenceMatcher(None, header_lower, pattern).ratio()
                if score > best_score:
                    best_score = score
                    best_match = field

            if best_score == 1.0:
                break

        if best_match and best_score > 0.5:
            confidence = 'HIGH' if best_score > 0.8 else 'MEDIUM' if best_score > 0.6 else 'LOW'
            mappings[header] = {'field': best_match, 'confidence': confidence}
            used_fields.add(best_match)
        else:
            mappings[header] = {'field': None, 'confidence': 'NONE'}

    return mappings
```

---

## Quality Audit Architecture

The quality audit is NOT a new feature -- it is a systematic review process applied to existing and newly-added code.

### Audit Scope Matrix

| Category | What to Check | Expected Output |
|----------|--------------|-----------------|
| Dark mode | Every page/component for hard-coded colors (`bg-white`, `text-gray-900`, `border-gray-200`) | Replace with semantic classes (`bg-card`, `text-foreground`, `border-border`) |
| New component dark mode | SmartsheetWizard, ColumnMapper, FilterBar, ActiveFilters | Verify all use Tailwind semantic variables |
| Import Center guidance card | `bg-blue-50 border-blue-200` on line 139 of ImportCenter.tsx | Add `dark:bg-blue-950 dark:border-blue-800` or use semantic |
| Permission consistency | `ListAPIView` subclasses missing queryset scoping | Verify `get_queryset()` scopes by owner for non-admin |
| Float arithmetic | `monthly_equivalent` property in Pledge model | Convert to Decimal math with `quantize()` |
| N+1 queries | Filtered list views with related field access in serializers | Add `prefetch_related`/`select_related` |
| Error handling | Consistent error response format across all import endpoints | Standardize error shape |

### Dark Mode Audit Process

1. Grep for hard-coded color classes across all frontend files
2. For each match, determine if it needs a `dark:` variant or should be replaced with a semantic class
3. Test each page with theme toggle to verify rendering

**Pattern to search for:**

```bash
grep -rn "bg-white\|bg-gray-\|text-gray-\|border-gray-\|bg-blue-50\|bg-green-\|bg-red-\|bg-yellow-" frontend/src/
```

**Semantic replacements:**

| Hard-coded | Semantic Alternative |
|-----------|---------------------|
| `bg-white` | `bg-background` or `bg-card` |
| `text-gray-900` | `text-foreground` |
| `text-gray-500` | `text-muted-foreground` |
| `border-gray-200` | `border-border` |
| `bg-gray-50` | `bg-muted` |
| `bg-blue-50` | `bg-primary/10` or add `dark:bg-blue-950` |

### Permission Audit Scope

Review all `ListAPIView` and `ListCreateAPIView` subclasses:

| View | Current Queryset Scoping | Issue |
|------|-------------------------|-------|
| `ContactListCreateView` | Scoped by owner in `get_queryset()` | OK |
| `DonationListCreateView` | Scoped by `contact__owner` in `get_queryset()` | OK |
| `PledgeListCreateView` | Scoped by `contact__owner` in `get_queryset()` | OK |
| `JournalListCreateView` | Scoped by owner in `get_queryset()` | OK |
| `ContactDonationsView` | Filters by contact_id but no owner check | REVIEW -- permission class `IsContactOwnerOrReadAccess` exists but is object-level |
| `ContactPledgesView` | Same pattern | REVIEW |
| `ContactTasksView` | Scoped by owner for non-admin | OK |

### Tech Debt Items

| Item | Location | Fix |
|------|----------|-----|
| `monthly_equivalent` float arithmetic | `pledges/models.py` | Use `Decimal` division with `quantize(Decimal('0.01'))` |
| N+1 queries in JournalGrid | `journals/serializers.py:101-140` | Add `prefetch_related('stage_events', 'decisions')` |
| Decision update race condition | `journals/serializers.py:295-332` | Add `select_for_update()` inside `transaction.atomic()` |
| Cross-user contact access in stage events | `journals/serializers.py:218-234` | Add `owner=user` filter to Contact lookup |

---

## Recommended Build Order

```
Phase 1: Backend Filter Infrastructure (2-3 days)
    Migrate filterset_fields to dict syntax
    Add new filter params
    Remove manual filter code from get_queryset()
    Update OpenAPI schema
    Add filter-specific tests
    |
    v
Phase 2: Smartsheet Backend (3-4 days)
    Install openpyxl dependency
    Build parse_smartsheet_file()
    Build auto_detect_mappings()
    Build apply_column_mapping()
    Build SmartsheetUploadView + SmartsheetImportView
    Add ImportRun.import_source field + migration
    Test with real Excel/CSV files from multiple sources
    |
    v
Phase 3: FilterBar Frontend + List Page Migrations (3-4 days)
    Build FilterBar composable component
    Build ActiveFilters badge component
    Migrate ContactList.tsx to FilterBar
    Migrate DonationList.tsx to FilterBar
    Add filters to JournalList.tsx
    Migrate PledgeList.tsx to FilterBar
    Wrap TaskList.tsx in FilterBar
    Update Transactions.tsx
    Update React Query hooks with new param names
    |
    v
Phase 4: Smartsheet Frontend Wizard (2-3 days)
    Build FieldMappingRow component
    Build ColumnMapper component
    Build SmartsheetWizard multi-step dialog
    Add SmartsheetImportTile to ImportCenter
    Build useSmartsheetImport hook
    Add API functions to imports.ts
    |
    v
Phase 5: Quality Audit (2-3 days)
    Dark mode grep + fix across all pages
    Permission audit of list views
    Fix monthly_equivalent Decimal arithmetic
    Fix known N+1 queries
    Fix known race conditions
    Verify new features in dark mode
    End-to-end testing
```

### Why This Order

1. **Backend filters first** because they are the smallest backend change with the widest frontend impact -- once backend accepts filter params, all frontend filter work is unblocked
2. **Smartsheet backend second** because openpyxl integration needs testing with real files before the wizard UI is built on top. File parsing edge cases surface here
3. **FilterBar third** because it touches the most pages (6 list pages) and establishes the reusable pattern that the rest of the app follows
4. **Smartsheet wizard fourth** because it is self-contained (only touches ImportCenter page) and depends on the backend being stable
5. **Quality audit last** because it must review ALL new code from phases 1-4. Running it mid-development wastes effort on code that will change

---

## Integration Points Summary

### Smartsheet Import -- Touchpoints

| Integration Point | Existing Code | How Smartsheet Connects | Code Modified? |
|------------------|---------------|------------------------|----------------|
| `parse_contacts_csv()` | `imports/services.py:95` | Smartsheet transforms to CSV-format string, calls this | NO |
| `import_contacts()` | `imports/services.py:178` | Receives validated records from parse function | NO |
| `parse_donations_csv()` | `imports/services.py:203` | Same transform-and-delegate pattern | NO |
| `import_donations()` | `imports/services.py:338` | Receives validated records | NO |
| `ImportRun` model | `imports/models.py:74` | New `import_source` field | YES (additive field) |
| `ImportRowError` model | `imports/models.py:153` | Errors from parse functions use this automatically | NO |
| `imports/urls.py` | `imports/urls.py` | New URL patterns for smartsheet endpoints | YES (additive) |
| `ImportCenter.tsx` | `pages/admin/ImportCenter.tsx` | Add SmartsheetWizard trigger tile | YES (additive) |
| `imports.ts` API | `api/imports.ts` | New functions added | YES (additive) |
| `useImports.ts` hooks | `hooks/useImports.ts` | New hook added | YES (additive) |

### Filter Integration -- Touchpoints

| Integration Point | Existing Code | How Filters Connect | Code Modified? |
|------------------|---------------|---------------------|----------------|
| `ContactListCreateView` | `contacts/views.py:43` | filterset_fields list -> dict, remove manual filters | YES |
| `DonationListCreateView` | `donations/views.py:35` | filterset_fields extended, remove manual filters | YES |
| `PledgeListCreateView` | `pledges/views.py:18` | filterset_fields extended | YES (minor) |
| `JournalListCreateView` | `journals/views.py:38` | Add filterset_fields | YES (additive) |
| `ContactList.tsx` | `pages/contacts/ContactList.tsx:278-325` | Replace filter Card with FilterBar | YES |
| `DonationList.tsx` | `pages/donations/DonationList.tsx:229-287` | Replace filter Card with FilterBar | YES |
| `JournalList.tsx` | `pages/journals/JournalList.tsx` | Add FilterBar (currently has no filters) | YES |
| `PledgeList.tsx` | `pages/pledges/PledgeList.tsx:264-295` | Wrap in FilterBar | YES (minor) |
| `useContacts.ts` | `hooks/useContacts.ts` | Pass new filter params | YES (minor) |
| `useDonations.ts` | `hooks/useDonations.ts` | Change param names (start_date -> date__gte) | YES |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Parallel Import Infrastructure

**What people do:** Create separate `SmartsheetImportRun`, `SmartsheetRowError` models and duplicate validation in `parse_smartsheet_contacts()`.

**Why it's wrong:** Validation divergence. When `parse_contacts_csv()` gets a new rule, the Smartsheet version doesn't. Two code paths, two bug surfaces.

**Do this instead:** Transform Smartsheet data to CSV format, call existing parse functions. One validation pipeline, two input formats.

### Anti-Pattern 2: Client-Side Filter State Separate from URL

**What people do:** Store filter values in `useState`, update URL on "Apply" button click, read URL on mount. Three sources of truth.

**Why it's wrong:** Browser back button breaks. Bookmarks don't restore state. Race conditions between state and URL.

**Do this instead:** URL params are the ONLY source of truth. Read from `useSearchParams()`, write to `setSearchParams()`. Exception: search input text can use local state for keystroke buffering, synced to URL on submit.

### Anti-Pattern 3: Monolithic FilterBar Component

**What people do:** Create one FilterBar with a config object listing all possible filters and conditional rendering logic.

**Why it's wrong:** Every page has different filters. Monolithic component becomes unwieldy, tightly coupled, hard to extend.

**Do this instead:** FilterBar is a layout wrapper (Card with flex-wrap). Filter controls are composable children (FilterBar.Search, FilterBar.Select, etc.). Each page composes its own set.

### Anti-Pattern 4: Complex UI Before Stable Backend

**What people do:** Build polished drag-drop column mapping wizard before backend parsing is tested with real files.

**Why it's wrong:** Backend limitations (encoding issues, empty cells, merged cells, formula cells) force UI redesign.

**Do this instead:** Build and test backend parsing thoroughly with real-world files first. Build simplest possible mapping UI (dropdown selects, not drag-drop).

### Anti-Pattern 5: Quality Audit During Feature Development

**What people do:** Audit dark mode while still building FilterBar, fix issues that get immediately broken by the next commit.

**Why it's wrong:** Wasted effort. Catches issues in code that will change, misses issues in code not yet written.

**Do this instead:** Complete all feature work, then run quality audit as a dedicated final pass.

---

## Scalability Considerations

| Concern | Current Scale (200 users) | At 1000 users | At 5000 users |
|---------|--------------------------|---------------|---------------|
| Filter query performance | Fine with `select_related` | Add `prefetch_related` for M2M (groups) | Consider denormalized filter columns |
| Smartsheet file parsing | Sync processing fine (<10MB) | Same | Add Celery task for >5MB files |
| Import run history | Unbounded list, fine | Add pagination to LatestImportRunsView | Add archival/cleanup for old runs |
| FilterBar URL param length | ~200 chars | Same | Same (URL limit is 2048 chars) |
| Auto-detect mapping | O(n*m) fuzzy match, <100ms | Same | Same (bounded by column count) |

**First bottleneck:** N+1 queries in filtered list views when serializers access related objects. Fix with `prefetch_related()`.

**Second bottleneck:** Large Excel file parsing (>10MB). Fix with file size validation and async Celery processing.

---

## Sources

**Existing Codebase (primary source, HIGH confidence):**
- `apps/imports/views.py` -- 780 lines, complete existing import pipeline
- `apps/imports/services.py` -- 1364 lines, CSV parsing/validation/import
- `apps/imports/models.py` -- ImportRun, ImportRowError, Fund models
- `apps/contacts/views.py` -- ContactListCreateView with DjangoFilterBackend
- `apps/donations/views.py` -- DonationListCreateView with manual filters
- `apps/pledges/views.py` -- PledgeListCreateView with filterset_fields
- `apps/journals/views.py` -- JournalListCreateView (minimal filtering)
- `frontend/src/pages/contacts/ContactList.tsx` -- URL param filter pattern
- `frontend/src/pages/donations/DonationList.tsx` -- Search + dropdown filter pattern
- `frontend/src/pages/admin/ImportCenter.tsx` -- SPO import tile pattern
- `frontend/src/components/shared/DataTable.tsx` -- Reusable table with pagination
- `.planning/EDGE_CASE_AUDIT.md` -- Known issues (N+1, permissions, race conditions)

**DRF Filtering (HIGH confidence):**
- [DRF Filtering Documentation](https://www.django-rest-framework.org/api-guide/filtering/)
- [django-filter Documentation](https://django-filter.readthedocs.io/en/stable/)

**Excel Processing (MEDIUM confidence, needs verification with actual files):**
- [openpyxl Documentation](https://openpyxl.readthedocs.io/en/stable/)
- openpyxl `read_only=True` and `data_only=True` modes for memory-efficient processing

---
*Architecture research for: DonorCRM v1.3 -- Smartsheet Import, Filters & Polish*
*Researched: 2026-02-16*
