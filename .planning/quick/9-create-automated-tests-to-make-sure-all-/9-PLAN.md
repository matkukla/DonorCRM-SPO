---
phase: quick-9
plan: 9
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/imports/tests/test_spo_csv_fixture_mapping.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "test_solicitors.csv maps all 25 missionary names without failure"
    - "test_gifts.csv maps correctly including Fund Split Amount as gift_amount"
    - "test_recurring_gifts.csv maps correctly via import_re_recurring_gifts"
    - "test_constituents.csv maps correctly via import_re_constituents"
    - "All 4 fixture tests pass in the existing test suite (python manage.py test)"
  artifacts:
    - path: "apps/imports/tests/test_spo_csv_fixture_mapping.py"
      provides: "End-to-end fixture mapping tests for all 4 SPO CSV files"
      exports: ["TestSolicitorsFixtureMapping", "TestGiftsFixtureMapping", "TestRecurringGiftsFixtureMapping", "TestConstituentsFixtureMapping"]
  key_links:
    - from: "test_data/test_solicitors.csv"
      to: "apps/imports/spo_services.reconcile_missionaries"
      via: "file bytes read from disk, passed to service function"
    - from: "test_data/test_gifts.csv"
      to: "apps/imports/spo_services.import_spo_gifts"
      via: "file bytes, Fund Split Amount header resolved via SPO_GIFT_HEADER_ALIAS_MAP"
    - from: "test_data/test_recurring_gifts.csv"
      to: "apps/imports/re_services.import_re_recurring_gifts"
      via: "file bytes read from disk, passed to service function"
    - from: "test_data/test_constituents.csv"
      to: "apps/imports/re_services.import_re_constituents"
      via: "file bytes read from disk, passed to service function"
---

<objective>
Create a new test file that imports each of the 4 real SPO CSV fixture files from test_data/ and asserts the data maps correctly through the import pipeline.

Purpose: The existing tests use synthetic in-memory CSV helpers (_make_solicitor_csv, _make_gifts_csv). These do not exercise the actual header aliases and column layouts in the real test_data files. This closes that gap.

Output: apps/imports/tests/test_spo_csv_fixture_mapping.py with 4 test classes, one per CSV file.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md

Key facts from codebase exploration:

**4 CSV files in test_data/**
- test_solicitors.csv — type-label row "Solicitor", header "Name", 25 missionaries
- test_gifts.csv — type-label row "Gift", headers include "Fund Split Amount" (alias for gift_amount), 100 gift rows
- test_recurring_gifts.csv — type-label row "Recurring Gift", 100 rows
- test_constituents.csv — type-label row "Constituent", 100+ rows

**Service functions to call**
- test_solicitors.csv → apps.imports.spo_services.reconcile_missionaries(file_bytes, filename, admin_user)
- test_gifts.csv → apps.imports.spo_services.import_spo_gifts(file_bytes, filename, admin_user)
- test_recurring_gifts.csv → apps.imports.re_services.import_re_recurring_gifts(file_bytes, filename, admin_user, owner)
- test_constituents.csv → apps.imports.re_services.import_re_constituents(file_bytes, filename, admin_user, owner)

**Key header mapping facts**
- test_gifts.csv uses "Fund Split Amount" as amount column — this IS in SPO_GIFT_HEADER_ALIAS_MAP as alias for gift_amount (fix was added in commit 1779430)
- test_gifts.csv has named constituent IDs (e.g. 100001..100100) — these contacts won't exist in test DB, so gifts with non-anonymous constituent IDs will hit contact_not_found. Anonymous gifts (Gift Is Anonymous = "Yes") will use anonymous contact. Empty constituent_id also uses anonymous contact.
- test_recurring_gifts.csv: constituent IDs also won't exist in test DB
- test_solicitors.csv: all 25 names are new (no existing users) → reconcile creates 25 users

**Imports needed in test file**
```python
import os
from django.test import TestCase
from apps.imports.models import ImportBatch, ImportBatchStatus
from apps.users.models import User

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_data')

def _fixture_bytes(filename):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()
```

**Existing test helper pattern (copy from test_spo_services.py)**
```python
def _make_admin():
    return User.objects.create_user(
        email='admin@example.com', password='adminpass',
        first_name='Admin', last_name='User', role='admin',
    )
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create fixture mapping tests for all 4 SPO CSV files</name>
  <files>apps/imports/tests/test_spo_csv_fixture_mapping.py</files>
  <action>
Create apps/imports/tests/test_spo_csv_fixture_mapping.py with 4 test classes. Do NOT use _make_solicitor_csv or _make_gifts_csv helpers — read actual files from disk using _fixture_bytes().

**File structure:**

```
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_data')

def _fixture_bytes(filename):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, 'rb') as f:
        return f.read()

def _make_admin():
    return User.objects.create_user(
        email='admin@example.com', password='adminpass',
        first_name='Admin', last_name='User', role='admin',
    )
```

**Class 1: TestSolicitorsFixtureMapping(TestCase)**

test_reconcile_missionaries_with_fixture():
- Read test_solicitors.csv bytes
- Call reconcile_missionaries(bytes, 'test_solicitors.csv', admin)
- Assert batch.status == ImportBatchStatus.COMPLETED
- Assert batch.created_count == 25 (all 25 names are new — no existing users)
- Assert batch.summary['missionaries_expected'] == 25
- Assert batch.summary['created'] == 25
- Assert batch.summary['unresolved'] == 0
- Assert User.objects.filter(role='missionary').count() == 25

test_reconcile_creates_solicitor_records():
- Read test_solicitors.csv, run reconcile_missionaries
- Import Solicitor from apps.gifts.models
- Assert Solicitor.objects.count() == 25 (one per missionary created)

**Class 2: TestGiftsFixtureMapping(TestCase)**

setUp(): Create admin user. Run reconcile_missionaries with test_solicitors.csv to set up missionaries and solicitor records that gift import depends on.

test_import_spo_gifts_with_fixture():
- Read test_gifts.csv bytes
- Call import_spo_gifts(bytes, 'test_gifts.csv', admin)
- Assert batch.status == ImportBatchStatus.COMPLETED
- Assert batch.error_count == 0
- Assert batch.created_count > 0 (some anonymous/blank-constituent gifts imported)
- Assert 'Fund Split Amount' resolved correctly: batch.summary['error_details'] is empty list (no "invalid amount" errors)
- The test_gifts.csv has "Gift Is Anonymous"="Yes" for some rows and blank constituent_id for some rows → those gifts use anonymous contact and ARE created. Named contacts (constituent_id set, not anonymous) hit contact_not_found and are skipped — that is expected behavior.

test_gifts_fund_split_amount_header_resolves():
- This specifically tests that "Fund Split Amount" (the actual header in test_gifts.csv) is recognized as the gift_amount alias
- Read test_gifts.csv bytes, run import_spo_gifts
- Assert batch.summary['error_details'] == [] (no rows failed due to amount parse errors)
- Assert at least 1 gift was created (Gift.objects.count() > 0)
- Import Gift from apps.gifts.models and assert Gift.objects.filter(amount_cents__gt=0).exists() — verifying amounts were parsed from Fund Split Amount column, not left as 0

test_gifts_anonymous_rows_imported():
- Run reconcile_missionaries then import_spo_gifts with test_gifts.csv
- From test_gifts.csv, rows with "Gift Is Anonymous"="Yes" (e.g. gift 200008, 200014, 200017...) should be imported using anonymous donor contact
- Import Contact from apps.contacts.models
- Assert Contact.objects.filter(first_name='Anonymous', last_name='Donor').exists()

**Class 3: TestRecurringGiftsFixtureMapping(TestCase)**

setUp(): Create admin user and a staff owner user (import_re_recurring_gifts needs owner param).

test_import_recurring_gifts_with_fixture():
- Read test_recurring_gifts.csv bytes
- Import import_re_recurring_gifts from apps.imports.re_services
- Call import_re_recurring_gifts(bytes, 'test_recurring_gifts.csv', admin, owner)
- Assert batch.status == ImportBatchStatus.COMPLETED
- Assert batch.error_count == 0
- Assert batch.total_rows == 100

test_recurring_gifts_type_label_row_skipped():
- Read test_recurring_gifts.csv bytes, run import_re_recurring_gifts
- The file has type-label "Recurring Gift" as first row — assert it is skipped (does not appear as a data row)
- Assert batch.total_rows == 100 (not 101)

**Class 4: TestConstituentsFixtureMapping(TestCase)**

setUp(): Create admin user and a staff owner user.

test_import_constituents_with_fixture():
- Read test_constituents.csv bytes
- Import import_re_constituents from apps.imports.re_services
- Call import_re_constituents(bytes, 'test_constituents.csv', admin, owner)
- Assert batch.status == ImportBatchStatus.COMPLETED
- Assert batch.error_count == 0
- Assert batch.created_count > 0

test_constituents_type_label_row_skipped():
- Read test_constituents.csv bytes, run import_re_constituents
- Assert the type-label "Constituent" row is skipped
- Assert batch.total_rows >= 100

**Do NOT** create any additional test classes beyond these 4. Keep file focused.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests.test_spo_csv_fixture_mapping --verbosity=2 2>&1 | tail -30</automated>
  </verify>
  <done>
All tests in test_spo_csv_fixture_mapping.py pass. The test run shows OK with the expected number of test methods. No failures or errors.
  </done>
</task>

</tasks>

<verification>
Run the full imports test suite to confirm new tests pass and no existing tests are broken:

```
cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests --verbosity=1 2>&1 | tail -10
```

Expected: "OK" with all tests passing (74 existing + new fixture tests).
</verification>

<success_criteria>
- test_spo_csv_fixture_mapping.py created with 4 test classes covering all 4 CSV files
- All tests pass: python manage.py test apps.imports.tests reports OK
- Tests specifically verify: solicitors.csv creates 25 users, gifts.csv resolves "Fund Split Amount" header without errors, recurring_gifts.csv and constituents.csv load without errors
- Existing 74 tests still pass (no regressions)
</success_criteria>

<output>
No SUMMARY.md needed for quick tasks. After tests pass, commit the new test file.
</output>
