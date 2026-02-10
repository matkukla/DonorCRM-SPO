---
type: quick
number: 004
description: "Fix ImportDialog empty file bug and generate test CSV data"
directory: .planning/quick/004-fix-import-dialog-empty-file-bug
---

# Quick Task 004: Fix ImportDialog empty file bug + generate test CSV data

## Goal

Fix bug where ImportDialog sends empty file to backend (CSV validation returns "CSV file is empty or has no headers") and provide test CSV files for all 4 SPO import types.

## Root Cause

`ImportDialog.tsx` used a separate `fileInputRef` (hidden `<input>` element) to capture the file, but `react-papaparse`'s `CSVReader` manages its own file input internally. The `fileInputRef` was never populated, so `state.file` fell through to `new File([], "unknown.csv")` — an empty file.

## Tasks

### Task 1: Fix file capture in ImportDialog
- Replace `fileInputRef` with `acceptedFileRef` (a `useRef<File | null>`)
- Capture `acceptedFile` from CSVReader render props into the ref
- Use ref value in `handleFileUpload` instead of `fileInputRef.current?.files?.[0]`
- Clear ref on dialog close
- Verify frontend builds successfully

### Task 2: Generate test CSV files
- Create `test_data/` directory with 4 CSV files matching SPO import column schemas
- funds.csv: 5 funds (FUND-001 to FUND-005)
- entities.csv: 8 entities (ENT-001 to ENT-008)
- transactions.csv: 10 transactions referencing funds and entities
- pledges.csv: 6 pledges with various cadences and optional fund_id
