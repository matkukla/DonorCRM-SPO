---
phase: 45
slug: fix-backend-to-frontend-data-mapping-issues
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | conftest.py (root) |
| **Quick run command** | `pytest apps/contacts/tests/ -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/contacts/tests/ -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 0 | org-name mapping | unit stub | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q` | ❌ W0 | ⬜ pending |
| 45-02-01 | 02 | 1 | full_name fallback | unit | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "full_name"` | ❌ W0 | ⬜ pending |
| 45-02-02 | 02 | 1 | serializer fields | unit | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "serializer"` | ❌ W0 | ⬜ pending |
| 45-02-03 | 02 | 1 | search list endpoint | integration | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "search"` | ❌ W0 | ⬜ pending |
| 45-02-04 | 02 | 1 | search typeahead endpoint | integration | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "search"` | ❌ W0 | ⬜ pending |
| 45-02-05 | 02 | 1 | CSV export full_name | unit | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "export"` | ❌ W0 | ⬜ pending |
| 45-02-06 | 02 | 1 | create serializer blank names | unit | `pytest apps/contacts/tests/test_org_contact_mapping.py -x -q -k "create"` | ❌ W0 | ⬜ pending |
| 45-03-01 | 03 | 2 | frontend form org field | manual | See manual verifications | N/A | ⬜ pending |
| 45-03-02 | 03 | 2 | detail view org display | manual | See manual verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/contacts/tests/test_org_contact_mapping.py` — dedicated test file covering all 7 backend behaviors:
  - `Contact.full_name` returns `organization_name` when first+last blank
  - `ContactListSerializer` includes `organization_name` in output
  - Contact list API response includes `organization_name`
  - List endpoint search finds org contacts by `organization_name`
  - Search endpoint (`/contacts/search/`) finds org contacts by `organization_name`
  - CSV export uses `full_name` (org contact name appears correctly)
  - `ContactCreateSerializer` accepts blank `first_name`/`last_name` with `organization_name`
- [ ] `OrgContactFactory` in `apps/contacts/tests/factories.py` (if factory_boy is used) — org contact with blank first/last and non-blank `organization_name`

*Existing infrastructure covers all other needs — conftest.py, pytest-django, DB setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Contact create form accepts org name without first/last | org contact creation | Frontend validation UX hard to automate | Open /contacts/new, leave first/last blank, enter org name, submit — should succeed |
| Organization name field appears in contact detail view | org name display | React render not testable with pytest | Open an org contact detail page, verify org name shown in Contact Information card |
| Organization name field is editable in edit form | org name editing | Form interaction | Open org contact edit form, modify org name, save, verify change persists |
| Contact list shows org name in Name column | name column display | React table rendering | Navigate to contacts list, verify org contacts show org name (not blank) in Name column |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
