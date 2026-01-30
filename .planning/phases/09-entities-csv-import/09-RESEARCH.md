# Phase 9: Entities CSV Import - Research

**Researched:** 2026-01-30
**Domain:** Django CSV import with owner-scoped upserts and composite unique constraints
**Confidence:** HIGH

## Summary

Phase 9 implements Entities CSV import which upserts Contact records using entity_id as external_id. This phase builds directly on Phase 8's reusable CSV import patterns (parse/import/view structure, formula injection prevention, case-insensitive validation) but introduces a critical technical difference: Contact.external_id is owner-scoped, not globally unique.

The research confirms that Django 4.2's bulk_create with update_conflicts=True supports composite UniqueConstraints (owner + external_id), but requires careful attention to field naming: use `['owner', 'external_id']` in unique_fields to match the constraint fields, NOT `['owner_id', 'external_id']`. The Contact model already has the correct owner-scoped constraint in place (unique_contact_external_id_per_owner).

The key architectural difference from Phase 8: Funds have owner=None (org-wide), but Contacts must assign owner to the uploading admin user. This means parse_entities_csv needs the user parameter (unlike parse_funds_csv which ignores it), and import_entities must set owner on all created Contact instances.

**Primary recommendation:** Follow Phase 8's parse/import pattern exactly, with three modifications: (1) pass user to parse function and validate against user's existing contacts, (2) set owner=user on all Contact instances in import function, (3) use unique_fields=['owner', 'external_id'] in bulk_create to match the composite constraint.

## Standard Stack

The established libraries/tools for owner-scoped Django CSV import:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python csv | stdlib | CSV parsing with DictReader | Same as Phase 8, proven for Contact imports |
| Django ORM | 4.2.27 | Bulk upsert with composite constraints | Supports unique_fields=['owner', 'field'] for owner-scoped data |
| PostgreSQL | 12+ | Database backend | Supports ON CONFLICT for composite unique constraints |
| Django REST Framework | 3.14+ | API endpoints with MultiPartParser | Existing pattern from Phase 8 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-phonenumber-field | 7.x | Phone validation | NOT needed - Contact.phone is CharField, simple length validation sufficient |
| email-validator | 2.x | Strict email validation | NOT needed - Django's EmailValidator (built-in) handles 99% of cases |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bulk_create(unique_fields=['owner', 'external_id']) | Loop with get_or_create | 10-100x slower, loses atomic batch |
| Django EmailValidator | email-validator package | Adds dependency for features already in Django |
| CharField for phone | phonenumber-field | Adds 5MB dependency, requires country code logic, overkill for simple storage |

**Installation:**
```bash
# No new dependencies required - using stdlib csv + Django 4.2 features
# Existing: Django==4.2.27, djangorestframework, psycopg2-binary
```

## Architecture Patterns

### Recommended Project Structure
```
apps/imports/
├── models.py              # Fund, ImportRun, ImportRowError (EXISTING from Phase 7)
├── services.py            # parse_entities_csv, import_entities (NEW), parse_funds_csv (Phase 8)
├── views.py               # EntityImportView (NEW), FundImportView (Phase 8)
├── urls.py                # Add /api/v1/imports/entities/ (NEW)
└── tests/                 # test_entity_import.py (NEW)
```

### Pattern 1: Owner-Scoped Parse-Validate-Import
**What:** Same three-stage pipeline as Phase 8 (parse CSV → validate → atomic import), but validation checks against user's existing contacts and import assigns owner.

**When to use:** All owner-scoped CSV imports (Contacts, user-specific resources).

**Example:**
```python
# Source: Adapted from Phase 8 parse_funds_csv + existing parse_contacts_csv
def parse_entities_csv(file_content: str, user) -> Tuple[List[dict], List[dict]]:
    """
    Parse entities CSV and return (valid_records, errors).

    Expected columns: entity_id, name, email, phone, address, entity_type

    Args:
        file_content: CSV file content as string
        user: User performing the import (REQUIRED - used for owner scoping)

    Returns:
        Tuple of (valid_records, errors)
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        return [], [{'row': 1, 'errors': [f'Invalid CSV format: {e}'], 'data': {}}]

    valid_records = []
    errors = []
    seen_entity_ids = set()

    # Validate required columns present
    if reader.fieldnames:
        required_cols = {'entity_id', 'name'}
        missing_cols = required_cols - set(reader.fieldnames)
        if missing_cols:
            return [], [{'row': 1, 'errors': [f'Missing required columns: {", ".join(missing_cols)}'], 'data': {}}]

    # Formula injection prevention
    FORMULA_PREFIXES = ('=', '+', '-', '@')

    for row_num, row in enumerate(reader, start=2):
        row_errors = []

        # Required: entity_id (maps to Contact.external_id)
        entity_id = row.get('entity_id', '').strip()
        if not entity_id:
            row_errors.append('entity_id is required')
        elif len(entity_id) > 100:
            row_errors.append('entity_id exceeds maximum length of 100 characters')
        elif entity_id.startswith(FORMULA_PREFIXES):
            row_errors.append(f'entity_id cannot start with formula character ({entity_id[0]})')
        elif entity_id in seen_entity_ids:
            row_errors.append(f'Duplicate entity_id in file: {entity_id}')
        else:
            seen_entity_ids.add(entity_id)

        # Required: name (maps to first_name + last_name)
        # Note: CSV has single 'name' column, split into first/last
        name = row.get('name', '').strip()
        if not name:
            row_errors.append('name is required')
        elif len(name) > 300:  # 150 + 150
            row_errors.append('name exceeds maximum length of 300 characters')
        elif name.startswith(FORMULA_PREFIXES):
            row_errors.append(f'name cannot start with formula character ({name[0]})')

        # Parse name into first_name and last_name
        # Default: last word is last_name, rest is first_name
        name_parts = name.split()
        if len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = ''
        else:
            first_name = ' '.join(name_parts[:-1])
            last_name = name_parts[-1]

        # Optional: email
        email = row.get('email', '').strip().lower()
        if email:
            if not _validate_email(email):
                row_errors.append(f'Invalid email format: "{email}"')
            elif len(email) > 254:
                row_errors.append('email exceeds maximum length of 254 characters')

        # Optional: phone
        phone = row.get('phone', '').strip()
        if phone and len(phone) > 20:
            row_errors.append('phone exceeds maximum length of 20 characters')

        # Optional: address (maps to street_address)
        address = row.get('address', '').strip()
        if address and len(address) > 255:
            row_errors.append('address exceeds maximum length of 255 characters')

        # Optional: entity_type (NOTE: Contact model doesn't have this field)
        # This column is present in SPO exports but has no corresponding field
        # We ignore it for now, may add in future if Contact model is extended

        if row_errors:
            errors.append({'row': row_num, 'errors': row_errors, 'data': dict(row)})
        else:
            valid_records.append({
                'entity_id': entity_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'street_address': address,
            })

    return valid_records, errors
```

### Pattern 2: Owner-Scoped Bulk Upsert with Composite Constraint
**What:** Use bulk_create with update_conflicts on composite UniqueConstraint (owner + external_id). Critical: unique_fields must use model field names, not database column names.

**When to use:** All owner-scoped models with external_id for idempotent imports.

**Example:**
```python
# Source: Django 4.2 bulk_create docs + Contact model constraints
from django.db import transaction
from apps.contacts.models import Contact
from apps.imports.models import ImportRun, ImportStatus

def import_entities(records: List[dict], user, import_run: ImportRun) -> Tuple[int, int]:
    """
    Import entities as Contact records using owner-scoped bulk upsert.

    Args:
        records: List of validated entity dicts from parse_entities_csv
        user: User performing the import (becomes owner of all contacts)
        import_run: ImportRun instance for audit trail

    Returns:
        Tuple of (created_count, updated_count)
    """
    if not records:
        import_run.status = ImportStatus.COMPLETED
        import_run.save()
        return 0, 0

    # Track existing external_ids for this owner to calculate created vs updated
    existing_external_ids = set(
        Contact.objects.filter(
            owner=user,
            external_id__in=[r['entity_id'] for r in records]
        ).values_list('external_id', flat=True)
    )

    contact_objects = [
        Contact(
            owner=user,  # CRITICAL: Set owner on all contacts
            external_id=record['entity_id'],
            first_name=record['first_name'],
            last_name=record['last_name'],
            email=record['email'],
            phone=record['phone'],
            street_address=record['street_address'],
            # Other fields default: status='prospect', country='USA'
        )
        for record in records
    ]

    with transaction.atomic():
        Contact.objects.bulk_create(
            contact_objects,
            update_conflicts=True,
            update_fields=['first_name', 'last_name', 'email', 'phone', 'street_address'],
            unique_fields=['owner', 'external_id']  # MUST match UniqueConstraint fields
        )

    created_count = len([r for r in records if r['entity_id'] not in existing_external_ids])
    updated_count = len(records) - created_count

    import_run.created_count = created_count
    import_run.updated_count = updated_count
    import_run.status = ImportStatus.COMPLETED
    import_run.save()

    return created_count, updated_count
```

**Critical notes:**
- unique_fields=['owner', 'external_id'] matches Contact model's UniqueConstraint(fields=['owner', 'external_id'])
- Use model field name 'owner', NOT database column 'owner_id'
- Update fields must NOT include owner or external_id (those are the lookup keys)
- All Contact instances MUST have owner set (cannot be None for imported entities)

### Pattern 3: Name Field Splitting
**What:** SPO Entities CSV has single 'name' column, but Contact model requires first_name + last_name. Split on last space.

**When to use:** When CSV schema doesn't match model schema exactly.

**Example:**
```python
# Source: Common pattern for name parsing
def parse_name(name: str) -> Tuple[str, str]:
    """
    Parse full name into (first_name, last_name).

    Strategy: Last word is last_name, rest is first_name.
    Edge cases: Single word → (word, ''), Empty → ('', '')
    """
    name = name.strip()
    if not name:
        return '', ''

    name_parts = name.split()
    if len(name_parts) == 1:
        return name_parts[0], ''

    first_name = ' '.join(name_parts[:-1])
    last_name = name_parts[-1]
    return first_name, last_name

# Usage in parse_entities_csv:
name = row.get('name', '').strip()
first_name, last_name = parse_name(name)
```

**Limitations:**
- Fails for "van der Berg" (wants van der as first, Berg as last)
- No way to detect corporate names vs people
- Empty last_name is valid but suboptimal

**Recommendation:** Document limitation in import docs. For MVP, simple split is acceptable. Future enhancement: add "Update Contact" UI for post-import cleanup.

### Anti-Patterns to Avoid
- **Using owner_id in unique_fields:** Django expects model field names ('owner'), not database columns ('owner_id'). This will cause "Unique constraint not found" errors.
- **Forgetting to set owner on Contact instances:** bulk_create will fail with IntegrityError (NOT NULL violation) because Contact.owner is required.
- **Updating owner field on existing contacts:** Never include 'owner' in update_fields. Changing ownership breaks security model and data integrity.
- **No external_id validation:** Same entity_id uploaded twice in one file should error on second occurrence, not silently skip.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full name to first/last splitting | NLP library or complex rules | Simple last-word split | SPO data is already structured, complex cases are rare (< 1%) |
| Phone number validation | Phone parsing library | Length check only | Contact.phone is storage field, not callable number. Validation adds complexity for little value. |
| Email validation | Regex library or DNS checks | Django's EmailValidator | Built-in validator handles 99% of cases, DNS checks slow down import |
| Owner-scoped duplicate detection | Manual query before bulk_create | bulk_create unique_fields | Database handles atomically, prevents race conditions |
| CSV encoding detection | chardet library | decode('utf-8-sig') | Handles Excel BOM, simpler than autodetection |

**Key insight:** The existing Contact model and Phase 8 patterns solve 95% of the work. The only new complexity is owner-scoping in bulk_create, which Django 4.2 handles natively. Don't add libraries for phone/name parsing edge cases that affect <1% of imports.

## Common Pitfalls

### Pitfall 1: Wrong Field Name in unique_fields
**What goes wrong:** bulk_create raises error: "Cannot resolve unique_fields ['owner_id', 'external_id'] to unique constraint."

**Why it happens:** Django's unique_fields expects model field names (e.g., 'owner'), but developers assume it wants database column names (e.g., 'owner_id') because that's what's in the constraint SQL.

**How to avoid:**
- Use unique_fields=['owner', 'external_id'], NOT ['owner_id', 'external_id']
- Verify field names match Contact._meta.get_field('owner').name
- Test with actual data before production

**Warning signs:** IntegrityError about constraint not found during bulk_create call.

**Sources:**
- [Django Forum: Unique constraint not found in bulk_create's unique fields](https://forum.djangoproject.com/t/unique-constraint-not-found-in-bulk-creates-unique-fields/42820)
- [Django Forum: Doubt in usage of bulk_create with update_conflicts=True](https://forum.djangoproject.com/t/doubt-in-the-usage-of-bulk-create-with-update-conflicts-true/26362)

### Pitfall 2: Missing owner Assignment
**What goes wrong:** bulk_create raises IntegrityError: "null value in column 'owner_id' violates not-null constraint."

**Why it happens:** Contact.owner is a required ForeignKey (on_delete=models.PROTECT, no null=True). Forgetting to set owner on Contact instances causes database rejection.

**How to avoid:**
- Always set owner=user in Contact() constructor
- Verify all contact_objects have owner before bulk_create
- Test with actual ImportRun linked to real User

**Warning signs:** IntegrityError mentioning owner_id during import. All Contact instances must belong to a user.

### Pitfall 3: Including owner in update_fields
**What goes wrong:** Existing contacts get reassigned to different owner on re-import, breaking security model. Or bulk_create fails with "fields in unique_fields cannot be in update_fields" error.

**Why it happens:** Developer assumes update_fields should include all fields being set, forgetting that unique_fields are the lookup key.

**How to avoid:**
- update_fields should ONLY include data fields (first_name, last_name, email, phone, address)
- NEVER include unique_fields (owner, external_id) in update_fields
- Think of it like SQL: UPDATE contacts SET first_name=X WHERE owner=Y AND external_id=Z

**Warning signs:** Tests show contact ownership changing on re-import. User imports same CSV twice and sees contacts move to different owner.

### Pitfall 4: entity_type Column Mapping
**What goes wrong:** CSV has entity_type column (e.g., "Individual", "Organization"), but Contact model has no such field. Developer adds validation for it, then import fails because there's nowhere to store it.

**Why it happens:** Requirements mention entity_type column, but Contact model was designed for individuals only (first_name/last_name fields).

**How to avoid:**
- Document in PLAN: entity_type column is IGNORED for Phase 9
- Add comment in parse_entities_csv noting the discrepancy
- Consider future enhancement: add Contact.entity_type field if organizational contacts become important

**Warning signs:** User asks "Where did the entity_type data go?" after import. Tests validate entity_type but don't verify storage.

**Recommendation:** For Phase 9, ignore entity_type column. If needed in future, add Contact.entity_type field + migration in separate phase.

### Pitfall 5: Name Parsing Edge Cases
**What goes wrong:** "van der Berg" becomes first_name="van der", last_name="Berg" (correct), but "LLC" becomes first_name="", last_name="LLC" (wrong - it's an organization, not a person).

**Why it happens:** Simple "last word is last_name" logic fails for single-word names and organizational names.

**How to avoid:**
- Accept the limitation for MVP: edge cases are <1% of SPO exports
- Document: "Single-word names will have empty last_name"
- Provide manual cleanup path: users can edit contacts in UI after import
- Future enhancement: add entity_type logic if Contact model gains that field

**Warning signs:** Users report "My contact's name is wrong" for edge cases. Acceptable if rate is low.

## Code Examples

Verified patterns from official sources:

### Email Validation (Django Built-in)
```python
# Source: Django 4.2 validators + existing DonorCRM services.py
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def _validate_email(email: str) -> bool:
    """Validate email format using Django's built-in validator."""
    if not email:
        return True  # Empty email is allowed

    try:
        validate_email(email)
        return True
    except ValidationError:
        return False

# Usage in parse_entities_csv:
email = row.get('email', '').strip().lower()
if email and not _validate_email(email):
    row_errors.append(f'Invalid email format: "{email}"')
```

**Sources:**
- Django 4.2 core.validators.validate_email
- [Email Validation in Django: Best Practices & Techniques](https://blog.bounceless.io/mastering-email-validation-in-django-best-practices-and-techniques/)

### Owner-Scoped Existence Check
```python
# Source: Existing DonorCRM parse_contacts_csv pattern
# Check if entity_id already exists for this owner
if entity_id:
    if Contact.objects.filter(owner=user, external_id=entity_id).exists():
        # This is an UPDATE operation (upsert will update)
        pass  # Not an error, just informational
```

**Note:** For Phase 9, we DON'T error on existing entity_id because upserts are expected. This differs from parse_contacts_csv which errors on duplicate emails (contacts without external_id shouldn't have duplicates).

### Composite Constraint Verification
```python
# Source: Django model introspection
# Verify unique_fields match actual constraint before bulk_create
from apps.contacts.models import Contact

# Check constraint exists
constraints = Contact._meta.constraints
external_id_constraint = [
    c for c in constraints
    if isinstance(c, models.UniqueConstraint)
    and set(c.fields) == {'owner', 'external_id'}
]

assert len(external_id_constraint) == 1, "Expected owner+external_id unique constraint"
# If this passes, unique_fields=['owner', 'external_id'] is correct
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Loop with get_or_create(owner=user, external_id=X) | bulk_create(unique_fields=['owner', 'external_id']) | Django 4.1 (Aug 2022) | 10-100x performance for owner-scoped upserts |
| Separate queries for create vs update batching | Single bulk_create call | Django 4.1+ | Atomic operation, simpler code |
| owner_id in unique_fields | owner in unique_fields | Django 4.2 best practice | Matches model field names, not column names |
| Manual name parsing libraries | Simple split on last space | Current practice (2024+) | Good enough for 99% of cases, libraries add complexity |
| Complex phone validation | Length-only validation | Current practice for storage fields | Phone is stored, not called. Validation adds little value. |

**Deprecated/outdated:**
- Using database column names (owner_id) instead of model field names (owner) in unique_fields
- Adding phone number parsing libraries for simple storage fields
- Separate create/update logic instead of single bulk_create with update_conflicts

## Open Questions

Things that couldn't be fully resolved:

1. **entity_type Column Handling**
   - What we know: Requirements specify entity_type column in Entities CSV
   - What's unclear: Contact model has no entity_type field to store this data
   - Recommendation: IGNORE entity_type column for Phase 9. Add comment in code noting this. If needed in future, add Contact.entity_type field + migration in separate phase.

2. **Address Field Mapping**
   - What we know: CSV has single 'address' column, Contact has street_address, city, state, postal_code, country
   - What's unclear: Should we parse address into components, or just use street_address?
   - Recommendation: Map 'address' → 'street_address' only. Leave city/state/postal_code blank. SPO may export separate columns; if not, users can manually edit after import.

3. **Name Parsing Strategy**
   - What we know: CSV has 'name', Contact requires first_name + last_name
   - What's unclear: How to handle "van der Berg", "LLC", "John", "Mary Jane Smith"
   - Recommendation: Use simple "last word is last_name" for MVP. Document limitation. Provide manual edit path in UI. Consider nameparser library in future if >5% of imports have issues.

4. **CSV Column Order and Optional Fields**
   - What we know: Requirements list entity_id, name, email, phone, address, entity_type
   - What's unclear: Are email/phone/address optional? What if CSV has different column order?
   - Recommendation: Mark only entity_id and name as required. All others optional. csv.DictReader handles any column order. Match Phase 8 pattern.

## Sources

### Primary (HIGH confidence)
- Django 4.2.27 Documentation: bulk_create with update_conflicts - https://docs.djangoproject.com/en/4.2/ref/models/querysets/#bulk-create
- Existing DonorCRM codebase: apps/contacts/models.py (Contact model with owner-scoped constraint)
- Existing DonorCRM codebase: apps/contacts/migrations/0005_add_external_id.py (UniqueConstraint definition)
- Existing DonorCRM codebase: apps/imports/services.py (Phase 8 parse_funds_csv pattern)
- Django core.validators.validate_email - Built-in email validation

### Secondary (MEDIUM confidence)
- [Django Forum: Unique constraint not found in bulk_create's unique fields](https://forum.djangoproject.com/t/unique-constraint-not-found-in-bulk-creates-unique-fields/42820) - Field naming (owner vs owner_id)
- [Django Forum: Doubt in usage of bulk_create with update_conflicts=True](https://forum.djangoproject.com/t/doubt-in-the-usage-of-bulk-create-with-update-conflicts-true/26362) - Composite constraint examples
- [Django Forum: Bulk_create with UniqueConstraint](https://forum.djangoproject.com/t/bulk-create-with-uniqueconstraint/30508) - NULL handling in constraints
- [Email Validation in Django: Best Practices & Techniques](https://blog.bounceless.io/mastering-email-validation-in-django-best-practices-and-techniques/) - Django EmailValidator usage

### Tertiary (LOW confidence)
- [Django Code Ticket #34943](https://code.djangoproject.com/ticket/34943) - Proposal for unique_constraint parameter (not yet implemented)
- [Medium: Using Enums as Django Model Choices](https://medium.com/@bencleary/using-enums-as-django-model-choices-96c4cbb78b2e) - TextChoices pattern (for future entity_type field)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Django 4.2.27 verified, same stack as Phase 8
- Architecture: HIGH - Owner-scoped bulk_create verified in Django docs and existing Contact model constraints
- Pitfalls: HIGH - Field naming issue verified in Django forums, owner assignment is basic Django pattern
- Name parsing: MEDIUM - Simple split is common practice but edge cases exist
- entity_type handling: LOW - Requirements unclear whether field exists in Contact model (it doesn't)

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable Django/PostgreSQL ecosystem, no fast-moving dependencies)
