---
phase: 53
slug: view-as-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — no frontend test framework configured |
| **Config file** | None — no vitest.config.ts or jest.config.ts detected |
| **Quick run command** | `cd frontend && npx tsc --noEmit` |
| **Full suite command** | `cd frontend && npm run build` |
| **Estimated runtime** | ~15 seconds (type-check) / ~30 seconds (full build) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc --noEmit`
- **After every plan wave:** Run `cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Full build must be green + manual browser verification
- **Max feedback latency:** ~15 seconds (type-check)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | VIEWAS-05, VIEWAS-10 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-01-02 | 01 | 1 | VIEWAS-05, VIEWAS-10 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-01-03 | 01 | 1 | VIEWAS-10, VIEWAS-11 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-02-01 | 02 | 1 | VIEWAS-03, VIEWAS-04 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-02-02 | 02 | 1 | VIEWAS-01, VIEWAS-02 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-03-01 | 03 | 2 | VIEWAS-09 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-03-02 | 03 | 2 | VIEWAS-06 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 53-03-03 | 03 | 2 | VIEWAS-06 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

No test files need to be created — this project has no frontend test infrastructure. The TypeScript compiler (`tsc --noEmit`) acts as a structural correctness gate after each task. All VIEWAS requirements require manual browser verification.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin sees dropdown of all missionaries in picker | VIEWAS-01 | No frontend test framework | Log in as admin → Dashboard → open picker → verify all active missionaries listed |
| Supervisor sees only assigned missionaries in picker | VIEWAS-02 | No frontend test framework | Log in as supervisor → Dashboard → open picker → verify only supervised missionaries listed |
| Banner appears with missionary name and read-only indicator | VIEWAS-03 | Visual/UI | Select any missionary → verify amber banner shows "Viewing [Name] · Read Only" |
| Exit button returns to own view, clears banner | VIEWAS-04 | Behavioral | While in View As mode → click Exit → banner gone, data reverts to own |
| Data on all pages belongs to selected missionary | VIEWAS-05 | Multi-page integration | Select missionary A → navigate contacts/donations/pledges/tasks/journals → verify data is missionary A's |
| Create/edit/delete buttons hidden throughout | VIEWAS-06 | Multi-page breadth | While in View As mode → visit contacts, donations, pledges, tasks, journals, groups, prayer → verify no mutation buttons visible |
| Admin nav items hidden (Import, Admin, Transactions) | VIEWAS-09 | Visual/sidebar | While in View As mode as admin → verify Import/Export, Admin, Transactions not in sidebar |
| View As persists across page navigation | VIEWAS-10 | Navigation | Select missionary → navigate away → banner still shows → data still scoped |
| React Query cache cleared on user change | VIEWAS-11 | Data correctness | Select missionary A → select missionary B → verify data is B's (not A's cached data) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
