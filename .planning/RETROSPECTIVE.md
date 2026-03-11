# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v2.2 — UI Polish, Journal Report & Supervisor Role

**Shipped:** 2026-03-11
**Phases:** 10 (38-47) | **Plans:** 34 | **Duration:** 57 days

### What Was Built
- UI polish pass: centered dialogs system-wide, "Potential Donor" rename, gift Type column, analytics cleanup (removed Review Queue and heatmap)
- Dashboard overhaul: bar/line chart toggle, cross-section drag-and-drop, tightened layout
- Journal report rebuilt from scratch: metric cards, goal progress bar, stage/decision charts, single-click stage checkbox
- Begin Prayer flow: intention selection dialog launching expanded Focus Mode
- Mission Supervisor and Coach role hierarchy with M2M assignments (multiple supervisors/coaches per missionary)
- Roles Redesign: staff→missionary, mission_supervisor→supervisor, Coach with financial block, Admin Assignments UI, My Team page
- SPO import pipeline: MissionaryAlias name matching, gift attribution, prayer extraction (CLI/API)
- Org contact data mapping: organization_name visible across all views and export
- Coach role gap closure: IsStaffOrAbove permission fix, coached_user_ids M2M persistence

### What Worked
- **Audit-driven gap closure**: Running `/gsd:audit-milestone` before declaring complete surfaced real gaps (Phase 43 coach access, stale role strings) that were systematically closed by Phases 46 and 47
- **M2M migration pattern**: FK→M2M migration with RunPython data copy before RemoveField preserved all existing assignments cleanly
- **get_visible_user_ids() helper**: Centralized scoping logic made it easy to extend visibility to new roles without touching individual views
- **Decimal phases**: Phase 46 (multiple supervisors) and 47 (coach gaps) inserted cleanly as scope expanded mid-milestone
- **Quick tasks** handled 6 auxiliary items (import bug fixes, AdminAssignments UX) without disrupting phase flow

### What Was Inefficient
- **Phase 43 scope creep**: Original 5 ROLE requirements ballooned with implicit dependencies on Phase 42 supervisor infrastructure; coach access gaps weren't discovered until audit
- **Stale role='staff' strings** in test fixtures weren't caught until Phase 47 — a search+replace at migration time would have saved a dedicated plan
- **v2.2-ROADMAP.md in milestones/** archived with outdated "in progress" content — CLI doesn't update milestone line text, required manual post-processing
- **SPO import has no frontend UI**: Deferred multiple times; acceptable for admin-only use but creates user friction for non-CLI operators

### Patterns Established
- **Dialog-first modal pattern**: All overlays use centered Dialog with `max-h-[80vh] overflow-y-auto`; Sheets retired for detail panels
- **get_visible_user_ids() sentinel**: Returns `None` for all-access roles (admin/missionary), `set[UUID]` for scoped roles — queryset filters on `None` skip scoping
- **Nyquist RED-first**: Phases 44/45/46/47 all opened with failing test stubs before implementation (Wave 0 test authoring)
- **Audit → gap-phase → close**: Gaps found by audit create decimal phases, not scope creep to current phase
- **M2M auto-clear in model.save()**: Role-change M2M cleanup belongs in `User.save()`, not serializer — model is correct invariant layer

### Key Lessons
1. **Run role rename search immediately after migration** — stale string literals in tests are invisible until runtime failure; `grep -r "role='staff'"` at migration time costs 30 seconds
2. **Audit before milestone close always pays off** — v2.2 audit found 4 requirement gaps that would have shipped as tech debt; gap-closure phases (46/47) were well-scoped and quick
3. **CLI archival needs post-processing** — `milestone complete` doesn't update the milestone list line in the archived ROADMAP copy; always verify and patch manually
4. **M2M frontend derivation avoids backend change**: Filtering `all_users` by `supervisor_ids.includes(supervisorUser.id)` on the frontend was sufficient; no new backend endpoint needed

### Cost Observations
- Model mix: primarily sonnet (balanced profile throughout)
- Notable: Parallel plan execution (yolo mode) made multi-plan phases fast; most plans completed in <15min

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 6 | 24 | Initial GSD workflow setup |
| v1.1 | 6 | 15 | CSV import patterns established |
| v1.2 | 7 | 18 | Admin analytics, permission patterns |
| v1.3 | 7 | 20 | Filter infrastructure, security fixes |
| v2.0 | 10 | 27 | Data model migration (Gift/RecurringGift), audit workflow |
| v2.1 | 1 | 3 | Security-only milestone; fast single-phase |
| v2.2 | 10 | 34 | Role hierarchy + M2M; audit-driven gap closure |

### Top Lessons (Verified Across Milestones)

1. **Audit before archiving** — First run in v2.2 found real gaps; makes milestone completion trustworthy
2. **Centralized permission/scoping helpers** — get_visible_user_ids() pattern (v2.2) mirrors the QuerySet scoping pattern from v1.2; single helper beats per-view duplication
3. **decimal phases for scope expansion** — Used in v1.3, v2.0, and v2.2; keeps numbering clean without renumbering downstream phases
