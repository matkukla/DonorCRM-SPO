# Phase 32: Import UI - Research

**Researched:** 2026-02-23
**Domain:** React frontend — unified Import/Export page with file upload, import results, and history
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Replace the existing sidebar "Import/Export" link to point to the new page; remove the admin imports sub-page entirely
- Page has three grouped tab sections:
  1. **RE Imports** — 4 tabs: Constituent, Solicitor, Gift, Recurring Gift
  2. **Smartsheet** — MPD import (existing functionality moved here)
  3. **Generic** — Contact and Donation tabs showing "Coming soon" placeholder (backend in Phase 35)
- Import history section below the tab groups listing past ImportBatch records with status icons and summary counts
- **Preview first** workflow: drag-and-drop (or click) to select file -> show filename and size -> user clicks "Import" button to start processing
- CSV header reference (required and optional columns) is **always visible** below the upload area on each tab
- Visual step numbering on RE import tabs (e.g., "Step 1 of 4", "Step 2 of 4") to guide recommended import order — all tabs remain accessible regardless
- After import completes, result banners show success/error/already-processed counts with expandable error details showing row numbers
- 5 import types total: 4 RE CSVs (Constituent, Solicitor, Gift, Recurring Gift) + 1 Smartsheet MPD
- Backend APIs already exist for all 5 import types at `/imports/re/*` and `/imports/mpd/`
- Exports (contacts CSV, donations CSV) currently exist as download buttons — need to be preserved somewhere on the new page
- Current admin Import Center has SPO legacy imports (Funds, Entities, Transactions, Pledges) — these are being removed along with the admin imports page

### Claude's Discretion
- Whether import results display inline on the tab or in a modal dialog
- Loading/progress indicator style during import processing
- Exact layout of the import history section (table vs cards, columns shown)
- How the Smartsheet section is visually distinguished from RE imports
- Error detail expansion pattern (accordion, collapsible section, etc.)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-IMP-01 | Import/Export page accessible from main sidebar (not admin-only) | Sidebar already has "Import/Export" at `/import-export`; rewrite page content at same route |
| UI-IMP-02 | RE import section with 4 tabs (Constituent, Solicitor, Gift, Recurring Gift) | Use existing shadcn Tabs component; nest within section header |
| UI-IMP-03 | Drag-and-drop file upload with file name/size display and import button | Existing ImportCard has native drag-drop pattern; reuse the pattern without react-papaparse |
| UI-IMP-04 | Import result display with success/error/already-processed banners and expandable error list | API returns `summary.errors` array with `{row, error}` objects; use Collapsible for expansion |
| UI-IMP-05 | CSV header reference showing required and optional headers per import type | Static data derived from backend header aliases; render as table below upload area |
| UI-IMP-06 | Import history list with status icons and past ImportBatch records | Needs new backend endpoint: GET `/imports/batches/` returning paginated ImportBatch list |
| UI-IMP-07 | Generic CSV import section for contacts and donations | Placeholder tabs with "Coming soon" message; backend wired in Phase 35 |
| UI-IMP-08 | Remove import functionality from admin analytics page | Remove `/admin/imports` route, ImportCenter page, admin sub-nav "Imports" link |
</phase_requirements>

## Summary

This phase replaces the current dual-location import system (sidebar Import/Export page for generic imports + admin Import Center for SPO/RE imports) with a single unified Import/Export page at the existing `/import-export` route. The page organizes imports into three grouped sections (RE, Smartsheet, Generic) with sub-tabs, shows persistent CSV header references, and displays import history from ImportBatch records. Exports are preserved as a separate section.

The backend API layer for all 5 import types (4 RE + 1 MPD) is fully implemented. The main frontend work involves: (1) rewriting the ImportExport page with the new grouped tab layout, (2) creating reusable upload components that follow the "preview first" workflow (select file -> show filename/size -> click Import), (3) handling the ImportBatch API response format (which is different from the old SPO ImportRun format), (4) adding a new backend endpoint to list ImportBatch history, and (5) removing the admin Import Center page and its route.

**Primary recommendation:** Build on existing project patterns (native drag-drop from ImportCard, Tabs from shadcn, Collapsible for error expansion) and create a new ImportBatch list API endpoint. The SPO import infrastructure (ImportRun, ImportDialog, SPOImportTile) can be fully removed since Phase 30 already returned 410 Gone for those endpoints.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.0 | UI framework | Already in project |
| @tanstack/react-query | 5.90.17 | Server state management | Already in project; used for mutations + queries |
| react-router-dom | 6.30.3 | Routing | Already in project |
| @radix-ui/react-tabs | 1.1.13 | Tab component (via shadcn) | Already in project |
| @radix-ui/react-collapsible | 1.1.12 | Expandable sections (via shadcn) | Already in project |
| lucide-react | 0.562.0 | Icons | Already in project |
| sonner | 2.0.7 | Toast notifications | Already in project |
| date-fns | 4.1.0 | Date formatting | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axios | 1.13.2 | HTTP client (via apiClient) | All API calls go through `api/client.ts` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native drag-drop | react-dropzone | Extra dependency; native pattern already works in ImportCard |
| react-papaparse | Native FileReader | react-papaparse is only used by SPO ImportDialog which is being removed; not needed for RE imports since server handles CSV parsing |

**Installation:** No new packages needed. All required dependencies already exist.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/imports/
│   └── ImportExport.tsx          # REWRITE: unified page with all sections
├── components/imports/
│   ├── REImportTab.tsx           # NEW: single RE import tab (parameterized)
│   ├── REImportSection.tsx       # NEW: RE section with 4 sub-tabs
│   ├── SmartsheetSection.tsx     # NEW: refactored from MPDImportTile
│   ├── GenericImportSection.tsx  # NEW: placeholder section
│   ├── ImportHistorySection.tsx  # NEW: ImportBatch history list
│   ├── ExportSection.tsx         # NEW: export cards (moved from existing)
│   ├── FileDropZone.tsx          # NEW: reusable drag-drop component
│   ├── ImportResultBanner.tsx    # NEW: success/error/duplicate banner
│   ├── CSVHeaderReference.tsx    # NEW: header reference table
│   ├── ExportCard.tsx            # KEEP: existing component
│   ├── MPDImportTile.tsx         # KEEP/REFACTOR: reuse inside SmartsheetSection
│   ├── MPDResultsDialog.tsx      # KEEP: MPD results dialog
│   ├── ImportCard.tsx            # DELETE: only used by old ImportExport page
│   ├── ImportDialog.tsx          # DELETE: SPO import dialog
│   ├── SPOImportTile.tsx         # DELETE: SPO import tile
│   └── CSVPreviewTable.tsx       # DELETE: only used by ImportDialog
├── api/
│   └── imports.ts                # UPDATE: add RE import functions, ImportBatch list, remove SPO functions
├── hooks/
│   └── useImports.ts             # UPDATE: add RE import hooks, ImportBatch list hook, remove SPO hooks
```

### Pattern 1: RE Import API Response Shape
**What:** All 4 RE import endpoints return the same ImportBatch-based response shape.
**When to use:** When building the import result display.
**Example:**
```typescript
// Response from POST /api/v1/imports/re/constituents/ (and similar)
interface REImportResponse {
  batch_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'duplicate'
  is_duplicate: boolean
  created_count: number
  updated_count: number
  skipped_count: number
  error_count: number
  total_rows: number
  summary: {
    errors: Array<{ row: number; error: string }>
    // Type-specific fields may exist (e.g., unlinked_solicitors for solicitor import)
  }
}
```

### Pattern 2: Native Drag-and-Drop File Upload
**What:** Reuse the proven drag-drop pattern from the existing ImportCard component.
**When to use:** All file upload areas (RE imports, Smartsheet).
**Example:**
```typescript
// Extract from existing ImportCard.tsx - proven native pattern
const handleDragOver = (e: React.DragEvent) => {
  e.preventDefault()
  setIsDragging(true)
}
const handleDrop = (e: React.DragEvent) => {
  e.preventDefault()
  setIsDragging(false)
  const droppedFile = e.dataTransfer.files[0]
  if (droppedFile && droppedFile.name.endsWith(".csv")) {
    if (droppedFile.size > MAX_FILE_SIZE) {
      toast.error("File too large (max 10 MB)")
      return
    }
    setFile(droppedFile)
  }
}
```

### Pattern 3: Import Mutation with Query Invalidation
**What:** Use React Query mutations for import API calls with appropriate cache invalidation.
**When to use:** Each import type needs its own mutation hook.
**Example:**
```typescript
export function useREImport(importType: REImportType) {
  const queryClient = useQueryClient()
  const endpoints: Record<REImportType, string> = {
    constituent: '/imports/re/constituents/',
    solicitor: '/imports/re/solicitors/',
    gift: '/imports/re/gifts/',
    recurring_gift: '/imports/re/recurring-gifts/',
  }
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await apiClient.post(endpoints[importType], formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data as REImportResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['importBatches'] })
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['gifts'] })
    },
  })
}
```

### Pattern 4: Grouped Sections with Inner Tabs
**What:** Page layout uses section dividers (not top-level tabs) for the 3 groups, with inner Tabs only for RE sub-types.
**When to use:** The unified page structure.
**Example:**
```typescript
// Page structure: sections stacked vertically, not nested tabs
<div className="space-y-8">
  {/* RE Imports Section */}
  <section>
    <h2>Raiser's Edge Imports</h2>
    <Tabs defaultValue="constituent">
      <TabsList>
        <TabsTrigger value="constituent">1. Constituent</TabsTrigger>
        <TabsTrigger value="solicitor">2. Solicitor</TabsTrigger>
        <TabsTrigger value="gift">3. Gift</TabsTrigger>
        <TabsTrigger value="recurring_gift">4. Recurring Gift</TabsTrigger>
      </TabsList>
      {/* TabsContent for each */}
    </Tabs>
  </section>

  {/* Smartsheet Section */}
  <section>...</section>

  {/* Generic Section */}
  <section>...</section>

  {/* Export Section */}
  <section>...</section>

  {/* Import History Section */}
  <section>...</section>
</div>
```

### Anti-Patterns to Avoid
- **Nested Tabs:** Do not nest tabs within tabs (e.g., top-level Import/Export tabs containing RE sub-tabs). Use vertical sections with one level of tabs per section.
- **CSV Parsing on Frontend:** Do not parse CSV files on the frontend for RE imports. The backend handles encoding detection (UTF-8-sig, UTF-8, Windows-1252), header alias mapping, and validation. Just send the raw file.
- **Using react-papaparse:** The SPO ImportDialog used react-papaparse for client-side preview. RE imports don't need this — the backend does all parsing. Remove this dependency when SPO components are deleted.
- **Mixing ImportRun and ImportBatch:** The old SPO import system uses ImportRun model. The new RE system uses ImportBatch. Don't mix the two in the UI or API layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop upload | Custom DnD library integration | Native HTML5 drag events (pattern from ImportCard) | Already proven in codebase; no extra dependency |
| Tab navigation | Custom tab state management | shadcn Tabs (Radix) | Already installed; handles accessibility, keyboard nav |
| Expandable sections | Custom accordion logic | shadcn Collapsible (Radix) | Already installed; handles animation, a11y |
| File type validation | Complex MIME type checking | Simple file extension check (`.csv`, `.xlsx`) | RE imports only accept CSV; MPD accepts CSV/XLSX |
| Error list display | Custom virtual scrolling | Simple `max-h-60 overflow-y-auto` with Collapsible wrapper | Error lists are typically < 100 items |

**Key insight:** Nearly all UI primitives needed for this phase already exist in the project's component library. The work is composition and layout, not new component development.

## Common Pitfalls

### Pitfall 1: ImportBatch List Endpoint Missing
**What goes wrong:** The frontend needs to display import history, but there is no GET endpoint for listing ImportBatch records.
**Why it happens:** RE import endpoints only exist as POST (upload) endpoints. The import history section needs a list/read endpoint.
**How to avoid:** Create a new DRF ListAPIView for ImportBatch with filtering by import_type and pagination. This is the one backend change needed in this phase.
**Warning signs:** 404 when trying to fetch import history.

### Pitfall 2: Confusing SPO and RE Response Shapes
**What goes wrong:** SPO imports return `{ created_count, updated_count, error_count, errors: string[], import_run_id }`. RE imports return `{ batch_id, status, is_duplicate, created_count, updated_count, skipped_count, error_count, total_rows, summary: { errors: [{row, error}] } }`.
**Why it happens:** Two different import systems with different models.
**How to avoid:** Define a clear `REImportResponse` TypeScript interface matching the actual backend response. Don't try to reuse the old `SPOImportResult` or `ImportResult` types.
**Warning signs:** Type errors when accessing `.summary.errors` vs `.errors`.

### Pitfall 3: Admin Sub-Nav "Imports" Link Left Behind
**What goes wrong:** After removing the admin ImportCenter page and route, the admin sub-navigation (shared across AdminUsers, AdminAnalyticsDashboard, StalledContacts, UserDetail) still shows an "Imports" tab link that 404s.
**Why it happens:** The admin sub-nav is duplicated inline in each admin page component (not extracted to a shared component).
**How to avoid:** When removing `/admin/imports` route, also remove the "Imports" NavLink from ALL admin page components: AdminUsers.tsx, ImportCenter.tsx (deleted entirely), AdminAnalyticsDashboard.tsx, StalledContacts.tsx, UserDetail.tsx.
**Warning signs:** Clicking "Imports" in admin section navigates to a non-existent page.

### Pitfall 4: Duplicate File (SHA256) Handling Display
**What goes wrong:** When a user uploads a file that has already been processed, the backend returns `status: 'duplicate'` and `is_duplicate: true`. If the UI only checks for `status: 'completed'` or `status: 'failed'`, the duplicate case shows nothing.
**Why it happens:** The duplicate status is a special case that isn't an error but also isn't a new import.
**How to avoid:** Explicitly handle the `is_duplicate` flag with an "Already Processed" info banner (not error, not success). Show the original import's counts.
**Warning signs:** No feedback when uploading a previously-processed file.

### Pitfall 5: FormData Content-Type Header
**What goes wrong:** Explicitly setting `Content-Type: multipart/form-data` without the boundary parameter.
**Why it happens:** Developers set the header manually, but the browser needs to set the boundary automatically.
**How to avoid:** Either let the browser set it automatically (don't set the header at all) or use the existing pattern from the codebase which works: `headers: { "Content-Type": "multipart/form-data" }`. Note: In the project's existing code, axios handles this correctly because it detects FormData and sets the proper boundary. The explicit header is technically redundant but not harmful with axios.
**Warning signs:** 400 errors from the backend about malformed multipart data.

### Pitfall 6: Stale Import History Cache
**What goes wrong:** After a successful import, the import history section doesn't show the new entry.
**Why it happens:** React Query caches the import history query and the global staleTime is 5 minutes.
**How to avoid:** In each RE import mutation's `onSuccess`, invalidate the `['importBatches']` query key. Same pattern used by existing `useSPOImport` which invalidates `['latestImports']`.
**Warning signs:** User must manually refresh to see new import in history.

## Code Examples

### CSV Header Reference Data (Static)
```typescript
// Derived from backend HEADER_ALIASES constants in re_services.py
export const RE_IMPORT_HEADERS = {
  constituent: {
    required: ['first_name OR last_name OR organization_name'],
    optional: ['constituent_id', 'email', 'phone', 'street_address', 'city', 'state', 'postal_code', 'country'],
    reAliases: {
      constituent_id: 'CnBio_ID',
      first_name: 'CnBio_First_Name',
      last_name: 'CnBio_Last_Name',
      organization_name: 'CnBio_Org_Name',
      email: 'CnAdrPrf_Email',
      phone: 'CnPh_1_01_Phone_Number',
    },
  },
  solicitor: {
    required: ['raw_name (solicitor name)'],
    optional: ['external_solicitor_id'],
    reAliases: {
      raw_name: 'CnSol_1_01_Name',
      external_solicitor_id: 'CnSol_1_01_Solicit_ID',
    },
  },
  gift: {
    required: ['gift_id', 'constituent_id', 'amount'],
    optional: ['gift_date', 'fund', 'description', 'solicitor_name', 'credit_amount', 'prayer_description'],
    reAliases: {
      gift_id: 'Gf_System_ID or Gf_ID',
      constituent_id: 'Gf_CnBio_ID',
      amount: 'Gf_Amount',
      gift_date: 'Gf_Date',
      fund: 'Gf_Fund',
      solicitor_name: 'Gf_CnSol_1_01_Name',
      credit_amount: 'Gf_CnSol_1_01_Amount',
    },
  },
  recurring_gift: {
    required: ['gift_id', 'constituent_id', 'amount'],
    optional: ['frequency', 'start_date', 'end_date', 'status', 'fund', 'solicitor_name', 'credit_amount'],
    reAliases: {
      gift_id: 'RG_ID or Gf_ID',
      constituent_id: 'Gf_CnBio_ID',
      amount: 'Gf_Amount',
      frequency: 'Gf_Installment_Frequency',
      start_date: 'Gf_Date',
      status: 'Gf_Status',
      solicitor_name: 'CnSol_1_01_Name',
    },
  },
} as const
```

### ImportBatch List Backend Endpoint
```python
# New view needed in apps/imports/views.py
class ImportBatchListView(generics.ListAPIView):
    """GET: List ImportBatch records for import history."""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = ImportBatch.objects.all().order_by('-created_at')
        import_type = self.request.query_params.get('import_type')
        if import_type:
            qs = qs.filter(import_type=import_type)
        return qs[:50]  # Cap at 50 recent records

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [{
            'id': str(b.id),
            'import_type': b.import_type,
            'import_type_display': b.get_import_type_display(),
            'status': b.status,
            'filename': b.filename,
            'total_rows': b.total_rows,
            'created_count': b.created_count,
            'updated_count': b.updated_count,
            'skipped_count': b.skipped_count,
            'error_count': b.error_count,
            'created_at': b.created_at.isoformat(),
            'uploaded_by': b.uploaded_by.full_name,
        } for b in qs]
        return Response(data)

# URL: path('batches/', ImportBatchListView.as_view(), name='import-batch-list'),
```

### Import Result Banner Component
```typescript
// Handles all three states: success, error, duplicate
interface ImportResultBannerProps {
  result: REImportResponse
}

function ImportResultBanner({ result }: ImportResultBannerProps) {
  if (result.is_duplicate) {
    return (
      <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800">
        <Badge variant="secondary" className="gap-1">
          <Info className="h-3 w-3" />
          Already Processed
        </Badge>
        <p className="text-sm mt-2">This file has been imported before. No changes were made.</p>
      </div>
    )
  }
  // ... success and error banners
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SPO CSV imports (Funds, Entities, Transactions, Pledges) via ImportRun | RE imports (Constituent, Solicitor, Gift, Recurring Gift) via ImportBatch | Phase 28-29 (2026-02) | Old SPO endpoints return 410 Gone; all new imports use ImportBatch |
| Admin-only import page at `/admin/imports` | Unified page at `/import-export` accessible to all auth users | This phase | Import moves to main sidebar, no longer admin sub-page |
| react-papaparse for client-side CSV preview | Server-side CSV parsing with encoding detection | Phase 28 | Frontend just sends raw file; no client-side parsing needed |

**Deprecated/outdated:**
- `ImportRun` model / `SPOImportResult` type: Legacy SPO system. Endpoints return 410 Gone since Phase 30. Remove all frontend code referencing these.
- `react-papaparse`: Only used by SPO ImportDialog. Can be uninstalled when ImportDialog is deleted.
- `ImportCard` component: Designed for legacy generic import (contacts/donations). Being replaced by new RE-specific upload components.

## Files to Delete

These files are no longer needed after this phase:

| File | Reason |
|------|--------|
| `frontend/src/pages/admin/ImportCenter.tsx` | Admin import page being removed entirely |
| `frontend/src/components/imports/ImportDialog.tsx` | SPO import dialog; SPO endpoints return 410 |
| `frontend/src/components/imports/SPOImportTile.tsx` | SPO import tile; SPO endpoints return 410 |
| `frontend/src/components/imports/CSVPreviewTable.tsx` | Only used by ImportDialog |
| `frontend/src/components/imports/ImportCard.tsx` | Old generic import card; replaced by new upload components |

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/pages/imports/ImportExport.tsx` | Complete rewrite with new grouped section layout |
| `frontend/src/api/imports.ts` | Add RE import functions, ImportBatch list function; remove SPO functions |
| `frontend/src/hooks/useImports.ts` | Add RE import hooks, ImportBatch list hook; remove SPO hooks |
| `frontend/src/App.tsx` | Remove `/admin/imports` route; remove ImportCenter import |
| `frontend/src/components/layout/Sidebar.tsx` | No change needed — already points to `/import-export` |
| `frontend/src/pages/admin/AdminUsers.tsx` | Remove "Imports" NavLink from admin sub-nav |
| `frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx` | Remove "Imports" NavLink from admin sub-nav |
| `frontend/src/pages/admin/analytics/StalledContacts.tsx` | Remove "Imports" NavLink from admin sub-nav |
| `frontend/src/pages/admin/analytics/UserDetail.tsx` | Remove "Imports" NavLink from admin sub-nav |
| `apps/imports/urls.py` | Add `batches/` URL for ImportBatch list endpoint |
| `apps/imports/views.py` | Add ImportBatchListView |

## Open Questions

1. **Should react-papaparse be uninstalled?**
   - What we know: It's only imported in ImportDialog.tsx (being deleted). No other files use it.
   - What's unclear: Whether to remove it from package.json in this phase or defer cleanup.
   - Recommendation: Remove it in this phase since it's dead code after deleting ImportDialog. Run `npm uninstall react-papaparse` as a task step.

2. **Import history — how many records to show?**
   - What we know: ImportBatch records accumulate over time. No existing pagination pattern for similar lists.
   - What's unclear: Whether to paginate or just show the most recent N records.
   - Recommendation: Show the most recent 20 records without pagination (similar to MPDImportTile which shows 5 recent uploads). This is sufficient for the typical use case and avoids pagination complexity. The backend endpoint caps at 50.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `apps/imports/re_services.py` — Header aliases, required canonical fields, and ImportBatch creation patterns
- Codebase inspection: `apps/imports/views.py` — RE import view response shapes (all 4 views return identical structure)
- Codebase inspection: `apps/imports/models.py` — ImportBatch model fields, ImportBatchType choices, ImportBatchStatus choices
- Codebase inspection: `apps/imports/urls.py` — Existing URL patterns for RE import endpoints
- Codebase inspection: `frontend/src/components/imports/ImportCard.tsx` — Native drag-drop pattern
- Codebase inspection: `frontend/src/components/imports/ImportDialog.tsx` — SPO import state machine (reference for what to NOT carry forward)
- Codebase inspection: `frontend/src/api/imports.ts` — Existing API functions and type definitions
- Codebase inspection: `frontend/src/hooks/useImports.ts` — Existing mutation patterns with query invalidation
- Codebase inspection: `frontend/src/App.tsx` — Current routing structure
- Codebase inspection: `frontend/src/components/layout/Sidebar.tsx` — Sidebar navigation structure

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies needed
- Architecture: HIGH — patterns derived directly from existing codebase; no novel architecture decisions
- Pitfalls: HIGH — identified through direct code inspection of response shape differences, admin sub-nav duplication, and missing endpoints

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable — all patterns are internal to the project)
