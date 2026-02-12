# Feature Landscape: Admin Analytics Dashboard

**Domain:** CRM Admin/Leadership Analytics for Fundraising Coaching
**Researched:** 2026-02-12
**Confidence:** HIGH

## Executive Summary

Admin analytics dashboards in modern CRM platforms serve two primary purposes: (1) provide real-time visibility into team performance metrics, and (2) enable data-driven coaching by surfacing actionable insights about individual fundraisers and team trends. The 2026 landscape emphasizes AI-driven alerts, drill-down capabilities, comparative analysis (team members, time periods), and role-based dashboards that tailor visibility to coach/supervisor needs.

For DonorCRM v1.2, the coach/supervisor user (10-20 at SPO) needs to monitor a team of missionaries, identify stalled relationships, spot coaching opportunities, and track overall fundraising pipeline health across their team. This research categorizes features into table stakes (expected by supervisors), differentiators (portfolio-impressive or competitive advantages), and anti-features (scope creep to avoid).

**Key Insight:** The shift in 2026 is from "reporting dashboards" (periodic reviews of historical data) to "coaching command centers" (real-time visibility with AI-powered recommendations). Coaches expect to see not just what happened, but what needs attention now and why.

## Table Stakes

Features users expect. Missing = product feels incomplete for coaching use case.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Dashboard Overview with Summary Cards** | Standard pattern across all CRM admin tools. Coaches expect to see key metrics (total contacts, active journals, conversion rates, stalled contacts count) at a glance when they log in. | Low | Journal analytics endpoints exist (v1.0) | Already have `/api/v1/insights/` endpoints that aggregate data. Frontend needs summary card components. |
| **Team Activity List/Table** | Coaches need to see what their missionaries are doing (recent journal updates, new contacts added, decisions logged) without clicking into each user. | Medium | User scoping for contacts/journals | Requires cross-user queries filtered by team membership. Need to determine team structure (is a coach assigned to specific users, or can they see all?). |
| **User Performance Comparison** | Supervisors compare fundraisers side-by-side to identify outliers (top performers for recognition, struggling fundraisers for coaching). | Medium | Per-user analytics aggregation | Calculate metrics like "contacts added this month," "decisions logged," "pipeline stage distribution" grouped by user. |
| **Stalled Contact Alerts (14+ days no activity)** | Universal pattern in nonprofit/fundraising CRMs. Relationships require momentum; stalled contacts = at-risk donations. Coaches need visibility into which missionaries have stagnant pipelines. | Low | Contact/journal event tracking | Filter journals/contacts by `updated_at` or last event timestamp. Pagination/sorting needed (could be hundreds). |
| **Conversion Funnel Visualization** | Coaches expect to see pipeline progression (how many contacts in each stage, conversion rates between stages) to understand bottlenecks. Industry standard in sales CRM admin tools. | Medium | Journal pipeline data (6 stages exist) | Aggregate journal contacts by stage, calculate stage-to-stage conversion percentages. Use existing Decision tracking for "Close → Decision" conversion. |
| **Time Period Filtering** | Admin dashboards universally offer date range pickers (This Month, Last Quarter, Custom Range) so coaches can compare current vs. historical performance. | Low | Timestamp filtering on analytics queries | Add `date_from`/`date_to` query params to existing endpoints. Frontend date picker component. |
| **Per-User Drill-Down** | Clicking a user in the team list should navigate to detailed view of that missionary's stats, journals, and contacts. Expected pattern in all team management dashboards. | Low | User detail page routing | Link from team table to user-specific view. Reuse existing per-user analytics logic with different scoping. |
| **Export to CSV** | Admins/coaches expect to download reports for offline analysis, sharing with leadership, or importing to other tools. Standard in all 2026 CRM platforms. | Low | Serialization of analytics data | Add CSV export endpoints mirroring existing `/api/v1/imports/export/` pattern. Include filters for date range, users, metrics. |
| **Role-Based Access (Admin Only)** | Team analytics should only be visible to coaches/admins, not individual fundraisers (privacy, focus). Standard permission scoping. | Low | Existing role system (admin, fundraiser, finance, read_only) | Permission checks in views: `if user.role not in ['admin', 'read_only']` deny access. Frontend route guards. |
| **Mobile-Responsive Layout** | Coaches check dashboards on tablets/phones between meetings or while traveling. 2026 expectation for all dashboard tools. | Medium | Responsive grid system (Tailwind CSS exists) | Ensure dashboard components reflow on mobile. Summary cards stack vertically, tables become scrollable/condensed. |

## Differentiators

Features that set product apart. Not expected, but valued. Portfolio-impressive.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|------------------|------------|--------------|-------|
| **Interactive Drill-Down Charts** | Click a funnel stage → see list of contacts in that stage. Click a user in comparison chart → navigate to their detail page. Makes analytics actionable, not just informative. Premium feature in 2026 CRM tools. | High | Chart library event handlers (Recharts supports onClick), dynamic filtering/navigation | Recharts already used for v1.0 journal analytics. Add `onClick` handlers that pass filters to contact list or user detail routes. Excellent portfolio demonstration (shows React state management + UX polish). |
| **Activity Heatmap Calendar View** | Visual representation of team activity density over time (e.g., GitHub-style contribution grid). Coaches instantly see patterns: "Team was active Jan 10-15, then dropped off." Uncommon in nonprofit CRMs, common in dev tools. | High | Per-day activity aggregation across team | Aggregate journal events, contact updates, decision logs by day. D3 or custom calendar grid component. Impressive visually for portfolio. Likely v1.3 candidate if time-constrained. |
| **Comparison Mode (Time Periods)** | Side-by-side comparison: "January vs. February" or "Q1 2025 vs. Q1 2026." Coaches identify seasonal trends or validate if coaching interventions improved metrics. Advanced feature in sales CRMs. | Medium | Dual date range queries, UI toggle for comparison mode | Fetch analytics twice (period A, period B), display side-by-side or overlaid on charts. Trend arrows (↑ 15% from last month). Strong portfolio feature (shows data viz + UX thoughtfulness). |
| **Comparison Mode (Users)** | Side-by-side user comparison: "User A vs. User B" across key metrics. Coaches benchmark performance, identify best practices to share. Less common than time comparison. | Medium | Multi-user filtering, comparison UI | Similar to time comparison but filter by multiple user IDs. Likely defer to v1.3 unless quick win. |
| **AI-Driven Alerts Panel** | Auto-generated recommendations: "Sarah has 8 contacts stalled >21 days," "Team conversion from Meet → Close dropped 10% this month." Proactive coaching prompts. 2026 trend in CRM analytics (82% of nonprofits use AI for insights). | High | Rules engine or lightweight ML for anomaly detection | Phase 1: hardcoded rules (e.g., if stalled_contacts > 5, flag user). Phase 2: detect metric drops >X%. Avoid actual ML for MVP. Portfolio-impressive if labeled "AI-powered insights" even with rule-based logic. |
| **User Drilldown Panel (Slide-In Sidebar)** | Click user row → slide-in drawer shows quick stats, recent journals, stalled contacts without navigating away from team overview. Smooth UX pattern in modern dashboards. | Medium | Radix UI Dialog/Sheet component, user detail API integration | Radix UI already in stack. Fetch user analytics on row click, display in `<Sheet>` overlay. Polished UX for portfolio demonstration. |
| **Trend Charts (Not Just Snapshots)** | Line charts showing team metrics over time (e.g., "Decisions logged per week for past 12 weeks"). Coaches see trajectory, not just current state. Expected in enterprise CRMs, differentiator in nonprofit space. | Medium | Time-series analytics queries (group by week/month) | Extend existing `/insights/` endpoints to return time-series data. Recharts LineChart component. Moderate complexity, high value. |
| **Configurable Alerts/Thresholds** | Coaches set custom thresholds: "Alert me when any missionary has >10 stalled contacts" or "Notify if team conversion <20%." Personalized coaching workflows. Rare in nonprofit CRMs. | High | User preferences model, alert logic, notification system | Likely v2.0 feature. Requires database schema for user alert config, background jobs to check thresholds. Skip for v1.2 unless stretch goal. |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-Time Collaboration (Live Cursors, Shared Editing)** | Scope creep. Coaches don't co-edit dashboards; they review data independently or in scheduled meetings. Adds WebSocket complexity for negligible value. Mentioned in 2026 trends but rarely used in practice for analytics. | Offer export/share functionality instead. Coaches can screenshot, export CSV, or share dashboard URL. Collaboration happens offline (email, Slack, meetings). |
| **Granular Permission System (Column-Level, Row-Level)** | Over-engineering. SPO has 10-20 coaches, not 10,000. Simple role-based access (admin sees all, fundraiser sees own) is sufficient. Row-level security (RLS) adds query complexity and maintenance burden. | Stick to role-based permissions: admins/read_only see team data, fundraisers see only their own. If team scoping needed later (coach sees only their assigned missionaries), add `coach_id` foreign key to User model in v2.0. |
| **Custom Dashboard Builder (Drag-and-Drop Widgets)** | Feature bloat. Coaches want answers to specific questions ("Who needs coaching?"), not to design their own dashboards. This is a power-user feature for enterprise ($$$) tools. | Provide 3-5 opinionated, well-designed dashboard views (Overview, Stalled Contacts, User Detail, Trends). Coaches switch between views via navigation, not widget customization. |
| **Bulk Editing from Dashboard** | Mixing concerns. Dashboards are for visibility and navigation; bulk actions belong in Contact/Journal management pages. Adding "Select All → Reassign Owner" to dashboard complicates UI and increases error risk. | Dashboard links to relevant pages. E.g., "8 stalled contacts" links to Stalled Contacts page with filters pre-applied, where bulk actions exist if needed. |
| **Historical Drill-Down Beyond 12 Months** | Diminishing returns. Fundraising coaching focuses on recent trends (last month, last quarter, YTD). Querying 3+ years of data is slow, rarely actionable. | Default to "Last 12 Months" with option to select custom range up to 24 months. Archive older data or aggregate to yearly summaries. Avoid unbounded date pickers. |
| **Notification Center with Email/SMS Alerts** | Premature. Alert fatigue is real; missionaries already get too many notifications. Building email/SMS infrastructure (Celery tasks, templates, delivery tracking) is significant effort. | In-app alerts panel on dashboard (passive notifications). Coaches check dashboard daily; no need for push notifications. If email alerts needed later (v2.0), use simple Django email backend with daily digest, not per-event spam. |
| **Org Chart Visualization** | Not relevant to coaching workflow. SPO structure is flat (coaches oversee missionaries); no deep hierarchy to visualize. Adds complexity without value. | Simple team list/table suffices. If hierarchy needed, add `reports_to` field to User model in v2.0 and display as nested list, not graph. |
| **Goal Setting & Tracking UI** | Scope creep for v1.2. While valuable (coaches set quarterly targets for missionaries), requires new models (Goal, Milestone), progress calculations, and UI for goal CRUD. Better as v1.3+ feature. | For v1.2, coaches manually assess performance vs. known targets (e.g., "Each missionary should log 10 decisions/month"). If goal tracking added later, integrate with existing Journal/Contact data, not separate system. |

## Feature Dependencies

Understanding how features build on each other to inform phase ordering:

```
Phase Structure (Recommended):

PHASE 1: Foundation - Data Access Layer
├─ Admin analytics endpoints (cross-user queries)
├─ Team activity aggregation service
├─ Stalled contact detection logic
└─ Permission checks (admin-only routes)
    ↓
PHASE 2: Dashboard Core - Overview & Tables
├─ Dashboard Overview page layout (Depends: endpoints from Phase 1)
├─ Summary cards component (Depends: analytics data)
├─ Team activity table (Depends: activity aggregation)
└─ Stalled Contacts page (Depends: stalled contact queries)
    ↓
PHASE 3: Visualizations - Charts & Funnels
├─ Conversion funnel chart (Depends: pipeline data from Phase 1)
├─ Trend line charts (Depends: time-series endpoints)
└─ User comparison bar charts (Depends: per-user metrics)
    ↓
PHASE 4: Interactivity - Drill-Down & Details
├─ Chart click handlers → navigation (Depends: charts from Phase 3)
├─ User Detail page (Depends: per-user endpoints from Phase 1)
├─ User Drilldown panel (slide-in) (Depends: user detail data)
└─ Alerts panel (rule-based) (Depends: analytics thresholds)
    ↓
PHASE 5: Advanced Features - Comparisons & Polish
├─ Time period comparison mode (Depends: analytics endpoints support dual date ranges)
├─ User comparison mode (Depends: multi-user filtering)
├─ Activity heatmap calendar (Depends: per-day activity data)
└─ CSV export (Depends: all analytics endpoints stable)
```

**Critical Path:** Foundation → Overview → Visualizations → Drill-Down. Everything depends on Phase 1 admin analytics endpoints.

**Defer to v1.3+:** Activity heatmap (high complexity, lower priority), configurable alerts (requires new models), user comparison mode (nice-to-have after time comparison proven).

## MVP Recommendation (v1.2 Scope)

For DonorCRM v1.2, prioritize:

### MUST HAVE (Table Stakes)
1. **Dashboard Overview** - Summary cards (total users, total journals, avg conversion rate, stalled contacts count)
2. **Team Activity Table** - Recent updates across all users (sortable, filterable by user/date)
3. **Stalled Contacts Page** - List of contacts with no activity 14+ days, pagination, sorting
4. **Conversion Funnel Chart** - Aggregate pipeline stage distribution with percentages
5. **User Detail Page** - Per-missionary stats, journal list, contact breakdown
6. **Time Period Filtering** - Date range picker for all dashboard views
7. **Role-Based Access** - Admin/read_only only; fundraisers see own data
8. **Export to CSV** - Download team activity, stalled contacts, user metrics

### SHOULD HAVE (Differentiators for Portfolio)
9. **User Drilldown Panel** - Slide-in sidebar from team table row click
10. **Drill-Down Charts** - Click funnel stage → see contacts in that stage
11. **Trend Charts** - Line chart showing "Decisions logged per week" over 12 weeks
12. **Alerts Panel** - Rule-based insights ("5 users have >10 stalled contacts")

### DEFER (Post-MVP)
- **Comparison Mode (Time Periods)** - Strong feature but adds UI complexity; defer to v1.3 if time-constrained
- **Comparison Mode (Users)** - Less valuable than time comparison; v1.3
- **Activity Heatmap** - Visually impressive but non-critical; v1.3
- **Configurable Alerts** - Requires user preferences model; v2.0

## Complexity Assessment

| Feature Category | Overall Complexity | Reasoning |
|------------------|-------------------|-----------|
| **Data Layer (Endpoints)** | **Medium** | Cross-user queries require careful permission scoping. Aggregations (SUM, AVG, GROUP BY) are straightforward in Django ORM. Time-series queries (GROUP BY week) slightly more complex. Existing `/insights/` endpoints provide foundation. |
| **Dashboard UI** | **Low-Medium** | Radix UI + Tailwind CSS provide component primitives. Recharts handles charts. Main challenge is layout responsiveness and state management (date filters, user selection). |
| **Stalled Contacts** | **Low** | Filter by `updated_at` or last event timestamp. Pagination via DRF. Sorting via query params. Standard CRUD patterns. |
| **Drill-Down Interactivity** | **Medium-High** | Requires chart library event handlers (Recharts onClick), React Router navigation with query params, dynamic filtering logic. Good portfolio demonstration but needs careful state management to avoid bugs. |
| **Comparison Modes** | **Medium-High** | Dual queries (fetch data for two periods or two users), UI toggle, side-by-side or overlay visualization. Chart legend/color differentiation. Not trivial but well-documented pattern. |
| **Activity Heatmap** | **High** | Custom D3 component or third-party calendar library. Per-day activity aggregation across team. Tooltip interactions, color scaling. Time-intensive for moderate value. |
| **Alerts Panel** | **Medium** | Rule-based (no ML): threshold checks in Python, return flagged items. UI is simple (list of alerts). Complexity in defining rules that are actually useful (avoid false positives). |

**Overall Complexity for v1.2:** **Medium**. Core dashboard (Overview, Team Table, Stalled Contacts, Funnel, User Detail) is low-medium complexity. Differentiators (Drill-Down, Trends, Alerts Panel, Drilldown Sidebar) add medium complexity but are portfolio-valuable.

## Dependency on Existing Features

| Existing Feature (v1.0-v1.1) | How v1.2 Depends On It |
|------------------------------|------------------------|
| **Journal 6-Stage Pipeline** | Conversion funnel aggregates contacts by stage. Drill-down shows contacts in selected stage. Critical dependency. |
| **Decision Tracking (Dual-Table)** | Trend charts show "Decisions logged over time." User performance metrics include decision counts. Used for conversion rate calculations. |
| **Contact Owner Scoping** | Team activity filters contacts by owner (user). Per-user detail pages show owned contacts. Core to multi-user analytics. |
| **Journal Analytics Endpoints (v1.0)** | Provide foundation for admin analytics. Decision trends, stage activity, pipeline breakdown already implemented per-user; extend to cross-user aggregation. |
| **Task System** | Stalled contacts logic may check "last task created" as activity signal (if no journal updates). Optional dependency. |
| **User Roles (admin, fundraiser, finance, read_only)** | Permission checks rely on existing role system. `admin` and `read_only` roles access team dashboards. No new roles needed. |
| **Insights App (v1.1)** | Contains service functions for analytics (`get_donations_by_month`, `get_follow_ups`, etc.). Admin analytics will extend this pattern with team-scoped functions. |

**Key Insight:** v1.2 builds heavily on v1.0 journal analytics foundation. Minimal new models needed (possibly UserAlert if configurable alerts added later). Primary work is frontend dashboard UI + extending existing analytics service layer to support cross-user queries.

## Domain-Specific Considerations

### Fundraising vs. Sales CRM Differences

| Sales CRM Pattern | Fundraising CRM Adaptation for DonorCRM |
|-------------------|------------------------------------------|
| **Deal velocity** (time to close) | **Relationship velocity** (time from Contact stage → Decision). Missionaries nurture long-term relationships, not transactional sales. |
| **Revenue forecasting** | **Pledge commitment forecasting**. SPO cares about monthly recurring commitments, not one-time deals. Funnel should emphasize pledge conversion, not just donation amounts. |
| **Lead scoring** | **Relationship health scoring**. Factors: recency of contact, stage progression speed, engagement indicators (meetings scheduled, thank-yous sent). Lower priority for v1.2; manual assessment suffices. |
| **Quota attainment** | **Support goal progress**. Missionaries have monthly support targets (e.g., $5K/month in pledges). Dashboard should show % to goal per user. Likely v1.3 feature (requires Goal model). |
| **Commission tracking** | **Not applicable**. Missionaries don't earn commission. Simplifies analytics. |

### SPO-Specific Context

- **Users:** 10-20 coaches, each overseeing 5-15 missionaries (estimate). Total ~100 missionaries.
- **Data scale:** Manageable. Even with 100 users x 100 contacts each = 10K contacts. Queries won't hit performance limits with proper indexing.
- **Workflow:** Coaches meet 1-on-1 with missionaries weekly or biweekly. Dashboard used to prepare for coaching sessions ("Pull up Sarah's stats before our meeting").
- **Pain points (from README research):** Users need actionable prompts, not just data dumps. Stalled contact detection directly addresses this.
- **Portfolio angle:** Demonstrating a coaching-focused admin dashboard (not just reports) shows UX thoughtfulness and understanding of user workflows beyond CRUD apps.

## Testing Considerations

### UAT Scenarios for v1.2

1. **Coach logs in → sees team overview** (verify summary cards aggregate correctly)
2. **Coach filters team activity by date range** (verify filtering works, dates persist in URL)
3. **Coach clicks stalled contacts → sees paginated list** (verify 14-day threshold, sorting by days stalled)
4. **Coach clicks funnel stage → drills down to contacts in that stage** (verify drill-down navigation, contact list matches stage filter)
5. **Coach clicks user row → sees detail page** (verify per-user stats match, journal list displays)
6. **Coach opens user drilldown panel** (verify slide-in sidebar, data loads correctly, close button works)
7. **Coach exports team activity to CSV** (verify file downloads, contains correct columns, respects filters)
8. **Fundraiser attempts to access admin dashboard → denied** (verify 403 response, redirected to own dashboard)
9. **Coach compares "This Month" vs. "Last Month"** (if comparison mode included: verify dual charts, trend indicators)
10. **Coach sees alerts panel → clicks alert → navigates to relevant user/page** (verify rule-based alerts trigger, navigation works)

### Edge Cases

- **Coach with no assigned users:** Should see empty state, not error.
- **User with zero journals:** Detail page should handle gracefully (show "No journals yet" message).
- **Date range with no activity:** Charts should show empty state or zero values, not break.
- **Slow queries (100+ users):** Add loading states, consider pagination for team activity table.

## Sources

### CRM Admin Dashboards & Team Management
- [CRM dashboards in 2026: the essential KPIs and real-world examples](https://monday.com/blog/crm-and-sales/crm-dashboards/)
- [CRM Dashboards in 2026: The Secret Weapon You Can't Ignore](https://www.breakcold.com/blog/crm-dashboard)
- [What Is a CRM Dashboard? KPIs, Examples, and Template | NetSuite](https://www.netsuite.com/portal/resource/articles/crm/crm-dashboard.shtml)
- [Sales Manager Dashboard: The Essential Metrics You Need to Track in 2026](https://www.hyperbound.ai/blog/sales-manager-dashboard)

### Sales Team Coaching & KPIs
- [Essential B2B Sales KPIs & Metrics: Complete Guide for 2026](https://forecastio.ai/blog/sales-kpis)
- [9 Sales KPIs Every Sales Team Should Be Tracking | Salesforce US](https://www.salesforce.com/sales/performance-management/sales-kpis/)
- [30+ Sales KPIs for Sales Team to Track in 2026](https://www.salesmate.io/blog/sales-kpis/)
- [10 must-have sales dashboards to boost performance](https://www.highspot.com/blog/sales-dashboards/)

### CRM Leadership Analytics & Performance Monitoring
- [2026 CRM Trends: Twelve Practical Shifts for Revenue Operations](https://www.siroccogroup.com/2026-crm-trends-twelve-practical-shifts-for-revenue-operations/)
- [Seamless CRM Reporting & Performance Tracking | Nutshell CRM](https://www.nutshell.com/crm/reporting-performance-tracking)
- [Top sales performance management (SPM) software: a 2026 comparison](https://monday.com/blog/crm-and-sales/sales-performance-management-software/)

### Nonprofit Fundraising & Coaching
- [Nonprofit Analytics & Advanced Reporting | Nonprofit KPI Dashboards](https://www.giveffect.com/nonprofit-analytics)
- [Best Nonprofit CRM Software: Top 25 Options for 2026](https://blog.charityengine.net/best-nonprofit-crm)
- [Fundraising Analytics Software: A Nonprofit's Guide | GoodUnited](https://www.goodunited.io/blog/fundraising-analytics-software-guide)

### Stalled Donors & Alert Systems
- [Free Donor Management Software: A CRM Built for Nonprofits | Givebutter](https://givebutter.com/donor-management-crm)
- [10 Best CRMs for Nonprofits in 2026: The Ultimate Buyer's Guide | Neon One](https://neonone.com/resources/blog/crms-for-nonprofits/)
- [21 best nonprofit CRM solutions to manage supporters in 2026](https://bloomerang.com/blog/nonprofit-crm/)

### Funnel Analytics & Drill-Down
- [7 Best SaaS Funnel Analysis Tools in 2026](https://userpilot.com/blog/funnel-analysis-tools/)
- [Conversion Funnel: The Ultimate Guide to Stages & Optimization (2026)](https://improvado.io/blog/conversion-funnel)
- [How to Build, Utilize, and Effectively Interpret Funnel Reports](https://databox.com/funnel-report)

### Team Comparison & Performance Dashboards
- [The Team Comparison Dashboard](https://support.activtrak.com/hc/en-us/articles/360057117952-The-Team-Comparison-Dashboard)
- [Top 10 Employee Performance Dashboard Examples for 2026](https://www.fanruan.com/en/blog/top-10-employee-performance-dashboard-examples)
- [Sales Team Performance Dashboard Examples and Reporting Templates](https://www.coupler.io/dashboard-examples/sales-team-performance-dashboard)

### Time Period Comparison
- [Period-over-period comparisons for time series | Metabase Learn](https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/time-series/time-series-comparisons)
- [Date Comparison | Adobe Analytics](https://experienceleague.adobe.com/en/docs/analytics/analyze/analysis-workspace/components/calendar-date-ranges/time-comparison)
- [How to Compare Periods of Time in Google Analytics 4 (GA4)](https://wholewhale.com/tips/how-to-compare-periods-of-time-in-google-analytics/)

### Sales Activity Tracking & Coaching Opportunities
- [Sales activity tracking: Ultimate guide for sales teams in 2026 — Method](https://www.method.me/blog/sales-activity-tracking/)
- [Sales Activity Management In 2026 For Modern Sales Teams](https://gain.io/blog/sales-activity-management)
- [Sales Performance Monitoring Guide for 2026](https://www.everstage.com/sales-performance/sales-performance-monitoring)

### Data Export & Reporting
- [Export your records](https://knowledge.hubspot.com/import-and-export/export-records)
- [Download CRM Analytics Images and Export Filtered Data](https://help.salesforce.com/s/articleView?id=sf.bi_download.htm&language=en_US&type=5)
- [Export CRM Data](https://help.zoho.com/portal/en/kb/crm/data-administration/export-data/articles/export-crm-data)

### Portfolio Projects & Interactive Dashboards
- [Living Project Portfolio Dashboard: From Status to Decision System](https://www.itonics-innovation.com/blog/project-portfolio-dashboard)
- [Project portfolio dashboard: Examples and tools](https://www.wrike.com/blog/project-portfolio-dashboard/)
- [28 Data Analytics Projects for All Levels in 2026 | DataCamp](https://www.datacamp.com/blog/data-analytics-projects-all-levels)
