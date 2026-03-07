---
phase: 44
slug: modify-the-spo-data-import-and-reconciliation-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` / `setup.cfg` |
| **Quick run command** | `cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports.tests --verbosity=1` |
| **Full suite command** | `cd /home/matkukla/projects/DonorCRM && python manage.py test apps.imports --verbosity=2` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.imports.tests --verbosity=1`
- **After every plan wave:** Run `python manage.py test apps.imports --verbosity=2`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 0 | MissionaryAlias model | unit | `python manage.py test apps.imports.tests.test_missionary_alias` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 0 | ImportBatchType SPO choices | unit | `python manage.py test apps.imports.tests.test_import_batch` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 1 | reconcile_missionaries service — exact match | unit | `python manage.py test apps.imports.tests.test_spo_services.TestReconcileMissionaries` | ❌ W0 | ⬜ pending |
| 44-02-02 | 02 | 1 | reconcile_missionaries service — normalized match | unit | `python manage.py test apps.imports.tests.test_spo_services.TestReconcileMissionaries` | ❌ W0 | ⬜ pending |
| 44-02-03 | 02 | 1 | reconcile_missionaries service — alias match | unit | `python manage.py test apps.imports.tests.test_spo_services.TestReconcileMissionaries` | ❌ W0 | ⬜ pending |
| 44-02-04 | 02 | 1 | reconcile_missionaries service — auto-create User | unit | `python manage.py test apps.imports.tests.test_spo_services.TestReconcileMissionaries` | ❌ W0 | ⬜ pending |
| 44-02-05 | 02 | 1 | reconcile_missionaries — tri-source comparison | unit | `python manage.py test apps.imports.tests.test_spo_services.TestTriSourceReconciliation` | ❌ W0 | ⬜ pending |
| 44-03-01 | 03 | 2 | import_spo_gifts — anonymous donor creation | unit | `python manage.py test apps.imports.tests.test_spo_services.TestImportSpoGifts` | ❌ W0 | ⬜ pending |
| 44-03-02 | 03 | 2 | import_spo_gifts — gift attribution | unit | `python manage.py test apps.imports.tests.test_spo_services.TestImportSpoGifts` | ❌ W0 | ⬜ pending |
| 44-03-03 | 03 | 2 | import_spo_gifts — unresolved solicitor skip | unit | `python manage.py test apps.imports.tests.test_spo_services.TestImportSpoGifts` | ❌ W0 | ⬜ pending |
| 44-04-01 | 04 | 2 | import_spo_prayers — prayer extraction | unit | `python manage.py test apps.imports.tests.test_spo_services.TestImportSpoPrayers` | ❌ W0 | ⬜ pending |
| 44-05-01 | 05 | 3 | management commands — reconcile_missionaries | integration | `python manage.py test apps.imports.tests.test_spo_commands` | ❌ W0 | ⬜ pending |
| 44-05-02 | 05 | 3 | management commands — import_spo_gifts | integration | `python manage.py test apps.imports.tests.test_spo_commands` | ❌ W0 | ⬜ pending |
| 44-05-03 | 05 | 3 | management commands — import_spo_prayers | integration | `python manage.py test apps.imports.tests.test_spo_commands` | ❌ W0 | ⬜ pending |
| 44-06-01 | 06 | 3 | API endpoints — SPO import views | integration | `python manage.py test apps.imports.tests.test_spo_views` | ❌ W0 | ⬜ pending |
| 44-07-01 | 07 | 4 | idempotency — SHA256 dedup rerun | unit | `python manage.py test apps.imports.tests.test_spo_services.TestIdempotency` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/imports/tests/test_missionary_alias.py` — stubs for MissionaryAlias model tests
- [ ] `apps/imports/tests/test_spo_services.py` — stubs for all SPO service function tests
- [ ] `apps/imports/tests/test_spo_commands.py` — stubs for management command integration tests
- [ ] `apps/imports/tests/test_spo_views.py` — stubs for API view tests
- [ ] `apps/imports/tests/test_import_batch.py` — stubs for ImportBatchType SPO choices (may extend existing)

*Existing pytest/Django test infrastructure covers all phase requirements — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Django admin MissionaryAlias registration UI | Admin UX | Visual, requires browser | Navigate to /admin/imports/missionaryalias/add/, verify name + user FK fields appear and save correctly |
| Terminal audit summary table formatting | Audit output format | Output formatting, not logic | Run `python manage.py reconcile_missionaries test_data/test_solicitors.csv`, verify formatted table prints at end |
| Import History UI surfaces SPO ImportBatch records | Frontend integration | Requires live browser + backend | After running any SPO command, verify record appears in Import History admin panel |
| Tri-source comparison report (Smartsheet vs CSV vs DB) | Tri-source reconciliation | Requires sample Smartsheet file | Run `reconcile_missionaries` with Smartsheet file, verify missionaries missing from one source are flagged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
