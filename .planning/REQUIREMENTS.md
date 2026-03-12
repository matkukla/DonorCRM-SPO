# Requirements: DonorCRM

**Defined:** 2026-03-12
**Milestone:** v2.3 — Goal Tracking & View As
**Core Value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## v2.3 Requirements

### Goal Page

- [ ] **GOAL-01**: Missionary can navigate to a dedicated Goal page from the sidebar (below Dashboard)
- [ ] **GOAL-02**: Missionary can set and save their monthly support goal (in dollars)
- [ ] **GOAL-03**: Missionary can select which of their journals count toward their goal (multi-select, persisted)
- [ ] **GOAL-04**: Goal page displays effective monthly support calculated from selected journals (monthly pledges + one-time gifts ÷ months remaining in fiscal year)
- [ ] **GOAL-05**: Goal page displays pacing targets: estimated calls and meetings needed based on goal amount (25 calls and 10 meetings per $1,000)
- [ ] **GOAL-06**: Goal page displays three progress bars: Monthly Support ($), Calls Completed, and Meetings Held — each with 25/50/75/100% milestone markers
- [ ] **GOAL-07**: Monthly Support progress bar changes color by threshold (red <75%, green 75-99%, honey gold 100%)
- [ ] **GOAL-08**: Goal page shows motivational milestone messages at 0%, 25%, 50%, 75%, 100% progress thresholds
- [ ] **GOAL-09**: Goal page shows empty-state messages when no goal is set or no journals are selected
- [ ] **GOAL-10**: Supervisor and admin see Goal page in read-only mode (cannot edit goal or journal selections)
- [ ] **GOAL-11**: Monthly support goal field is removed from Settings page (or replaced with a link to Goal page)

### Fiscal Year

- [ ] **FISC-01**: Fiscal year starts July 1 and resets annually — shared utility used by Goal page and dashboard calculations
- [ ] **FISC-02**: Months remaining in fiscal year is calculated dynamically (minimum 1 to avoid division by zero)

### View As Mode

- [ ] **VIEWAS-01**: Admin can select any missionary from a dropdown to view as
- [ ] **VIEWAS-02**: Supervisor can select any of their assigned missionaries from a dropdown to view as
- [ ] **VIEWAS-03**: When viewing as a missionary, a persistent banner appears showing the missionary's name and a read-only indicator
- [ ] **VIEWAS-04**: Banner includes an "Exit" button that returns the user to their own view
- [ ] **VIEWAS-05**: All data shown while in View As mode belongs to the selected missionary (contacts, journals, gifts, dashboard stats, prayers, tasks)
- [ ] **VIEWAS-06**: All create/edit/delete actions are disabled or hidden in View As mode (frontend)
- [ ] **VIEWAS-07**: Backend enforces read-only: mutations return 403 when `X-View-As-User-Id` header is present
- [ ] **VIEWAS-08**: Backend validates viewer has permission before allowing View As (admin → any missionary; supervisor → assigned only)
- [ ] **VIEWAS-09**: Admin-only navigation sections (user management, import, analytics admin) are hidden while in View As mode
- [ ] **VIEWAS-10**: View As selection persists across page navigation (sessionStorage) until explicitly exited
- [ ] **VIEWAS-11**: All React Query caches are invalidated when View As user changes
- [ ] **VIEWAS-12**: GET /api/users/viewable returns the correct list of users per role (admin → all missionaries; supervisor → assigned only)

### Data Scoping

- [ ] **SCOPE-01**: Admin and supervisor roles default to seeing only their own data (owner=self) in all list views — same as missionary role
- [ ] **SCOPE-02**: Elevated cross-user data access only activates when a View As session is active

### MPD Dashboard

- [x] **MPD-01**: Dashboard displays a "Monthly Average" tile in the MPD Financial Overview section showing average monthly giving
- [x] **MPD-02**: Dashboard displays an MPD Overview section visible only to admin role, showing org-wide MPD health metrics from Smartsheet data

## v2.4+ Requirements (Deferred)

### Goal Enhancements
- **GOAL-EX-01**: Goal history / trend chart showing support progress over time
- **GOAL-EX-02**: Per-journal goal breakdown showing each journal's contribution
- **GOAL-EX-03**: Email or in-app notifications when milestones are reached

### View As Enhancements
- **VIEWAS-EX-01**: Coach can view their assigned missionaries (coach-specific permission)
- **VIEWAS-EX-02**: Audit log of View As sessions (who viewed whom and when)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Goal shared across team (supervisor sets missionary's goal) | Missionaries own their goals; supervisor oversight is read-only |
| Real-time/push notification when missionary hits goal | No notification infrastructure yet |
| Custom pacing ratios per missionary | Centralized constants sufficient; configurable later if needed |
| Full session impersonation (JWT swap) | X-View-As-User-Id header approach is secure and simpler; no token issuance needed |
| View As for coach role | Coach visibility already handled by coached_users M2M; defer extended View As to v2.4+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MPD-01 | Phase 48 | Complete |
| MPD-02 | Phase 48 | Complete |
| FISC-01 | Phase 49 | Pending |
| FISC-02 | Phase 49 | Pending |
| GOAL-02 | Phase 49 | Pending |
| GOAL-03 | Phase 49 | Pending |
| GOAL-04 | Phase 49 | Pending |
| GOAL-11 | Phase 49 | Pending |
| GOAL-01 | Phase 50 | Pending |
| GOAL-05 | Phase 50 | Pending |
| GOAL-06 | Phase 50 | Pending |
| GOAL-07 | Phase 50 | Pending |
| GOAL-08 | Phase 50 | Pending |
| GOAL-09 | Phase 50 | Pending |
| GOAL-10 | Phase 50 | Pending |
| SCOPE-01 | Phase 51 | Pending |
| SCOPE-02 | Phase 51 | Pending |
| VIEWAS-07 | Phase 52 | Pending |
| VIEWAS-08 | Phase 52 | Pending |
| VIEWAS-12 | Phase 52 | Pending |
| VIEWAS-01 | Phase 53 | Pending |
| VIEWAS-02 | Phase 53 | Pending |
| VIEWAS-03 | Phase 53 | Pending |
| VIEWAS-04 | Phase 53 | Pending |
| VIEWAS-05 | Phase 53 | Pending |
| VIEWAS-06 | Phase 53 | Pending |
| VIEWAS-09 | Phase 53 | Pending |
| VIEWAS-10 | Phase 53 | Pending |
| VIEWAS-11 | Phase 53 | Pending |

**Coverage:**
- v2.3 requirements: 29 total
- Mapped to phases: 29/29
- Unmapped: 0

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 — traceability updated (phase order revised: MPD moved to Phase 48, Goal backend to 49, Goal frontend to 50, Data Scoping to 51, View As backend to 52, View As frontend to 53)*
