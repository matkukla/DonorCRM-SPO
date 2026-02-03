# Phase 12: Import Center UI - Research

**Researched:** 2026-02-03
**Domain:** React/TypeScript frontend UI, CSV client-side parsing, multi-step workflow
**Confidence:** HIGH

## Summary

Phase 12 delivers an admin-only Import Center UI that provides a unified interface for all 4 CSV import types (Funds, Entities, Transactions, Pledges) with a complete Upload → Preview → Validate → Import → Summary workflow. The research confirms the existing frontend stack (React 19 + TypeScript + Vite, Radix UI, TanStack Query) provides all necessary primitives, and identifies react-papaparse as the standard library for client-side CSV parsing and preview.

The backend APIs for all 4 import types are complete (Phases 8-11), with established patterns for multipart file upload, validate_only mode, and structured error responses. The ImportRun model tracks import history with status and counts, enabling the UI to display last import date/status for each tile.

**Primary recommendation:** Build Import Center as new admin-only route at /admin/imports using existing AppLayout, implement multi-step workflow with useReducer state machine pattern, use react-papaparse for client-side CSV preview (first 25 rows), and add new API endpoint GET /api/v1/imports/runs/latest/ to fetch last import status per type for tile display.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.0 | UI framework | Already used across entire frontend, React 19 stable |
| TypeScript | ~5.9.3 | Type safety | Project uses TypeScript throughout, strong type checking for CSV data |
| React Router | 6.30.3 | Routing | Existing router, supports ProtectedRoute with role checking |
| TanStack Query | 5.90.17 | Server state | Already used for all API calls, perfect for import mutations |
| Radix UI Dialog | 1.1.15 | Modal dialogs | Existing component library, ideal for multi-step workflows |
| Tailwind CSS | 3.4.19 | Styling | Project styling system, existing utility classes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-papaparse | 4.5.0+ | CSV parsing | Client-side preview, fast in-browser CSV parser with TypeScript support |
| axios | 1.13.2 | HTTP client | Already configured with auth interceptors, used by apiClient |
| lucide-react | 0.562.0 | Icons | Consistent iconography across app, use Upload/Download/CheckCircle/AlertTriangle |
| sonner | 2.0.7 | Toast notifications | Existing toast system for success/error messages |
| date-fns | 4.1.0 | Date formatting | Format last import timestamps for tile display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-papaparse | Native FileReader + manual CSV parsing | Manual parsing is error-prone, no header detection, Papa Parse is battle-tested |
| useReducer state machine | useState for each step | Multiple useState becomes messy for complex workflows, useReducer centralizes state transitions |
| Dialog for workflow | Sheet component | Sheet is for sidebar panels, Dialog is semantic for modal workflows |

**Installation:**
```bash
npm install react-papaparse
npm install --save-dev @types/papaparse
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/
│   └── admin/
│       └── ImportCenter.tsx          # Main Import Center page (4 tiles + layout)
├── components/
│   └── imports/
│       ├── ImportTile.tsx            # Reusable tile component (status, last import)
│       ├── ImportDialog.tsx          # Multi-step import workflow dialog
│       ├── CSVPreviewTable.tsx       # Preview first 25 rows
│       ├── ValidationResults.tsx     # Display validation errors
│       └── ImportSummary.tsx         # Success/error summary with download errors button
└── api/
    └── imports.ts                    # Add new functions: getLatestImports(), downloadErrorsCSV()
```

### Pattern 1: Multi-Step State Machine with useReducer
**What:** Manage Upload → Preview → Validate → Import → Summary workflow with explicit state transitions
**When to use:** Complex workflows with strict state transitions, prevents invalid state combinations
**Example:**
```typescript
// Source: https://kyleshevlin.com/how-to-use-usereducer-as-a-finite-state-machine/
// https://undefined.technology/blog/state-machine-in-react-with-usereducer/

type ImportState =
  | { step: 'idle' }
  | { step: 'preview'; file: File; rows: ParsedRow[] }
  | { step: 'validating'; file: File }
  | { step: 'validated'; file: File; errors: string[] }
  | { step: 'importing'; file: File }
  | { step: 'complete'; result: ImportResult }
  | { step: 'error'; message: string }

type ImportAction =
  | { type: 'UPLOAD_FILE'; file: File; rows: ParsedRow[] }
  | { type: 'START_VALIDATION' }
  | { type: 'VALIDATION_COMPLETE'; errors: string[] }
  | { type: 'START_IMPORT' }
  | { type: 'IMPORT_COMPLETE'; result: ImportResult }
  | { type: 'IMPORT_ERROR'; message: string }
  | { type: 'CANCEL' }

function importReducer(state: ImportState, action: ImportAction): ImportState {
  switch (state.step) {
    case 'idle':
      return action.type === 'UPLOAD_FILE'
        ? { step: 'preview', file: action.file, rows: action.rows }
        : state
    case 'preview':
      return action.type === 'START_VALIDATION'
        ? { step: 'validating', file: state.file }
        : action.type === 'CANCEL'
        ? { step: 'idle' }
        : state
    // ... other state transitions
  }
}
```

### Pattern 2: Client-Side CSV Preview with react-papaparse
**What:** Parse CSV in browser to preview first 25 rows before uploading to server
**When to use:** Always preview before validation to catch obvious errors early
**Example:**
```typescript
// Source: https://react-papaparse.js.org/docs
// https://blog.logrocket.com/working-csv-files-react-papaparse/

import { useCSVReader } from 'react-papaparse'

function CSVPreview({ onParse }: { onParse: (rows: ParsedRow[]) => void }) {
  const { CSVReader } = useCSVReader()

  return (
    <CSVReader
      onUploadAccepted={(results: ParseResult) => {
        const preview = results.data.slice(0, 25) // First 25 rows
        onParse(preview)
      }}
      config={{
        header: true,  // Parse first row as headers
        skipEmptyLines: true,
        encoding: 'UTF-8'
      }}
    >
      {({ getRootProps, acceptedFile }: any) => (
        <div {...getRootProps()}>
          {acceptedFile ? acceptedFile.name : 'Drop CSV or click to browse'}
        </div>
      )}
    </CSVReader>
  )
}
```

### Pattern 3: Generate Downloadable Errors CSV
**What:** Create CSV file in browser with original row data + error_message column
**When to use:** After failed import, allow admin to download errors for fixing
**Example:**
```typescript
// Source: https://geeksforgeeks.org/javascript/how-to-create-and-download-csv-file-in-javascript/
// https://code-maven.com/create-and-download-csv-with-javascript

import Papa from 'papaparse'

function downloadErrorsCSV(errors: ImportRowError[], filename: string) {
  // Add error_message column to row data
  const rowsWithErrors = errors.map(err => ({
    ...err.row_data,
    error_message: err.error_messages.join('; ')
  }))

  // Convert to CSV
  const csv = Papa.unparse(rowsWithErrors, {
    header: true,
    skipEmptyLines: true
  })

  // Trigger download
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
```

### Pattern 4: Admin-Only Route Protection
**What:** Restrict Import Center to admin users using existing ProtectedRoute component
**When to use:** All admin-specific pages (already pattern in AdminUsers page)
**Example:**
```typescript
// Source: frontend/src/App.tsx (existing pattern)

<Route
  path="/admin/imports"
  element={
    <ProtectedPage requiredRole="admin">
      <ImportCenter />
    </ProtectedPage>
  }
/>
```

### Anti-Patterns to Avoid
- **Don't parse entire CSV in browser for large files:** Limit preview to 25 rows, full validation happens server-side
- **Don't bypass validation step:** Always require explicit "Validate" before "Import" button enables
- **Don't lose upload state on dialog close:** Warn user if they close dialog mid-import
- **Don't hardcode import type URLs:** Use ImportType enum and map to API endpoints

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Manual split/regex | react-papaparse | Handles encoding, quoted fields, multiline values, BOM, malformed CSVs |
| Multi-step wizard | Chain of useState | useReducer state machine | Prevents invalid states (e.g., importing without validation), centralizes transitions |
| File download | Manual anchor creation | Existing downloadFile helper | Already implemented in api/imports.ts, handles blob cleanup |
| Toast notifications | Custom notification system | sonner (already used) | Consistent UX across app, accessible, auto-dismiss |
| Date formatting | Manual date strings | date-fns (already used) | Handles timezones, locales, relative time ("2 hours ago") |

**Key insight:** CSV parsing has edge cases (quoted commas, line breaks in fields, BOM characters, encoding issues) that Papa Parse handles. Manual parsing will break on real-world exports from Excel or SPO.

## Common Pitfalls

### Pitfall 1: Large File Memory Issues
**What goes wrong:** Parsing 10,000+ row CSV in browser causes tab to freeze or crash
**Why it happens:** Papa Parse loads entire file into memory, React re-renders on every state update
**How to avoid:**
- Limit preview to first 25 rows only (requirement IMP-10)
- Show file size warning if >5MB
- Full validation and import happen server-side (already implemented)
**Warning signs:** Browser DevTools shows high memory usage, UI becomes unresponsive during file upload

### Pitfall 2: State Management Complexity
**What goes wrong:** Managing file, preview data, validation results, import status across multiple useState calls becomes unmaintainable
**Why it happens:** Each step adds more state variables, conditions for transitions become tangled
**How to avoid:** Use useReducer with explicit state machine pattern from Pattern 1
**Warning signs:** Seeing checks like `if (file && !validating && !importing && validated)` scattered across component

### Pitfall 3: Missing Error CSV Download
**What goes wrong:** Admin uploads 500-row CSV, gets 50 errors, can't see which rows failed
**Why it happens:** Validation response only returns first 20 errors (backend limit)
**How to avoid:**
- Fetch full error list from ImportRowError model when errors exist
- Use Pattern 3 to generate downloadable CSV with error_message column
- Button only appears when error_count > 0
**Warning signs:** User complains "I can't see all the errors" or "How do I fix the failed rows?"

### Pitfall 4: Dependency Order Confusion
**What goes wrong:** Admin imports Transactions before Entities, gets 100% orphan reference errors
**Why it happens:** Transaction CSV references entity_id that don't exist yet
**How to avoid:**
- Display recommended order prominently: Funds → Entities → Transactions → Pledges
- Check if Funds/Entities tables empty, show warning before Transaction/Pledge import
- Make warning dismissible (don't block, requirement IMP-19 says non-blocking)
**Warning signs:** All validation errors are "entity_id X not found" or "fund_id Y not found"

### Pitfall 5: Radix Dialog Controlled State Issues
**What goes wrong:** Dialog closes unexpectedly, or open state gets out of sync with workflow state
**Why it happens:** Mixing controlled and uncontrolled Radix Dialog state
**How to avoid:**
- Use controlled Dialog with `open` and `onOpenChange` props
- Sync dialog open state with workflow reducer (idle = closed, any other step = open)
- Show confirmation dialog when user tries to close mid-import
**Warning signs:** Dialog closes when clicking outside, losing import progress

## Code Examples

Verified patterns from official sources:

### Fetch Latest Import Status for Tiles
```typescript
// Source: Backend API pattern, new endpoint needed
// GET /api/v1/imports/runs/latest/

// Backend (apps/imports/views.py):
class LatestImportRunsView(APIView):
    """GET: Fetch last import run for each type"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.imports.models import ImportRun, ImportType
        from django.db.models import Max

        latest = {}
        for import_type in ImportType.values:
            run = ImportRun.objects.filter(
                type=import_type
            ).order_by('-created_at').first()

            if run:
                latest[import_type] = {
                    'id': run.id,
                    'status': run.status,
                    'created_at': run.created_at.isoformat(),
                    'created_count': run.created_count,
                    'updated_count': run.updated_count,
                    'error_count': run.error_count
                }
            else:
                latest[import_type] = None

        return Response(latest)

// Frontend (api/imports.ts):
export interface LatestImportRun {
  id: string
  status: string
  created_at: string
  created_count: number
  updated_count: number
  error_count: number
}

export async function getLatestImports(): Promise<Record<string, LatestImportRun | null>> {
  const response = await apiClient.get('/imports/runs/latest/')
  return response.data
}
```

### Complete ImportDialog Component Structure
```typescript
// Source: Multi-step dialog pattern combining Radix UI Dialog + useReducer
// https://www.shadcn.io/patterns/sheet-form-5
// https://kyleshevlin.com/how-to-use-usereducer-as-a-finite-state-machine/

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useReducer } from 'react'
import { useCSVReader } from 'react-papaparse'

interface ImportDialogProps {
  importType: 'funds' | 'entities' | 'transactions' | 'pledges'
  open: boolean
  onClose: () => void
}

export function ImportDialog({ importType, open, onClose }: ImportDialogProps) {
  const [state, dispatch] = useReducer(importReducer, { step: 'idle' })
  const { CSVReader } = useCSVReader()

  const handleClose = () => {
    if (state.step === 'importing') {
      // Show confirmation dialog
      if (!confirm('Import in progress. Are you sure you want to cancel?')) {
        return
      }
    }
    dispatch({ type: 'CANCEL' })
    onClose()
  }

  return (
    <Dialog open={open && state.step !== 'idle'} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            Import {importType.charAt(0).toUpperCase() + importType.slice(1)}
          </DialogTitle>
        </DialogHeader>

        {/* Step 1: Upload */}
        {state.step === 'idle' && (
          <CSVUploadStep
            onUpload={(file, rows) =>
              dispatch({ type: 'UPLOAD_FILE', file, rows })
            }
          />
        )}

        {/* Step 2: Preview */}
        {state.step === 'preview' && (
          <CSVPreviewStep
            rows={state.rows}
            onValidate={() => dispatch({ type: 'START_VALIDATION' })}
            onCancel={handleClose}
          />
        )}

        {/* Step 3: Validation */}
        {(state.step === 'validating' || state.step === 'validated') && (
          <ValidationStep
            importType={importType}
            file={state.file}
            onImport={() => dispatch({ type: 'START_IMPORT' })}
            onCancel={handleClose}
          />
        )}

        {/* Step 4: Import */}
        {state.step === 'importing' && (
          <ImportingStep importType={importType} file={state.file} />
        )}

        {/* Step 5: Summary */}
        {state.step === 'complete' && (
          <SummaryStep result={state.result} onClose={handleClose} />
        )}
      </DialogContent>
    </Dialog>
  )
}
```

### Dependency Warning Component
```typescript
// Source: Requirement IMP-19
// Non-blocking warning when importing Transactions/Pledges with empty dependencies

import { AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface DependencyWarningProps {
  importType: 'transactions' | 'pledges'
  emptyTables: { funds: boolean; entities: boolean }
}

export function DependencyWarning({ importType, emptyTables }: DependencyWarningProps) {
  if (!emptyTables.funds && !emptyTables.entities) return null

  const missing = []
  if (emptyTables.entities) missing.push('Entities')
  if (emptyTables.funds) missing.push('Funds')

  return (
    <Alert variant="warning" className="mb-4">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription>
        <strong>Recommended import order:</strong> Funds → Entities → Transactions → Pledges
        <br />
        You haven't imported {missing.join(' or ')} yet.
        {importType === 'transactions'
          ? ' Transactions require valid entity_id and fund_id references.'
          : ' Pledges require valid entity_id references (fund_id is optional).'
        }
        <br />
        <em>You can proceed, but expect validation errors if your CSV references missing IDs.</em>
      </AlertDescription>
    </Alert>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server-side validation only | Client-side preview + server validation | 2024+ | Better UX, catch errors early before upload |
| Multiple useState for wizards | useReducer state machine | 2023+ | Prevents invalid states, clearer transitions |
| Custom CSV parsers | Papa Parse library | Mature (2015+) | Handles edge cases, encoding, malformed CSVs |
| Uncontrolled Radix Dialog | Controlled with open/onOpenChange | Radix v1.0+ | Predictable state, integrates with React state |
| Inline error messages | Downloadable error CSV | Modern pattern | Large imports need full error list for fixing |

**Deprecated/outdated:**
- react-dropzone: Still popular but unnecessary with react-papaparse's built-in CSVReader component
- redux for wizard state: Overkill for component-local workflow, useReducer is sufficient

## Open Questions

Things that couldn't be fully resolved:

1. **How to check if Funds/Entities tables are empty for dependency warning?**
   - What we know: ImportRun tracks import history, could check if any completed imports exist for Funds/Entities
   - What's unclear: Should we query Fund.objects.count() and Contact.objects.filter(external_id__isnull=False).count() for accuracy?
   - Recommendation: Add counts to /api/v1/imports/runs/latest/ response (funds_count, entities_count fields), fetch once on Import Center mount

2. **Should Import Center replace existing /import-export page?**
   - What we know: /import-export currently has Contacts and Donations import (legacy), Import Center adds 4 new SPO-compatible imports
   - What's unclear: Keep both pages or merge? Are Contacts/Donations imports still needed?
   - Recommendation: Keep both pages for now, Import Center is admin-only SPO workflow, /import-export is general-purpose (Phase 12 scope only covers new page)

3. **How to handle ImportRowError for downloads when error_count > 20?**
   - What we know: Backend returns first 20 errors in response, full errors stored in ImportRowError model
   - What's unclear: Should frontend fetch ImportRowError.objects.filter(import_run=X) for download, or backend provides CSV endpoint?
   - Recommendation: Add GET /api/v1/imports/runs/{id}/errors/csv/ endpoint that generates CSV server-side, frontend just triggers download (cleaner, no N+1 queries)

## Sources

### Primary (HIGH confidence)
- React 19 documentation - https://react.dev (official)
- TypeScript 5.9 documentation - https://www.typescriptlang.org/docs/ (official)
- Radix UI Dialog documentation - https://www.radix-ui.com/primitives/docs/components/dialog (official)
- react-papaparse documentation - https://react-papaparse.js.org/docs (official library docs)
- Papa Parse documentation - https://www.papaparse.com/ (official, underlying library)
- Django REST Framework documentation - https://www.django-rest-framework.org/ (official)
- Existing codebase: frontend/src/App.tsx, frontend/src/pages/imports/ImportExport.tsx, frontend/src/components/imports/ImportCard.tsx, apps/imports/views.py, apps/imports/models.py (verified patterns)

### Secondary (MEDIUM confidence)
- [Working with CSV files with react-papaparse - LogRocket Blog](https://blog.logrocket.com/working-csv-files-react-papaparse/)
- [How to Use useReducer as a Finite State Machine | Kyle Shevlin](https://kyleshevlin.com/how-to-use-usereducer-as-a-finite-state-machine/)
- [Writing State Machine in React with TypeScript Using useReducer](https://undefined.technology/blog/state-machine-in-react-with-usereducer/)
- [State Management in 2026: Redux, Context API, and Modern Patterns](https://www.nucamp.co/blog/state-management-in-2026-redux-context-api-and-modern-patterns)
- [How to create and download CSV file in JavaScript - GeeksforGeeks](https://www.geeksforgeeks.org/javascript/how-to-create-and-download-csv-file-in-javascript/)
- [Create and download data in CSV format using plain JavaScript](https://code-maven.com/create-and-download-csv-with-javascript)
- [React Multi-Step Form Sheet - shadcn/ui](https://www.shadcn.io/patterns/sheet-form-5)
- [Radix Dialog: Mastering Modal Mastery in React | ReactLibs.dev](https://reactlibs.dev/articles/radix-dialog-modal-mastery/)

### Tertiary (LOW confidence)
- None - all findings verified with official documentation or existing codebase patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in package.json except react-papaparse (verified standard for React CSV parsing)
- Architecture: HIGH - Patterns match existing codebase (ProtectedRoute, Dialog, TanStack Query mutations, existing ImportCard pattern)
- Pitfalls: HIGH - Based on Papa Parse documentation (encoding, memory), React state machine patterns (useReducer complexity), and existing backend validation patterns
- API integration: HIGH - All 4 backend import APIs complete (Phases 8-11 verified), API patterns established

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - React/Radix UI stable, Papa Parse mature library)
