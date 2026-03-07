---
phase: quick-11
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/imports/spo_services.py
  - apps/imports/re_services.py
  - apps/imports/tests/test_spo_services.py
  - apps/imports/tests/test_re_services.py
autonomous: true
requirements: [BUG-D1, BUG-D6]

must_haves:
  truths:
    - "SPO-imported gifts have payment_type set (not blank/null)"
    - "Payment type values EFT, Direct Debit, Cash map to existing PaymentType choices"
    - "Recurring gift rows with prayer text create PrayerIntention records"
    - "Prayer intentions from recurring gifts are correctly linked to Contact, not to any Gift"
  artifacts:
    - path: "apps/imports/spo_services.py"
      provides: "payment_type header alias and field assignment in import_spo_gifts()"
      contains: "'gift payment type'"
    - path: "apps/imports/re_services.py"
      provides: "prayer extraction loop after RecurringGiftCredit creation"
      contains: "prayer_description"
    - path: "apps/imports/tests/test_spo_services.py"
      provides: "test asserting payment_type set on SPO gift"
    - path: "apps/imports/tests/test_re_services.py"
      provides: "test asserting PrayerIntention created from recurring gift row"
  key_links:
    - from: "SPO_GIFT_HEADER_ALIAS_MAP"
      to: "_get(row, 'payment_type')"
      via: "new alias entry 'gift payment type' in _SPO_GIFT_HEADER_ALIASES_NESTED"
    - from: "_get(row, 'payment_type')"
      to: "Gift.objects.create(payment_type=...)"
      via: "_normalize_payment_type() call"
    - from: "first_row.get('prayer_description')"
      to: "PrayerIntention.objects.create()"
      via: "inline prayer creation block in import_re_recurring_gifts()"
---

<objective>
Fix two confirmed bugs in the Phase 44 SPO CSV import pipeline:
1. SPO gift import never sets payment_type on Gift records — missing header alias and missing field assignment
2. RE recurring gift import maps the prayer_description column but never reads it — PrayerIntentions are silently dropped

Purpose: Ensure data integrity for all imported gifts and recurring gift prayer requests.
Output: Two service fixes and two new test assertions.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/10-read-import-analysis-md-to-analyze-the-c/10-ANALYSIS.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix payment_type omission in import_spo_gifts()</name>
  <files>apps/imports/spo_services.py, apps/imports/tests/test_spo_services.py</files>
  <behavior>
    - Test: SPO gift with "Gift Payment Type" = "EFT" creates Gift with payment_type="direct_deposit"
    - Test: SPO gift with "Gift Payment Type" = "Check" creates Gift with payment_type="check"
    - Test: SPO gift with "Gift Payment Type" = "Credit Card" creates Gift with payment_type="credit_card"
    - Test: SPO gift with "Gift Payment Type" = "Cash" creates Gift with payment_type="" (or blank — _normalize_payment_type returns '' for unknown types)
    - Test: SPO gift with no payment type column creates Gift without error (blank payment_type)
  </behavior>
  <action>
    Two changes in apps/imports/spo_services.py:

    1. In `_SPO_GIFT_HEADER_ALIASES_NESTED` (around line 554), add a new entry for payment_type:
       ```python
       'payment_type': ['Gift Payment Type', 'Payment Type', 'payment_type'],
       ```
       This makes the flat SPO_GIFT_HEADER_ALIAS_MAP include 'gift payment type' -> 'payment_type'.

    2. In `import_spo_gifts()` in the row-processing loop (around line 730, after gift_date is parsed),
       add payment_type extraction and pass it to Gift.objects.create():
       ```python
       payment_type_raw = _get(row, 'payment_type')
       payment_type = _normalize_payment_type(payment_type_raw)
       ```
       Then update the Gift.objects.create() call (currently around line 739) to include:
       ```python
       gift = Gift.objects.create(
           donor_contact=contact,
           amount_cents=amount_cents,
           gift_date=gift_date,
           external_gift_id=gift_id,
           payment_type=payment_type,
       )
       ```

    Note: `_normalize_payment_type` is defined in re_services.py. It is already imported — check
    top of spo_services.py for existing imports from re_services. If not imported, add it to the
    import line that brings in other re_services utilities.

    In apps/imports/tests/test_spo_services.py:

    Update `_make_gifts_csv()` helper to include "Gift Payment Type" in the header row and
    a 'payment_type' key in the row dict (defaulting to ''). Then add a new test method to
    TestImportSpoGifts:

    ```python
    def test_payment_type_set_on_spo_gift(self):
        """Gift Payment Type column is mapped and stored on Gift.payment_type."""
        from apps.gifts.models import Gift, Solicitor
        from apps.imports.spo_services import import_spo_gifts
        from apps.imports.re_services import normalize_solicitor_name

        admin = _make_admin()
        missionary = _make_user('pay.type@test.com', 'Pay', 'Type')
        Solicitor.objects.create(
            user=missionary,
            normalized_name=normalize_solicitor_name(missionary.full_name),
        )
        csv_bytes = _make_gifts_csv({
            'gift_id': 'G-PAY-01',
            'solicitor_name': 'Pay Type',
            'gift_amount': '100.00',
            'payment_type': 'EFT',
        })
        batch = import_spo_gifts(csv_bytes, 'gifts.csv', admin)
        self.assertEqual(batch.status, ImportBatchStatus.COMPLETED)
        gift = Gift.objects.get(external_gift_id='G-PAY-01')
        self.assertEqual(gift.payment_type, 'direct_deposit')  # EFT maps to direct_deposit
    ```

    Commit message: `fix(spo-import): set payment_type on SPO-imported gifts`
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests.test_spo_services.TestImportSpoGifts.test_payment_type_set_on_spo_gift --no-input 2>&1 | tail -10</automated>
  </verify>
  <done>
    - _SPO_GIFT_HEADER_ALIASES_NESTED contains 'payment_type' entry with 'Gift Payment Type' alias
    - Gift.objects.create() in import_spo_gifts() passes payment_type=_normalize_payment_type(...)
    - New test passes: Gift with EFT payment type has payment_type='direct_deposit'
    - Existing SPO tests still pass
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extract prayer intentions from import_re_recurring_gifts()</name>
  <files>apps/imports/re_services.py, apps/imports/tests/test_re_services.py</files>
  <behavior>
    - Test: Recurring gift row with non-empty prayer_description creates one PrayerIntention for the contact
    - Test: Recurring gift row with empty prayer_description creates no PrayerIntention
    - Test: Two recurring gift rows with same prayer text for same contact create only one PrayerIntention (dedup)
    - Test: PrayerIntention has no gift M2M link (recurring gifts have no Gift object)
  </behavior>
  <action>
    In apps/imports/re_services.py, inside `import_re_recurring_gifts()`:

    1. Before the outer `try:` block (around line 1661), initialize the seen_prayers dict:
       ```python
       seen_prayers: dict = {}
       ```

    2. After the RecurringGiftCredit creation loop ends (after line 1832, inside the inner try block
       before `transaction.savepoint_commit(sp)`), add prayer extraction:
       ```python
       # Extract prayer intention from recurring gift (no Gift M2M link — RecurringGift has no Gift)
       prayer_text = first_row.get('prayer_description', '').strip()
       if prayer_text:
           from apps.prayers.models import PrayerIntention, PrayerIntentionStatus
           PRAYER_STOPLIST = {
               'n/a', 'na', 'none', 'no', '-', '--', '---', 'no prayer request',
               'x', 'xx', 'xxx', 'general', 'same', 'same as above',
               'see above', 'ditto', 'tbd', 'unknown',
           }
           if prayer_text.lower() not in PRAYER_STOPLIST and any(c.isalnum() for c in prayer_text):
               normalized = prayer_text.lower()
               dedup_key = (contact.id, normalized)
               if dedup_key not in seen_prayers:
                   existing_prayer = PrayerIntention.objects.filter(
                       contact=contact,
                       description__iexact=prayer_text,
                   ).first()
                   if existing_prayer:
                       seen_prayers[dedup_key] = existing_prayer
                   else:
                       title = prayer_text[:80].rsplit(' ', 1)[0] if len(prayer_text) > 80 else prayer_text
                       prayer = PrayerIntention.objects.create(
                           contact=contact,
                           title=title,
                           description=prayer_text,
                           status=PrayerIntentionStatus.ACTIVE,
                       )
                       seen_prayers[dedup_key] = prayer
       ```

    The pattern mirrors the gift-free branch already used in import_spo_prayers() (spo_services.py
    around line 930). No shared helper extraction needed — inline is correct here.

    Note: `prayer_description` is already in RECURRING_GIFT_HEADER_ALIASES (confirmed at lines 1502-1505
    of re_services.py) so `first_row.get('prayer_description', '')` will work once the header alias
    mapping is resolved by _group_rows_by_id() via _build_header_mapping(). Verify this by checking
    that rows in groups have canonical keys, not raw CSV column names. If rows store raw column values
    under canonical keys (as mapped by col_map in _group_rows_by_id), use `first_row.get('prayer_description', '')`.
    If they store raw column names, use `_get(first_row, 'prayer_description')` with a col_map lookup.

    In apps/imports/tests/test_re_services.py, add a new test class after TestImportRERecurringGifts:

    ```python
    @pytest.mark.django_db
    class TestImportRERecurringGiftsPrayers:
        """Test prayer extraction from recurring gift import."""

        @pytest.fixture
        def setup_contact(self, staff_user):
            return Contact.objects.create(
                owner=staff_user,
                external_constituent_id='C-PRAY-01',
                first_name='Prayer',
                last_name='Donor',
            )

        def test_prayer_extracted_from_recurring_gift(self, admin_user, staff_user, setup_contact):
            """Recurring gift with prayer_description creates PrayerIntention."""
            from apps.prayers.models import PrayerIntention
            csv_data = _to_bytes(
                'Recurring Gift\n'
                'Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,'
                'Gift Specific Attributes Prayer Requests Description\n'
                'RG-PRAY-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,Healing for family\n'
            )
            batch = import_re_recurring_gifts(csv_data, 'recurring.csv', admin_user, staff_user)
            assert batch.status == ImportBatchStatus.COMPLETED
            assert PrayerIntention.objects.count() == 1
            prayer = PrayerIntention.objects.first()
            assert 'Healing' in prayer.description
            assert prayer.contact == setup_contact
            # No gift M2M link — recurring gifts have no associated Gift record
            assert prayer.gifts.count() == 0

        def test_no_prayer_when_description_empty(self, admin_user, staff_user, setup_contact):
            """Recurring gift with empty prayer description creates no PrayerIntention."""
            from apps.prayers.models import PrayerIntention
            csv_data = _to_bytes(
                'Recurring Gift\n'
                'Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,'
                'Gift Specific Attributes Prayer Requests Description\n'
                'RG-NOPRAY-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,\n'
            )
            batch = import_re_recurring_gifts(csv_data, 'recurring.csv', admin_user, staff_user)
            assert batch.status == ImportBatchStatus.COMPLETED
            assert PrayerIntention.objects.count() == 0

        def test_prayer_dedup_across_recurring_gifts(self, admin_user, staff_user, setup_contact):
            """Two recurring gifts with identical prayer text → one PrayerIntention."""
            from apps.prayers.models import PrayerIntention
            csv_data = _to_bytes(
                'Recurring Gift\n'
                'Gift ID,Constituent ID,Amount,Frequency,Gift Date,Status,'
                'Gift Specific Attributes Prayer Requests Description\n'
                'RG-DEDUP-01,C-PRAY-01,100.00,Monthly,2025-01-01,Active,Same prayer text\n'
                'RG-DEDUP-02,C-PRAY-01,200.00,Monthly,2025-02-01,Active,Same prayer text\n'
            )
            batch = import_re_recurring_gifts(csv_data, 'recurring.csv', admin_user, staff_user)
            assert batch.status == ImportBatchStatus.COMPLETED
            assert PrayerIntention.objects.count() == 1
    ```

    Note: The RE recurring gift CSV uses the same type-label row pattern ('Recurring Gift' in row 1)
    as the real test CSV — include it in the test fixture so skip_re_type_label_row() handles it.
    Check existing tests to confirm whether _to_bytes / the import handles this.

    Commit message: `fix(re-import): extract prayer intentions from recurring gift rows`
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests.test_re_services.TestImportRERecurringGiftsPrayers --no-input 2>&1 | tail -15</automated>
  </verify>
  <done>
    - import_re_recurring_gifts() reads prayer_description from first_row after RecurringGiftCredit loop
    - PrayerIntention created for recurring gift rows with non-empty, non-stoplist prayer text
    - Dedup by (contact.id, normalized_text) prevents duplicate PrayerIntentions in one run
    - All 3 new tests pass
    - Existing recurring gift tests still pass (no regressions)
  </done>
</task>

<task type="auto">
  <name>Task 3: Run full import test suite and verify no regressions</name>
  <files></files>
  <action>
    Run the full imports test suite to confirm both fixes are clean and no existing tests regressed:

    ```bash
    cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports --no-input 2>&1 | tail -20
    ```

    If any tests fail that were passing before these two fixes, diagnose and fix them before committing.

    Once green, commit both changes together under a single commit or keep as separate commits per task
    (one commit per task as specified in constraints).

    After both commits, run the fixture-based mapping tests as a final integration check:
    ```bash
    cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests.test_spo_csv_fixture_mapping --no-input 2>&1 | tail -10
    ```
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports --no-input 2>&1 | tail -5</automated>
  </verify>
  <done>
    - All apps.imports tests pass (0 failures, 0 errors)
    - Both bug fixes confirmed green
  </done>
</task>

</tasks>

<verification>
- Gift.objects.create() in spo_services.py includes payment_type= argument
- 'gift payment type' key exists in SPO_GIFT_HEADER_ALIAS_MAP (derived from _SPO_GIFT_HEADER_ALIASES_NESTED)
- import_re_recurring_gifts() contains prayer extraction block after RecurringGiftCredit creation loop
- seen_prayers dict initialized before processing loop in import_re_recurring_gifts()
- All apps.imports tests pass with 0 failures
</verification>

<success_criteria>
- SPO gift with "Gift Payment Type" = "EFT" saves as payment_type="direct_deposit" — confirmed by test
- SPO gift with "Gift Payment Type" = "Check" saves as payment_type="check" — confirmed by test
- Recurring gift row with prayer text creates PrayerIntention linked to Contact — confirmed by test
- Recurring gift row with empty prayer text creates no PrayerIntention — confirmed by test
- Full import test suite green (no regressions)
</success_criteria>

<output>
After completion, create `.planning/quick/11-fix-all-bugs-found-in-10-analysis-md/11-SUMMARY.md`
</output>
