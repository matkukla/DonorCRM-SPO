# Architecture Research: Smartsheet Import, Filtering, & Quality Audit

**Domain:** DonorCRM Smartsheet Import & Filtering Integration
**Researched:** 2026-02-16
**Confidence:** HIGH

## Integration Overview

This milestone extends the existing DonorCRM architecture to support:
1. **Smartsheet file import** (Excel/CSV upload with user-defined column mapping)
2. **Comprehensive filtering** for Contacts, Journals, Donations pages
3. **Quality/dark mode audit** (systematic review, not new architecture)

### Key Integration Points

```
Existing Import Pipeline                  NEW: Smartsheet Pipeline
┌────────────────────────┐                ┌────────────────────────┐
│  ImportRun Model       │                │  ColumnMappingConfig   │
│  ImportRowError Model  │                │  (per import session)  │
│  Type-specific parsers │◄───extends─────│  Smartsheet parser     │
│  (funds, entities...)  │                │  (dynamic columns)     │
└────────────────────────┘                └────────────────────────┘

Existing List Pages                       NEW: Filter System
┌────────────────────────┐                ┌────────────────────────┐
│  ContactList           │                │  Enhanced URL params   │
│  JournalList           │◄───adds────────│  FilterBar component   │
│  DonationList          │                │  Multi-filter state    │
│  (basic filters)       │                │  (owner, date, group)  │
└────────────────────────┘                └────────────────────────┘
```

## Component Architecture

### Backend Components (Django)

#### NEW Components

| Component | Type | Responsibility |
|-----------|------|----------------|
| `SmartsheetImportView` | APIView | Handle Excel/CSV upload, validate format, create import session |
| `ColumnMappingView` | APIView | Save/retrieve column mappings, return field choices |
| `SmartsheetProcessor` | Service | Parse Excel/CSV with openpyxl, apply mappings, transform to internal format |
| `ColumnMappingConfig` | Model (session-based) | Store temporary mapping config (optional - can use frontend-only) |

#### MODIFIED Components

| Component | Modification | Reason |
|-----------|-------------|--------|
| `ContactListCreateView` | Add filterset fields: `owner`, `group`, `created_at`, `last_gift_date` | Support comprehensive filtering |
| `JournalListView` | Add filterset fields: `owner`, `created_at`, `status` (if exists) | Support journal filtering |
| `DonationListView` | Add filterset fields: `owner`, `date`, `amount_min`, `amount_max`, `payment_method` | Support donation filtering |
| `ImportRunViewSet` | Add `import_source` field to distinguish SPO vs Smartsheet | Audit trail clarity |

### Frontend Components (React)

#### NEW Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `SmartsheetImportDialog` | `components/imports/` | Multi-step wizard: upload → map columns → validate → import |
| `ColumnMapper` | `components/imports/` | Drag-drop or dropdown UI for mapping source columns to DonorCRM fields |
| `FieldMappingRow` | `components/imports/` | Single row: source column → target field selector with confidence indicator |
| `FilterBar` | `components/shared/` | Reusable filter component (search + dropdowns + date range) |
| `DateRangePicker` | `components/ui/` | Date range selector for filtering |
| `SmartsheetImportTile` | `components/imports/` | Tile for Smartsheet import in Import Center (parallel to SPOImportTile) |

#### MODIFIED Components

| Component | Modification | Reason |
|-----------|-------------|--------|
| `ContactList.tsx` | Add owner, group, date range filters to FilterBar | Comprehensive filtering |
| `JournalList.tsx` | Add owner, created date filters; convert grid to list+filters | Comprehensive filtering |
| `DonationList.tsx` | Add owner, date range, amount range, payment method filters | Comprehensive filtering |
| `ImportCenter.tsx` | Add Smartsheet import tile alongside SPO tiles | New import source |

## Data Flow

### Smartsheet Import Flow

```
1. User uploads Excel/CSV
   │
   ↓ (MultiPartParser)
   SmartsheetImportView.post()
   │
   ├─→ Validate file format (Excel/CSV)
   ├─→ Parse headers with openpyxl/csv.DictReader
   ├─→ Auto-detect possible mappings (fuzzy match field names)
   │
   ↓ (Return headers + suggested mappings)
   Frontend: ColumnMapper UI
   │
   ↓ (User confirms/adjusts mappings)
   POST /api/imports/smartsheet/ with mapping config
   │
   ↓ (SmartsheetProcessor)
   ├─→ Apply column mappings to rows
   ├─→ Transform to internal format (Contact/Donation/Pledge)
   ├─→ Validate each row (reuse existing validators)
   ├─→ Create ImportRun audit record
   ├─→ Bulk import via existing import_contacts/donations/pledges services
   │
   ↓
   Return ImportRun ID + stats (created/updated/errors)
```

### Filter State Flow (Contacts Example)

```
User Action (Filter UI)
   │
   ↓
handleFilterChange() → URL params update
   │
   ↓ (useSearchParams)
URL: /contacts?owner=123&status=donor&group=abc&search=Smith
   │
   ↓ (React Query)
useContacts({ owner, status, group, search })
   │
   ↓ (API request)
GET /api/contacts/?owner=123&status=donor&group=abc&search=Smith
   │
   ↓ (DjangoFilterBackend)
ContactListCreateView.get_queryset()
   ├─→ Apply owner filter
   ├─→ Apply status filter
   ├─→ Apply group filter (M2M through)
   ├─→ Apply search filter
   │
   ↓
Return paginated, filtered results
```

### Column Mapping Auto-Detection

```
Uploaded Headers: ["First Name", "Last Name", "Email Address", "Phone #"]
   │
   ↓ (Fuzzy matching algorithm)
SmartsheetProcessor.auto_detect_mappings()
   │
   ├─→ "First Name" → first_name (confidence: HIGH)
   ├─→ "Last Name" → last_name (confidence: HIGH)
   ├─→ "Email Address" → email (confidence: MEDIUM - variation)
   ├─→ "Phone #" → phone (confidence: LOW - special char)
   │
   ↓
Return mapping suggestions with confidence scores
   │
   ↓ (Frontend ColumnMapper)
Display mappings with confidence indicators
   ├─→ HIGH: green checkmark, auto-confirm
   ├─→ MEDIUM: yellow warning, prompt user
   ├─→ LOW/NONE: red alert, require manual selection
```

## Architectural Patterns

### Pattern 1: Reuse Existing Import Infrastructure

**What:** Smartsheet imports transform to the existing ImportRun/ImportRowError/processor pattern instead of creating parallel infrastructure.

**Why:** Avoid code duplication, leverage existing validation logic, maintain consistent audit trail.

**Implementation:**
```python
# apps/imports/services.py
def import_smartsheet_contacts(file_content, column_mapping, user):
    """
    Parse Smartsheet file with custom column mapping, transform to
    internal format, then delegate to existing import_contacts().
    """
    # Parse with openpyxl or csv.DictReader
    rows = parse_smartsheet_file(file_content)

    # Apply column mapping transformation
    transformed_records = []
    for row in rows:
        mapped_row = apply_column_mapping(row, column_mapping)
        transformed_records.append(mapped_row)

    # Reuse existing validation and import logic
    valid_records, errors = parse_contacts_csv(
        transformed_records_to_csv_format(transformed_records),
        user
    )

    # Reuse existing import service
    count, contacts = import_contacts(valid_records, user)
    return count, errors
```

**Trade-offs:**
- Pro: Minimal new code, validation reuse, consistent error handling
- Pro: ImportRun audit trail works automatically
- Con: Must transform Smartsheet data to match CSV format (small overhead)

### Pattern 2: Frontend-Only Column Mapping State

**What:** Store column mapping configuration in frontend state during the import session instead of persisting to database.

**Why:** Mapping is session-specific, not reusable across imports (user headers vary), avoids unnecessary database table.

**Implementation:**
```typescript
// frontend/src/pages/admin/SmartsheetImport.tsx
const [columnMapping, setColumnMapping] = useState<Record<string, string>>({})

const handleImport = () => {
  // Send mapping config in request body, not persisted server-side
  importSmartsheet.mutate({
    file: uploadedFile,
    column_mapping: columnMapping, // { "First Name": "first_name", ... }
    import_type: "contacts"
  })
}
```

**Trade-offs:**
- Pro: Simpler backend (no new model)
- Pro: No cleanup needed (session-based state)
- Con: User must re-map if they re-upload same file (acceptable for infrequent use)

### Pattern 3: URL Param Sync for Filter State

**What:** Persist filter state in URL query parameters instead of component state.

**Why:** Enables shareable filtered views, browser back/forward works, filter state survives page refresh.

**Implementation:**
```typescript
// frontend/src/pages/contacts/ContactList.tsx
const [searchParams, setSearchParams] = useSearchParams()

const owner = searchParams.get("owner")
const status = searchParams.get("status")
const group = searchParams.get("group")

const handleOwnerFilter = (ownerId: string | null) => {
  const params = new URLSearchParams(searchParams)
  if (ownerId) {
    params.set("owner", ownerId)
  } else {
    params.delete("owner")
  }
  params.set("page", "1") // Reset pagination
  setSearchParams(params)
}
```

**Trade-offs:**
- Pro: Shareable URLs (admin can link to "all donor contacts for user X")
- Pro: Browser back/forward navigates filter history
- Con: URL can get long with many filters (acceptable, not a UX issue)

**EXISTING PATTERN:** DonationList and ContactList already use this pattern. Extend to JournalList.

### Pattern 4: django-filter for Backend Filtering

**What:** Use `django-filter` library's `DjangoFilterBackend` and `filterset_fields` for declarative filtering instead of manual query construction.

**Why:** Automatic query parameter parsing, type coercion, validation, consistent API across list views.

**Implementation:**
```python
# apps/contacts/views.py
class ContactListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'needs_thank_you': ['exact'],
        'owner': ['exact'],          # NEW
        'created_at': ['gte', 'lte'], # NEW (date range)
        'last_gift_date': ['gte', 'lte'], # NEW (date range)
    }
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'created_at', 'last_gift_date', 'total_given']
```

**Trade-offs:**
- Pro: Minimal code (declarative)
- Pro: Auto-generates OpenAPI schema for filters
- Pro: Consistent error handling for invalid filter values
- Con: Less control over complex filter logic (use custom FilterSet class if needed)

**EXISTING PATTERN:** ContactListCreateView already uses DjangoFilterBackend. Extend filterset_fields.

## Recommended Project Structure

### Backend Structure (NEW files only)

```
apps/
├── imports/
│   ├── services.py              # ADD: import_smartsheet_contacts(), parse_smartsheet_file()
│   ├── views.py                 # ADD: SmartsheetImportView, ColumnMappingMetadataView
│   ├── urls.py                  # ADD: smartsheet import endpoints
│   └── tests/
│       └── test_smartsheet.py   # NEW: Smartsheet import tests
```

### Frontend Structure (NEW files only)

```
frontend/src/
├── components/
│   ├── imports/
│   │   ├── SmartsheetImportDialog.tsx   # NEW: Multi-step import wizard
│   │   ├── ColumnMapper.tsx             # NEW: Column mapping UI
│   │   ├── FieldMappingRow.tsx          # NEW: Single mapping row
│   │   └── SmartsheetImportTile.tsx     # NEW: Import Center tile
│   ├── shared/
│   │   ├── FilterBar.tsx                # NEW: Reusable filter component
│   │   └── DateRangePicker.tsx          # NEW: Date range selector
├── pages/
│   ├── contacts/
│   │   └── ContactList.tsx              # MODIFY: Add comprehensive filters
│   ├── journals/
│   │   └── JournalList.tsx              # MODIFY: Add filters, list view
│   └── donations/
│       └── DonationList.tsx             # MODIFY: Add amount/date range filters
├── hooks/
│   └── useSmartsheetImport.ts           # NEW: Import mutation hook
```

## Integration Points

### Smartsheet Import Integration

| Integration Point | How It Connects | Notes |
|------------------|-----------------|-------|
| Import Center UI | Add SmartsheetImportTile alongside SPO tiles | Parallel import source |
| ImportRun model | Add `import_source` field ('spo' \| 'smartsheet') | Distinguish import sources in audit trail |
| Existing parsers | Smartsheet processor transforms to CSV format, then reuses parse_contacts_csv() | Validation reuse |
| Import Center API | New endpoint: `/api/imports/smartsheet/` | POST with file + mapping config |
| Error handling | Reuse ImportRowError model for validation errors | Consistent error reporting |

### Filter Integration

| Integration Point | How It Connects | Notes |
|------------------|-----------------|-------|
| ContactListCreateView | Extend `filterset_fields` dict | Add owner, created_at, last_gift_date |
| JournalListView | Add DjangoFilterBackend, define filterset_fields | New backend filtering support |
| DonationListView | Extend `filterset_fields` dict | Add owner, date range, amount range |
| FilterBar component | Reusable across Contact/Journal/Donation lists | Consistent UI pattern |
| URL params | useSearchParams hook manages filter state | Shareable URLs |

### Quality Audit Integration

**NOT NEW ARCHITECTURE** — Quality audit is a review process, not a feature:
- Review existing components for dark mode class inconsistencies
- Check permission classes for proper enforcement
- Audit API endpoints for consistent error responses
- Review frontend forms for validation completeness

**OUTPUT:** Bug fixes and consistency improvements, not new components.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k imports/month | Current sync import flow sufficient; openpyxl processes Excel in memory (limit: 10MB files) |
| 1k-10k imports/month | Move to async Celery task for files >50 rows (reuse existing ASYNC_THRESHOLD pattern) |
| 10k+ imports/month | Add Redis caching for column mapping suggestions (fuzzy match results), batch processing |

### Bottlenecks

1. **Excel parsing:** openpyxl loads entire workbook into memory
   - **Mitigation:** For files >10MB, reject with error or use streaming parser (openpyxl read_only mode)
   - **When:** Phase 1 MVP can defer this (most Smartsheet exports <10MB)

2. **Fuzzy matching column headers:** O(n×m) comparison for auto-detection
   - **Mitigation:** Limit to first 100 columns, cache common patterns
   - **When:** Only matters for files with >50 columns (rare)

3. **Filter queries:** M2M group filtering can be slow without proper indexing
   - **Mitigation:** Ensure `groups` M2M table has index on both FKs (already exists in Django)
   - **When:** With >10k contacts and complex group filters

## Anti-Patterns

### Anti-Pattern 1: Creating Parallel Import Infrastructure

**What people do:** Build separate SmartsheetImportRun, SmartsheetRowError models and processors.

**Why it's wrong:** Code duplication, validation divergence, separate audit trails to maintain.

**Do this instead:** Transform Smartsheet data to match existing CSV import format, reuse ImportRun/ImportRowError/validation logic.

### Anti-Pattern 2: Persisting Column Mappings

**What people do:** Create ColumnMappingConfig model to save user's mappings for reuse.

**Why it's wrong:** Smartsheet exports have variable column names (user-defined), mappings aren't reusable, adds database complexity.

**Do this instead:** Store mapping in frontend state during import session, let user re-map if needed (infrequent operation).

### Anti-Pattern 3: Client-Side Filtering for Large Lists

**What people do:** Fetch all contacts, filter in JavaScript with Array.filter().

**Why it's wrong:** Doesn't scale beyond ~500 items, breaks pagination, wastes bandwidth.

**Do this instead:** Use URL params + DjangoFilterBackend for server-side filtering, return only filtered page.

**EXISTING GOOD PATTERN:** ContactList and DonationList already do server-side filtering. JournalList needs this pattern added.

### Anti-Pattern 4: Complex Filter UI on First Iteration

**What people do:** Build multi-select, range sliders, autocomplete for all filters on day 1.

**Why it's wrong:** Over-engineering before validating which filters users actually need.

**Do this instead:** Start with simple dropdowns and text inputs (existing pattern), upgrade to advanced UI only after usage data shows need.

## Excel Processing: openpyxl Integration

### Library Choice

**Recommended:** `openpyxl` (already standard for Django Excel import)

**Why:**
- Pure Python, no external dependencies
- Reads .xlsx (Excel 2010+) format natively
- Supports read_only mode for memory efficiency
- Well-documented, actively maintained

**Alternative:** `pandas` (NOT recommended for this use case)
- Pro: Powerful data manipulation
- Con: Heavy dependency (NumPy), overkill for simple row parsing
- Con: Memory-intensive for large files

### Installation

```bash
# Add to requirements/base.txt
openpyxl>=3.1,<4.0
```

### Usage Pattern

```python
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

def parse_smartsheet_file(file_content, import_type):
    """
    Parse uploaded Excel/CSV file, return headers and preview rows.
    """
    try:
        # Detect file type
        if file_content.startswith(b'PK'):  # Excel magic bytes
            wb = load_workbook(
                filename=io.BytesIO(file_content),
                read_only=True,  # Memory-efficient streaming
                data_only=True   # Read values, not formulas
            )
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            rows = [[cell.value for cell in row] for row in ws.iter_rows(min_row=2, max_row=6)]
        else:  # CSV
            reader = csv.DictReader(io.StringIO(file_content.decode('utf-8')))
            headers = reader.fieldnames
            rows = [dict(row) for row in itertools.islice(reader, 5)]

        return {
            'headers': headers,
            'preview_rows': rows,
            'suggested_mappings': auto_detect_mappings(headers, import_type)
        }
    except InvalidFileException:
        raise ValidationError("Invalid Excel file format")
```

### Auto-Detection Algorithm

```python
def auto_detect_mappings(uploaded_headers, import_type):
    """
    Fuzzy match uploaded headers to DonorCRM fields.
    Returns dict: { uploaded_header: (target_field, confidence) }
    """
    from difflib import SequenceMatcher

    # Field patterns for contact import
    FIELD_PATTERNS = {
        'first_name': ['first', 'fname', 'first name', 'firstname'],
        'last_name': ['last', 'lname', 'last name', 'lastname'],
        'email': ['email', 'e-mail', 'email address'],
        'phone': ['phone', 'telephone', 'mobile', 'cell'],
        'street_address': ['address', 'street', 'street address'],
        'city': ['city', 'town'],
        'state': ['state', 'province', 'region'],
        'postal_code': ['zip', 'postal', 'postal code', 'zipcode'],
    }

    mappings = {}
    for header in uploaded_headers:
        header_lower = header.lower().strip()
        best_match = None
        best_score = 0

        for field, patterns in FIELD_PATTERNS.items():
            for pattern in patterns:
                score = SequenceMatcher(None, header_lower, pattern).ratio()
                if score > best_score:
                    best_score = score
                    best_match = field

        # Confidence thresholds
        if best_score > 0.8:
            confidence = 'HIGH'
        elif best_score > 0.6:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'

        mappings[header] = {'field': best_match, 'confidence': confidence}

    return mappings
```

**Trade-offs:**
- Simple fuzzy matching (SequenceMatcher) works for 90% of cases
- For complex cases (abbreviations, non-English), user corrects in UI
- Could upgrade to ML-based matching later if needed (defer for MVP)

## Sources

**Excel Processing:**
- [openpyxl PyPI](https://pypi.org/project/openpyxl/)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/en/stable/)
- [Python Circle: Upload and Process Excel in Django](https://pythoncircle.com/post/591/how-to-upload-and-process-the-excel-file-in-django/)

**Column Mapping UI:**
- [Flatfile: Building a Seamless CSV Import Experience](https://flatfile.com/blog/optimizing-csv-import-experiences-flatfile-portal/)
- [Salesforce Data Import: Tools and Best Practices in 2026](https://litextension.com/blog/salesforce-data-import/)

**Existing Codebase:**
- ContactList.tsx (URL param filtering pattern)
- DonationList.tsx (server-side filtering pattern)
- apps/imports/views.py (existing import pipeline)
- apps/imports/services.py (CSV parsing and validation)

---
*Architecture research for: DonorCRM Smartsheet Import & Filtering*
*Researched: 2026-02-16*
