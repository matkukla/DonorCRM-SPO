# Pitfalls Research: CSV Import Pipeline

**Domain:** CSV Import Pipeline for CRM
**Researched:** 2026-01-30
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Denormalized Field Desynchronization on Bulk Import

**What goes wrong:**
Contact has denormalized giving statistics (`total_given`, `gift_count`, `first_gift_date`, `last_gift_date`, `last_gift_amount`) that are updated via `update_giving_stats()` method. When bulk importing donations via CSV, these fields can become stale or incorrect if the update method isn't called for each affected contact. Users see incorrect donation totals and gift counts.

**Why it happens:**
Django's `bulk_create()` doesn't trigger signals or model save methods. The existing `Contact.update_giving_stats()` method recalculates from donations, but bulk imports skip this unless explicitly invoked. With thousands of rows, calling it for every donation creates N+1 queries.

**How to avoid:**
1. After bulk import completes, collect all affected contact IDs
2. Use `select_for_update()` to lock contact records during batch updates
3. Call `update_giving_stats()` once per unique contact, not once per donation
4. Wrap in transaction to prevent partial updates on failure

**Warning signs:**
- Contact dashboard shows "0 donations" for donors with imported gifts
- Total given amounts don't match sum of donations
- Import succeeds but contact stats remain unchanged
- Concurrent imports on same contacts create race conditions

**Phase to address:**
Phase 2 (Transactions CSV Import) — First phase where denormalized fields are affected by bulk imports. Must establish pattern before Pledges import in Phase 4.

---

### Pitfall 2: Foreign Key Orphan Records (Missing Entity/Fund References)

**What goes wrong:**
Transactions CSV references `entity_id` (Contact) and `fund_id` that don't exist in the database. If validation skips these checks, donations are created pointing to non-existent contacts or funds. Queries fail with 500 errors, reports show broken data, and CASCADE deletes can't clean up properly.

**Why it happens:**
SPO exports contain entity_id and fund_id values from their system. If Entities CSV wasn't imported first, or if it was imported with errors, the IDs won't exist. Developers assume foreign key constraints will catch this, but Django's ORM allows setting FK to any value if you bypass model validation.

**How to avoid:**
1. **Pre-flight validation:** Before importing Transactions, query for all unique entity_id and fund_id values in CSV
2. **Batch existence check:** Use `Contact.objects.filter(external_id__in=entity_ids).values_list('external_id', flat=True)` to get existing IDs
3. **Missing ID report:** Return list of missing IDs with row numbers before import starts
4. **Strict mode enforcement:** Reject entire import if any orphan references exist (PROJECT.md specifies "strict mode only for v1.1")
5. **Import order documentation:** UI should recommend Funds → Entities → Transactions → Pledges

**Warning signs:**
- Import succeeds with "created" count but records are invisible in UI
- Database foreign key constraint errors during import
- Donation queries return empty sets despite import success
- Contact pages throw 404 errors when loading donations

**Phase to address:**
Phase 2 (Transactions CSV Import) — Must validate entity_id references. Phase 1 (Funds) has no foreign keys so less critical. Phase 4 (Pledges) inherits this pattern.

---

### Pitfall 3: Transaction Rollback Without Error Context

**What goes wrong:**
Import processes 5,000 rows in a transaction. Row 4,237 fails validation (e.g., invalid date format). Entire transaction rolls back, import shows "0 created", user has no idea which row failed or why. They retry the same file repeatedly, wasting time.

**Why it happens:**
Django's `atomic()` rolls back on any exception. If validation errors are raised as exceptions (e.g., `IntegrityError`, `ValidationError`), the whole batch fails. Standard practice is wrapping everything in one transaction for atomicity, but this creates all-or-nothing behavior with poor error visibility.

**How to avoid:**
1. **Two-phase import:** Validate all rows first (collecting errors), then import only valid rows in transaction
2. **Row-level error tracking:** Use ImportRowError model (already planned in PROJECT.md) to log row number, error message, and raw data
3. **Partial success reporting:** Show "4,236 created, 764 errors" with downloadable error CSV
4. **Savepoints for batches:** Use nested `atomic(savepoint=True)` blocks for each batch of 1000 rows, allowing partial rollback
5. **Validation before transaction:** Parse entire CSV, validate all rows, collect errors, return early if validation fails

**Warning signs:**
- Import returns "0 created" with vague error message
- Users report "it just doesn't work" without specifics
- Support tickets ask "which row is wrong?"
- Same file imported multiple times with same failure

**Phase to address:**
Phase 1 (Funds CSV Import) — Establish pattern early with simplest entity. All subsequent phases inherit this validation/import separation.

---

### Pitfall 4: Memory Exhaustion on Large File Upload

**What goes wrong:**
User uploads 50MB CSV with 100,000 donations. Server reads entire file into memory with `file.read()`, parses all rows into Python objects, then creates 100,000 Donation model instances in memory before saving. Server runs out of RAM, request times out, or gunicorn worker is killed.

**Why it happens:**
Existing code in `imports/views.py` uses `content = file.read().decode('utf-8')` which loads entire file into memory. PROJECT.md says "synchronous processing for MVP (no Celery)" but doesn't address memory limits. With denormalized fields and FK lookups, each row creates multiple Python objects.

**How to avoid:**
1. **File size limits:** Enforce max upload size (e.g., 10MB) at web server and Django settings level
2. **Streaming CSV parsing:** Use Python's csv.DictReader on file chunks instead of reading full content
3. **Batch processing with bulk_create:** Process 1000 rows at a time, call `bulk_create()`, clear list, repeat
4. **Row count estimation:** Show error if CSV has >10,000 rows, recommend breaking into smaller files
5. **Progress streaming:** For large files, use streaming response with progress updates instead of single response

**Warning signs:**
- 502 Bad Gateway errors on large file uploads
- Server logs show "Memory allocation failed" or OOM errors
- Import works for 100 rows, fails for 10,000 rows
- gunicorn worker restarts during import

**Phase to address:**
Phase 1 (Funds CSV Import) — Establish batch size limits early. Pattern must scale to Phase 2 (Transactions) where files will be largest.

---

### Pitfall 5: CSV Injection (Formula Injection) Security Vulnerability

**What goes wrong:**
User imports CSV with cell value `=2+5` or `=cmd|'/c calc'!A1`. When admin exports data to CSV and opens in Excel, the formula executes. In worst case, malicious formulas can execute shell commands, exfiltrate data via `WEBSERVICE()`, or exploit DDE vulnerabilities.

**Why it happens:**
CSV is treated as plain text during import, but spreadsheet programs auto-execute formulas starting with `=`, `+`, `-`, `@`, `\t`, or `\r`. If user-provided data (like contact names or donation notes) contains these characters, they're stored as-is and become active formulas on export.

**How to avoid:**
1. **Input sanitization on import:** Detect formula indicators (`=`, `+`, `-`, `@`) at start of string values
2. **Prefix with single quote:** Prepend `'` to force text treatment: `=2+5` becomes `'=2+5`
3. **Blocklist dangerous patterns:** Reject cells containing `cmd`, `powershell`, `DDE`, `WEBSERVICE`, `HYPERLINK`
4. **Export sanitization:** When exporting CSV, prepend `'` to any cell starting with formula indicators
5. **User warnings:** Document that formula-like content will be escaped for security

**Warning signs:**
- Contact names like "=SUM(A1:A10)" in database
- Excel shows formula results instead of raw values on export
- Security scans flag CSV injection vulnerabilities
- Users report "weird values" after opening exported CSVs

**Phase to address:**
Phase 1 (Funds CSV Import) — Implement sanitization in shared CSV parsing utility. All phases (Entities, Transactions, Pledges) must use same sanitizer.

---

### Pitfall 6: Duplicate External ID Handling Without Clear Strategy

**What goes wrong:**
CSV contains two rows with same `entity_id=12345`. First import creates Contact with `external_id=12345`. Second import should update that contact (upsert), but instead creates duplicate or fails with unique constraint error. User doesn't understand why "same person is in the system twice."

**Why it happens:**
Django's `bulk_create()` doesn't support upsert. `update_or_create()` works for single records but causes N queries for N rows. PostgreSQL has `ON CONFLICT` but requires custom SQL. Developers either create duplicates or fail entire batch on constraint violation.

**How to avoid:**
1. **Pre-check existing external_ids:** Before import, query `Contact.objects.filter(external_id__in=csv_external_ids)` to separate creates vs updates
2. **Split create/update batches:** Use `bulk_create()` for new records, `bulk_update()` for existing records
3. **Unique constraint enforcement:** Database-level `UNIQUE (external_id)` constraint (already exists for Donation in models.py)
4. **Deduplication report:** During validation phase, report "Row 5 and Row 47 have duplicate entity_id=12345"
5. **Last-write-wins strategy:** Document that if CSV has duplicates, last occurrence wins (or reject with error)

**Warning signs:**
- "Duplicate entry" errors during import
- Same donor appears multiple times in contact list with different UUIDs
- Import validation passes but database insert fails
- Re-importing same CSV doubles record count

**Phase to address:**
Phase 1 (Funds CSV Import) — Establish pattern for detecting in-file duplicates. Phase 2 (Entities CSV Import) — Most critical, as entity_id is FK for Transactions and Pledges.

---

### Pitfall 7: Missing Progress Feedback for Long-Running Imports

**What goes wrong:**
User uploads CSV with 10,000 rows. Browser shows loading spinner for 90 seconds with no feedback. User thinks it froze, refreshes page, cancels import, or submits duplicate request. Server is still processing first import, creating race conditions or duplicate data.

**Why it happens:**
Synchronous processing blocks HTTP response until complete. PROJECT.md says "no Celery" for MVP. Without async processing or streaming, there's no way to send progress updates during import. User has no visibility into "validating row 5,432 of 10,000."

**How to avoid:**
1. **Optimistic UI:** After upload, immediately show "Import queued: 10,000 rows" and redirect to status page
2. **Polling endpoint:** Use ImportRun model (planned in PROJECT.md) to track status, poll `/api/imports/{id}/status` every 2 seconds
3. **Progress calculation:** Update ImportRun.processed_count during batch processing, show "45% complete (4,500 / 10,000)"
4. **Timeout warning:** Show "Large import detected, this may take 2-3 minutes" upfront
5. **Disable re-submit:** Disable upload button during processing to prevent duplicate submissions

**Warning signs:**
- Users report "is it frozen?" or "nothing is happening"
- Multiple duplicate imports from same user within minutes
- Support tickets: "I waited 5 minutes and canceled"
- High bounce rate on import page during processing

**Phase to address:**
Phase 1 (Funds CSV Import) — Even small imports need progress UI pattern. Critical for Phase 2 (Transactions) where files are largest.

---

### Pitfall 8: Owner Assignment Confusion on Multi-Missionary Imports

**What goes wrong:**
Admin imports Entities CSV with 1,000 contacts. All contacts are assigned to the admin's account (`owner=admin`). Other missionaries can't see the imported contacts because of owner-scoped filtering (`Contact.objects.filter(owner=request.user)`). Data exists but is invisible to intended users.

**Why it happens:**
Existing code in `imports/services.py` likely uses `request.user` as owner for all imported contacts. SPO CSVs don't contain "owner" column. There's no UI for "import contacts for user X." Admin assumes imported contacts will be accessible to everyone.

**How to avoid:**
1. **Admin import visibility:** Admins can see all contacts regardless of owner (already supported based on permission patterns)
2. **Post-import assignment UI:** After import completes, show "Assign these 1,000 contacts to:" dropdown with user list
3. **CSV owner column:** Support optional `owner_email` column in CSV to specify owner per row
4. **Bulk reassignment tool:** Separate feature to reassign contacts from one owner to another
5. **Documentation:** Clearly explain that CSV imports are owner-scoped unless admin reassigns

**Warning signs:**
- "I imported contacts but can't see them" from non-admin users
- All imported contacts show owner=admin in database
- Donation import fails because contact.owner != user
- Support tickets about "missing imported data"

**Phase to address:**
Phase 2 (Entities CSV Import) — Critical for multi-missionary deployments. Funds don't have owner field. Transactions and Pledges inherit contact's owner.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip validation phase, validate during insert | Faster development (one code path) | Poor error messages, all-or-nothing imports, no error CSV download | Never — validation-first is table stakes for CSV import UX |
| Read entire file into memory | Simple code (`file.read()`) | Memory errors on large files, server crashes | Only for MVP with strict file size limit (<5MB) + clear docs |
| Use `bulk_create()` without batch splitting | Faster imports (single query) | Out of memory on 10k+ rows, no progress tracking | Acceptable if file size limit enforces <1000 rows |
| Store CSV content in database (ImportRun.csv_content) | Easy re-processing and audit trail | Database bloat (50MB CSV = 50MB JSONB), slow queries | Never — store S3 URL or file path, not content |
| Single transaction for entire import | True atomicity, easier rollback | No partial success, poor error UX, long lock times | Acceptable for <100 rows; use savepoints for larger |
| Skip CSV injection sanitization | Faster processing, no data modification | Security vulnerability, potential RCE on export | Never — sanitization is security requirement |
| No duplicate detection (allow duplicates) | Simpler code, no upsert logic | Data quality issues, duplicate contacts | Never for entities with external_id; OK for transactions if intentional |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SPO CSV Format | Assume column names match Django field names | Create explicit mapping dictionary: `{'Acct-Fund': 'fund_id', 'Trans Amt': 'amount'}` |
| External IDs | Treat external_id as optional or nullable | Enforce NOT NULL constraint, use for all SPO imports, enable idempotent re-imports |
| Foreign Key References | Import Transactions before Entities exist | Document and enforce import order: Funds → Entities → Transactions → Pledges |
| Date Formats | Assume MM/DD/YYYY | Support multiple formats (MM/DD/YYYY, YYYY-MM-DD, DD/MM/YYYY) with explicit parsing |
| Currency Fields | Store as float or use Excel's currency format | Store as cents (integer) to avoid floating point errors, parse `$1,234.56` to `123456` |
| CSV Encoding | Assume UTF-8 | Detect encoding with chardet library, show clear error for non-UTF-8 files |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 queries during FK lookup | Import time grows linearly with rows: 100 rows = 1s, 1000 rows = 10s, 10000 rows = 100s | Pre-fetch all FK lookups into dict: `contact_map = {c.external_id: c.id for c in Contact.objects.filter(external_id__in=ids)}` | >500 rows with FK references |
| No batch size limit | First 1000 rows succeed, then memory error | Process in batches of 1000, call `bulk_create(batch_size=1000)`, clear list between batches | >5000 rows, or >2000 with complex models |
| Recalculating denormalized fields per row | `update_giving_stats()` called for each donation creates N queries | Collect affected contact IDs, call `update_giving_stats()` once per unique contact after bulk insert | >100 donations imported |
| Single transaction for 10k+ row import | Long database locks, timeout errors, rollback on any error | Use savepoints for batch-level atomicity: `with transaction.atomic(savepoint=True):` per 1000 rows | >5000 rows or imports taking >30 seconds |
| Synchronous processing blocking web workers | gunicorn workers exhausted during large imports, site becomes unresponsive | Move to async processing (Celery) or enforce strict file size limits (<1000 rows) | >5000 rows or >3 concurrent imports |
| Validating entire file in transaction | Validation errors cause rollback, lose progress tracking | Validate outside transaction, store results in ImportRowError, then import only valid rows | Any file with validation errors + >1000 rows |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No CSV injection sanitization | Formula execution in Excel, potential RCE, data exfiltration via `WEBSERVICE()` | Sanitize on import AND export: prefix `=+-@\t\r` with single quote, blocklist `DDE`, `cmd`, `HYPERLINK` |
| Accepting non-CSV files | Malicious file upload, server-side code execution | Validate file extension AND MIME type (`text/csv`), reject if mismatch |
| No file size limits | DoS via large file upload, server memory exhaustion | Enforce 10MB limit at nginx/Apache AND Django `FILE_UPLOAD_MAX_MEMORY_SIZE` |
| Storing sensitive data in ImportRowError | PII exposure in error logs, compliance violations | Truncate error context to 100 chars, don't log full row data for GDPR compliance |
| Admin-only import without audit trail | No visibility into who imported what data, compliance risk | Use ImportRun model to log uploaded_by, filename, row counts, timestamp |
| No rate limiting on import endpoint | DoS via rapid import submissions | Rate limit to 10 imports per user per hour, use Django ratelimit decorator |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Generic "Import failed" error | User doesn't know which row failed or why, retries same file | Show row-level errors with line numbers: "Row 47: Invalid date '13/32/2025'" |
| No download template | User guesses column names, formatting, upload fails | Provide downloadable CSV template for each import type with example data |
| No preview before import | User commits 10,000 row import with wrong mapping | Show preview of first 5 rows after upload, "Does this look right?" confirmation |
| No progress indicator | User thinks browser froze, refreshes page, cancels import | Show progress bar or percentage: "Processing 4,500 / 10,000 rows (45%)" |
| Can't download error CSV | User must manually find and fix errors in 10k row file | Provide "Download errors as CSV" button with row numbers and error messages |
| No import history | User asks "did my import work?" days later | Show import history table: date, filename, status, created/updated/error counts |
| No validation-only mode | User can't test CSV without committing import | Support `?validate_only=true` query param to dry-run validation |
| Unclear import order | User imports Transactions before Entities, gets orphan errors | Show recommended order in UI: "Import in this order: 1. Funds, 2. Entities, 3. Transactions, 4. Pledges" |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **CSV Import Feature:** Often missing error download CSV — verify users can export validation errors to fix in spreadsheet
- [ ] **Foreign Key Validation:** Often missing existence checks — verify import validates all FK references before insert
- [ ] **Upsert Logic:** Often missing duplicate detection — verify same external_id updates instead of creating duplicate
- [ ] **Denormalized Fields:** Often missing recalculation trigger — verify Contact.total_given updates after donation import
- [ ] **Progress Tracking:** Often missing ImportRun status updates — verify UI shows real-time progress percentage
- [ ] **Transaction Safety:** Often missing savepoints for batches — verify partial success possible, not all-or-nothing
- [ ] **Security Sanitization:** Often missing CSV injection prevention — verify `=`, `+`, `-`, `@` are escaped on import AND export
- [ ] **Import Audit Trail:** Often missing uploaded_by tracking — verify ImportRun logs which admin ran import and when
- [ ] **Owner Assignment:** Often missing owner visibility warnings — verify admin knows imported contacts default to their account
- [ ] **File Size Limits:** Often missing server-level enforcement — verify nginx/gunicorn config matches Django settings

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Denormalized fields out of sync | MEDIUM | Create management command to recalculate all contacts: `python manage.py fix_contact_stats` runs `update_giving_stats()` for all |
| Orphan records created | HIGH | Manual cleanup required: identify donations with invalid contact_id, export to CSV, fix mappings, delete orphans, re-import |
| Duplicate records from failed upsert | MEDIUM | Write script to find duplicates by external_id, merge data into earliest record, delete duplicates |
| Partial import from transaction rollback | LOW | Check ImportRun.status, if failed re-run import — idempotent external_id prevents duplicates |
| Memory exhaustion crash | LOW | Restart server, add file size limits, ask user to split CSV into smaller files |
| CSV injection in exported data | MEDIUM | Run sanitization migration on existing data: `UPDATE contacts SET name = CASE WHEN name LIKE '=%' THEN '''' || name ELSE name END` |
| Wrong owner assignment | MEDIUM | Bulk reassign contacts: `Contact.objects.filter(owner=admin_user, created_at__gte=import_date).update(owner=correct_user)` |
| Lost import progress (no audit trail) | HIGH | No recovery possible — implement ImportRun model before launching to prevent |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Denormalized field desync | Phase 2 (Transactions Import) | After importing 100 donations, verify Contact.total_given matches SUM of donations.amount |
| Foreign key orphan records | Phase 1 (Funds Import) | Attempt to import Transaction CSV with non-existent fund_id, verify validation error with missing ID list |
| Transaction rollback without context | Phase 1 (Funds Import) | Upload CSV with invalid row 50, verify error shows "Row 50: Invalid status value" |
| Memory exhaustion | Phase 1 (Funds Import) | Upload 15MB CSV, verify rejection with "File too large (max 10MB)" error |
| CSV injection | Phase 1 (Funds Import) | Import fund with name "=2+5", export CSV, verify cell contains "'=2+5" (escaped) |
| Duplicate external ID handling | Phase 2 (Entities Import) | Import CSV with duplicate entity_id, verify validation error lists duplicate rows |
| Missing progress feedback | Phase 1 (Funds Import) | Import 1000 rows, verify progress bar updates every 10% or shows "Processing..." |
| Owner assignment confusion | Phase 2 (Entities Import) | Admin imports entities, verify UI shows "These contacts will be assigned to: admin@example.com" warning |

## Sources

**Data Integrity & Validation:**
- [CSV Formatting Top Tips for Data Accuracy (Updated 2026) | Integrate.io](https://www.integrate.io/blog/csv-formatting-tips-and-tricks-for-data-accuracy/)
- [5 CSV File Import Errors (and How to Fix Them Quickly)](https://ingestro.com/blog/5-csv-file-import-errors-and-how-to-fix-them-quickly)
- [6 Common CSV Import Errors and How to Fix Them | Flatfile](https://flatfile.com/blog/top-6-csv-import-errors-and-how-to-fix-them/)
- [5 Common Data Import Errors and How to Fix Them | Dromo](https://dromo.io/blog/common-data-import-errors-and-how-to-fix-them)
- [Best Practices for Dynamics 365 Data Import - ServerSys](https://www.serversys.com/insights/best-practices-for-dynamics-365-data-import/)

**Performance & Memory Management:**
- [Optimizing Memory Usage for Large CSV Processing in Python 3.12](https://discuss.python.org/t/optimizing-memory-usage-for-large-csv-processing-in-python-3-12/98287)
- [Loading large datasets into a database with Django — Makimo](https://makimo.com/blog/loading-large-datasets-into-a-database-with-django/)
- [Optimized ways to Read Large CSVs in Python | Analytics Vidhya](https://medium.com/analytics-vidhya/optimized-ways-to-read-large-csvs-in-python-ab2b36a7914e)
- [How to Boost the Performance of Your File Upload Feature?](https://www.merixstudio.com/blog/how-boost-performance-your-file-upload-feature)

**Transaction Management:**
- [Database transactions | Django documentation](https://docs.djangoproject.com/en/6.0/topics/db/transactions/)
- [Solved: How to Fix the 'DatabaseError: Current Transaction is Aborted' in Python Applications](https://sqlpey.com/python/solved-how-to-fix-the-databaseerror-current-transaction-is-aborted-in-python-applications/)

**Foreign Keys & Duplicate Detection:**
- [Uploading csv with ForeignKey field - Django Forum](https://forum.djangoproject.com/t/uploading-csv-with-foreignkey-field/19316)
- [django-csvimport · PyPI](https://pypi.org/project/django-csvimport/)
- [Import data process - Dynamics 365 Customer Insights | Microsoft Learn](https://learn.microsoft.com/en-us/dynamics365/customer-insights/journeys/import-data)
- [When to Use Salesforce Data Loader's Update vs. Upsert Action](https://salesforcemasterclass.com/salesforce-data-loader-update-vs-upsert/)

**Security:**
- [CSV Injection | OWASP Foundation](https://owasp.org/www-community/attacks/CSV_Injection)
- [CSV Injection: Risks, Attack Payloads & Prevention Guide](https://resources.uprootsecurity.com/csv_injection)
- [Best-practice methods to prevent CSV formula injection attacks](https://www.cyberchief.ai/2024/09/csv-formula-injection-attacks.html)
- [Validation of uploaded files - django-filer documentation](https://django-filer.readthedocs.io/en/latest/validation.html)
- [Django: FileField with ContentType and File Size Validation](https://nemesisdesign.net/blog/coding/django-filefield-content-type-size-validation/index.html)

**UX Best Practices:**
- [Building a Seamless CSV Import Experience with Flatfile](https://flatfile.com/blog/optimizing-csv-import-experiences-flatfile-portal/)
- [CSV import / Spreadsheet import: Best practices - Benedict Roeser](https://benedictroeser.de/2021/03/csv-import-best-practices/)
- [How to Build a Seamless CSV Importer | Step-by-Step Guide | Dromo](https://dromo.io/blog/building-a-seamless-csv-importer)
- [Designing An Attractive And Usable Data Importer For Your App — Smashing Magazine](https://www.smashingmagazine.com/2020/12/designing-attractive-usable-data-importer-app/)
- [Progress Trackers and Indicators – With 6 Examples To Do It Right](https://userguiding.com/blog/progress-trackers-and-indicators)

**Denormalization Patterns:**
- [How to update denormalized fields in other models on save? — Django ORM Cookbook](https://books.agiliq.com/projects/django-orm-cookbook/en/latest/update_denormalized_fields.html)
- ["Normalize until it hurts; denormalize until it works" in Django | DjangoCon US](https://2018.djangocon.us/talk/normalize-until-it-hurts-denormalize-it/)

---
*Pitfalls research for: DonorCRM CSV Import Pipeline*
*Researched: 2026-01-30*
