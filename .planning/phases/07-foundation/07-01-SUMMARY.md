---
# Execution metadata
phase: 07-foundation
plan: 01
subsystem: imports
tags: [models, django, audit, funds]

# Dependency graph
requires: []
provides:
  - Fund model with external_id
  - ImportRun audit model
  - ImportRowError for row-level errors
  - ImportType and ImportStatus enums
affects:
  - 07-02 (external_id fields on existing models)
  - 08-xx (fund import service)
  - 09-xx (transaction import service)
  - 12-xx (import center UI)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TextChoices enums for type safety
    - JSONField for error storage
    - TimeStampedModel inheritance
    - on_delete PROTECT/CASCADE patterns

# File tracking
key-files:
  created:
    - apps/imports/models.py
    - apps/imports/admin.py
  modified: []

# Decision tracking
decisions:
  - id: 07-01-D1
    area: model-design
    choice: Fund.external_id globally unique (not owner-scoped)
    rationale: SPO fund IDs are globally unique, multiple missionaries may reference same fund
    alternatives: [owner-scoped uniqueness]
  - id: 07-01-D2
    area: model-design
    choice: Fund.owner nullable for org-wide funds
    rationale: Some funds are shared across all missionaries (e.g., Ministry General Fund)
    alternatives: [required owner, separate GlobalFund model]

# Metrics
metrics:
  duration: 1m 53s
  completed: 2026-01-30
---

# Phase 7 Plan 1: Import Infrastructure Models Summary

**One-liner:** Created Fund, ImportRun, ImportRowError models with TextChoices enums for CSV import audit trail.

## What Was Done

### Task 1: Create imports/models.py (03726e9)
Created the core import infrastructure models:

- **ImportType enum:** FUNDS, ENTITIES, TRANSACTIONS, PLEDGES
- **ImportStatus enum:** PENDING, VALIDATING, VALIDATED, IMPORTING, COMPLETED, FAILED
- **Fund model:** external_id (unique, indexed), name, status, optional owner FK
- **ImportRun model:** type, status, filename, counts (total/created/updated/skipped/error), uploaded_by FK, error_summary JSONField
- **ImportRowError model:** import_run FK (CASCADE), row_number, error_messages JSONField, row_data JSONField

All models inherit from TimeStampedModel providing UUID primary key, created_at, and updated_at fields.

### Task 2: Register models in admin (e13fd2f)
Created admin configuration for all three models:

- FundAdmin with name, external_id, status, owner display
- ImportRunAdmin with type, status, counts, date_hierarchy
- ImportRowErrorAdmin with import_run, row_number display

## Key Implementation Details

```python
# apps/imports/models.py - Core model structure
class Fund(TimeStampedModel):
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='active')
    owner = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True)

class ImportRun(TimeStampedModel):
    type = models.CharField(max_length=20, choices=ImportType.choices)
    status = models.CharField(max_length=20, choices=ImportStatus.choices)
    uploaded_by = models.ForeignKey('users.User', on_delete=models.PROTECT)
    error_summary = models.JSONField(default=dict, blank=True)

class ImportRowError(TimeStampedModel):
    import_run = models.ForeignKey(ImportRun, on_delete=models.CASCADE)
    error_messages = models.JSONField()
    row_data = models.JSONField()
```

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 07-01-D1 | Fund.external_id globally unique | SPO fund IDs are globally unique across all missionaries |
| 07-01-D2 | Fund.owner nullable | Allows org-wide funds (null owner) and user-specific funds |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `python manage.py check` - no issues
- Models import successfully: `from apps.imports.models import Fund, ImportRun, ImportRowError`
- Enums import successfully: `from apps.imports.models import ImportType, ImportStatus`
- Fund.external_id has unique=True and db_index=True
- ImportRun.uploaded_by uses PROTECT on_delete
- ImportRowError.import_run uses CASCADE on_delete

## Next Phase Readiness

**For 07-02 (External ID fields on existing models):**
- Fund model now available for Donation/Pledge foreign key references
- ImportType enum ready for other import services

**Migration note:** No migration generated yet - will generate in 07-02 after all model changes complete to minimize migration count.

## Artifacts

| File | Purpose | Key Contents |
|------|---------|--------------|
| apps/imports/models.py | Import infrastructure models | Fund, ImportRun, ImportRowError, ImportType, ImportStatus |
| apps/imports/admin.py | Django admin registration | FundAdmin, ImportRunAdmin, ImportRowErrorAdmin |
