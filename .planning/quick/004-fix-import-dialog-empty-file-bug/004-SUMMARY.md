---
type: quick
number: 004
description: "Fix ImportDialog empty file bug and generate test CSV data"
completed: 2026-02-10
---

# Quick Task 004: Fix ImportDialog empty file bug + generate test CSV data

**One-liner:** Fixed bug where ImportDialog sent empty file to backend by capturing acceptedFile from react-papaparse render props; also generated 4 test CSV files for UAT.

## What Was Fixed

### Bug: Empty file sent to backend during import validation/import

**Symptom:** Clicking "Validate" in ImportDialog returned `{"error_count": 1, "errors": [{"row": 1, "errors": ["CSV file is empty or has no headers"], "data": {}}]}`

**Root cause:** `ImportDialog.tsx` used a separate `fileInputRef` (`useRef<HTMLInputElement>`) pointing to a hidden `<input>` element. However, `react-papaparse`'s `CSVReader` component manages its own internal file input — the hidden input was never populated. When `handleFileUpload` ran, `fileInputRef.current?.files?.[0]` was `undefined`, falling through to `new File([], "unknown.csv")` — an empty file.

**Fix:** Replaced `fileInputRef` with `acceptedFileRef` (`useRef<File | null>`). The `acceptedFile` object from CSVReader's render props (which IS a standard browser File object) is captured into the ref during render. `handleFileUpload` reads from `acceptedFileRef.current` to get the actual file with contents.

### Files Modified

- `frontend/src/components/imports/ImportDialog.tsx` - Fixed file capture logic

### Test Data Created

- `test_data/funds.csv` - 5 funds (FUND-001 to FUND-005)
- `test_data/entities.csv` - 8 entities (ENT-001 to ENT-008)
- `test_data/transactions.csv` - 10 transactions referencing funds and entities
- `test_data/pledges.csv` - 6 pledges with various cadences

## Verification

- Frontend build passes (`npm run build` succeeds)
- No TypeScript errors
