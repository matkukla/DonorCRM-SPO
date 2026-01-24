---
phase: 01-foundation-data-model
plan: 01
subsystem: data-model
tags: [django, models, migrations, postgresql]
dependencies:
  requires: []
  provides: [journals-app, journal-models, pipeline-stages, event-logging]
  affects: [01-02, 02-01, 03-01, 04-01]
tech-stack:
  added: []
  patterns: [timestamped-models, append-only-events, through-tables, enum-choices]
file-tracking:
  created:
    - apps/journals/__init__.py
    - apps/journals/apps.py
    - apps/journals/models.py
    - apps/journals/admin.py
    - apps/journals/signals.py
    - apps/journals/tests/__init__.py
    - apps/journals/migrations/__init__.py
    - apps/journals/migrations/0001_initial.py
  modified:
    - config/settings/base.py
decisions:
  - key: use-decimal-field-for-money
    decision: Use DecimalField(max_digits=10, decimal_places=2) for goal_amount
    rationale: Follows existing codebase patterns in pledges and donations apps
    alternatives: Integer cents storage
  - key: archive-pattern
    decision: Use is_archived boolean + archived_at timestamp + archive() method
    rationale: Soft delete pattern allows historical analysis
    alternatives: Hard delete, status enum
  - key: append-only-events
    decision: JournalStageEvent is immutable append-only log
    rationale: Preserves complete audit trail of donor engagement
    alternatives: Mutable status tracking
metrics:
  duration: 7 minutes
  completed: 2026-01-24
---

# Phase 1 Plan 01: Foundation Data Model Summary

JWT auth with refresh rotation using jose library

## What Was Built

Created the journals Django app with complete data model foundation:

**Journal model:** Fundraising campaign tracker with goal amount, deadline, and archive pattern. Each journal belongs to a missionary (owner) and can contain multiple contacts through JournalContact.

**JournalContact model:** Many-to-many through-table linking journals to contacts with unique constraint ensuring each contact appears once per journal. Supports tracking which donors are in which campaigns.

**JournalStageEvent model:** Append-only event log recording every interaction, note, and stage change for a contact in a journal. Includes stage, event_type, notes, metadata JSONField, and triggered_by user reference.

**PipelineStage enum:** Defines the 6-stage donor engagement pipeline: Contact → Meet → Close → Decision → Thank → Next Steps.

**StageEventType enum:** 14 typed events covering all pipeline activities (calls, emails, meetings, asks, decisions, thank-yous, notes).

## Implementation Details

**Models follow codebase conventions:**
- All inherit from TimeStampedModel (UUID PK, created_at, updated_at)
- Use absolute imports (from apps.journals.models)
- Use verbose_name positional arg on fields
- db_index=True on all ForeignKeys and filter fields
- DecimalField for money (not integer cents)

**Database optimization:**
- Composite indexes on JournalStageEvent for efficient timeline queries
- Unique constraint on (journal, contact) prevents duplicates
- Indexes on (owner, is_archived) for filtered journal lists

**Admin interface:**
- All three models registered with list_display, filters, search
- Readonly fields for id, timestamps

**Placeholder for signals:**
- Created apps/journals/signals.py stub (full implementation in Plan 02)
- AppConfig ready() imports signals to prepare for event logging

## Verification Results

All success criteria met:

✅ journals app exists with proper Django structure
✅ All models inherit TimeStampedModel
✅ PipelineStage defines exactly 6 stages
✅ StageEventType defines 14 event types
✅ Journal.goal_amount is DecimalField (not integer cents)
✅ Journal has archive pattern (is_archived + archived_at + archive() method)
✅ Migration 0001_initial applied
✅ Tables exist: journals, journal_contacts, journal_stage_events
✅ App registered in LOCAL_APPS
✅ `python manage.py check` passes with no errors
✅ JournalContact has unique_together on (journal, contact)
✅ JournalStageEvent has composite indexes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created .env file with database credentials**
- **Found during:** Task 2 - Running migrations
- **Issue:** No .env file existed, causing authentication failure to PostgreSQL
- **Fix:** Created .env with DB_PASSWORD=donorcrm_dev_password matching docker-compose.yml
- **Files created:** .env
- **Commit:** Not committed (environment-specific configuration)

**2. [Rule 3 - Blocking] Created Python virtual environment**
- **Found during:** Task 1 - Model verification
- **Issue:** Django dependencies not installed in system Python (externally-managed environment)
- **Fix:** Created venv/ and installed requirements/dev.txt
- **Files created:** venv/ directory
- **Commit:** Not committed (development artifact)

**3. [Rule 3 - Blocking] Started PostgreSQL database via Docker**
- **Found during:** Task 2 - Running migrations
- **Issue:** Database not running, connection refused
- **Fix:** Ran `docker compose up -d db` to start PostgreSQL container
- **Files modified:** None
- **Commit:** Not applicable (infrastructure operation)

All three issues were infrastructure/environment setup required for basic Django operation. No code changes were needed.

## Task Breakdown

### Task 1: Create journals app structure and models
**Commit:** a93a235
**Files:**
- apps/journals/__init__.py - Empty app init
- apps/journals/apps.py - JournalsConfig with signals import
- apps/journals/models.py - Journal, JournalContact, JournalStageEvent, PipelineStage, StageEventType
- apps/journals/admin.py - Admin registration for all three models
- apps/journals/signals.py - Placeholder stub for Plan 02
- apps/journals/tests/__init__.py - Test directory init

**Verification:** Models import successfully, no Django check errors

### Task 2: Register app and run migrations
**Commit:** 69d6307
**Files:**
- config/settings/base.py - Added 'apps.journals' to LOCAL_APPS
- apps/journals/migrations/__init__.py - Migrations package init
- apps/journals/migrations/0001_initial.py - Initial migration creating all tables

**Verification:** Migration applied, tables exist, models query database successfully

## Files Changed

**Created (8 files):**
- apps/journals/__init__.py
- apps/journals/apps.py
- apps/journals/models.py (255 lines - all three models + two enums)
- apps/journals/admin.py
- apps/journals/signals.py
- apps/journals/tests/__init__.py
- apps/journals/migrations/__init__.py
- apps/journals/migrations/0001_initial.py

**Modified (1 file):**
- config/settings/base.py (added apps.journals to LOCAL_APPS)

**Total:** 9 files, ~345 lines of code

## Decisions Made

**1. DecimalField for goal_amount**
- Follows existing pattern in pledges.Pledge.amount and donations.Donation.amount
- Avoids floating-point precision issues
- max_digits=10, decimal_places=2 supports goals up to $99,999,999.99

**2. Archive pattern instead of hard delete**
- is_archived boolean allows filtering active vs archived journals
- archived_at timestamp preserves when archival occurred
- archive() method ensures consistent archival (sets both fields + updated_at)
- Preserves historical data for reporting

**3. Append-only event log design**
- JournalStageEvent records are never updated or deleted
- created_at provides immutable timestamp
- metadata JSONField allows flexible additional data without schema changes
- Supports complete audit trail reconstruction

**4. PipelineStage as TextChoices**
- Fixed 6-stage pipeline matches PROJECT.md requirements
- TextChoices provides value + label for UI display
- Stage values are lowercase slugs (contact, meet, close, decision, thank, next_steps)

**5. StageEventType as comprehensive enum**
- 14 event types cover all common donor engagement activities
- Structured event types enable timeline visualization and analytics
- NOTE_ADDED and OTHER provide escape hatches for unstructured events

## Next Phase Readiness

**Ready for Phase 1 Plan 02 (Event Logging & Signals):**
- ✅ All models exist and are migrated
- ✅ JournalStageEvent structure supports event logging
- ✅ signals.py placeholder ready for implementation
- ✅ metadata JSONField supports task linking

**Ready for Phase 2 (API Endpoints):**
- ✅ Journal model has all fields for serialization
- ✅ JournalContact provides M2M foundation for nested endpoints
- ✅ Archive pattern ready for filtering (active vs archived)

**Ready for Phase 3 (Permissions):**
- ✅ Journal.owner ForeignKey ready for ownership checks
- ✅ triggered_by field on events supports audit trail

**Blockers:** None

**Concerns:**
- Note: contacts migration 0004_alter_contact_owner was created during makemigrations but not committed (outside scope of this plan)
- Future plan should verify if this migration needs to be included

## Performance Characteristics

**Database indexes created:**
- journals: (owner, is_archived) - For filtering user's active/archived journals
- journal_contacts: (journal, contact) - For unique constraint and lookups
- journal_stage_events: (journal_contact, stage, created_at) - For stage-filtered timelines
- journal_stage_events: (journal_contact, created_at) - For full timeline queries

**Expected query patterns supported:**
- Get all journals for a user (owner filter)
- Get active journals (is_archived=False filter)
- Get contacts in a journal (journal_contacts lookup)
- Get event timeline for a contact in journal (efficient ordered query)
- Get events by stage (stage filter with timeline ordering)

**Scalability considerations:**
- UUID primary keys allow distributed ID generation
- Append-only events prevent lock contention on updates
- Composite indexes support efficient timeline queries even with 1000+ events per contact

## Testing Notes

**Manual verification performed:**
- Django check --deploy passes
- All models importable
- Migration creates all tables
- Database queries work (Journal.objects.count())
- Enum values accessible (PipelineStage.CONTACT, StageEventType.CALL_LOGGED)
- Constraints exist (unique_together on JournalContact)

**Unit tests needed in future plans:**
- Journal.archive() method behavior
- JournalContact unique constraint enforcement
- PipelineStage enum completeness (exactly 6 stages)
- StageEventType enum coverage (14 types)
- Timestamp auto-population (created_at, updated_at)

## Integration Points

**Existing apps used:**
- apps.core.models.TimeStampedModel - Base model inheritance
- apps.contacts.models.Contact - ForeignKey in JournalContact
- apps.tasks.models.Task - Will link via JournalStageEvent.metadata in Plan 02

**Provides for future plans:**
- Journal model for API serialization (Plan 02-01)
- JournalStageEvent for signal-based logging (Plan 01-02)
- PipelineStage enum for stage progression logic (Plan 05-01)
- Through-table pattern for contact membership (Plan 02-01)

## Rollback Plan

If issues discovered:

**Rollback migration:**
```bash
python manage.py migrate journals zero
```

**Remove from INSTALLED_APPS:**
- Remove 'apps.journals' from config/settings/base.py

**Revert commits:**
```bash
git revert 69d6307  # Revert Task 2
git revert a93a235  # Revert Task 1
```

No data loss risk - no production data exists yet.
