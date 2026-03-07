# Phase 45: Fix Backend-to-Frontend Data Mapping Issues - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix places where data that the backend stores correctly does not reach the frontend — specifically: organization_name field on Contact is stored and imported but never serialized to the frontend, causing org-type contacts to show blank names across the entire application.

SPO import UI (Phase 44 endpoints) is explicitly OUT OF SCOPE for this phase — the 3-step pipeline UI will not be built.

</domain>

<decisions>
## Implementation Decisions

### Organization name in contact list
- Contact list displays organization_name in the Name column when first_name + last_name are both blank
- full_name property (and/or ContactListSerializer) updated to fall back to organization_name
- No prefix or label — just the org name, clean, same column as person names
- ContactListSerializer must include organization_name in its fields

### Organization name search
- Backend contact search (icontains filter) must include organization_name alongside first_name, last_name, email
- Searching "Acme" finds org contacts by organization_name

### Organization name in CSV export
- Contact export uses the same full_name fallback — org contacts export with organization_name in the full_name column
- No separate organization_name column in the export

### Contact detail view — organization_name field
- organization_name is shown AND editable in the contact detail view
- Positioned at the top of the form, alongside First Name / Last Name in the Basic Info section
- ContactDetailSerializer must include organization_name as a writable field
- Edit form includes organization_name as an optional text field

### Contact create form — organization_name field
- organization_name is an optional field in the contact create/edit form
- Users can manually create org-type contacts (not just via import)
- ContactCreateSerializer must include organization_name

### SPO import UI
- NOT implemented in this phase — explicitly deferred
- The 3-step SPO pipeline (reconcile missionaries, import gifts, import prayers) has no frontend UI in Phase 45
- SPO result display (per_missionary breakdown) is also deferred

### Claude's Discretion
- Exact placement of organization_name relative to first_name/last_name fields in the UI form
- Whether to show organization_name as a separate labeled row or inline with the name fields
- Placeholder text for the organization_name input

</decisions>

<specifics>
## Specific Ideas

- org contacts come from RE constituent imports where Organization Name is populated and First/Last are blank
- The full_name property on the Contact model currently returns `f'{self.first_name} {self.last_name}'.strip()` — empty string for orgs — this needs to fall back to organization_name
- The ContactListSerializer, ContactDetailSerializer, and ContactCreateSerializer all need organization_name added

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ContactListSerializer` (apps/contacts/serializers.py:11) — add organization_name to fields list
- `ContactDetailSerializer` (apps/contacts/serializers.py:28) — add organization_name to fields and remove from read_only_fields
- `ContactCreateSerializer` (apps/contacts/serializers.py:86) — add organization_name to fields
- `Contact.full_name` property (apps/contacts/models.py:152) — update fallback to return organization_name when first+last are blank
- `ContactListItem` interface (frontend/src/api/contacts.ts) — add organization_name?: string
- `ContactDetail` interface (frontend/src/api/contacts.ts) — add organization_name?: string
- `ContactCreate` interface (frontend/src/api/contacts.ts) — add organization_name?: string
- ContactDetail page (frontend/src/pages/contacts/ContactDetail.tsx) — add field in Basic Info section
- Contact search filter (apps/contacts/filters.py or views.py) — extend icontains to cover organization_name

### Established Patterns
- Serializer fields: read_only_fields declared explicitly in Meta; writable fields omitted from read_only_fields
- Frontend contact types: ContactDetail extends ContactListItem — organization_name added to ContactListItem flows down
- Edit forms in contact detail use the same ContactDetailSerializer — one serializer change covers view + edit

### Integration Points
- ContactListSerializer feeds contact list table and its Name column
- Contact.full_name property is used in ContactListSerializer (as CharField read_only) and elsewhere — the property fix propagates everywhere full_name is serialized
- ContactDetailSerializer feeds the contact detail page (view + edit)
- ContactCreateSerializer feeds the create contact dialog
- Search is handled in contacts/filters.py or contacts/views.py — the search= query param filters

</code_context>

<deferred>
## Deferred Ideas

- SPO import UI (3-step pipeline: reconcile missionaries, import gifts, import prayers) — explicitly out of scope, no frontend UI to be built in this phase
- SPO result display (per_missionary breakdown, tri-source comparison) — deferred with SPO UI
- Separate organization_name column in contact CSV export — user chose full_name fallback approach

</deferred>

---

*Phase: 45-fix-backend-to-frontend-data-mapping-issues*
*Context gathered: 2026-03-07*
