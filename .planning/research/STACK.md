# Stack Research

**Domain:** Smartsheet Import, Filtering UI, Quality Audit
**Researched:** 2026-02-16
**Confidence:** HIGH

## Current Project Stack (Verified)

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.12.3, targeting py311+ |
| Backend | Django | 4.2.x (LTS) |
| API | Django REST Framework | 3.14.x |
| Auth | djangorestframework-simplejwt | 5.3.x |
| Filtering | django-filter | 23.x (currently installed) |
| Database | PostgreSQL via psycopg2-binary | 2.9.x |
| Async | Celery + Redis | 5.3.x / 5.0.x |
| Docs | drf-spectacular | 0.27.x |
| Frontend | React | 19.2.0 |
| Types | TypeScript | 5.9.3 |
| Build | Vite | 7.2.4 |
| CSS | Tailwind CSS | 3.4.19 |
| UI | Radix UI primitives | Various (^1.x-^2.x) |
| Tables | TanStack Table | 8.21.3 |
| Data | TanStack Query | 5.90.17 |
| CSV | react-papaparse | 4.4.0 |
| Charts | Recharts | 3.6.0 |
| Dates | date-fns + react-day-picker | 4.1.0 / 9.13.2 |
| Code Quality | black + isort + flake8 | 23.x / 5.12.x / 6.x |

## Recommended Stack Additions

### 1. Excel Parsing (Backend) -- NEW DEPENDENCY

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openpyxl | 3.1.5 | Parse .xlsx files from Smartsheet exports | Industry-standard Python library for modern Excel formats (.xlsx/.xlsm). Lightweight (~2MB vs pandas ~50MB+). Direct cell access with automatic type conversion. Python 3.8-3.14 compatible. 100M+ downloads. The only maintained library for .xlsx reading in Python. |

**Confidence:** HIGH -- verified via [PyPI](https://pypi.org/project/openpyxl/), latest release 2024-06-28, Python >=3.8.

### 2. Filtering (Backend) -- UPGRADE EXISTING

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| django-filter | 24.3 | Custom FilterSet classes with range/lookup filters | **ALREADY INSTALLED** at >=23.0,<24.0. Upgrade to 24.3 for Django 5.1 support, grouped choices on Django 5.0+, and `unknown_field_behavior` option. The project already uses `DjangoFilterBackend` + `filterset_fields` in 6 viewsets but needs custom `FilterSet` classes for date ranges, amount ranges, and text search filters. |

**CRITICAL: NOT 25.2.** Version 25.2 (released 2025-10-05) dropped Django <5.2 and Python <3.10. This project uses Django 4.2 LTS. Version 24.3 is the correct choice: supports Django 4.2+, Python 3.8+, released 2024-08-02.

**Confidence:** HIGH -- verified via [django-filter CHANGES.rst](https://github.com/carltongibson/django-filter/blob/main/CHANGES.rst): v25.2 changelog explicitly states "Dropped support for Django <5.2 LTS" and "Dropped support for Python 3.9."

### 3. Column Mapping UI (Frontend) -- NO NEW DEPENDENCIES

Column mapping for Smartsheet import does NOT need drag-and-drop. The UI pattern is:

- User uploads .xlsx file
- Backend extracts column headers, returns them to frontend
- Frontend renders a mapping form: each CRM field shows a Radix Select dropdown listing the Excel columns
- User selects which Excel column maps to which CRM field
- Submit mapping + file for import

This is a standard form with dropdowns, not a drag-and-drop interface. The project already has:
- `@radix-ui/react-select` (^2.2.6) for accessible dropdowns
- `@radix-ui/react-dialog` (^1.1.15) for the mapping modal
- `lucide-react` for icons

If drag-and-drop column reordering is later needed (unlikely for this feature), `@dnd-kit/core` 6.3.1 is the stable choice. The newer `@dnd-kit/react` 0.3.0 is beta and should not be used yet.

**Confidence:** HIGH -- based on actual codebase analysis. The existing ImportDialog.tsx already uses a multi-step flow (upload -> preview -> validate -> import). Column mapping adds a step between upload and validate using existing Radix Select components.

### 4. Filtering UI (Frontend) -- NO NEW DEPENDENCIES

The project already has everything needed for comprehensive filtering:

| Component | Package | Status | Use For |
|-----------|---------|--------|---------|
| Popover | @radix-ui/react-popover (^1.1.15) | Installed | Filter panel container |
| Select | @radix-ui/react-select (^2.2.6) | Installed | Enum/status dropdowns |
| Checkbox | @radix-ui/react-checkbox (^1.3.3) | Installed | Boolean/multi-select filters |
| Date Picker | react-day-picker (^9.13.2) | Installed | Date range filters |
| Table | @tanstack/react-table (^8.21.3) | Installed | Column sorting, client-side filtering |
| Icons | lucide-react (^0.562.0) | Installed | Filter/clear icons |
| Query | @tanstack/react-query (^5.90.17) | Installed | Refetch with filter params |

**Confidence:** HIGH -- verified all packages in `frontend/package.json`.

### 5. Code Quality Audit (Development) -- NEW + REPLACE EXISTING

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ruff | 0.15.1 | Python linting AND formatting | Replaces black (23.x), isort (5.12.x), and flake8 (6.x) -- all three currently in requirements/dev.txt. Written in Rust, 10-100x faster. 800+ built-in rules. Single config in pyproject.toml. Adopted by pandas, FastAPI, Apache Airflow. The 2026 style guide includes latest formatting conventions. |

**Replaces in requirements/dev.txt:**
```
# REMOVE these three:
black>=23.0,<24.0
isort>=5.12,<6.0
flake8>=6.0,<7.0

# REPLACE with:
ruff>=0.15.1,<1.0
```

**Replaces in pyproject.toml:**
```
# REMOVE [tool.black] and [tool.isort] sections
# ADD [tool.ruff] section
```

**Confidence:** HIGH -- ruff 0.15.1 verified via [PyPI](https://pypi.org/project/ruff/), released 2026-02-12. Python >=3.7 required.

### 6. Accessibility Audit (Development) -- OPTIONAL NEW

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| @axe-core/playwright | 4.11.1 | Automated WCAG accessibility testing | Industry-standard a11y engine (powers Lighthouse). 83 rules for WCAG 2.x violations. Only useful if Playwright is installed for e2e tests. |

**Note:** This project does NOT appear to have Playwright installed. For the quality audit, manual browser DevTools accessibility checks or the axe browser extension are sufficient. Only add @axe-core/playwright if setting up e2e tests.

**Confidence:** MEDIUM -- 4.11.1 verified via [npm](https://www.npmjs.com/package/@axe-core/playwright), but Playwright prerequisite not confirmed in project.

## Installation

### Backend

```bash
# Excel parsing (NEW)
pip install openpyxl>=3.1.5,<4.0

# Filtering (UPGRADE -- stay on 24.x for Django 4.2 compatibility)
pip install django-filter>=24.3,<25.0

# Code quality (DEV ONLY -- replaces black + isort + flake8)
pip install ruff>=0.15.1,<1.0
```

Update `requirements/base.txt`:
```
# Change this line:
django-filter>=23.0,<24.0
# To:
django-filter>=24.3,<25.0

# Add:
openpyxl>=3.1.5,<4.0
```

Update `requirements/dev.txt`:
```
# Remove:
black>=23.0,<24.0
isort>=5.12,<6.0
flake8>=6.0,<7.0

# Add:
ruff>=0.15.1,<1.0
```

### Frontend

```bash
# NO NEW DEPENDENCIES NEEDED
# Column mapping: use existing Radix Select
# Filtering: use existing Radix + TanStack Table
```

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| django-filter 25.x | Requires Django 5.2+, breaks with Django 4.2 LTS | django-filter 24.3 |
| pandas for Excel | 50MB+ dependency, overkill for parsing file uploads | openpyxl (2MB, purpose-built) |
| xlrd for .xlsx | Deprecated since 2020, only supports legacy .xls | openpyxl |
| @dnd-kit/* for column mapping | Over-engineered for dropdown-based mapping. Adds 3 packages + 30KB+ for what Select does natively. | Radix Select (already installed) |
| @dnd-kit/react 0.3.0 | Beta, no official stability timeline, no maintainer response on production readiness | @dnd-kit/core 6.3.1 if drag-drop ever needed |
| react-beautiful-dnd | Archived/unmaintained since 2021 | @dnd-kit/core if drag-drop needed |
| Custom CSV/Excel frontend parser | Backend should parse Excel (openpyxl), frontend only needs to display preview | Backend parsing + API response |
| New charting libraries | Recharts already installed, no new analytics in this milestone | Existing Recharts |
| Playwright + axe-core | Adding e2e framework just for audit is disproportionate | Browser DevTools a11y audit + manual review |

## Alternatives Considered

| Category | Chosen | Alternative | Why Not |
|----------|--------|-------------|---------|
| Excel parsing | openpyxl 3.1.5 | pandas.read_excel | pandas uses openpyxl internally anyway, adds 50MB+ overhead. Only makes sense for data science pipelines, not web file imports. |
| Excel parsing | openpyxl 3.1.5 | xlrd | Deprecated for .xlsx since 2020. Only reads legacy .xls format. Official docs say "use openpyxl." |
| Filtering | django-filter 24.3 | django-filter 25.2 | 25.2 dropped Django 4.2 support. Would require Django upgrade (5.2+) which is out of scope. |
| Filtering | django-filter 24.3 | Raw ORM in get_queryset | Already used in some views (e.g., DonationListCreateView date range). FilterSet classes are cleaner, more maintainable, and auto-generate API docs via drf-spectacular. |
| Column mapping | Radix Select dropdowns | @dnd-kit drag-and-drop | Drag-and-drop is flashy but worse UX for column mapping: harder to see all mappings at once, no keyboard-only workflow, unnecessary complexity. Dropdowns let users see source->target in a table layout. |
| Linting | ruff 0.15.1 | Keep black+isort+flake8 | Three separate tools with three configs vs one tool with one config. ruff is 10-100x faster and has broader rule coverage. Industry has standardized on ruff. |

## Stack Patterns by Use Case

### Smartsheet Excel Import

**Architecture:** Backend-only parsing with frontend column mapping UI.

```
Frontend:                          Backend:
1. Upload .xlsx/.csv file    -->   2. Detect file type
                                   3. Extract headers (openpyxl or csv)
                             <--   4. Return headers list
5. Show column mapping form
   (Radix Select dropdowns)
6. Submit file + mapping     -->   7. Apply mapping to rows
                                   8. Convert to standard dict format
                                   9. Reuse existing validation logic
                                  10. Import to database
                             <--  11. Return results
```

**Integration with existing code:**
```python
# apps/imports/services.py -- add alongside existing parse_*_csv functions
from openpyxl import load_workbook
from io import BytesIO

def extract_headers_from_excel(file_content: bytes) -> list[str]:
    """Extract column headers from first row of Excel file."""
    wb = load_workbook(filename=BytesIO(file_content), read_only=True)
    sheet = wb.active
    return [str(cell.value) for cell in sheet[1] if cell.value is not None]

def parse_excel_with_mapping(
    file_content: bytes,
    column_mapping: dict[str, str]  # {excel_col: crm_field}
) -> list[dict]:
    """Parse Excel file applying column mapping to produce standard dicts."""
    wb = load_workbook(filename=BytesIO(file_content), read_only=True)
    sheet = wb.active
    headers = [str(cell.value) for cell in sheet[1] if cell.value is not None]

    rows = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        raw = dict(zip(headers, row))
        # Apply mapping: rename Excel columns to CRM fields
        mapped = {}
        for excel_col, crm_field in column_mapping.items():
            value = raw.get(excel_col, '')
            # Convert openpyxl types to strings (dates, numbers)
            mapped[crm_field] = str(value) if value is not None else ''
        rows.append(mapped)
    return rows
```

**File type detection in views:**
```python
# Extend existing import views to accept .xlsx
ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}

def get_file_extension(filename: str) -> str:
    return '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

# In view:
ext = get_file_extension(file.name)
if ext not in ALLOWED_EXTENSIONS:
    return Response({'detail': 'File must be CSV or XLSX.'}, status=400)
```

### List Page Filtering

**Current state:** All 6 viewsets already use `DjangoFilterBackend` with basic `filterset_fields`. The upgrade adds custom `FilterSet` classes for richer filtering.

**What already works (no changes needed):**
```python
# contacts/views.py -- already has:
filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
filterset_fields = ['status', 'needs_thank_you']
search_fields = ['first_name', 'last_name', 'email']
```

**What to add -- custom FilterSet classes for range queries:**
```python
# contacts/filters.py -- NEW file
from django_filters import FilterSet, CharFilter, DateFilter, NumberFilter
from apps.contacts.models import Contact

class ContactFilter(FilterSet):
    # Text search (supplements existing search_fields)
    city = CharFilter(lookup_expr='icontains')
    state = CharFilter(lookup_expr='iexact')

    # Date ranges
    created_after = DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = DateFilter(field_name='created_at', lookup_expr='lte')
    last_gift_after = DateFilter(field_name='last_gift_date', lookup_expr='gte')

    # Amount ranges
    total_given_min = NumberFilter(field_name='total_given', lookup_expr='gte')
    total_given_max = NumberFilter(field_name='total_given', lookup_expr='lte')

    class Meta:
        model = Contact
        fields = ['status', 'needs_thank_you']  # Keep existing simple filters

# contacts/views.py -- change filterset_fields to filterset_class:
# filterset_fields = ['status', 'needs_thank_you']  # REMOVE
filterset_class = ContactFilter  # ADD
```

**Frontend pattern (already in use):**
```typescript
// DonationList.tsx already does this pattern:
const donationType = searchParams.get("donation_type") as DonationType | undefined
const thanked = searchParams.get("thanked")

const { data } = useDonations({
  page,
  donation_type: donationType,
  thanked: thanked === "true" ? true : undefined,
})

// Extend with new filter params:
const { data } = useContacts({
  page,
  status: statusFilter,
  total_given_min: amountMin,
  total_given_max: amountMax,
  created_after: dateRange?.from?.toISOString(),
  created_before: dateRange?.to?.toISOString(),
})
```

### Quality Audit

**ruff configuration (replaces [tool.black] and [tool.isort] in pyproject.toml):**
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = [".git", ".venv", "migrations", "node_modules"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors (replaces flake8)
    "W",   # pycodestyle warnings
    "F",   # pyflakes (replaces flake8)
    "I",   # isort (replaces isort)
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "SIM", # flake8-simplify
]

[tool.ruff.lint.isort]
known-first-party = ["apps", "config"]
known-third-party = ["django", "rest_framework"]

[tool.ruff.format]
# Replaces black
quote-style = "double"
```

**Dark mode audit approach (no new tools):**
- Browser DevTools "Emulate CSS prefers-color-scheme: dark"
- Manual review of all pages for contrast issues
- Check for hardcoded colors (e.g., `bg-green-50` in ImportDialog.tsx -- will look wrong in dark mode)
- Verify all Tailwind classes use theme-aware tokens (`text-foreground`, `bg-background`, etc.)

## Version Compatibility Matrix

| Package | Python | Django | React | Notes |
|---------|--------|--------|-------|-------|
| openpyxl 3.1.5 | 3.8-3.14 | N/A | N/A | No framework dependency |
| django-filter 24.3 | 3.8+ | 4.2-5.1 | N/A | Last version supporting Django 4.2 |
| ruff 0.15.1 | 3.7+ | N/A | N/A | Dev tool, no runtime dependency |
| @dnd-kit/core 6.3.1 | N/A | N/A | 16.8+ | NOT NEEDED -- listed for reference only |

**All verified compatible with: Python 3.12.3 + Django 4.2 + React 19.2.0.**

## Sources

**Backend (verified):**
- [openpyxl 3.1.5 on PyPI](https://pypi.org/project/openpyxl/) -- Latest stable, Python >=3.8, released 2024-06-28
- [django-filter CHANGES.rst](https://github.com/carltongibson/django-filter/blob/main/CHANGES.rst) -- Version history, compatibility drops
- [django-filter 25.2 on PyPI](https://pypi.org/project/django-filter/) -- Requires Python >=3.10, Django 5.2+ (INCOMPATIBLE with this project)
- [django-filter 24.3 docs](https://django-filter.readthedocs.io/en/stable/) -- Installation, DRF integration
- [ruff 0.15.1 on PyPI](https://pypi.org/project/ruff/) -- Released 2026-02-12, Python >=3.7

**Frontend (verified):**
- [dnd-kit documentation](https://dndkit.com/) -- @dnd-kit/core 6.3.1 stable, @dnd-kit/react 0.3.0 beta
- [dnd-kit roadmap discussion #1842](https://github.com/clauderic/dnd-kit/discussions/1842) -- No maintainer response on @dnd-kit/react stability
- [@axe-core/playwright on npm](https://www.npmjs.com/package/@axe-core/playwright) -- 4.11.1, requires Playwright peer dep

**Quality audit:**
- [ruff GitHub releases](https://github.com/astral-sh/ruff/releases) -- 2026 style guide, block suppression comments
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/) -- Accessibility standards for audit

---
*Stack research for: Smartsheet Import + Filtering UI + Quality Audit*
*Researched: 2026-02-16*
*Confidence: HIGH -- Critical django-filter version incompatibility caught and corrected. All versions verified with official sources.*
