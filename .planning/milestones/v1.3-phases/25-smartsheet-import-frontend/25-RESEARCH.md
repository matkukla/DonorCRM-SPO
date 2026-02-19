# Phase 25: Smartsheet MPD Report Frontend - Research

**Researched:** 2026-02-19
**Domain:** React frontend (file upload, data display, backend API endpoints)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Upload lives in the **Import Center** as a new tab/tile alongside existing CSV import types
- After upload, results display in a **modal/dialog** (not inline or navigation)
- Results modal shows **unmatched names with their financial row data** so admin can see what was skipped
- Upload history display is at Claude's discretion (see below)
- MPD data appears as a **new "MPD Overview" section below existing dashboard content** (not integrated into team table)
- Key fields per missionary: **MPD Cap, Roll Forward Balance, Months Remaining** (not full snapshot)
- Layout: **sortable summary table** with one row per missionary and MPD columns
- No "last uploaded" freshness date indicator needed
- MPD data is **inline with existing stats** on the admin per-missionary detail page (not a separate tab/section)
- Shows same fields: MPD Cap, Roll Forward Balance, Months Remaining
- Missionaries see their **own MPD data on their home/overview page**
- Same detail level as admin sees (MPD Cap, Roll Forward Balance, Months Remaining)
- **Latest snapshot only** -- no trend charts or historical comparison

### Claude's Discretion
- Whether to show upload history list in Import Center (past uploads with date/filename/counts)
- Exact placement and styling of MPD fields on missionary detail and personal views
- Loading states and empty states when no MPD data exists yet
- Error handling UX for failed uploads

### Deferred Ideas (OUT OF SCOPE)
- Historical trend display (MPD Cap over time charts, sparklines) -- requirement IMP-10 mentions trend enablement but user wants latest-only for now. Data accumulates; visualization can be added later.
</user_constraints>

## Summary

This phase adds MPD (Ministry Partner Development) financial data surfacing across four frontend touchpoints: Import Center upload tile, admin analytics dashboard table, admin per-missionary detail page, and the missionary's personal dashboard. A critical discovery is that **no backend read endpoints exist yet** -- Phase 24 only created the upload endpoint (`POST /api/v1/imports/mpd/`). This phase must create 2-3 new backend API endpoints before any frontend data display is possible.

The frontend work follows well-established patterns in the codebase. The Import Center already has 4 SPO CSV tiles with a dialog-based upload flow (ImportDialog + SPOImportTile). The admin analytics dashboard uses TanStack Table for sortable tables and shadcn/ui Cards. The personal missionary dashboard uses StatCard and Card components. All API communication uses axios via `apiClient` with React Query hooks.

**Primary recommendation:** Build 2 new backend endpoints first (admin MPD overview list + current user MPD data), then add the MPD upload tile to Import Center reusing existing dialog patterns, then surface data on the admin dashboard and missionary views using existing component patterns.

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | ^5.90.17 | Server state management | Already used for all API hooks |
| @tanstack/react-table | ^8.21.3 | Sortable table on admin dashboard | Already used in TeamActivityTable, DataTable |
| axios | ^1.13.2 | HTTP client via `apiClient` | Already used for all API calls |
| @radix-ui/react-dialog | ^1.1.15 | Results modal after upload | Already used in ImportDialog |
| lucide-react | ^0.562.0 | Icons | Already used everywhere |
| sonner | ^2.0.7 | Toast notifications | Already used for upload feedback |
| react-papaparse | ^4.4.0 | CSV file parsing in browser | Already used in ImportDialog's CSVReader |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| date-fns | ^4.1.0 | Date formatting | For upload timestamps in history |
| class-variance-authority | ^0.7.1 | Component variants | For badge/button styling |

### Alternatives Considered
None -- this phase uses only existing libraries. No new dependencies needed.

## Architecture Patterns

### Critical Discovery: Missing Backend Endpoints

Phase 24 created ONLY:
- `POST /api/v1/imports/mpd/` -- Upload MPD file (returns upload_id, matched/unmatched counts)
- Models: `MPDUpload`, `MPDSnapshot`
- Service: `process_mpd_upload()` in `mpd_services.py`

**Missing endpoints that must be built:**
1. `GET /api/v1/imports/mpd/overview/` -- Admin: Latest MPD snapshot data per user (for dashboard table)
2. `GET /api/v1/imports/mpd/me/` -- Any user: Current user's latest MPD snapshot (for personal dashboard)
3. `GET /api/v1/imports/mpd/uploads/` -- Admin: Upload history list (optional, Claude's discretion)

### Recommended File Structure
```
# Backend (new files/additions)
apps/imports/views.py          # Add MPDOverviewView, MPDMyDataView, MPDUploadHistoryView
apps/imports/urls.py           # Add new URL patterns

# Frontend (new files)
frontend/src/api/mpd.ts                          # MPD API functions and types
frontend/src/hooks/useMPD.ts                     # React Query hooks for MPD data
frontend/src/components/imports/MPDImportTile.tsx # Upload tile for Import Center
frontend/src/components/imports/MPDResultsDialog.tsx # Results modal after upload
frontend/src/components/mpd/MPDOverviewTable.tsx  # Sortable table for admin dashboard
frontend/src/components/mpd/MPDStatsInline.tsx    # Inline stats for detail/personal views

# Frontend (modified files)
frontend/src/pages/admin/ImportCenter.tsx                    # Add MPD tile
frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx # Add MPD section
frontend/src/pages/admin/analytics/UserDetail.tsx            # Add MPD inline stats
frontend/src/pages/Dashboard.tsx                             # Add MPD inline stats
```

### Pattern 1: MPD Upload Tile (Import Center)

**What:** New tile in Import Center for MPD Smartsheet uploads
**When to use:** Import Center page layout

The existing Import Center uses `SPOImportTile` + `ImportDialog` for CSV imports. The MPD tile is different because:
- Accepts CSV or XLSX (not just CSV)
- No validate-then-import flow (single-step upload)
- Results show matched/unmatched missionaries (not created/updated/errors)
- No template download needed

**Example pattern (from existing SPOImportTile):**
```typescript
// ImportCenter.tsx currently has:
const IMPORT_CONFIGS: Array<{ type: ImportType; title: string; description: string }> = [...]

// MPD tile should be added separately (not in IMPORT_CONFIGS array)
// because it has different behavior/props than SPO CSV imports.
// Place it after the existing grid, perhaps in its own section.
```

### Pattern 2: Results Dialog (Modal)

**What:** Modal showing upload results after MPD file processing
**When to use:** After successful MPD upload

The existing `ImportDialog` uses `useReducer` for a multi-step state machine (upload -> preview -> validate -> import -> complete). The MPD dialog is simpler:
- Upload step (file picker, accepts .csv and .xlsx)
- Processing step (spinner)
- Results step (matched count, unmatched list with financial data)

**Example pattern (from existing ImportDialog):**
```typescript
// Existing ImportDialog uses:
Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
// from @radix-ui/react-dialog (shadcn/ui wrapper)

// Max dialog width for wide content (unmatched rows table):
<DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">

// File upload uses native drag-and-drop (MPD shouldn't use react-papaparse
// since it doesn't need CSV preview parsing -- backend handles all parsing):
<input type="file" accept=".csv,.xlsx,.xls" />
```

**Key difference from ImportDialog:** The MPD upload sends the raw file to the backend and gets structured results back. No client-side CSV parsing needed (unlike SPO imports that use react-papaparse for preview). Use native `<input type="file">` with drag-and-drop.

### Pattern 3: Sortable Admin Dashboard Table

**What:** MPD Overview table on admin analytics dashboard
**When to use:** Below existing dashboard content

**Example pattern (from TeamActivityTable.tsx):**
```typescript
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
} from "@tanstack/react-table"

// Column definitions with sortable headers:
columnHelper.accessor("current_mpd_cap", {
  header: ({ column }) => (
    <button
      className="flex items-center gap-2 hover:text-foreground cursor-pointer"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      MPD Cap
      <ArrowUpDown className="h-4 w-4" />
    </button>
  ),
  cell: (info) => formatCurrency(info.getValue()),
})
```

### Pattern 4: Inline MPD Stats (Detail/Personal Pages)

**What:** MPD data displayed alongside existing stats
**When to use:** Admin UserDetail page and missionary Dashboard

**Example pattern (from UserDetail.tsx metrics grid):**
```typescript
// Existing pattern on UserDetail:
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
  <Card>
    <CardHeader>
      <CardTitle className="text-sm font-medium text-muted-foreground">
        Total Contacts
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{user.total_contacts}</div>
    </CardContent>
  </Card>
  ...
</div>

// MPD fields can be added as additional Card items in the same grid,
// or as a separate "MPD Overview" Card with internal layout.
```

### Pattern 5: API Layer Convention

**What:** Consistent API client + React Query hook pattern
**When to use:** All new endpoints

**Example pattern (from api/imports.ts + hooks/useImports.ts):**
```typescript
// api/mpd.ts - API functions
export async function uploadMPDFile(file: File): Promise<MPDUploadResult> {
  const formData = new FormData()
  formData.append("file", file)
  const response = await apiClient.post("/imports/mpd/", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  })
  return response.data
}

export async function getMPDOverview(): Promise<MPDOverviewResponse> {
  const response = await apiClient.get("/imports/mpd/overview/")
  return response.data
}

// hooks/useMPD.ts - React Query hooks
export function useMPDOverview() {
  return useQuery({
    queryKey: ["mpd", "overview"],
    queryFn: getMPDOverview,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useMPDUpload() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadMPDFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mpd"] })
    },
  })
}
```

### Anti-Patterns to Avoid
- **Don't use react-papaparse for MPD upload:** The backend handles CSV/XLSX parsing. Using react-papaparse would try to parse XLSX in the browser (it can't) and is unnecessary for CSV since we don't need a preview step.
- **Don't add MPD as an ImportType in the existing IMPORT_CONFIGS array:** MPD has completely different behavior (no validate-then-import, different result format, accepts XLSX). Keep it as a separate section/tile.
- **Don't fetch full MPDSnapshot for dashboard/detail views:** The user decided on 3 fields only (MPD Cap, Roll Forward Balance, Months Remaining). The backend endpoint should return only what's needed.
- **Don't create new page routes for MPD:** Data is embedded in existing pages (Import Center, Admin Dashboard, UserDetail, Dashboard).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sortable table | Custom sort logic | `@tanstack/react-table` with `getSortedRowModel` | Already used in TeamActivityTable, handles all edge cases |
| File upload with drag-and-drop | Custom drag-and-drop | Native HTML5 drag events (see ImportCard pattern) | Existing ImportCard already has this exact pattern |
| Modal dialog | Custom modal | `Dialog` from `@radix-ui/react-dialog` (shadcn/ui) | Already used by ImportDialog |
| Server state | Manual fetch/cache | `@tanstack/react-query` | Already used for all API data |
| Toast notifications | Custom alerts | `sonner` via `toast()` | Already used throughout the app |
| Currency formatting | Regex-based | `Intl.NumberFormat` | Already used in SupportProgress, GivingSummaryCard |

**Key insight:** Every UI pattern needed for this phase already exists in the codebase. The MPD features are essentially "the same patterns applied to different data."

## Common Pitfalls

### Pitfall 1: No Backend Read Endpoints Exist
**What goes wrong:** Frontend code tries to fetch MPD data from endpoints that don't exist yet
**Why it happens:** Phase 24 only created the upload endpoint, not read endpoints
**How to avoid:** Build backend endpoints FIRST before any frontend data display components. The upload tile/dialog can be built in parallel since `POST /api/v1/imports/mpd/` already exists.
**Warning signs:** 404 errors when fetching MPD overview or personal MPD data

### Pitfall 2: MPD Upload Accepts XLSX -- Not Just CSV
**What goes wrong:** File picker only accepts .csv, or frontend tries to parse XLSX client-side
**Why it happens:** All other imports in the Import Center are CSV-only with react-papaparse
**How to avoid:** Use `accept=".csv,.xlsx,.xls"` on file input. Do NOT use react-papaparse CSVReader. Send raw file to backend (backend handles format detection via PK magic bytes per 24-02 decision).
**Warning signs:** "File must be a CSV" errors when uploading XLSX files

### Pitfall 3: Unmatched Rows Need Financial Data
**What goes wrong:** Results dialog only shows names for unmatched missionaries, not their financial data
**Why it happens:** The current MPDImportView response includes `unmatched_rows` as `[{row, first_name, last_name}]` -- no financial data
**How to avoid:** The backend `unmatched_rows` JSON currently stores only `{row, first_name, last_name}`. To show financial data for unmatched rows, either: (a) expand the backend response to include key financial fields in unmatched_rows, or (b) re-read the MPDUpload's unmatched_rows from the model which already has this structure. **The user explicitly requested "unmatched names with their financial row data"** -- this requires a backend change to include financial fields (mpd_cap, roll_forward_balance, months_remaining at minimum) in the unmatched_rows JSON.
**Warning signs:** Results dialog shows names but no financial context for skipped rows

### Pitfall 4: months_remaining_rf Is a CharField, Not Numeric
**What goes wrong:** Frontend tries to format months_remaining as a number, crashes on "infinite"
**Why it happens:** Per Phase 24 decision, `months_remaining_rf` is a CharField that can be numeric or "infinite"
**How to avoid:** Display as-is (string), or check for "infinite" explicitly before numeric formatting
**Warning signs:** NaN or formatting errors when displaying months remaining

### Pitfall 5: DecimalField Values Come as Strings from DRF
**What goes wrong:** Currency formatting fails because values are strings like "3085.00" not numbers
**Why it happens:** Django REST Framework serializes DecimalField to strings by default
**How to avoid:** Parse with `parseFloat()` before formatting, or use a serializer that coerces to float. The existing dashboard uses cents (integers), but MPD values are dollar-amount DecimalFields.
**Warning signs:** "[object Object]" or "NaN" displayed instead of currency values

### Pitfall 6: Missionary Personal View Needs Permission-Appropriate Endpoint
**What goes wrong:** Staff users can't access admin-only MPD endpoints, or endpoint leaks other users' data
**Why it happens:** All MPD data currently behind admin-only upload endpoint
**How to avoid:** Create a `/api/v1/imports/mpd/me/` endpoint that returns only the current user's latest snapshot, with `permissions.IsAuthenticated` (not IsAdmin). The admin overview endpoint should use `IsAdmin`.
**Warning signs:** 403 errors for staff users trying to see their own MPD data

## Code Examples

### Backend: MPD Overview Endpoint (Admin)
```python
# In apps/imports/views.py
class MPDOverviewView(APIView):
    """
    GET: Latest MPD snapshot data per active user (admin only).
    Returns list of users with their latest MPD Cap, Roll Forward Balance,
    and Months Remaining.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.users.models import User
        from django.db.models import Subquery, OuterRef

        # Get latest snapshot per user using subquery
        latest_upload_ids = MPDSnapshot.objects.filter(
            user=OuterRef('pk')
        ).order_by('-upload__created_at').values('upload_id')[:1]

        users_with_mpd = User.objects.filter(
            is_active=True,
            mpd_snapshots__isnull=False,
        ).distinct().prefetch_related('mpd_snapshots')

        results = []
        for user in users_with_mpd:
            latest = user.mpd_snapshots.order_by('-upload__created_at').first()
            if latest:
                results.append({
                    'user_id': str(user.id),
                    'user_name': user.full_name,
                    'current_mpd_cap': str(latest.current_mpd_cap) if latest.current_mpd_cap else None,
                    'latest_roll_forward_balance': str(latest.latest_roll_forward_balance) if latest.latest_roll_forward_balance else None,
                    'months_remaining_rf': latest.months_remaining_rf,
                })

        return Response({'missionaries': results})
```

### Backend: My MPD Data Endpoint (Any Authenticated User)
```python
class MPDMyDataView(APIView):
    """
    GET: Current user's latest MPD snapshot.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        latest = MPDSnapshot.objects.filter(
            user=request.user
        ).select_related('upload').order_by('-upload__created_at').first()

        if not latest:
            return Response({'has_data': False})

        return Response({
            'has_data': True,
            'current_mpd_cap': str(latest.current_mpd_cap) if latest.current_mpd_cap else None,
            'latest_roll_forward_balance': str(latest.latest_roll_forward_balance) if latest.latest_roll_forward_balance else None,
            'months_remaining_rf': latest.months_remaining_rf,
        })
```

### Frontend: Currency Formatting Helper
```typescript
// Use existing Intl.NumberFormat pattern from GivingSummaryCard/SupportProgress:
function formatMPDCurrency(value: string | null): string {
  if (!value) return "--"
  const num = parseFloat(value)
  if (isNaN(num)) return "--"
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}
```

### Frontend: File Upload Without react-papaparse
```typescript
// Pattern from ImportCard.tsx adapted for CSV+XLSX:
const fileInputRef = useRef<HTMLInputElement>(null)

const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  const selectedFile = e.target.files?.[0]
  if (!selectedFile) return

  const validExtensions = ['.csv', '.xlsx', '.xls']
  const hasValidExtension = validExtensions.some(ext =>
    selectedFile.name.toLowerCase().endsWith(ext)
  )

  if (!hasValidExtension) {
    toast.error("Please upload a CSV or Excel file")
    return
  }
  if (selectedFile.size > MAX_FILE_SIZE) {
    toast.error("File too large (max 10 MB)")
    return
  }

  setFile(selectedFile)
}

// Note: Per 24-02 decision, no file extension check on the backend.
// Frontend validates extension for UX; backend auto-detects from PK magic bytes.
```

### Backend: Unmatched Rows with Financial Data

The current `match_users()` function in `mpd_services.py` stores unmatched rows as:
```python
unmatched.append({
    'row': row_num,
    'first_name': row_data.get('_first_name', ''),
    'last_name': row_data.get('_last_name', ''),
})
```

To satisfy the user requirement of showing financial data for unmatched rows, modify to include key fields:
```python
unmatched.append({
    'row': row_num,
    'first_name': row_data.get('_first_name', ''),
    'last_name': row_data.get('_last_name', ''),
    # Add financial data so admin can see what was skipped
    'current_mpd_cap': str(row_data.get('current_mpd_cap', '')) if row_data.get('current_mpd_cap') is not None else None,
    'latest_roll_forward_balance': str(row_data.get('latest_roll_forward_balance', '')) if row_data.get('latest_roll_forward_balance') is not None else None,
    'months_remaining_rf': row_data.get('months_remaining_rf', ''),
})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-papaparse for all uploads | Native file input for non-CSV formats | Always (XLSX can't be parsed by papaparse) | MPD upload must use native file input |
| Separate validation + import steps | Single-step upload (backend validates + imports atomically) | Phase 24 design | MPD dialog is simpler than SPO import dialog |

**Deprecated/outdated:**
- None relevant. All libraries in `package.json` are current versions.

## Open Questions

1. **Unmatched Rows Financial Data Requires Backend Change**
   - What we know: User explicitly wants "unmatched names with their financial row data" in the results dialog
   - What's unclear: The current `match_users()` in `mpd_services.py` stores only `{row, first_name, last_name}` in `unmatched_rows`. The financial data IS available at that point in the code (it's in `row_data`) but is not saved.
   - Recommendation: Modify `match_users()` to include `current_mpd_cap`, `latest_roll_forward_balance`, and `months_remaining_rf` in the unmatched_rows JSON. This is a ~5 line backend change. The MPDUpload model already stores `unmatched_rows` as JSONField, so the schema change is backward-compatible.

2. **Upload History -- Recommend YES**
   - What we know: User marked this as Claude's discretion
   - What's unclear: How much history to show, what fields
   - Recommendation: YES, show upload history. It's essentially free to build (MPDUpload model already has all needed data: filename, created_at, total_rows, matched_count, unmatched_count, status). Display as a small list below the MPD upload tile showing last 5 uploads. This helps admin verify that uploads are being processed correctly and provides an audit trail. The endpoint can piggyback on the overview endpoint or be a separate lightweight query.

3. **Admin Per-Missionary Detail = UserDetail Page?**
   - What we know: User says "admin per-missionary detail page" should show MPD inline
   - What's unclear: The existing `UserDetail.tsx` at `/admin/analytics/users/:id` shows analytics metrics. Is this the right page? There's no separate "missionary detail" page.
   - Recommendation: Yes, `UserDetail.tsx` is the admin's per-missionary view. Add MPD stats (3 Card items) to the existing metrics grid. This page already fetches user data; we'll add a second query for the user's latest MPD snapshot.

4. **How to Get MPD Data for Specific User (Admin)**
   - What we know: Admin UserDetail page needs a specific user's MPD data
   - What's unclear: Whether to build a parameterized endpoint or reuse the overview list
   - Recommendation: Add a `user_id` query parameter to the `/api/v1/imports/mpd/me/` endpoint (admin can pass any user_id, non-admin gets their own). Or create a separate `/api/v1/imports/mpd/user/<uuid:user_id>/` endpoint for admin. The simplest approach is to have the overview endpoint return all users' data and filter client-side (the data set is small -- typically <50 missionaries).

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** -- Read all relevant files directly:
  - `apps/imports/views.py` -- MPDImportView (POST endpoint, lines 836-901)
  - `apps/imports/models.py` -- MPDUpload + MPDSnapshot models
  - `apps/imports/mpd_services.py` -- process_mpd_upload, match_users, parse_row
  - `apps/imports/urls.py` -- Only `mpd/` URL pattern exists (POST)
  - `frontend/src/pages/admin/ImportCenter.tsx` -- Existing import center layout
  - `frontend/src/components/imports/ImportDialog.tsx` -- Multi-step dialog pattern
  - `frontend/src/components/imports/SPOImportTile.tsx` -- Tile component pattern
  - `frontend/src/components/imports/ImportCard.tsx` -- File upload drag-and-drop pattern
  - `frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx` -- Dashboard layout
  - `frontend/src/pages/admin/analytics/components/TeamActivityTable.tsx` -- Sortable table pattern
  - `frontend/src/pages/admin/analytics/UserDetail.tsx` -- Per-user detail page
  - `frontend/src/pages/Dashboard.tsx` -- Personal dashboard layout
  - `frontend/src/api/imports.ts` -- Import API client pattern
  - `frontend/src/hooks/useImports.ts` -- React Query hooks pattern
  - `frontend/src/api/dashboard.ts` -- Dashboard API types
  - `frontend/src/hooks/useDashboard.ts` -- Dashboard hooks pattern
  - `frontend/src/providers/AuthProvider.tsx` -- User role checking
  - `frontend/src/components/auth/ProtectedRoute.tsx` -- Role-based access
  - `frontend/src/api/client.ts` -- Axios client with JWT
  - `frontend/src/api/auth.ts` -- User type with role field
  - `frontend/package.json` -- All dependencies verified

### Secondary (MEDIUM confidence)
- None needed -- all patterns derived from direct codebase reading

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and used extensively in codebase
- Architecture: HIGH -- All patterns directly observed in existing code (ImportDialog, SPOImportTile, TeamActivityTable, UserDetail, Dashboard)
- Pitfalls: HIGH -- Identified from direct code analysis (missing endpoints confirmed by reading urls.py and grepping for MPD; unmatched_rows format confirmed by reading mpd_services.py; DecimalField behavior is standard DRF)
- Backend gap: HIGH -- Verified by reading all URL configs; no read endpoints for MPD data exist

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable -- all patterns are from the current codebase, not external libraries)
