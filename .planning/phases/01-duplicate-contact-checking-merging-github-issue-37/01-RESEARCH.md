# Phase 1: Duplicate Contact Checking + Merging - Research

**Researched:** 2026-03-27
**Domain:** Django REST Framework backend + React frontend for duplicate detection and contact merging
**Confidence:** HIGH

## Summary

This phase implements duplicate contact detection and merging for DonorCRM. The backend leverages PostgreSQL's pg_trgm extension via Django's built-in `django.contrib.postgres` module for fuzzy name matching, combined with exact email/phone matching. The frontend adds a dedicated `/contacts/duplicates` page, a side-by-side merge view, and a creation-time warning dialog.

The core technical challenge is the atomic merge transaction: reassigning all FK relationships (Gift, RecurringGift, Task, JournalContact, PrayerIntention, Event) from the loser contact to the survivor while handling unique constraint conflicts (particularly JournalContact's `unique_together = ['journal', 'contact']`), union-merging M2M groups, recalculating denormalized stats, and producing an audit log. The detection side is straightforward with Django's `TrigramSimilarity` annotation + threshold filtering.

**Primary recommendation:** Use Django 4.2's built-in `TrigramSimilarity` from `django.contrib.postgres.search` for name matching. Install pg_trgm via a `TrigramExtension` migration operation. Build the merge as a single service function wrapped in `transaction.atomic()` with a `ContactMergeLog` audit model. Add `django.contrib.postgres` to `INSTALLED_APPS`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Detect duplicates both on contact creation (pre-save check) and via a dedicated scan page (/contacts/duplicates)
- Use PostgreSQL pg_trgm trigram similarity for fuzzy name matching -- no external Python dependencies needed
- Similarity threshold of 0.4 for name matching (catches "John/Jon", "Smith/Smyth" without excessive false positives)
- Detection scoped to owner's contacts only -- consistent with existing data isolation model
- Dedicated "/contacts/duplicates" page accessible from contact list, plus warning banner on create
- Side-by-side card comparison view -- each field row shows both values, user picks which to keep
- 3-tier confidence scoring: High (exact email or phone match), Medium (name similarity >= 0.6), Low (name similarity >= 0.4)
- DismissedDuplicate model (contact_a, contact_b, dismissed_by, dismissed_at) for persistent dismissal tracking
- Left/right "Keep this one" selection on comparison view -- user picks survivor contact
- Field-by-field radio buttons for conflicting values -- pre-selected to survivor's value, user can override per field
- Soft delete merged-away contact with merge audit log -- mark as merged (not hard delete), store metadata for undo potential
- Automatic FK reassignment in single atomic transaction -- all Gift, RecurringGift, Task, JournalContact FKs updated to survivor
- Duplicate check fires on form submission (before save) -- API returns potential matches, frontend shows warning dialog
- Modal dialog listing top 3 matches with name, email, phone, confidence badge -- "Possible duplicates found" with View/Merge/Create Anyway buttons
- Check triggers on first_name + last_name + email + phone -- any non-empty field checked; email/phone exact match, name fuzzy
- User can bypass with "Create Anyway" -- no forced merge at creation time

### Claude's Discretion
- Database migration strategy and model field choices
- API endpoint naming and URL structure
- Component composition and file organization
- pg_trgm extension installation approach

### Deferred Ideas (OUT OF SCOPE)
- Auto-merge suggestions (automatic merging without user confirmation)
- Cross-owner duplicate detection
- Configurable per-user similarity thresholds
- Undo merge feature (soft delete enables this but UI deferred)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| django.contrib.postgres | 4.2 (built-in) | TrigramSimilarity, TrigramExtension for pg_trgm | Django's native PostgreSQL support; no external deps |
| Django REST Framework | 3.14+ | API views, serializers for duplicate check/merge endpoints | Already in project stack |
| React + TanStack Query | 5.90+ | Frontend state management and API hooks for duplicate operations | Already in project stack |
| shadcn/ui | latest | RadioGroup, AlertDialog (new), plus existing Card/Badge/Dialog/Table | Already in project stack; needs 2 new component installs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-radio-group | latest | Field-by-field merge value selection | Must install: `npx shadcn@latest add radio-group` |
| @radix-ui/react-alert-dialog | latest | Merge confirmation dialog (destructive action) | Must install: `npx shadcn@latest add alert-dialog` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pg_trgm (locked) | thefuzz/fuzzywuzzy Python lib | Locked out by CONTEXT.md -- pg_trgm is faster (DB-level), no extra deps |
| RadioGroup | Button-style toggles (Phase 56 pattern) | UI-SPEC specifies RadioGroup; install is trivial |

**Installation (backend):**
```bash
# No new pip packages needed -- django.contrib.postgres is built into Django
# Just add 'django.contrib.postgres' to INSTALLED_APPS
```

**Installation (frontend):**
```bash
cd frontend && npx shadcn@latest add radio-group alert-dialog
```

## Architecture Patterns

### Recommended Project Structure
```
apps/contacts/
  models.py              # Add DismissedDuplicate, ContactMergeLog models + is_merged/merged_into fields on Contact
  services.py            # NEW: find_duplicates(), merge_contacts() business logic
  views.py               # Add DuplicateCheckView, DuplicateScanView, MergeContactsView, DismissDuplicateView
  serializers.py         # Add DuplicatePairSerializer, MergeRequestSerializer, DuplicateCheckSerializer
  urls.py                # Add duplicate-related URL patterns
  migrations/
    0009_*.py            # pg_trgm extension + new models

frontend/src/
  api/contacts.ts                                    # Add duplicate check, scan, merge, dismiss API functions
  hooks/useContacts.ts                               # Add useDuplicateScan, useMergeContacts, useDismissDuplicate hooks
  pages/contacts/
    DuplicateList.tsx                                 # /contacts/duplicates page
    DuplicateMergeView.tsx                            # /contacts/duplicates/:pairId merge view
    components/
      DuplicateWarningDialog.tsx                      # Creation-time warning modal
      ConfidenceBadge.tsx                             # Reusable badge for High/Medium/Low
      MergeFieldRow.tsx                               # Single field row with radio selection
```

### Pattern 1: Duplicate Detection Service
**What:** Centralized `find_duplicates()` function in `apps/contacts/services.py` that handles both creation-time checks and batch scans.
**When to use:** Any time the system needs to find potential duplicates for a contact or across all contacts for an owner.
**Example:**
```python
# Source: Django 4.2 docs - django.contrib.postgres.search.TrigramSimilarity
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value, FloatField
from django.db.models.functions import Greatest, Coalesce

def find_duplicates_for_contact(contact_data, owner_id, exclude_id=None):
    """
    Find potential duplicates for a contact based on name similarity,
    exact email match, and exact phone match.
    Returns list of (contact, confidence, reasons) tuples.
    """
    qs = Contact.objects.filter(owner_id=owner_id)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)

    # Build name string for comparison
    name = f"{contact_data.get('first_name', '')} {contact_data.get('last_name', '')}".strip()

    results = []

    if name:
        # Fuzzy name matching via pg_trgm
        name_matches = qs.annotate(
            name_similarity=Greatest(
                TrigramSimilarity('first_name', contact_data.get('first_name', '')),
                TrigramSimilarity('last_name', contact_data.get('last_name', '')),
            )
        ).filter(name_similarity__gte=0.4)
        results.extend(name_matches)

    # Exact email match
    email = contact_data.get('email', '').strip()
    if email:
        email_matches = qs.filter(email__iexact=email)
        results.extend(email_matches)

    # Exact phone match
    phone = contact_data.get('phone', '').strip()
    if phone:
        phone_matches = qs.filter(Q(phone=phone) | Q(phone_secondary=phone))
        results.extend(phone_matches)

    # Deduplicate and score
    return _score_and_deduplicate(results, contact_data)
```

### Pattern 2: Atomic Merge Transaction
**What:** Single `merge_contacts()` function that handles all FK reassignment, M2M merging, stats recalculation, and audit logging in one atomic transaction.
**When to use:** When user confirms merge of two contacts.
**Example:**
```python
from django.db import transaction

@transaction.atomic
def merge_contacts(survivor_id, loser_id, field_overrides, merged_by):
    """
    Merge loser contact into survivor contact.
    field_overrides: dict of {field_name: 'left'|'right'} for conflicting fields.
    """
    survivor = Contact.objects.select_for_update().get(pk=survivor_id)
    loser = Contact.objects.select_for_update().get(pk=loser_id)

    # 1. Apply field overrides to survivor
    for field, choice in field_overrides.items():
        if choice == 'right':  # Use loser's value
            setattr(survivor, field, getattr(loser, field))

    # 2. Reassign FKs (handle JournalContact unique constraint)
    Gift.objects.filter(donor_contact=loser).update(donor_contact=survivor)
    RecurringGift.objects.filter(donor_contact=loser).update(donor_contact=survivor)
    Task.objects.filter(contact=loser).update(contact=survivor)
    PrayerIntention.objects.filter(contact=loser).update(contact=survivor)
    Event.objects.filter(contact=loser).update(contact=survivor)

    # JournalContact: handle unique_together conflict
    _merge_journal_contacts(survivor, loser)

    # 3. Union-merge M2M groups
    loser_groups = loser.groups.all()
    survivor.groups.add(*loser_groups)

    # 4. Soft-delete loser
    loser.is_merged = True
    loser.merged_into = survivor
    loser.save(update_fields=['is_merged', 'merged_into', 'updated_at'])

    # 5. Recalculate survivor stats
    survivor.save()
    survivor.update_giving_stats()

    # 6. Create audit log
    ContactMergeLog.objects.create(
        survivor=survivor,
        loser=loser,
        merged_by=merged_by,
        field_overrides=field_overrides,
        metadata={...}
    )

    return survivor
```

### Pattern 3: Batch Duplicate Scan
**What:** Owner-scoped scan comparing all contacts pairwise using pg_trgm, filtering out already-dismissed pairs.
**When to use:** When user clicks "Scan for Duplicates" on the duplicates page.
**Example:**
```python
from django.db.models import F

def scan_duplicates_for_owner(owner_id):
    """
    Scan all contacts for an owner and return potential duplicate pairs.
    Excludes dismissed pairs and already-merged contacts.
    """
    contacts = Contact.objects.filter(
        owner_id=owner_id, is_merged=False
    ).order_by('last_name', 'first_name')

    pairs = []
    dismissed = set(
        DismissedDuplicate.objects.filter(
            Q(contact_a__owner_id=owner_id) | Q(contact_b__owner_id=owner_id)
        ).values_list('contact_a_id', 'contact_b_id')
    )

    # For each contact, find similar contacts with higher ID (avoid duplicating pairs)
    for contact in contacts:
        similar = contacts.filter(pk__gt=contact.pk).annotate(
            name_sim=TrigramSimilarity(
                'first_name', contact.first_name
            )
        ).filter(name_sim__gte=0.4)
        # ... score and add to pairs
    return pairs
```

### Anti-Patterns to Avoid
- **N+1 in batch scan:** Do NOT run a separate query for each contact in the scan. Use a windowed approach or self-join with raw SQL if needed for large datasets.
- **Forgetting JournalContact unique constraint:** Blindly updating `JournalContact.contact = survivor` will violate `unique_together = ['journal', 'contact']` if both contacts are in the same journal. Must check for conflicts and merge the JournalContact records (keeping stage events from both).
- **Not locking rows during merge:** Use `select_for_update()` on both contacts to prevent concurrent modifications during the merge transaction.
- **Recalculating stats outside the transaction:** `update_giving_stats()` must run inside the same atomic block as the FK reassignment to avoid stale data.
- **Not handling external_id conflicts:** If both contacts have different `external_id` or `external_constituent_id`, warn the user (CONTEXT.md specific idea) -- the survivor keeps its value.
- **Using pg_trgm in SQLite tests:** Tests use SQLite (in-memory). pg_trgm functions will not work in SQLite. The service layer must be testable with mocked similarity or the test settings need a PostgreSQL backend for integration tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom Levenshtein or Jaro-Winkler in Python | `TrigramSimilarity` from `django.contrib.postgres.search` | DB-level, indexed, handles Unicode, no Python overhead per comparison |
| Extension installation | Raw SQL `CREATE EXTENSION pg_trgm` | `TrigramExtension` migration operation | Django migration system tracks it, idempotent, works with `migrate` |
| Atomic FK reassignment | Manual SQL or sequential ORM updates | `transaction.atomic()` + bulk `update()` calls | Django's transaction management handles rollback on any failure |
| Radio group UI | Custom radio buttons with state management | `shadcn/ui radio-group` (Radix-backed) | Accessible, keyboard-navigable, focus-trapped, ARIA labels |
| Destructive confirmation | Custom confirm dialog | `shadcn/ui alert-dialog` (Radix-backed) | Focus trap, escape handling, accessible, project-consistent |

**Key insight:** pg_trgm at the database level is dramatically faster than Python-level string comparison for batch scans across hundreds of contacts. Django 4.2 wraps it natively -- no external dependencies.

## Common Pitfalls

### Pitfall 1: JournalContact Unique Constraint Violation During Merge
**What goes wrong:** When merging two contacts that both appear in the same journal, updating `JournalContact.contact = survivor` will fail because `unique_together = ['journal', 'contact']` already has a row for (journal, survivor).
**Why it happens:** The merge blindly updates all FK references without checking for existing relationships on the survivor side.
**How to avoid:** Before updating JournalContact FKs, query for overlapping journals. For overlapping entries, keep the survivor's JournalContact row, transfer stage events from the loser's JournalContact to the survivor's, then delete the loser's JournalContact row.
**Warning signs:** IntegrityError during merge for contacts that share a journal.

### Pitfall 2: unique_contact_email_per_owner Constraint After Field Override
**What goes wrong:** If the user picks the loser's email as the merge result, and another contact already has that email for the same owner, the unique constraint `unique_contact_email_per_owner` fires.
**Why it happens:** The existing `UniqueConstraint(fields=['owner', 'email'], condition=~Q(email=''))` prevents duplicate emails per owner.
**How to avoid:** Validate the merged field values before saving. If the loser's email would conflict with a third contact, show a validation error. Note: the loser itself is being soft-deleted so its email slot will be freed, but if the survivor already has a different email AND the user picks the loser's email, the old email on the survivor is simply overwritten -- no conflict unless a third contact has that email.
**Warning signs:** IntegrityError on contact save during merge.

### Pitfall 3: SQLite Test Environment vs pg_trgm
**What goes wrong:** `TrigramSimilarity` and `TrigramExtension` are PostgreSQL-specific. Tests using SQLite (current test.py config) will fail when running any code path that uses these.
**Why it happens:** `config/settings/test.py` uses `'ENGINE': 'django.db.backends.sqlite3'` with in-memory database.
**How to avoid:** Two approaches: (1) Mock the similarity scoring in unit tests and test the service logic separately, or (2) create a `test_postgres.py` settings file that uses a real PostgreSQL database for integration tests of the duplicate detection service. The merge logic itself (FK reassignment) works fine in SQLite -- only the trigram matching needs PostgreSQL.
**Warning signs:** `django.db.utils.OperationalError: no such function: similarity` in tests.

### Pitfall 4: Denormalized Stats Not Recalculated After Merge
**What goes wrong:** After moving gifts from loser to survivor, the survivor's `total_given`, `gift_count`, `first_gift_date`, `last_gift_date`, `last_gift_amount` are stale.
**Why it happens:** These are denormalized fields on Contact that are normally updated by `update_giving_stats()` when individual gifts change.
**How to avoid:** Call `survivor.update_giving_stats()` inside the atomic merge transaction after all Gift FK updates are complete.
**Warning signs:** Survivor's donation totals don't include the transferred gifts.

### Pitfall 5: Race Condition on Concurrent Merge
**What goes wrong:** Two users attempt to merge the same contact pair simultaneously, or one user merges while another is editing the loser contact.
**Why it happens:** Without row-level locking, both transactions can read the same state.
**How to avoid:** Use `select_for_update()` on both contacts at the start of the merge transaction. Check `is_merged` status immediately after acquiring locks.
**Warning signs:** Duplicate FK reassignment or data loss.

### Pitfall 6: DismissedDuplicate Pair Ordering
**What goes wrong:** User dismisses (A, B) but scan later finds (B, A) and shows it again.
**Why it happens:** DismissedDuplicate stores (contact_a, contact_b) without canonicalization.
**How to avoid:** Always store with `contact_a_id < contact_b_id` (compare UUID strings). Query dismissed pairs with both orderings or use the same canonicalization.
**Warning signs:** Dismissed pairs reappearing in scan results.

### Pitfall 7: Batch Scan Performance with O(n^2) Pairwise Comparison
**What goes wrong:** Naive pairwise comparison of N contacts requires N*(N-1)/2 similarity checks.
**Why it happens:** Without indexing or smart query structure, every contact is compared to every other.
**How to avoid:** Use a single SQL query with self-join + `similarity()` function call, or use GIN/GiST trigram index on name fields. For DonorCRM's scale (hundreds to low thousands of contacts per owner), a simple annotated query loop is acceptable, but for future-proofing, consider a GIN trigram index.
**Warning signs:** Scan taking more than a few seconds for owners with >500 contacts.

## Code Examples

### Migration: Install pg_trgm Extension
```python
# Source: Django 4.2 docs - django.contrib.postgres.operations.TrigramExtension
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('contacts', '0008_allow_blank_first_last_name'),
    ]

    operations = [
        TrigramExtension(),  # Installs pg_trgm extension
        # ... model additions follow
    ]
```

### New Models
```python
# DismissedDuplicate model
class DismissedDuplicate(TimeStampedModel):
    contact_a = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='+')
    contact_b = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='+')
    dismissed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = 'dismissed_duplicates'
        constraints = [
            models.UniqueConstraint(
                fields=['contact_a', 'contact_b'],
                name='unique_dismissed_pair'
            )
        ]

    def save(self, **kwargs):
        # Canonicalize: contact_a_id < contact_b_id
        if str(self.contact_a_id) > str(self.contact_b_id):
            self.contact_a_id, self.contact_b_id = self.contact_b_id, self.contact_a_id
        super().save(**kwargs)


# ContactMergeLog audit model
class ContactMergeLog(TimeStampedModel):
    survivor = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, related_name='merge_logs_as_survivor')
    loser_id = models.UUIDField(help_text='ID of the merged-away contact')
    loser_name = models.CharField(max_length=300, help_text='Name snapshot at merge time')
    merged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    field_overrides = models.JSONField(default=dict, help_text='Field resolution choices')
    records_migrated = models.JSONField(default=dict, help_text='Counts of migrated FK records')

    class Meta:
        db_table = 'contact_merge_logs'
        ordering = ['-created_at']
```

### Contact Model Additions (Soft Delete for Merge)
```python
# Add to Contact model:
is_merged = models.BooleanField('merged', default=False, db_index=True)
merged_into = models.ForeignKey(
    'self', on_delete=models.SET_NULL, null=True, blank=True,
    related_name='merged_contacts',
    help_text='Contact this was merged into'
)
```

### JournalContact Merge Handling
```python
def _merge_journal_contacts(survivor, loser):
    """Handle JournalContact unique_together constraint during merge."""
    from apps.journals.models import JournalContact, JournalStageEvent

    loser_jcs = JournalContact.objects.filter(contact=loser)

    for loser_jc in loser_jcs:
        # Check if survivor is already in this journal
        survivor_jc = JournalContact.objects.filter(
            journal=loser_jc.journal, contact=survivor
        ).first()

        if survivor_jc:
            # Both in same journal: transfer events, delete loser's JournalContact
            JournalStageEvent.objects.filter(
                journal_contact=loser_jc
            ).update(journal_contact=survivor_jc)
            # Transfer decisions, next_steps similarly
            loser_jc.decisions.all().update(journal_contact=survivor_jc)
            loser_jc.next_steps.all().update(journal_contact=survivor_jc)
            loser_jc.delete()
        else:
            # No conflict: simply reassign
            loser_jc.contact = survivor
            loser_jc.save(update_fields=['contact'])
```

### Duplicate Check API Endpoint
```python
# Source: Follows existing ContactSearchView pattern
class DuplicateCheckView(APIView):
    """POST: Check for duplicates before creating a contact."""
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]

    def post(self, request):
        data = request.data
        duplicates = find_duplicates_for_contact(
            contact_data=data,
            owner_id=request.user.id,
        )
        serializer = DuplicatePairSerializer(duplicates, many=True)
        return Response(serializer.data)
```

### Frontend: useMergeContacts Hook
```typescript
// Source: Follows existing mutation pattern from useContacts.ts
export function useMergeContacts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MergeRequest) => mergeContacts(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["duplicates"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python-level fuzzywuzzy/thefuzz | PostgreSQL pg_trgm via Django ORM | Django 1.10+ (2016), improved in 4.2 | No Python package dependency, DB-level performance |
| Custom similarity scoring | `TrigramSimilarity` annotation | Django 4.2 stable | Direct Django ORM integration, no raw SQL |
| Hard delete merged contacts | Soft delete with `is_merged` flag | Modern CRM pattern | Audit trail, potential undo, data integrity |

**Deprecated/outdated:**
- `fuzzywuzzy` Python library: replaced by `thefuzz`, but neither needed when using pg_trgm
- Manual `CREATE EXTENSION pg_trgm` SQL: use `TrigramExtension` migration operation instead

## Open Questions

1. **Batch scan performance at scale**
   - What we know: DonorCRM currently has low hundreds of contacts per owner. Simple annotated queries will work fine at this scale.
   - What's unclear: If an owner has 2000+ contacts, the self-join approach may slow down. A GIN trigram index on name fields would help.
   - Recommendation: Start with the simple approach. Add GIN index as a performance optimization if scan times exceed 3-5 seconds. This is a LOW risk given current data volumes.

2. **Decision/NextStep unique constraints during JournalContact merge**
   - What we know: `Decision` has `UniqueConstraint(fields=['journal_contact'], name='unique_decision_per_journal_contact')`. If both JournalContacts (survivor and loser) have Decisions, merging them into one JournalContact creates a conflict.
   - What's unclear: Which Decision should win when both exist.
   - Recommendation: Keep the survivor's Decision. If the loser also has a Decision, log it in the merge metadata for audit but delete it (or the survivor's, picking whichever has higher amount/more recent status). Document this choice in the merge confirmation UI.

3. **External ID handling during merge**
   - What we know: CONTEXT.md says "warn if both have different external IDs." The `external_id` and `external_constituent_id` fields have unique constraints.
   - What's unclear: Whether to show external IDs in the field comparison UI at all (missionaries may not understand them).
   - Recommendation: Show external IDs in the field comparison only if both contacts have non-empty values. Pre-select survivor's value. Display a warning if values differ ("Different external system IDs detected -- contact your administrator if unsure").

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | pg_trgm extension | Assumed (production DB) | -- (cannot connect locally) | None -- pg_trgm is core to the approach |
| django.contrib.postgres | TrigramSimilarity, TrigramExtension | Built into Django 4.2 | 4.2.28 | None |
| Node.js / npm | shadcn component installation | Assumed (frontend builds) | -- | None |

**Missing dependencies with no fallback:**
- `django.contrib.postgres` must be added to `INSTALLED_APPS` (currently not listed)
- pg_trgm extension must be installed in the PostgreSQL database (via migration)
- `radio-group` and `alert-dialog` shadcn components must be installed in frontend

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-django |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest apps/contacts/tests/ -x --no-cov` |
| Full suite command | `pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DUP-01 | Creating contact triggers duplicate check API call | integration | `pytest apps/contacts/tests/test_duplicate_check.py -x --no-cov` | Wave 0 |
| DUP-02 | Batch scan returns duplicate pairs for owner | unit | `pytest apps/contacts/tests/test_duplicate_scan.py -x --no-cov` | Wave 0 |
| DUP-03 | Merge reassigns all FKs atomically | integration | `pytest apps/contacts/tests/test_merge.py -x --no-cov` | Wave 0 |
| DUP-04 | Dismissed pairs excluded from scan results | unit | `pytest apps/contacts/tests/test_duplicate_scan.py::test_dismissed_excluded -x --no-cov` | Wave 0 |
| DUP-05 | Merge creates audit log entry | unit | `pytest apps/contacts/tests/test_merge.py::test_merge_creates_log -x --no-cov` | Wave 0 |
| DUP-06 | Soft delete marks loser as merged | unit | `pytest apps/contacts/tests/test_merge.py::test_soft_delete -x --no-cov` | Wave 0 |
| DUP-07 | JournalContact unique constraint handled during merge | integration | `pytest apps/contacts/tests/test_merge.py::test_journal_contact_conflict -x --no-cov` | Wave 0 |
| DUP-08 | Survivor stats recalculated after merge | unit | `pytest apps/contacts/tests/test_merge.py::test_stats_recalculated -x --no-cov` | Wave 0 |

### Testing Considerations for pg_trgm
- **Unit tests (SQLite-safe):** Test merge logic, FK reassignment, audit logging, dismissal tracking, stats recalculation. These do NOT require pg_trgm.
- **Integration tests (PostgreSQL-required):** Test `find_duplicates_for_contact()` and `scan_duplicates_for_owner()` with actual TrigramSimilarity. Either: (a) mock the similarity scoring in unit tests, or (b) mark these tests with `@pytest.mark.integration` and run them against a PostgreSQL test database.
- **Recommendation:** Mock the similarity service in most tests. Write a small number of `@pytest.mark.integration` tests that run against PostgreSQL to verify the actual pg_trgm behavior.

### Sampling Rate
- **Per task commit:** `pytest apps/contacts/tests/ -x --no-cov`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/contacts/tests/test_duplicate_check.py` -- covers DUP-01
- [ ] `apps/contacts/tests/test_duplicate_scan.py` -- covers DUP-02, DUP-04
- [ ] `apps/contacts/tests/test_merge.py` -- covers DUP-03, DUP-05, DUP-06, DUP-07, DUP-08
- [ ] `apps/contacts/services.py` -- new file for service functions
- [ ] Frontend: `radio-group` and `alert-dialog` shadcn components must be installed

## Complete FK Inventory (for Merge Reassignment)

All models with ForeignKey to `contacts.Contact`:

| Model | FK Field | related_name | on_delete | Unique Constraints | Merge Strategy |
|-------|----------|--------------|-----------|-------------------|----------------|
| Gift | donor_contact | gifts | CASCADE | None on FK | Bulk update to survivor |
| RecurringGift | donor_contact | recurring_gifts | CASCADE | None on FK | Bulk update to survivor |
| Task | contact | tasks | CASCADE (nullable) | None on FK | Bulk update to survivor |
| JournalContact | contact | journal_memberships | CASCADE | unique_together: ['journal', 'contact'] | Check for conflict, merge events if both in same journal |
| PrayerIntention | contact | prayer_intentions | CASCADE | None on FK | Bulk update to survivor |
| Event | contact | events | CASCADE (nullable) | None on FK | Bulk update to survivor |

M2M relationships:
| Model | Field | Through Table | Merge Strategy |
|-------|-------|---------------|----------------|
| Contact.groups | groups | auto (contacts_groups) | Union merge: survivor.groups.add(*loser.groups.all()) |

## Project Constraints (from CLAUDE.md)

No CLAUDE.md file exists in the project root. Project conventions are inferred from codebase patterns:
- UUID primary keys on all models (via TimeStampedModel)
- Owner-scoped querysets via `get_visible_user_ids()`
- DRF serializers with List/Detail/Create variants
- React Query mutations with `invalidateQueries` cache busting
- nuqs URL state management for filter persistence
- shadcn/ui (manual install) with Radix primitives
- Test settings use SQLite in-memory (`config/settings/test.py`)
- `django-filter==24.3` (NOT 25.2)

## Sources

### Primary (HIGH confidence)
- Django 4.2 official docs: [Full Text Search - Trigram Similarity](https://docs.djangoproject.com/en/4.2/ref/contrib/postgres/search/#trigram-similarity) -- verified TrigramSimilarity API, parameter order, installation
- Django 4.2 source code: `django.contrib.postgres.operations.TrigramExtension` -- confirmed migration operation wraps `CREATE EXTENSION pg_trgm`
- Django 4.2 source code: `django.contrib.postgres.search` -- confirmed TrigramSimilarity, TrigramDistance, TrigramWordSimilarity classes available
- GitHub Issue #37: acceptance criteria for duplicate detection and merging
- Codebase analysis: Contact model, all FK relationships, unique constraints, existing serializer/view/hook patterns

### Secondary (MEDIUM confidence)
- [Django docs - PostgreSQL lookups](https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/lookups/) -- trigram_similar lookup
- [Medium: Using PostgreSQL's pg_trgm with Django](https://poonkawin.medium.com/making-your-search-smarter-using-postgresqls-pg-trgm-with-django-ef9d9f18b7d7) -- practical usage patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are either already in the project or built into Django 4.2 (verified from source)
- Architecture: HIGH - Patterns follow established project conventions (views.py, serializers.py, hooks) with well-understood Django ORM operations
- Pitfalls: HIGH - Each pitfall identified from direct codebase analysis (unique constraints, test settings, FK relationships)
- Testing: MEDIUM - pg_trgm/SQLite incompatibility is a known issue; mocking strategy is sound but untested in this project

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, no fast-moving dependencies)
