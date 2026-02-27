# Requirements: DonorCRM

**Defined:** 2026-02-26
**Core Value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## v2.2 Requirements

Requirements for v2.2 milestone. Each maps to roadmap phases.

### Dashboard

- [x] **DASH-01**: User can toggle between bar chart and line graph on the Donations chart
- [x] **DASH-02**: Dashboard tiles are draggable to any position (cross-section)
- [x] **DASH-03**: Dashboard gaps between tiles are visually tightened
- [x] **DASH-04**: "2026 calendar year" text is removed from Giving summary
- [x] **DASH-05**: "Updated today" text is removed from Monthly Gifts
- [x] **DASH-06**: "Recent Journal Activity" tile is removed from dashboard

### UI Polish

- [x] **UI-01**: All modal dialogs are centered on screen
- [x] **UI-02**: "Prospect" is renamed to "Potential Donor" on contacts page
- [x] **UI-03**: Fund and Description columns are removed from gifts list page
- [x] **UI-04**: Type column (Credit Card / Direct Deposit / Check) is added to gifts list page
- [x] **UI-05**: Fund column is removed from pledges list page

### Analytics

- [x] **ANLY-01**: Review Queue is removed from the analytics dashboard
- [x] **ANLY-02**: Activity heat map is removed from the analytics dashboard

### Journal

- [x] **JRNL-01**: Journal report displays 4 metric cards (Total Contacts, With Decisions, Confirmed $, Pending)
- [x] **JRNL-02**: Journal report displays goal progress bar with confirmed amount
- [x] **JRNL-03**: Journal report displays Contacts by Stage bar chart with stage colors
- [x] **JRNL-04**: Journal report displays Decision Status donut chart
- [x] **JRNL-05**: Journal report displays conditional stalled contacts and open next steps alerts
- [x] **JRNL-06**: Pipeline Breakdown is removed from journal reports
- [x] **JRNL-07**: Decision column between Close and Thank supports adding a decision (not checkbox)
- [x] **JRNL-08**: Clicking a stage checkbox directly checks it (auto-creates event) without dialog

### Prayer

- [ ] **PRAY-01**: Prayer Request page has a "Begin Prayer" button that launches expanded Focus Mode

### Supervisor

- [ ] **SUPV-01**: Mission Supervisor role exists in the system (UserRole choice + migration)
- [ ] **SUPV-02**: Admin can assign missionaries to a supervisor via management UI
- [ ] **SUPV-03**: Supervisor sees only their assigned missionaries' data across all pages
- [ ] **SUPV-04**: Admin and Supervisor can select a missionary and view their dashboard

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Supervisor Extensions

- **SUPV-05**: Supervisor can view admin analytics dashboard scoped to their missionaries
- **SUPV-06**: Supervisor assignment via bulk import (CSV/Smartsheet)

### Dashboard Persistence

- **DASH-07**: Dashboard tile order persists across sessions (requires backend user preferences)

### Prayer Extensions

- **PRAY-02**: Prayer session history tracked server-side (PrayerSession model)
- **PRAY-03**: Prayer activity visible to coaches/supervisors

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Supervisor can edit missionary data | Breaks ownership model; supervisor role is view-only |
| Supervisor self-assignment | Breaks admin control over org structure; security risk |
| Dynamic column visibility toggle | Over-engineered for current needs; curate correct defaults instead |
| Backend "prospect" -> "potential_donor" value change | Display-only rename sufficient; data migration unnecessary |
| Real-time prayer session sync | No WebSocket infrastructure; prayer is personal |
| Persistent dashboard tile order (backend) | Requires user preferences model; session-only sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 38 | Complete |
| UI-02 | Phase 38 | Complete |
| UI-03 | Phase 38 | Complete |
| UI-04 | Phase 38 | Complete |
| UI-05 | Phase 38 | Complete |
| ANLY-01 | Phase 38 | Complete |
| ANLY-02 | Phase 38 | Complete |
| DASH-01 | Phase 39 | Complete |
| DASH-02 | Phase 39 | Complete |
| DASH-03 | Phase 39 | Complete |
| DASH-04 | Phase 39 | Complete |
| DASH-05 | Phase 39 | Complete |
| DASH-06 | Phase 39 | Complete |
| JRNL-01 | Phase 40 | Complete |
| JRNL-02 | Phase 40 | Complete |
| JRNL-03 | Phase 40 | Complete |
| JRNL-04 | Phase 40 | Complete |
| JRNL-05 | Phase 40 | Complete |
| JRNL-06 | Phase 40 | Complete |
| JRNL-07 | Phase 40 | Complete |
| JRNL-08 | Phase 40 | Complete |
| PRAY-01 | Phase 41 | Pending |
| SUPV-01 | Phase 42 | Pending |
| SUPV-02 | Phase 42 | Pending |
| SUPV-03 | Phase 42 | Pending |
| SUPV-04 | Phase 42 | Pending |

**Coverage:**
- v2.2 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after roadmap creation*
