# Phase 35: Generic CSV Import - Research

**Researched:** 2026-02-24
**Domain:** CSV import pipeline (Django backend + React frontend)
**Confidence:** HIGH

## Summary

Phase 35 adds two new import types -- generic contacts and generic donations -- to the existing import infrastructure built in Phases 27-29 and 32. The RE import pipeline (`re_services.py`) provides a complete, battle-tested pattern for CSV parsing, SHA256 dedup, cascading encoding, header alias mapping, row-level error collection, and ImportBatch result tracking. The frontend has a ready-made placeholder (`GenericImportSection.tsx`) with two "Coming soon" cards that need to be wired up with real functionality using the same `FileDropZone`, `ImportResultBanner`, and `useREImport`-style hooks already in place.

The key differentiator from RE imports is that generic imports do NOT have fixed header schemas. Instead, users upload CSVs with arbitrary column names, and the backend needs flexible column matching. For contacts, the system must support configurable dedup matching (by name, email, or external ID). For donations, the system must link to existing contacts and trigger stat recalculation via the existing `update_giving_stats()` method and Gift signal infrastructure.

**Primary recommendation:** Follow the RE import orchestrator pattern exactly (same function signature, same return type, same error shape) to ensure the existing `ImportResultBanner` and `ImportHistorySection` components work without modification. Add new endpoint pairs at `/imports/generic/contacts/` and `/imports/generic/donations/`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMP-08 | Generic CSV import for contacts with matching and dedup options | Backend: new `import_generic_contacts()` in `re_services.py` (or new `generic_services.py`) using `_match_contact()` three-tier hierarchy + configurable matching mode. Frontend: replace GenericImportSection placeholder with real FileDropZone + matching option selector. |
| IMP-09 | Generic CSV import for donations with contact linking and stat recalculation | Backend: new `import_generic_donations()` creating Gift records with contact lookup (by name, email, or external ID), using Gift post_save signal for auto stat recalculation. Frontend: donations card with FileDropZone + import button. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python csv (stdlib) | 3.x | CSV parsing with DictReader | Already used throughout imports; no external dependency needed |
| Django ORM | 4.2+ | Database operations, transactions, atomic savepoints | Already used for all RE imports with proven savepoint isolation pattern |
| hashlib (stdlib) | 3.x | SHA256 file dedup | Already used via `check_duplicate_import()` in re_services.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.x | Mutation hooks for file upload + query invalidation | Already used by `useREImport` hook |
| shadcn/ui | latest | FileDropZone, ImportResultBanner, Select, Badge | Already used for RE import UI components |
| sonner | latest | Toast notifications for import errors | Already used in REImportTab |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom CSV parsing | django-import-export | Overkill for two import types; adds dependency for no clear benefit. Project already has working CSV parsing infrastructure. |
| Manual column matching | Automatic header inference | Manual matching adds complexity. Header alias approach (like RE imports) with broader default aliases is simpler. |

**Installation:** No new packages needed. All required infrastructure already exists.

## Architecture Patterns

### Recommended Project Structure

```
apps/imports/
├── re_services.py            # Existing RE import orchestrators (no changes)
├── generic_services.py       # NEW: Generic contact + donation import orchestrators
├── views.py                  # ADD: GenericContactImportView, GenericDonationImportView
├── urls.py                   # ADD: generic/contacts/, generic/donations/ endpoints
└── models.py                 # No changes (ImportBatchType already has GENERIC_CONTACTS, GENERIC_DONATIONS)

frontend/src/
├── api/imports.ts            # ADD: importGenericContacts(), importGenericDonations() functions
├── hooks/useImports.ts       # ADD: useGenericContactImport(), useGenericDonationImport() hooks
└── components/imports/
    └── GenericImportSection.tsx  # REPLACE: placeholder -> real upload cards
```

### Pattern 1: Follow RE Import Orchestrator Pattern

**What:** Each generic import function follows the same 7-step pattern as `import_re_constituents()` and `import_re_gifts()`:
1. SHA256 dedup check via `check_duplicate_import()`
2. Decode with `decode_csv_bytes()` cascading encoding
3. Parse CSV with `csv.DictReader` + header alias mapping via `_build_header_mapping()`
4. Validate required headers
5. Iterate rows with per-row error collection inside `transaction.atomic()`
6. Create ImportBatch record with results
7. Return ImportBatch

**When to use:** Both generic contact and donation imports.

**Example (orchestrator signature):**
```python
def import_generic_contacts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
    match_by: str = 'name',  # 'name', 'email', or 'external_id'
) -> ImportBatch:
    """Import generic contact CSV end-to-end.

    Returns ImportBatch (may be existing if duplicate).
    """
```

### Pattern 2: Header Alias Mapping for Flexible Columns

**What:** Use the existing `_build_header_mapping()` function with broad alias dictionaries that cover common CSV header variations (e.g., "First Name", "first_name", "FirstName", "fname" all map to canonical `first_name`).

**When to use:** Generic imports need broader alias coverage than RE imports since users may export from any system (Google Contacts, Outlook, spreadsheets, etc.).

**Example (contact header aliases):**
```python
GENERIC_CONTACT_HEADER_ALIASES: dict[str, str] = {
    # First name
    'first_name': 'first_name',
    'first name': 'first_name',
    'firstname': 'first_name',
    'fname': 'first_name',
    'given name': 'first_name',
    'given_name': 'first_name',
    # Last name
    'last_name': 'last_name',
    'last name': 'last_name',
    'lastname': 'last_name',
    'lname': 'last_name',
    'surname': 'last_name',
    'family name': 'last_name',
    'family_name': 'last_name',
    # Email
    'email': 'email',
    'email_address': 'email',
    'email address': 'email',
    'e-mail': 'email',
    # ... etc.
}
```

### Pattern 3: Configurable Contact Matching

**What:** The user selects a matching strategy when uploading contacts. The backend uses different matching logic based on the selection.

**When to use:** Generic contact import (IMP-08 requires "configurable matching by name, email, or external ID").

**Matching strategies:**
- **By name**: Match on `(first_name, last_name)` within owner scope. Exact match (case-insensitive). Creates new if no match.
- **By email**: Match on `email` within owner scope. Uses existing `unique_contact_email_per_owner` constraint logic.
- **By external ID**: Match on `external_id` within owner scope (uses existing `external_id` field on Contact, NOT `external_constituent_id`). For users importing from non-RE systems.

**Example (matching mode parameter):**
```python
match_by = request.data.get('match_by', 'email')  # Sent with FormData
```

### Pattern 4: Donation Contact Linking

**What:** Generic donation import CSV rows must reference an existing contact. The matching uses the same configurable strategy as contacts: by name, email, or external ID.

**When to use:** Generic donation import (IMP-09).

**Key fields:**
- `contact_first_name` + `contact_last_name` (name matching)
- `contact_email` (email matching)
- `contact_external_id` (external ID matching)
- `amount` (required)
- `date` / `gift_date` (required)
- `description` (optional)

### Pattern 5: Gift Signal for Stat Recalculation

**What:** The existing `post_save` signal on Gift model automatically calls `contact.update_giving_stats()` and sets `needs_thank_you = True` and creates an Event. This fires for every Gift created, including via import.

**When to use:** Generic donation import. No manual stat recalculation needed -- the signal handles it. For large imports, this is acceptable because the RE gift import also uses the same pattern (no `disable_gift_signals()`).

**Important caveat:** The signal fires per-Gift. For a 500-row donation CSV, this means 500 calls to `update_giving_stats()`. The RE import already works this way, so this is the established pattern. If performance becomes a concern, the `disable_gift_signals()` / `enable_gift_signals()` functions exist but are currently only used in `generate_sample_data`.

### Anti-Patterns to Avoid

- **Building a column mapping UI (drag-drop or complex config):** Out of scope per REQUIREMENTS.md ("Drag-drop column mapping UI" is explicitly listed in Out of Scope). Use alias-based auto-detection instead.
- **Using the old SPO import code path:** The `ContactImportView` and `parse_contacts_csv()` in services.py are legacy code. Build new generic importers following the RE pattern with ImportBatch tracking.
- **Creating a preview/dry-run step:** Not in requirements. The RE imports don't have preview. Keep it simple: upload -> import -> show results.
- **Adding WebSocket real-time progress:** Explicitly out of scope in REQUIREMENTS.md.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File encoding detection | Custom encoding sniffer | `decode_csv_bytes()` from re_services.py | Handles UTF-8-sig, UTF-8, Windows-1252 with null byte stripping |
| SHA256 file dedup | Custom dedup logic | `check_duplicate_import()` from re_services.py | Already handles ImportBatch lookup and dedup status |
| Field sanitization | Custom sanitizer | `_sanitize_field()` from re_services.py | Strips whitespace, truncates to 10k chars, strips null bytes |
| Import result display | New result component | `ImportResultBanner` component | Handles success/partial/duplicate states with expandable error list |
| File upload UI | New upload component | `FileDropZone` component | Drag-drop, file validation, size limit, selected file display |
| Query invalidation | Manual cache busting | React Query `invalidateQueries` in mutation `onSuccess` | Already used in `useREImport` hook pattern |
| Contact matching hierarchy | New matching code | `_match_contact()` from re_services.py (for external_constituent_id/email/phone tiers) | Proven three-tier matching with logging. For generic imports, adapt to use configurable single-tier matching. |

**Key insight:** The RE import pipeline built in Phases 28-29 already solves 90% of the problems. The generic import is essentially a simplified version of RE import with broader header aliases and configurable matching instead of fixed constituent_id matching.

## Common Pitfalls

### Pitfall 1: Duplicate Contacts on Name Match

**What goes wrong:** Two contacts named "John Smith" exist. Name-based matching picks the first one found, potentially linking to the wrong contact.
**Why it happens:** Name matching is inherently ambiguous -- names are not unique identifiers.
**How to avoid:** For name matching, match within owner scope AND require exact match on both first AND last name (case-insensitive). If multiple matches found, skip the row with an error: "Multiple contacts match 'John Smith' -- use email or external ID matching instead."
**Warning signs:** Users report donations linked to wrong contacts after import.

### Pitfall 2: Missing Contact for Donation Import

**What goes wrong:** Donation CSV row references a contact that doesn't exist. The row silently creates nothing or throws an unhandled error.
**Why it happens:** User imports donations before importing contacts, or contact matching fails.
**How to avoid:** Collect missing-contact rows as errors (same pattern as RE gift import: "Constituent ID not found -- skipping gift group"). Show clear error message: "Row 5: No contact found matching 'john@example.com' -- import contacts first or check matching criteria."
**Warning signs:** Import shows 0 created with many errors.

### Pitfall 3: Amount Format Variations

**What goes wrong:** Users enter amounts as "$1,234.56", "1234.56", "1,234", or negative amounts. Parser fails or creates wrong values.
**Why it happens:** Generic CSVs come from diverse sources with no standard format.
**How to avoid:** Reuse `_parse_amount_to_cents()` from re_services.py which handles $, commas, and decimal parsing. Add validation for zero/negative amounts.
**Warning signs:** Gift records with $0.00 amount or unexpected values.

### Pitfall 4: Date Format Ambiguity

**What goes wrong:** Is "01/02/2026" January 2 or February 1? Depends on locale.
**Why it happens:** US vs. international date formats are inherently ambiguous in MM/DD vs DD/MM.
**How to avoid:** Reuse `_parse_date()` from re_services.py which tries YYYY-MM-DD first (unambiguous), then MM/DD/YYYY. Document that MM/DD/YYYY is assumed for ambiguous dates (US locale is the project's primary audience -- missionaries with US organizations).
**Warning signs:** Dates in the wrong month.

### Pitfall 5: Not Invalidating the Right Query Keys

**What goes wrong:** After successful generic import, the contacts list or gifts list doesn't update until manual refresh.
**Why it happens:** Missing query key invalidation in the mutation's `onSuccess` handler.
**How to avoid:** Follow `useREImport` pattern: invalidate `['contacts']`, `['gifts']`, `['importBatches']`, and `['dashboard']` on success.
**Warning signs:** Stale data after import until page refresh.

### Pitfall 6: Permission Model Mismatch

**What goes wrong:** Generic import section is visible to all users (per Phase 32 decision), but the backend endpoint requires admin-only access, causing 403 errors for staff users.
**Why it happens:** RE imports are admin-only, but generic imports should be accessible to staff users who manage their own contacts and donations.
**How to avoid:** Use `IsStaffOrAbove` permission (not `IsAdmin`) for generic import endpoints. Staff users can only import to their own ownership scope (`owner=request.user`). Admin users import with the same behavior (owner is the uploading user).
**Warning signs:** Staff users see the import section but get permission errors when trying to upload.

## Code Examples

### Backend: Generic Contact Import Orchestrator (simplified)

```python
# apps/imports/generic_services.py

GENERIC_CONTACT_HEADER_ALIASES: dict[str, str] = {
    'first_name': 'first_name', 'first name': 'first_name',
    'firstname': 'first_name', 'fname': 'first_name',
    'given name': 'first_name', 'given_name': 'first_name',
    'last_name': 'last_name', 'last name': 'last_name',
    'lastname': 'last_name', 'lname': 'last_name',
    'surname': 'last_name', 'family name': 'last_name',
    'email': 'email', 'email_address': 'email', 'email address': 'email',
    'e-mail': 'email',
    'phone': 'phone', 'phone_number': 'phone', 'phone number': 'phone',
    'external_id': 'external_id', 'id': 'external_id',
    'organization': 'organization_name', 'org_name': 'organization_name',
    'organization_name': 'organization_name',
    'street_address': 'street_address', 'address': 'street_address',
    'city': 'city', 'state': 'state',
    'postal_code': 'postal_code', 'zip': 'postal_code', 'zip_code': 'postal_code',
    'country': 'country',
    'notes': 'notes',
}

def import_generic_contacts(
    file_bytes: bytes,
    filename: str,
    uploaded_by: User,
    owner: User,
    match_by: str = 'email',
) -> ImportBatch:
    """Import generic contacts CSV.

    match_by options: 'name', 'email', 'external_id'
    """
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 1: SHA256 dedup
    existing = check_duplicate_import(file_bytes, ImportBatchType.GENERIC_CONTACTS)
    if existing:
        existing.status = ImportBatchStatus.DUPLICATE
        existing.save(update_fields=['status'])
        return existing

    # Step 2: Decode
    content = decode_csv_bytes(file_bytes)

    # Step 3: Parse + validate headers
    reader = csv.DictReader(io.StringIO(content))
    col_map = _build_header_mapping(reader.fieldnames or [], GENERIC_CONTACT_HEADER_ALIASES)

    # Step 4: Validate minimum headers based on match_by
    # ... (validate that required columns for the matching strategy exist)

    # Step 5: Iterate rows with matching + merge/create
    with transaction.atomic():
        for row_number, row in enumerate(reader, start=2):
            # Build row_data from col_map
            # Match using selected strategy
            # Create or merge contact
            pass

    # Step 6: Create ImportBatch
    return batch
```

### Backend: Generic Donation Import View Pattern

```python
class GenericContactImportView(APIView):
    """POST: Import generic contacts CSV."""
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided.'}, status=400)

        file = request.FILES['file']
        if file.size > MAX_UPLOAD_SIZE:
            return Response({'detail': 'File too large (max 10 MB).'}, status=400)

        file_bytes = file.read()
        match_by = request.data.get('match_by', 'email')

        if match_by not in ('name', 'email', 'external_id'):
            return Response({'detail': 'Invalid match_by option.'}, status=400)

        batch = import_generic_contacts(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            match_by=match_by,
        )

        # Return same shape as RE imports for ImportResultBanner compatibility
        return Response({
            'batch_id': str(batch.id),
            'status': batch.status,
            'is_duplicate': batch.status == ImportBatchStatus.DUPLICATE,
            'created_count': batch.created_count,
            'updated_count': batch.updated_count,
            'skipped_count': batch.skipped_count,
            'error_count': batch.error_count,
            'total_rows': batch.total_rows,
            'summary': batch.summary,
        })
```

### Frontend: Generic Import Hook Pattern

```typescript
// hooks/useImports.ts -- add alongside existing hooks

export type GenericImportType = 'contacts' | 'donations'

const GENERIC_ENDPOINTS: Record<GenericImportType, string> = {
  contacts: '/imports/generic/contacts/',
  donations: '/imports/generic/donations/',
}

export function useGenericImport(importType: GenericImportType) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, matchBy }: { file: File; matchBy: string }) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('match_by', matchBy)
      return apiClient.post(GENERIC_ENDPOINTS[importType], formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data as REImportResponse)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['gifts'] })
      queryClient.invalidateQueries({ queryKey: ['importBatches'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
```

### Frontend: GenericImportSection Replacement

```tsx
// components/imports/GenericImportSection.tsx

export function GenericImportSection() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileUp className="h-5 w-5 text-muted-foreground" />
          Generic CSV Import
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <GenericContactImportCard />
        <GenericDonationImportCard />
      </div>
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Legacy `parse_contacts_csv()` in services.py | RE-style import with ImportBatch tracking | Phase 28 (2026-02-22) | Generic imports must follow the ImportBatch pattern, not the legacy error-only pattern |
| `ContactImportView` with `ImportRun` tracking | `REConstituentImportView` with `ImportBatch` tracking | Phase 28 | New generic views should use ImportBatch, not ImportRun |
| Per-model import views (FundImportView, EntityImportView) | Unified RE import views returning same response shape | Phase 32 | Generic imports must return the same `REImportResponse` shape for `ImportResultBanner` compatibility |

**Deprecated/outdated:**
- `ContactImportView`: Uses old `parse_contacts_csv()` with `ImportRun` tracking. Do not extend -- build new views following RE pattern.
- `DonationImportView`: Returns 410 Gone. Fully superseded.
- `services.py` import functions: Legacy SPO code. Do not modify or reuse (except utility functions like `_validate_email`, `_parse_amount`, `_parse_date` which can be referenced).

## Open Questions

1. **Contact matching: merge-only or full overwrite?**
   - What we know: RE constituent import uses merge-only (`merge_contact_fields()` -- only fills blank fields, never overwrites). The existing legacy `import_contacts()` in services.py always creates new contacts (no update).
   - What's unclear: Should generic contact import follow merge-only (like RE) or always create new (like legacy)?
   - Recommendation: Follow merge-only pattern (like RE imports) for consistency. This is safer and prevents accidental data loss. The match_by parameter controls WHICH contact to merge into; merge_contact_fields controls WHAT gets updated.

2. **Should generic contact import also support the three-tier matching hierarchy?**
   - What we know: RE constituent import uses three-tier matching (constituent_id > email > phone). Generic import requirement says "configurable matching (by name, email, or external ID)."
   - What's unclear: Should the user pick ONE strategy, or should it be a hierarchy?
   - Recommendation: Single strategy selection (not hierarchy). The user selects one matching mode. This is simpler and more predictable. The three-tier hierarchy is RE-specific because RE data always has constituent IDs.

3. **Permission model for generic imports**
   - What we know: RE imports are admin-only (`IsAdmin`). Generic import placeholder is "visible to all users" per Phase 32. The requirement says "user can upload."
   - What's unclear: Should staff users be able to import, or only admin?
   - Recommendation: Use `IsStaffOrAbove` so staff users can import contacts/donations for their own scope (`owner=request.user`). This aligns with the UI being "visible to all users" and the requirement saying "user can upload."

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of `apps/imports/re_services.py` (RE import orchestrators with all utility functions)
- Direct codebase inspection of `apps/imports/models.py` (ImportBatchType already includes GENERIC_CONTACTS, GENERIC_DONATIONS)
- Direct codebase inspection of `apps/imports/views.py` (RE import view pattern with ImportBatch response shape)
- Direct codebase inspection of `frontend/src/components/imports/` (GenericImportSection placeholder, REImportTab pattern, FileDropZone, ImportResultBanner)
- Direct codebase inspection of `apps/gifts/signals.py` (Gift post_save signal for stat recalculation)
- Direct codebase inspection of `apps/contacts/models.py` (Contact model with matching fields and constraints)
- Direct codebase inspection of `apps/gifts/models.py` (Gift model with cents-based amounts)

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` (IMP-08, IMP-09 definitions; Out of Scope items)
- `.planning/STATE.md` (Phase decisions and accumulated context)
- `.planning/research/CSV_IMPORT_ARCHITECTURE.md` (Original CSV import architecture research)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use; no new dependencies
- Architecture: HIGH - Follows proven RE import pattern exactly; all utility functions verified in codebase
- Pitfalls: HIGH - Identified from actual codebase patterns and prior phase decisions

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable -- no dependency changes expected)
