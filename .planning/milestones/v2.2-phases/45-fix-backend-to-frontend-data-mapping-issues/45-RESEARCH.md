# Phase 45: Fix Backend-to-Frontend Data Mapping Issues - Research

**Researched:** 2026-03-07
**Domain:** Django REST Framework serializers, Django filter search_fields, React TypeScript API types, contact form UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Contact list displays organization_name in the Name column when first_name + last_name are both blank
- full_name property (and/or ContactListSerializer) updated to fall back to organization_name
- No prefix or label — just the org name, clean, same column as person names
- ContactListSerializer must include organization_name in its fields
- Backend contact search (icontains filter) must include organization_name alongside first_name, last_name, email
- Searching "Acme" finds org contacts by organization_name
- Contact export uses the same full_name fallback — org contacts export with organization_name in the full_name column
- No separate organization_name column in the export
- organization_name is shown AND editable in the contact detail view
- Positioned at the top of the form, alongside First Name / Last Name in the Basic Info section
- ContactDetailSerializer must include organization_name as a writable field
- Edit form includes organization_name as an optional text field
- organization_name is an optional field in the contact create/edit form
- Users can manually create org-type contacts (not just via import)
- ContactCreateSerializer must include organization_name

### Claude's Discretion
- Exact placement of organization_name relative to first_name/last_name fields in the UI form
- Whether to show organization_name as a separate labeled row or inline with the name fields
- Placeholder text for the organization_name input

### Deferred Ideas (OUT OF SCOPE)
- SPO import UI (3-step pipeline: reconcile missionaries, import gifts, import prayers) — explicitly out of scope, no frontend UI to be built in this phase
- SPO result display (per_missionary breakdown, tri-source comparison) — deferred with SPO UI
- Separate organization_name column in contact CSV export — user chose full_name fallback approach
</user_constraints>

---

## Summary

Phase 45 is a surgical data-mapping fix. The `organization_name` field exists on the `Contact` model (added in migration `0006`), is populated during RE constituent imports, but is excluded from every serializer. This causes org-type contacts (first_name and last_name both blank) to appear with blank names across the entire application.

The fix spans three tiers: (1) backend serializers — add `organization_name` to `ContactListSerializer`, `ContactDetailSerializer`, and `ContactCreateSerializer`; (2) backend model/search — update `Contact.full_name` to fall back to `organization_name`, update the `search_fields` list in `ContactListCreateView`, and add `organization_name` to the Q-filter in `ContactSearchView`; (3) frontend — add `organization_name?: string` to `ContactListItem`, `ContactDetail`, and `ContactCreate` TypeScript interfaces, then add the field to `ContactForm.tsx` (both create and edit paths share the same component).

**Primary recommendation:** All changes are additive. No migrations needed (field already exists). The `Contact.full_name` property change is the highest-leverage fix — it propagates everywhere the property is serialized, including the CSV export which uses `contact.full_name` indirectly via the property.

---

## Standard Stack

### Core (verified by direct code inspection)
| Component | Version/Location | Purpose |
|-----------|-----------------|---------|
| DRF ModelSerializer | apps/contacts/serializers.py | Serializes Contact model to/from JSON |
| django-filter 24.3 | apps/contacts/filters.py | FilterSet for list endpoint |
| DRF SearchFilter | apps/contacts/views.py:56 | search_fields for the list endpoint |
| React + TypeScript | frontend/src/api/contacts.ts | API type interfaces |
| shadcn/ui Input + Label | frontend/src/pages/contacts/ContactForm.tsx | Form field components |

---

## Architecture Patterns

### Serializer Inheritance Pattern
`ContactDetail` interface in TypeScript **extends** `ContactListItem`. This means adding `organization_name?: string` to `ContactListItem` automatically makes it available on `ContactDetail` as well. The Python side does NOT use inheritance — each serializer declares its own `fields` list independently.

### Two Distinct Search Paths
There are **two separate search mechanisms** in `apps/contacts/views.py`:

1. **`ContactListCreateView` (line 49):** Uses DRF's `SearchFilter` backend with `search_fields = ['first_name', 'last_name', 'email']`. The `search` query param drives this. Adding `'organization_name'` to this list enables search on the contacts list page.

2. **`ContactSearchView` (line 242):** Used by `searchContacts()` API function (which hits `/contacts/search/?q=...`). This view uses a manual `Q()` filter on `first_name`, `last_name`, `email`, `phone`. Organization_name must be explicitly added here too.

Both paths need updating.

### CSV Export Pattern
`export_views.py` (line 70) hand-builds the Name column with `f'{contact.first_name} {contact.last_name}'` rather than using the `full_name` property. This is the one place where fixing the `full_name` property alone does NOT propagate automatically. The export `generate_csv()` function must be updated to use `contact.full_name` (or equivalent fallback) instead of the manual f-string.

### ContactForm.tsx Serves Both Create and Edit
`ContactForm.tsx` is used for both creating new contacts (`/contacts/new`) and editing existing ones (`/contacts/:id/edit`). The form's `formData` state is typed as `ContactCreate`. The `useEffect` that pre-populates from `existingContact` (line 53-70) must also be updated to include `organization_name` from the contact detail response.

### Validation: first_name and last_name Are Currently Required
`ContactForm.tsx` validate() at line 84 requires both `first_name` and `last_name`. For org contacts, both can be blank. The validation must be relaxed: require that at least one of `first_name`, `last_name`, or `organization_name` is non-blank.

### ContactCreateSerializer Does NOT Have first_name/last_name as Required
Looking at the model: `first_name` and `last_name` are `CharField` with `max_length=150` and no `blank=True` at the model level. This means the database requires non-blank values. However, RE imports set them to empty string `""` for org contacts. The backend `ContactCreateSerializer` requires `first_name` and `last_name` by default (DRF CharField without `required=False` or `allow_blank=True`). This needs investigation — if org contacts are only imported (not manually created), this may already be handled by the import service bypassing serializer validation.

**Verified:** Looking at `re_services.py`, the import service creates contacts directly via `Contact.objects.create(**validated_data)` or `Contact.objects.update_or_create(...)`, bypassing the API serializer. So org contacts with blank first/last names reach the database fine through the import path. But if a user tries to create an org contact via the API form, the serializer will reject blank first_name/last_name.

**Action required:** `ContactCreateSerializer` needs `first_name` and `last_name` to have `allow_blank=True` (and `required=False`) to support manually creating org-type contacts — per locked decision "Users can manually create org-type contacts."

### Read-Only Fields Pattern
`ContactDetailSerializer.Meta.read_only_fields` does NOT include `organization_name`, so it will be writable by default once added to `fields`. No special handling needed. The pattern: fields listed in `read_only_fields` are protected; fields in `fields` but not in `read_only_fields` are writable.

---

## Complete Change Map

### Backend Changes

#### 1. `apps/contacts/models.py` — `Contact.full_name` property (line 151-154)
**Current:**
```python
@property
def full_name(self):
    """Return the contact's full name."""
    return f'{self.first_name} {self.last_name}'.strip()
```
**Change:** Add fallback to `organization_name` when first+last are blank.
```python
@property
def full_name(self):
    """Return the contact's full name, falling back to organization_name for org contacts."""
    name = f'{self.first_name} {self.last_name}'.strip()
    return name or self.organization_name
```

#### 2. `apps/contacts/serializers.py` — `ContactListSerializer` (line 11-25)
Add `'organization_name'` to the `fields` list. No other changes needed — `full_name` is already a read-only CharField that pulls from the property.

#### 3. `apps/contacts/serializers.py` — `ContactDetailSerializer` (line 28-83)
Add `'organization_name'` to the `fields` list. It is NOT in `read_only_fields`, so it will be writable.

#### 4. `apps/contacts/serializers.py` — `ContactCreateSerializer` (line 86-121)
Add `'organization_name'` to the `fields` list. Also add `allow_blank=True` and `required=False` to `first_name` and `last_name` fields to support org-type contacts. These need explicit field declarations (not just listed in Meta.fields).

#### 5. `apps/contacts/views.py` — `ContactListCreateView.search_fields` (line 56)
**Current:** `search_fields = ['first_name', 'last_name', 'email']`
**Change:** `search_fields = ['first_name', 'last_name', 'email', 'organization_name']`

#### 6. `apps/contacts/views.py` — `ContactSearchView.get_queryset()` (line 261-266)
Add `Q(organization_name__icontains=query)` to the Q filter chain.

#### 7. `apps/contacts/export_views.py` — `generate_csv()` (line 70)
**Current:** `sanitize_csv_value(f'{contact.first_name} {contact.last_name}')`
**Change:** `sanitize_csv_value(contact.full_name)` — uses the property which now falls back to organization_name.

### Frontend Changes

#### 8. `frontend/src/api/contacts.ts` — `ContactListItem` interface (line 5-19)
Add: `organization_name?: string`

#### 9. `frontend/src/api/contacts.ts` — `ContactCreate` interface (line 40-54)
Add: `organization_name?: string`

Note: `ContactDetail` extends `ContactListItem`, so change #8 propagates automatically.

#### 10. `frontend/src/pages/contacts/ContactForm.tsx` — form state and useEffect
- Add `organization_name: ""` to initial `formData` state
- Add `organization_name: existingContact.organization_name || ""` in the `useEffect` pre-population block
- Add Organization Name Input field in the Basic Information card (per Claude's discretion: separate labeled row above First Name / Last Name)
- Update `validate()` to require at least one of `first_name`, `last_name`, or `organization_name`

#### 11. `frontend/src/pages/contacts/ContactDetail.tsx` — overview tab display
The contact detail view shows `contact.full_name` in the page header (line 169) — this will already display correctly once the backend `full_name` property and serializer are updated. No header change needed.

The "Contact Information" card (line 278-314) shows email, phone, address but NOT the name fields (they're in the header). The `organization_name` field should appear in the "Basic Info" section — but there is no "Basic Info" section in the detail view. The Contact Information card is for contact details (email, phone, address). A sensible placement: add `organization_name` display to the Contact Information card when it has a value, below the header.

**Alternative (better):** The CONTEXT says "positioned at the top of the form alongside First Name / Last Name in the Basic Info section" — this refers to the **edit form** (`ContactForm.tsx`), not the detail view display. For the detail view itself, show organization_name as a labeled field in the Contact Information card (similar to how email and phone are shown).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| ORM search across multiple fields | Custom SQL | DRF SearchFilter `search_fields` list (list endpoint) or Q() objects (search endpoint) |
| CSV streaming | Custom buffer | Existing `Echo` pseudo-buffer pattern already in `export_views.py` |
| Form validation | Custom required-field logic | Extend the existing `validate()` in `ContactForm.tsx` |

---

## Common Pitfalls

### Pitfall 1: Forgetting the Two Search Paths
**What goes wrong:** Developer adds `organization_name` to `search_fields` on `ContactListCreateView` but forgets to update `ContactSearchView.get_queryset()`. The main contact list search works, but the typeahead/search endpoint (used by journal contact-add dialogs) still misses org contacts.
**How to avoid:** Update both locations: `search_fields` list (line 56) AND the `Q()` filter in `ContactSearchView` (line 261).

### Pitfall 2: CSV Export Still Uses f-string
**What goes wrong:** `full_name` property is fixed, serializers are fixed, but the CSV export still produces blank Name column for org contacts because it uses `f'{contact.first_name} {contact.last_name}'` directly.
**How to avoid:** Replace the f-string at `export_views.py:70` with `contact.full_name`.

### Pitfall 3: ContactForm Validation Blocks Org Contact Creation
**What goes wrong:** `first_name` and `last_name` are required by the frontend validation and the backend serializer. Submitting an org contact with blank first/last fails.
**How to avoid:** (a) Update `validate()` in `ContactForm.tsx` to accept org contacts (require at least one of three name fields). (b) Add `allow_blank=True, required=False` to `first_name` and `last_name` fields in `ContactCreateSerializer`.

### Pitfall 4: useEffect Pre-population Misses organization_name
**What goes wrong:** Edit form pre-populates from `existingContact` but `organization_name` is not in the `setFormData()` call, so editing an org contact clears the org name on save.
**How to avoid:** Add `organization_name: existingContact.organization_name || ""` to the `useEffect` block.

### Pitfall 5: ContactDetail Interface Change Not Typed Correctly
**What goes wrong:** `ContactDetail extends ContactListItem` — adding `organization_name` to `ContactListItem` is sufficient. Developer might duplicate it on `ContactDetail` causing type conflicts.
**How to avoid:** Add ONLY to `ContactListItem`. The extension handles the rest.

---

## Code Examples

### full_name property fix
```python
# apps/contacts/models.py — Contact.full_name (verified: line 151)
@property
def full_name(self):
    """Return the contact's full name, falling back to organization_name for org contacts."""
    name = f'{self.first_name} {self.last_name}'.strip()
    return name or self.organization_name
```

### ContactListSerializer fields addition
```python
# apps/contacts/serializers.py — ContactListSerializer.Meta.fields (verified: line 20)
fields = [
    'id', 'first_name', 'last_name', 'full_name',
    'organization_name',          # ADD THIS
    'email', 'phone', 'status',
    'total_given', 'gift_count', 'last_gift_date',
    'needs_thank_you', 'owner', 'owner_name'
]
```

### ContactCreateSerializer with allow_blank
```python
# apps/contacts/serializers.py — ContactCreateSerializer
class ContactCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'organization_name',  # ADD organization_name
            'email', 'phone', 'phone_secondary',
            'street_address', 'city', 'state', 'postal_code', 'country',
            'status', 'notes', 'group_ids',
            'total_given', 'gift_count', 'needs_thank_you'
        ]
        read_only_fields = ['id', 'total_given', 'gift_count', 'needs_thank_you']
```

### Search fields update
```python
# apps/contacts/views.py — ContactListCreateView (verified: line 56)
search_fields = ['first_name', 'last_name', 'email', 'organization_name']
```

### ContactSearchView Q filter
```python
# apps/contacts/views.py — ContactSearchView.get_queryset() (verified: line 261-266)
if query:
    queryset = queryset.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query) |
        Q(organization_name__icontains=query)   # ADD THIS
    )
```

### CSV export fix
```python
# apps/contacts/export_views.py — generate_csv() (verified: line 70)
yield writer.writerow([
    sanitize_csv_value(contact.full_name),      # WAS: f'{contact.first_name} {contact.last_name}'
    sanitize_csv_value(contact.email or ''),
    sanitize_csv_value(contact.phone or ''),
    sanitize_csv_value(contact.status or ''),
    sanitize_csv_value(contact.owner.full_name if contact.owner else ''),
    contact.last_gift_date or '',
    str(contact.total_given or 0),
])
```

### TypeScript interface additions
```typescript
// frontend/src/api/contacts.ts — ContactListItem (verified: line 5)
export interface ContactListItem {
  id: string
  first_name: string
  last_name: string
  full_name: string
  organization_name?: string    // ADD THIS
  email: string | null
  phone: string | null
  status: ContactStatus
  total_given: string
  gift_count: number
  last_gift_date: string | null
  needs_thank_you: boolean
  owner: string
  owner_name: string
}

// frontend/src/api/contacts.ts — ContactCreate (verified: line 40)
export interface ContactCreate {
  first_name: string
  last_name: string
  organization_name?: string    // ADD THIS
  email?: string
  // ... rest unchanged
}
```

### ContactForm validate() update
```typescript
// frontend/src/pages/contacts/ContactForm.tsx — validate() (verified: line 84)
const validate = (): boolean => {
  const newErrors: Record<string, string> = {}

  // For org contacts, organization_name can substitute for first/last name
  const hasPersonName = formData.first_name?.trim() || formData.last_name?.trim()
  const hasOrgName = formData.organization_name?.trim()

  if (!hasPersonName && !hasOrgName) {
    newErrors.first_name = "First name or organization name is required"
  }

  if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
    newErrors.email = "Invalid email address"
  }

  setErrors(newErrors)
  return Object.keys(newErrors).length === 0
}
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | conftest.py (root) |
| Quick run command | `pytest apps/contacts/tests/ -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `Contact.full_name` returns organization_name when first+last blank | unit | `pytest apps/contacts/tests/ -x -q -k "full_name"` | ❌ Wave 0 |
| ContactListSerializer includes organization_name | unit | `pytest apps/contacts/tests/ -x -q -k "serializer"` | ❌ Wave 0 |
| Contact list API includes organization_name in response | integration | `pytest apps/contacts/tests/test_integration.py -x -q` | ❌ add test |
| Search finds org contacts by organization_name (list endpoint) | integration | `pytest apps/contacts/tests/ -x -q -k "search"` | ❌ Wave 0 |
| Search finds org contacts by organization_name (search endpoint) | integration | `pytest apps/contacts/tests/ -x -q -k "search"` | ❌ Wave 0 |
| CSV export uses full_name (org contact appears correctly) | unit | `pytest apps/contacts/tests/ -x -q -k "export"` | ❌ Wave 0 |
| ContactCreateSerializer accepts blank first/last with org name | unit | `pytest apps/contacts/tests/ -x -q -k "create"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/contacts/tests/ -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/contacts/tests/test_org_contact_mapping.py` — dedicated test file covering all 7 behaviors above
- [ ] `ContactFactory` in `apps/contacts/tests/factories.py` — add `OrgContactFactory` with blank first/last and non-blank organization_name

No missing framework or conftest — existing `conftest.py` and pytest infrastructure cover all needs.

---

## Open Questions

1. **Does the model allow blank first_name/last_name at the DB level?**
   - What we know: Model fields are `CharField(max_length=150)` without `blank=True` — Django CharField without blank=True sets `blank=False` for form validation but NOT for DB-level. The DB column is VARCHAR without NOT NULL or CHECK constraint on content, so empty string `""` is stored fine.
   - What's unclear: Does DRF enforce `blank=False` at the serializer level for CharFields sourced from model fields without explicit `blank=True`?
   - Recommendation: Explicitly declare `first_name` and `last_name` in `ContactCreateSerializer` with `required=False, allow_blank=True` rather than relying on model introspection. Safe and explicit.

2. **Does ContactDetail.tsx need a separate "Organization" section/display?**
   - What we know: The overview tab has a "Contact Information" card (email, phone, address) and a "Groups & Notes" card. No "Basic Info" card exists in the detail view — "Basic Info" language appears only in the form.
   - What's unclear: Where exactly to surface organization_name in the read-only detail view.
   - Recommendation (Claude's discretion): Add it to the Contact Information card as a labeled row before email, since it's a primary identification field. Display only when non-blank (same conditional pattern as email/phone).

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `apps/contacts/serializers.py` — verified all three serializers and their fields lists
- Direct code inspection of `apps/contacts/models.py` — verified `full_name` property and `organization_name` field
- Direct code inspection of `apps/contacts/views.py` — verified both search paths (`search_fields` and `ContactSearchView` Q filter)
- Direct code inspection of `apps/contacts/export_views.py` — verified CSV generation uses f-string, not property
- Direct code inspection of `frontend/src/api/contacts.ts` — verified all three TypeScript interfaces
- Direct code inspection of `frontend/src/pages/contacts/ContactForm.tsx` — verified form state, validation, and useEffect
- Direct code inspection of `frontend/src/pages/contacts/ContactDetail.tsx` — verified header uses `full_name`, no organization_name display

### Secondary (MEDIUM confidence)
- Migration `apps/contacts/migrations/0006_contact_external_constituent_id_and_more.py` — confirmed `organization_name` field exists at DB level (file path verified via glob)

---

## Metadata

**Confidence breakdown:**
- Change map (what to change and where): HIGH — every change location verified by direct code inspection
- Serializer pattern (read_only_fields, field ordering): HIGH — verified from existing code
- Two search paths: HIGH — verified both in `views.py`
- CSV export issue: HIGH — verified f-string usage at line 70 of `export_views.py`
- Frontend TypeScript inheritance: HIGH — `ContactDetail extends ContactListItem` verified at line 21 of `contacts.ts`
- Validation relaxation: MEDIUM — DRF CharField blank handling requires the explicit `allow_blank` declaration to be safe

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable codebase, no external dependencies changing)

---

## RESEARCH COMPLETE
