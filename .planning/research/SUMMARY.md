# Research Summary: Admin Analytics Dashboard (v1.2)

**Project:** DonorCRM v1.2 - Admin Analytics Dashboard
**Research Date:** 2026-02-12
**Target Users:** 10-20 coaches/supervisors monitoring 200+ missionaries
**Context:** Existing Django/React CRM with journal pipeline tracking

---

## Executive Summary

The v1.2 Admin Analytics Dashboard extends DonorCRM to provide coaching-focused visibility across missionary teams. Modern CRM admin dashboards have evolved from "periodic reporting tools" to "real-time coaching command centers" that surface actionable insights—not just historical data. Coaches need to see who needs help now and why, not just aggregate statistics.

The recommended approach leverages DonorCRM's existing stack with minimal additions: extend the `insights` app for cross-user aggregation endpoints, add 1-2 frontend libraries (react-activity-calendar for heatmaps, optionally vaul for enhanced mobile panels), and reuse Recharts for all charts (FunnelChart, ComposedChart, LineChart). No backend dependencies are required—Django ORM's native aggregation (Trunc, Window functions, annotate/aggregate) handles all analytics queries at this scale (10-20 admin users, 200 missionaries).

Critical risks center on query performance (N+1 queries amplified by cross-user aggregation can generate 7000+ queries without proper optimization), permission bypass vulnerabilities (existing ListAPIView permission bugs become catastrophic when exposing all users' data), and data integrity issues (race conditions in update_giving_stats() corrupt aggregated totals). These must be addressed in Phase 1 before building dashboard features. The architecture follows existing patterns (insights app for reports, admin role-based permissions) and builds incrementally: backend foundation → basic dashboard → visualizations → interactive drill-down → polish.

---

## Stack Additions

### Frontend - New Libraries (2 total)

| Library | Version | Purpose | Bundle Impact |
|---------|---------|---------|---------------|
| **react-activity-calendar** | ^3.0.5 | GitHub-style contribution heatmap for user activity visualization | ~15KB gzipped |
| **vaul** (optional) | ^1.1.2 | Enhanced drawer/slide-in panel with mobile gestures and snap points | ~10KB gzipped |

**Total bundle addition:** ~25KB gzipped

**Installation:**
```bash
npm install react-activity-calendar@^3.0.5
npm install vaul@^1.1.2  # Optional but recommended for mobile UX
```

### Frontend - Existing Libraries (No Changes)

All chart capabilities use **existing Recharts 3.6.0**:
- FunnelChart for conversion funnel visualization
- ComposedChart for multi-series comparison views (period vs period, user vs user)
- BarChart/LineChart for trend charts

All UI components use **existing Radix UI** (Dialog/Sheet for panels, existing component library).

All data fetching uses **existing TanStack Query 5.90.17** and **TanStack Table 8.21.3**.

### Backend - NO New Dependencies

Django ORM (4.2) + PostgreSQL handle all analytics:
- **Trunc functions** (TruncDay, TruncWeek, TruncMonth) for time-series aggregation
- **Window functions** (Rank, RowNumber, Lag, Lead) for user comparisons
- **Annotate/Aggregate** for summary statistics

No analytics libraries, no aggregation frameworks, no caching layers needed at this scale.

### Why This Approach

1. **Minimal dependencies** — Only 1-2 small libraries (25KB total)
2. **Pattern consistency** — Reuses existing component patterns (Recharts, Radix UI, TanStack ecosystem)
3. **Performance** — PostgreSQL + Django ORM scales to 10-20 admins viewing 200 missionaries with millions of records
4. **Maintenance** — Fewer dependencies = less upgrade churn
5. **Proven stack** — All core libraries already in production use

---

## Feature Priorities

### Table Stakes (Expected by Coaches)

Features that users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| **Dashboard Overview with Summary Cards** | Standard CRM admin pattern. Coaches expect key metrics at a glance (total contacts, active journals, conversion rates, stalled contacts count). | Low |
| **Team Activity List/Table** | Coaches need to see what missionaries are doing (recent journal updates, new contacts, decisions logged) without clicking into each user. | Medium |
| **User Performance Comparison** | Supervisors compare fundraisers side-by-side to identify outliers (top performers, struggling fundraisers needing coaching). | Medium |
| **Stalled Contact Alerts (14+ days no activity)** | Universal pattern in fundraising CRMs. Coaches need visibility into stagnant pipelines. | Low |
| **Conversion Funnel Visualization** | Industry standard. Coaches expect to see pipeline progression (contacts in each stage, conversion rates) to understand bottlenecks. | Medium |
| **Time Period Filtering** | Date range pickers (This Month, Last Quarter, Custom Range) for current vs. historical performance. | Low |
| **Per-User Drill-Down** | Click user in team list → detailed view of that missionary's stats, journals, contacts. | Low |
| **Export to CSV** | Admins expect to download reports for offline analysis, sharing with leadership. | Low |
| **Role-Based Access (Admin Only)** | Team analytics only visible to coaches/admins, not individual fundraisers. | Low |
| **Mobile-Responsive Layout** | Coaches check dashboards on tablets/phones between meetings. | Medium |

### Differentiators (Portfolio-Impressive)

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity |
|---------|------------------|------------|
| **Interactive Drill-Down Charts** | Click funnel stage → see contacts in that stage. Click user in chart → navigate to detail page. Makes analytics actionable, not just informative. Premium 2026 CRM feature. | High |
| **Activity Heatmap Calendar View** | GitHub-style contribution grid showing team activity density over time. Uncommon in nonprofit CRMs. Visually impressive for portfolio. | High |
| **Comparison Mode (Time Periods)** | Side-by-side: "January vs. February" or "Q1 2025 vs. Q1 2026." Coaches identify seasonal trends or validate coaching interventions. | Medium |
| **Comparison Mode (Users)** | Side-by-side user comparison across key metrics. Benchmark performance, identify best practices. | Medium |
| **AI-Driven Alerts Panel** | Auto-generated recommendations: "Sarah has 8 contacts stalled >21 days," "Team conversion dropped 10%." Phase 1: rule-based logic. Portfolio-impressive even without ML. | High |
| **User Drilldown Panel (Slide-In Sidebar)** | Click user row → slide-in drawer shows quick stats, recent journals, stalled contacts without navigating away. Smooth modern UX pattern. | Medium |
| **Trend Charts (Not Just Snapshots)** | Line charts showing team metrics over time (e.g., "Decisions logged per week for past 12 weeks"). Coaches see trajectory, not just current state. | Medium |

### Anti-Features (Explicitly Avoid)

Features to NOT build. Common scope creep mistakes.

| Anti-Feature | Why Avoid |
|--------------|-----------|
| **Real-Time Collaboration (Live Cursors, Shared Editing)** | Coaches review data independently or in meetings. WebSocket complexity for negligible value. |
| **Granular Permission System (Row-Level Security)** | Over-engineering for 10-20 coaches. Simple role-based access (admin sees all, fundraiser sees own) is sufficient. |
| **Custom Dashboard Builder (Drag-and-Drop Widgets)** | Coaches want answers to specific questions, not to design dashboards. Provide 3-5 opinionated views instead. |
| **Bulk Editing from Dashboard** | Mixing concerns. Dashboards are for visibility; bulk actions belong in Contact/Journal management pages. |
| **Historical Drill-Down Beyond 12 Months** | Diminishing returns. Fundraising coaching focuses on recent trends (last month, last quarter, YTD). |
| **Notification Center with Email/SMS Alerts** | Alert fatigue is real. In-app alerts panel suffices. Email infrastructure is significant effort for v1.2. |
| **Org Chart Visualization** | Not relevant to flat SPO structure. Simple team list/table suffices. |
| **Goal Setting & Tracking UI** | Valuable but scope creep for v1.2. Requires new models (Goal, Milestone), progress calculations, CRUD UI. Defer to v1.3+. |

### MVP Recommendation (v1.2 Scope)

**MUST HAVE (Table Stakes):**
1. Dashboard Overview with summary cards
2. Team Activity Table (sortable, filterable)
3. Stalled Contacts Page (pagination, sorting)
4. Conversion Funnel Chart (pipeline stage distribution)
5. User Detail Page (per-missionary stats, journal list)
6. Time Period Filtering (date range picker)
7. Role-Based Access (admin/read_only only)
8. Export to CSV (team activity, stalled contacts, user metrics)

**SHOULD HAVE (Differentiators for Portfolio):**
9. User Drilldown Panel (slide-in sidebar from team table)
10. Drill-Down Charts (click funnel stage → see contacts in that stage)
11. Trend Charts (line chart showing "Decisions logged per week" over 12 weeks)
12. Alerts Panel (rule-based insights like "5 users have >10 stalled contacts")

**DEFER (Post-MVP):**
- Comparison Mode (Time Periods) — v1.3 if time-constrained
- Comparison Mode (Users) — v1.3
- Activity Heatmap — v1.3 (visually impressive but non-critical)
- Configurable Alerts — v2.0 (requires user preferences model)

---

## Architecture Decisions

### Core Pattern: Extend Existing `insights` App

**Decision:** Add admin analytics endpoints to existing `insights` app rather than creating new `admin_analytics` app.

**Rationale:**
- DonorCRM already separates `dashboard` (per-user) vs. `insights` (reports/analytics)
- `insights` app already has admin-only endpoints (ReviewQueueView, TransactionsView) with role-based visibility
- Adding 5-7 endpoints doesn't justify new app complexity
- Avoids ambiguity ("Is this insights or admin_analytics?")

**Pattern match:** Existing `journals/views.py:JournalAnalyticsViewSet.admin_summary` already does cross-user aggregation. Admin dashboard extends this pattern.

### Backend Architecture

**Component boundaries:**

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **AdminDashboardView** | `insights/views.py` (NEW) | Aggregate overview metrics across all users |
| **StalledContactsView** | `insights/views.py` (NEW) | Detect contacts with 14+ days no activity |
| **UserPerformanceView** | `insights/views.py` (NEW) | Per-user performance metrics and trends |
| **ConversionFunnelView** | `insights/views.py` (NEW) | Pipeline stage counts for funnel visualization |
| **TeamActivityView** | `insights/views.py` (NEW) | Recent activity across all users |
| **admin_analytics_services** | `insights/services.py` (EXTEND) | Business logic for metrics calculation |

**Permissions:** Use existing `IsAdmin` and `IsFinanceOrAdmin` permission classes. No new permission classes needed.

### Frontend Architecture

**Route structure:** `/admin/analytics/*` (matches existing `/admin/users`, `/admin/imports` pattern)

| Route | Component | Purpose |
|-------|-----------|---------|
| `/admin/analytics/dashboard` | `AdminAnalyticsDashboard.tsx` (NEW) | Overview page with all widgets |
| `/admin/analytics/stalled` | `StalledContacts.tsx` (NEW) | Stalled contacts page with table |
| `/admin/analytics/users/:id` | `UserPerformance.tsx` (NEW) | User detail page with trends |

**Navigation:** Add "Analytics" submenu under Admin nav section (Admin → Users, Import Center, Analytics).

**Component reuse:**
- Charts: Recharts (FunnelChart, ComposedChart, BarChart, LineChart)
- Tables: Existing React Table patterns from contact/donation lists
- Panels: Radix UI Dialog/Sheet (or Vaul for enhanced mobile UX)
- Data fetching: TanStack Query hooks following existing patterns

### Data Flow Pattern

**Aggregation query pattern:**
```
1. Frontend hook calls GET /api/v1/insights/admin-dashboard/
2. AdminDashboardView.get(request)
3. Call service functions:
   - get_summary_cards(user)
   - get_conversion_funnel(user)
   - get_team_activity(user, limit=10)
   - get_donation_trend(user, months=12)
4. Each service function:
   - Builds base queryset (all users if admin)
   - Uses annotate() for aggregation
   - Uses select_related/prefetch_related to avoid N+1
   - Returns dict with computed metrics
5. View combines all results into single response
6. Frontend renders widgets
```

**Critical optimization:** All aggregations use Django ORM annotate/aggregate (database-level), NOT Python-level loops. With 200 missionaries, Python loops trigger 600-1400 queries. Database aggregation: 1-20 queries.

### Integration Points with Existing System

**Reuse existing analytics endpoints:**
- `journals/views.py:JournalAnalyticsViewSet` already provides `decision_trends`, `stage_activity`, `pipeline_breakdown`, `admin_summary`
- Extend these with optional `user_id` filter for per-user views instead of duplicating logic

**Reuse dashboard service patterns:**
- `dashboard/services.py` has `get_giving_summary(user, year)`, `get_monthly_gifts(user, months)`
- Admin analytics uses similar patterns but across ALL users
- Extract common aggregation logic into shared utility: `scope_queryset_by_role(qs, user, owner_field='owner')`

**Permission pattern:**
- Use existing `IsAdmin` for admin-only endpoints (stalled contacts, user performance)
- Use existing `IsFinanceOrAdmin` for read-only analytics (conversion funnel, trends)
- **Critical fix required:** Existing code mixes `is_staff` vs. `role == 'admin'` (Edge Case Audit 1.5). Standardize on `role == 'admin'` before building dashboard.

### Stalled Contact Detection Algorithm

**Definition:** Contact is "stalled" when:
- Contact is in a journal (has JournalContact record)
- Last JournalStageEvent for that contact is >14 days ago
- OR contact has no stage events at all (added to journal but no activity)

**Implementation pattern:**
```python
latest_event = JournalStageEvent.objects.filter(
    journal_contact__contact=OuterRef('pk')
).order_by('-created_at').values('created_at')[:1]

stalled = Contact.objects.annotate(
    last_activity_date=Subquery(latest_event)
).filter(
    Q(last_activity_date__lt=date.today() - timedelta(days=14)) |
    Q(last_activity_date__isnull=True)
).distinct().select_related('owner').order_by('last_activity_date')
```

**Index needed:** `models.Index(fields=['journal_contact', '-created_at'])` on JournalStageEvent.

### Conversion Funnel Architecture

**Reuse existing journal pipeline stages** (contact, meet, close, decision, thank, next_steps). No new stages needed.

**Calculation pattern:**
```python
latest_stage = JournalStageEvent.objects.filter(
    journal_contact=OuterRef('pk')
).order_by('-created_at').values('stage')[:1]

breakdown = JournalContact.objects.annotate(
    current_stage=Subquery(latest_stage)
).values('current_stage').annotate(
    count=Count('id')
).order_by('current_stage')
```

**Drill-down:** When user clicks funnel stage, query contacts in that stage with `select_related('contact__owner', 'journal__owner')`, display in modal/panel.

---

## Critical Pitfalls

### Top 5 Risks and Mitigations

#### 1. CRITICAL: N+1 Queries on Cross-User Aggregation

**Risk:** Admin dashboard loads 200 missionaries' data. Each missionary triggers 3-7 queries for related stats. Total: 600-1400 queries for a single page load → 30s timeout.

**Existing vulnerability:** Edge case audit issue 1.1 already documents journal grid doing 7N queries per contact. Cross-user aggregation multiplies this by 200 users.

**Mitigation:**
```python
# WRONG: N+1 disaster
missionaries = User.objects.filter(role='missionary')
for m in missionaries:
    total_contacts = m.contacts.count()  # +200 queries

# CORRECT: Database-level aggregation
missionaries = User.objects.filter(role='missionary').annotate(
    total_contacts=Count('contacts'),
    total_donations=Count('contacts__donations'),
    active_journals=Count('journals', filter=Q(journals__is_active=True))
)
```

**Detection:** django-debug-toolbar in development. Log warning if endpoint executes >50 queries. Load test: 200 users should complete in <3s.

**Phase impact:** Must address in Phase 1 (backend foundation). Every aggregation endpoint needs query optimization audit.

#### 2. CRITICAL: Permission Bypass via ListAPIView

**Risk:** Admin analytics list view uses permission class with only `has_object_permission()`. DRF's `ListAPIView` only checks `has_permission()` on list views → permission class is ignored → any authenticated user can access admin-only aggregation endpoints.

**Existing vulnerability:** Edge case audit issue 2.2/4.1 documents this exact bug in `IsContactOwnerOrReadAccess`.

**Mitigation:**
```python
# CORRECT: Implement has_permission() in permission class
class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin'

# Or add explicit check in view
class MissionaryStatsView(ListAPIView):
    def list(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=403)
        return super().list(request, *args, **kwargs)
```

**Detection:** Test suite: Read-only user calls admin endpoint → expect 403. Code review: All `ListAPIView` with admin data must check role in `list()` or permission class.

**Phase impact:** Phase 1 (permissions). Block all analytics work until this pattern is established.

#### 3. CRITICAL: Race Conditions in Stat Updates

**Risk:** Admin imports 500 donations via CSV. Each save triggers `update_giving_stats()` signal. Multiple signals for same contact run concurrently, each reads current `total_given`, adds new amount, saves → last write wins → intermediate donations lost from total.

**Existing vulnerability:** Edge case audit issues 2.1 (update_giving_stats race) and 3.2 (record_fulfillment race).

**Consequence:** Dashboard shows "Total Given: $45,000" when actual is $48,000. Stats differ between "All Missionaries" view and individual user view.

**Mitigation:**
```python
# Disable signals during bulk operations
def bulk_import_donations(donations_data):
    post_save.disconnect(update_giving_stats_signal, sender=Donation)
    try:
        Donation.objects.bulk_create([...])
        # Update stats once per affected contact
        for contact_id in affected_contacts:
            contact = Contact.objects.select_for_update().get(pk=contact_id)
            contact.update_giving_stats()
    finally:
        post_save.connect(update_giving_stats_signal, sender=Donation)

# Use F() expressions for atomic updates
Contact.objects.filter(pk=self.pk).update(
    total_given=F('total_given') + new_amount
)
```

**Detection:** Test: Import 100 donations for same contact simultaneously → stats should be exact.

**Phase impact:** Phase 1 (data integrity). Must fix existing race conditions before building dashboard that depends on accurate stats.

#### 4. CRITICAL: Float Arithmetic in Aggregated Money Totals

**Risk:** Dashboard aggregates float `monthly_equivalent` values across 200 missionaries × 50 pledges each → penny discrepancies compound → "Total Monthly Pledges: $49,999.97" when actual is $50,000.00.

**Existing vulnerability:** Edge case audit issue 3.1 documents float multiplication in pledge `monthly_equivalent` property.

**Mitigation:**
```python
# Fix existing pledge model property
@property
def monthly_equivalent(self):
    multipliers = {'weekly': Decimal('4.33'), 'monthly': Decimal('1'), ...}
    return self.amount * multipliers[self.frequency]

# In aggregation, use Decimal throughout
from django.db.models import Sum, DecimalField
from django.db.models.functions import Cast

total_monthly = Pledge.objects.filter(status='ACTIVE').annotate(
    monthly=Cast('amount', DecimalField()) * Case(
        When(frequency='weekly', then=Decimal('4.33')),
        When(frequency='monthly', then=Decimal('1')),
        # ...
    )
).aggregate(total=Sum('monthly'))['total']
```

**Detection:** Test: Aggregate 1000 $33.33 weekly pledges → should equal $144,652.00 exactly. Lint rule: Flag `float()` calls on money fields.

**Phase impact:** Phase 2 (dashboard backend). Fix existing pledge model first, then build aggregations on corrected base.

#### 5. HIGH: Inconsistent Role Checks (is_staff vs. role == 'admin')

**Risk:** Existing code mixes `is_staff` vs. `role == 'admin'` for permission checks. Admin dashboard adds more endpoints with inconsistent checks → finance users see missionary journal data they shouldn't access.

**Existing vulnerability:** Edge case audit issue 1.5 documents `admin_summary` uses `is_staff` while other endpoints use `role == 'admin'`.

**Mitigation:** Standardize all admin analytics endpoints on `role == 'admin'`. Update existing `admin_summary` endpoint to match.

```python
# Consistent pattern for all admin endpoints
def admin_analytics(request):
    if request.user.role != 'admin':
        return Response({'error': 'Admin only'}, status=403)
    # Now safe to aggregate across users
```

**Detection:** API test: Finance user calls `/api/v1/admin/analytics/` → should get 403.

**Phase impact:** Phase 1 (permissions setup). Must establish before any aggregation logic.

### Additional High-Priority Pitfalls

**Unbounded Data in Aggregation Endpoints:** Endpoint returns 50,000 journal events → browser tab freezes. Mitigation: Pagination + date windowing (default last 90 days, 50 items per page, 500 hard limit).

**Query Result Timing Inconsistencies:** Multiple service functions execute separate queries at different times → "Total Donations: 1,247" in header but "Recent Donations" widget shows 1,250. Mitigation: Single query with subqueries or use `@transaction.atomic` for consistent snapshots.

**GET Request with Side Effects:** Admin opens dashboard → all events marked as "seen" → browser crashes before rendering → events permanently lost as "new". Mitigation: Separate POST endpoint for mutations (mark-as-read). GET = read-only always.

**Stale Data Detection Logic Errors:** "Stalled Contacts" shows contacts with no activity in 60 days but includes contacts created 30 days ago (never had activity vs. activity stopped). Mitigation: Explicit null handling with `Q(last_contact_date__lt=cutoff) | Q(last_contact_date__isnull=True)` and filter by `created_at__lt=cutoff`.

---

## Build Order Recommendation

### Phase 1: Backend Foundation (Data Access Layer)
**Goal:** Core analytics endpoints functional, testable via API.

**Deliverables:**
1. Extend `insights/services.py` with cross-user aggregation functions (get_admin_dashboard_summary, get_stalled_contacts, get_user_performance, get_conversion_funnel, get_team_activity)
2. Add views to `insights/views.py` (AdminDashboardView, StalledContactsView, UserPerformanceView)
3. Extend `insights/urls.py` with new paths
4. Add indexes to JournalStageEvent model
5. Write tests for each service function (query count, correct results, permission checks)

**Critical path items:**
- Fix permission bypass vulnerability (implement has_permission() in all permission classes)
- Standardize on role=='admin' (not is_staff)
- Fix existing race conditions in update_giving_stats() and record_fulfillment()
- Fix float arithmetic in pledge monthly_equivalent

**Dependencies:** None. Builds on existing models and permission classes.

**Validation:** Test via API client (Postman, Swagger UI) before starting frontend.

### Phase 2: Frontend Foundation (Pages & Navigation)
**Goal:** Pages render with data from API.

**Deliverables:**
1. Add API client functions in `api/adminAnalytics.ts`
2. Add React Query hooks in `hooks/useAdminAnalytics.ts`
3. Create placeholder pages (AdminAnalyticsDashboard, StalledContacts, UserPerformance) with basic data display
4. Add routes to App.tsx with requiredRole="admin"
5. Update navigation in AppLayout.tsx to add Analytics submenu under Admin

**Dependencies:** Phase 1 complete (API endpoints working).

**Validation:** Pages load with real data from API. No errors in console.

### Phase 3: Dashboard Core (Overview & Tables)
**Goal:** Overview page has all widgets functional.

**Deliverables:**
1. Build chart components (ConversionFunnelChart, TrendChart, TeamActivityTable)
2. Build layout components (summary cards grid, two-column chart layout, activity table)
3. Add alerts panel (severity badges, message list)
4. Wire up all components in AdminAnalyticsDashboard.tsx

**Dependencies:** Phase 2 complete (API hooks working).

**Validation:** Dashboard page matches design, all widgets display data correctly.

### Phase 4: Stalled Contacts & User Detail Pages
**Goal:** Stalled contacts page with pagination/sorting, user detail page with trends.

**Deliverables:**
1. Build stalled contacts table (React Table with columns: Contact Name, Owner, Days Since Activity, Current Stage, Actions)
2. Add pagination controls and sorting
3. Build user performance page (user header, trend charts, journals table)
4. Add navigation from team activity table to user detail page

**Dependencies:** Phase 2 complete (API hooks working).

**Validation:** Stalled contacts page loads, pagination works, sorting works. User detail page loads, charts display.

### Phase 5: Visualizations & Interactivity
**Goal:** Charts functional with drill-down capabilities.

**Deliverables:**
1. Add click handler to ConversionFunnelChart (capture clicked stage, open UserDrilldownPanel with contact list)
2. Build UserDrilldownPanel (slide-in sidebar with contact list, close button)
3. Add drill-down endpoint (extend ConversionFunnelView to accept ?stage=decision)
4. Wire up panel to funnel chart

**Dependencies:** Phase 3 complete (charts working).

**Validation:** Click funnel stage, panel opens with correct contact list.

### Phase 6: Advanced Features (Time Period Filtering, CSV Export)
**Goal:** Time filtering and export functionality.

**Deliverables:**
1. Add date range picker to dashboard (This Month, Last Quarter, Custom Range)
2. Wire up date filtering to all analytics queries
3. Add CSV export endpoints mirroring `/api/v1/imports/export/` pattern
4. Add export buttons to Stalled Contacts and Team Activity pages

**Dependencies:** Phase 3-4 complete (dashboard and detail pages working).

**Validation:** Date filtering updates all widgets. CSV export downloads correct data.

### Phase 7: Polish & Optimization
**Goal:** Production-ready performance and UX.

**Deliverables:**
1. Query optimization audit (django-debug-toolbar on each endpoint, verify query count <20)
2. Loading states (skeleton loaders for charts, table loading spinner)
3. Error handling (API error toast notifications, empty state messages)
4. Accessibility (ARIA labels on charts, keyboard navigation for panels)
5. Responsive design (mobile layout, chart responsiveness)

**Dependencies:** Phases 1-6 complete.

**Validation:** Performance audit passes (query count <20, response time <3s). UX polished (no layout shift, smooth loading states).

### Rationale for This Order

**Backend first:** API endpoints are testable independently. Catches data modeling issues early. Frontend can develop against real API, not mocks.

**Foundation before features:** Routing and navigation working before complex widgets. Validates API integration early. Reduces context switching.

**Dashboard before detail pages:** Dashboard is the landing page, highest priority. Stalled contacts page is simpler (table-only), good second page.

**Drill-down last:** Enhancement, not MVP requirement. Requires both funnel chart and panel working. Can be deferred if timeline tight.

**Polish always last:** Performance optimization requires full feature set. UX polish needs user feedback.

---

## Open Questions

### Unresolved Items Across Research

**Team structure and scoping:**
- Is a coach assigned to specific missionaries, or can they see all users?
- If team scoping needed: Add `coach_id` foreign key to User model? Or use existing hierarchy?
- Current assumption: Admins see all missionaries. No team-level filtering in v1.2.

**Stalled contact threshold:**
- 14 days is standard in nonprofit CRMs, but is this right for SPO's workflow?
- Should threshold be configurable per coach? (Defer to v2.0 if yes)
- Should archived journals be excluded from stalled detection?

**Activity definition for heatmap:**
- What counts as "activity" for heatmap calendar? (Journal stage events, contact updates, decision logs, task creation?)
- Should heatmap show per-user activity or aggregate team activity?
- If aggregate: How to handle overlapping activity (multiple users active same day)?

**Comparison mode implementation:**
- Time period comparison: Should it be side-by-side charts or overlaid on single chart?
- User comparison: Top N users or select specific users?
- If time-constrained: Defer both to v1.3?

**CSV export scope:**
- Which metrics/columns to include in CSV export?
- Should export respect date filters?
- Should export be per-page or full dataset?

**Performance thresholds:**
- At what user count should caching be added? (Assumption: not needed for 10-20 admins, 200 missionaries)
- What response time is acceptable for dashboard load? (Target: <2s)
- Should there be a hard limit on date range queries? (Recommendation: 24 months max)

**Alert panel rules:**
- What thresholds trigger alerts? (Current: >20% stalled contacts, users with 0 activity in 30 days)
- Should alerts be dismissible and persist dismissal state?
- How many alerts to show before "View All" link?

### Research Flags for Roadmapper

**Needs deeper research during planning:**
- **Phase 5 (Heatmap calendar):** Research canvas-based heatmap libraries for performance with large datasets. react-activity-calendar is SVG-based (may struggle with 73,000 cells for 200 users × 365 days).
- **Phase 6 (Comparison modes):** UX pattern research for side-by-side vs. overlay comparison charts. No strong recommendation from current research.

**Standard patterns (skip research):**
- Phase 1-2 (Backend foundation, frontend pages): Well-documented Django aggregation patterns + React Query patterns. No additional research needed.
- Phase 3-4 (Dashboard core, tables): Recharts documentation + React Table patterns. Standard implementation.

### Gaps to Address During Implementation

**Testing strategy:**
- Load testing with 200 concurrent users hasn't been scoped
- Performance benchmarks for aggregation queries need baseline measurements
- UAT scenarios for coaches need refinement (10 scenarios identified in FEATURES.md but need user validation)

**Accessibility:**
- ARIA labels for charts mentioned but specific implementation not researched
- Keyboard navigation patterns for drill-down panels need design
- Screen reader support for heatmap calendar not addressed

**Mobile experience:**
- Vaul recommended for mobile panels but mobile layout design not fully scoped
- Chart responsiveness patterns identified but specific breakpoints not defined
- Touch gesture support for drill-down not detailed

**Error handling:**
- Empty state designs mentioned but copy/visuals not defined
- API error messages need standardization
- Retry logic for failed aggregation queries not addressed

**Data migration:**
- No existing admin analytics data to migrate, but indexes need to be added to JournalStageEvent (performance impact during migration on large datasets?)

---

## Confidence Assessment

| Area | Confidence | Reasoning |
|------|------------|-----------|
| **Stack** | HIGH | Minimal additions (2 libraries), all core capabilities in existing stack. Versions verified via npm. Django ORM capabilities documented in official docs. |
| **Features** | HIGH | 250+ sources on CRM admin dashboards, fundraising coaching, team performance management. Clear pattern: table stakes vs. differentiators. |
| **Architecture** | HIGH | Existing codebase patterns well-documented. Django ORM aggregation patterns proven. React component architecture follows established patterns. |
| **Pitfalls** | HIGH | 20 pitfalls identified, 8 critical/high-priority. Most based on existing edge case audit (known vulnerabilities). Django N+1, permission bypass, race conditions well-documented in official docs + community articles. |
| **Build Order** | MEDIUM-HIGH | Phase dependencies clear. Backend → frontend → features → polish is standard. Drill-down and heatmap complexity may shift based on implementation challenges. |

### Overall Confidence: HIGH

**Strengths:**
- Existing DonorCRM edge case audit provides concrete vulnerability evidence (not theoretical)
- Minimal stack additions reduce unknowns
- Architecture extends existing patterns (insights app, admin permissions) rather than introducing new paradigms
- Critical pitfalls documented in official Django/DRF/TanStack documentation with proven mitigation patterns

**Gaps:**
- Limited 2026-specific content for React dashboard patterns (most sources 2025, but patterns stable)
- No domain-specific research on nonprofit CRM admin dashboards (applied general CRM/sales patterns to fundraising context)
- Heatmap performance with large datasets is theoretical (no benchmark data for 73,000 cells)
- Comparison mode UX patterns are generic (no nonprofit CRM-specific examples)

**Risk mitigation:**
- Phase 1 addresses all critical pitfalls (N+1, permissions, race conditions, float arithmetic) before building features
- Query optimization audit in Phase 7 catches performance issues before production
- Incremental build order allows validation at each phase (backend testable before frontend, foundation before advanced features)

---

## Sources

**Stack Research:**
- [Vaul GitHub Repository](https://github.com/emilkowalski/vaul)
- [react-activity-calendar npm](https://www.npmjs.com/package/react-activity-calendar)
- [Recharts FunnelChart API](https://recharts.github.io/en-US/api/FunnelChart/)
- [Recharts ComposedChart API](https://recharts.github.io/en-US/api/ComposedChart/)
- [Time-Series Data with Django ORM](https://medium.com/django-unleashed/time-series-data-with-django-orm-monthly-weekly-daily-aggregations-b5ddfa1e194e)
- [Window Functions in Django ORM](https://medium.com/django-unleashed/unpacking-djangos-window-functions-analytics-made-easy-7e4a2ce1f470)

**Features Research:**
- [CRM dashboards in 2026: essential KPIs and real-world examples](https://monday.com/blog/crm-and-sales/crm-dashboards/)
- [Essential B2B Sales KPIs & Metrics: Complete Guide for 2026](https://forecastio.ai/blog/sales-kpis)
- [Nonprofit Analytics & Advanced Reporting](https://www.giveffect.com/nonprofit-analytics)
- [Conversion Funnel: Ultimate Guide to Stages & Optimization (2026)](https://improvado.io/blog/conversion-funnel)
- [Period-over-period comparisons for time series | Metabase](https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/time-series/time-series-comparisons)

**Architecture Research:**
- [Django Database Access Optimization](https://docs.djangoproject.com/en/6.0/topics/db/optimization/)
- [Optimizing Django Queries with select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [SaaS Applications with Django: Building Analytics and Dashboards](https://medium.com/@mathur.danduprolu/saas-applications-with-django-building-analytics-and-dashboards-part-5-7-5e5e11ec310a)
- [Six Principles of Dashboard Information Architecture](https://www.gooddata.com/blog/six-principles-of-dashboard-information-architecture/)

**Pitfalls Research:**
- [Django QuerySet Optimization: Stop Strangling API Performance](https://medium.com/@sizanmahmud08/django-queryset-optimization-stop-stranglingyour-api-performance-6bc368d72512)
- [Django N+1 Queries Problem](https://www.scoutapm.com/blog/django-and-the-n1-queries-problem)
- [Django Role-Based Access Control (RBAC)](https://www.permit.io/blog/how-to-implement-role-based-access-control-rbac-into-a-django-application)
- [React Query Cache Invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation)
- [Recharts vs Chart.js Performance for Big Data](https://www.oreateai.com/blog/recharts-vs-chartjs-navigating-the-performance-maze-for-big-data-visualizations/4aff3db4085050dc635fd25267846922)

**Plus:** 200+ additional sources across STACK.md, FEATURES.md, ARCHITECTURE.md, and ADMIN_ANALYTICS_PITFALLS.md research files.

---

**Research Complete.** Ready for roadmap creation.
