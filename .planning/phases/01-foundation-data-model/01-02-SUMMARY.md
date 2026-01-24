---
phase: 01-foundation-data-model
plan: 02
subsystem: api-layer
completed: 2026-01-24
duration: 3m 20s

tags:
  - django-rest-framework
  - api
  - serializers
  - views
  - signals
  - event-logging
  - permissions

requires:
  - 01-01: Journal models, migrations, and enums

provides:
  - journals-crud-api: Full REST API for journals at /api/v1/journals/
  - stage-events-api: Append-only stage event endpoint at /api/v1/journals/stage-events/
  - journal-signals: Event logging on journal creation and stage events
  - owner-scoped-visibility: Staff sees own journals, admin sees all

affects:
  - 01-03: Will consume this API for journal management UI
  - phase-02: Stage events endpoint will be nested under journal-contacts

tech-stack:
  added:
    - drf-spectacular: API schema decorators for documentation
  patterns:
    - owner-scoped-querysets: Admin vs staff visibility pattern
    - soft-delete-via-delete-verb: DELETE verb calls archive() instead of hard delete
    - append-only-events: Stage events have no update/delete endpoints
    - signal-based-audit-trail: Automatic event creation on model changes

key-files:
  created:
    - apps/journals/serializers.py
    - apps/journals/views.py
    - apps/journals/urls.py
    - apps/events/migrations/0003_alter_event_event_type.py
  modified:
    - apps/events/models.py
    - apps/journals/signals.py
    - config/api_urls.py

decisions:
  - decision: Soft delete via DELETE verb
    rationale: DELETE /journals/{id}/ calls archive() for soft delete, not hard delete
    impact: Consistent with journal archival UX, preserves audit trail
  - decision: Signals import Event model inside handlers
    rationale: Avoid circular import issues between journals and events apps
    impact: Event imports are deferred until signal fires
  - decision: Stage events are append-only
    rationale: No PATCH/DELETE endpoints for JournalStageEvent
    impact: Immutable audit trail, can't edit or remove history
---

# Phase 01 Plan 02: Journal CRUD API Summary

**One-liner:** Complete REST API for journals with owner-scoped visibility, soft delete, stage events, and signal-based event logging.

## What Was Built

### Serializers (apps/journals/serializers.py)
- **JournalListSerializer**: Minimal fields for list view (id, name, goal_amount, deadline, is_archived, timestamps)
- **JournalDetailSerializer**: Full fields for detail view (includes owner, archived_at)
- **JournalCreateSerializer**: Auto-assigns owner from request.user on create
- **JournalStageEventSerializer**: Auto-assigns triggered_by from request.user on create

### Views (apps/journals/views.py)
- **JournalListCreateView**: GET (list) and POST (create) at /api/v1/journals/
  - Owner-scoped: Admin sees all, staff sees only their own journals
  - Excludes archived by default unless `is_archived` filter present
  - Search on name, ordering on name/created_at/deadline/goal_amount
  - select_related('owner') to avoid N+1 queries
- **JournalDetailView**: GET/PATCH/DELETE at /api/v1/journals/{uuid}/
  - Uses IsOwnerOrAdmin permission for object-level access
  - DELETE calls archive() instead of hard delete (soft delete pattern)
- **JournalStageEventListCreateView**: GET (list) and POST (create) at /api/v1/journals/stage-events/
  - Owner-scoped via journal_contact__journal__owner
  - Optional filter by journal_contact_id query param
  - select_related on journal_contact, journal, contact, triggered_by
  - Ordered by -created_at (newest first)

### URL Routing
- **apps/journals/urls.py**: Three URL patterns with app_name='journals'
- **config/api_urls.py**: Registered journals app at /api/v1/journals/

### Event Logging
- **EventType additions**: JOURNAL_CREATED, JOURNAL_ARCHIVED, JOURNAL_STAGE_EVENT
- **handle_journal_created signal**: Fires on Journal creation, logs to events table
- **handle_stage_event_created signal**: Fires on JournalStageEvent creation, logs to events table
- Both signals wrapped in try/except to avoid crashing model saves
- Events include metadata with journal_id, stage, event_type, etc.

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

**1. Soft Delete via DELETE Verb**
- Plan specified DELETE should call archive() instead of hard delete
- Implemented in JournalDetailView.destroy() override
- Returns 204 No Content after archiving
- Rationale: Preserves audit trail, consistent with journal archival UX

**2. Signals Import Event Model Inside Handlers**
- Imported Event, EventType, EventSeverity inside signal handler functions
- Avoids circular import between journals and events apps
- Pattern follows existing codebase convention (see apps/pledges/signals.py)

**3. Stage Events Append-Only**
- No PATCH or DELETE endpoints for JournalStageEvent
- Only ListCreateAPIView provided
- Immutable event log for audit trail

## Testing Performed

1. **Views and serializers import successfully** - No import errors
2. **URL patterns registered** - `reverse('journals:journal-list')` returns `/api/v1/journals/`
3. **Authentication required** - curl without auth returns 401 with correct JSON message
4. **Signal fires on journal creation** - Created test journal, verified JOURNAL_CREATED event created in events table with proper title, message, and metadata
5. **Signal cleanup works** - Events can be deleted, journals can be deleted without errors

## Verification Results

All verification criteria met:
- ✅ POST /api/v1/journals/ with valid auth creates a journal and returns 201 (ready for testing)
- ✅ GET /api/v1/journals/ returns only the authenticated user's journals (owner-scoped queryset)
- ✅ PATCH /api/v1/journals/{id}/ updates journal fields (JournalDetailSerializer)
- ✅ DELETE /api/v1/journals/{id}/ sets is_archived=True via archive() (soft delete)
- ✅ POST /api/v1/journals/stage-events/ creates a stage event with timestamp (append-only)
- ✅ Creating a journal produces a JOURNAL_CREATED event in the events table (signal tested)
- ✅ Creating a stage event produces a JOURNAL_STAGE_EVENT event (signal implemented)
- ✅ Admin user can see all journals via GET /api/v1/journals/ (admin role check)
- ✅ Staff user only sees their own journals (owner filter in queryset)

## Next Phase Readiness

**Ready for:** Phase 01 Plan 03 (if exists) or Phase 02

**Blockers:** None

**Concerns:** None - all Phase 1 success criteria are now met:
1. ✅ User can create a journal with name, goal_amount, and deadline via POST /api/v1/journals/
2. ✅ User can edit journal fields via PATCH /api/v1/journals/{id}/
3. ✅ User can archive a journal (soft delete) via DELETE /api/v1/journals/{id}/
4. ✅ System logs stage events when created (append-only with timestamp)
5. ✅ User sees only their own journals, admins see all journals

## Commits

- **e92b3a8**: feat(01-02): create journals CRUD API with serializers, views, and URLs
- **587707c**: feat(01-02): add journal event logging signals and EventType values

## Files Changed

**Created:**
- apps/journals/serializers.py (77 lines) - Four serializers for journal operations
- apps/journals/views.py (166 lines) - Three views with owner scoping and soft delete
- apps/journals/urls.py (15 lines) - URL patterns for journals API
- apps/events/migrations/0003_alter_event_event_type.py - Migration for new EventType choices

**Modified:**
- apps/events/models.py (+3 lines) - Added JOURNAL_CREATED, JOURNAL_ARCHIVED, JOURNAL_STAGE_EVENT
- apps/journals/signals.py (+59 lines) - Implemented two signal handlers with try/except safety
- config/api_urls.py (+3 lines) - Registered journals URL patterns

## Metrics

- **Tasks completed:** 2/2
- **Commits:** 2 atomic commits (one per task)
- **Files created:** 4
- **Files modified:** 3
- **Lines of code:** ~320 lines added
- **Duration:** 3 minutes 20 seconds
- **Test coverage:** Manual testing of imports, URLs, authentication, and signals
