---
phase: quick
plan: 5
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/layout/Sidebar.tsx
autonomous: true

must_haves:
  truths:
    - "Analytics tab no longer appears in the left sidebar for any user"
    - "Analytics dashboard remains accessible via Admin page sub-navigation tabs"
    - "Insights dropdown in sidebar still works correctly with its BarChart3 icon"
  artifacts:
    - path: "frontend/src/components/layout/Sidebar.tsx"
      provides: "Sidebar navigation without standalone Analytics entry"
  key_links:
    - from: "AdminUsers.tsx"
      to: "/admin/analytics"
      via: "NavLink in admin sub-navigation"
      pattern: 'to="/admin/analytics"'
---

<objective>
Remove the standalone "Analytics" tab from the left sidebar's bottom navigation section.

Purpose: Analytics (journal analytics) should only be accessible from the Admin page's sub-navigation tabs, not as a separate sidebar item. This reduces sidebar clutter and keeps analytics scoped under the admin section where it belongs.

Output: Updated Sidebar.tsx with the Analytics entry removed from bottomNavItems.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/layout/Sidebar.tsx
@frontend/src/pages/admin/AdminUsers.tsx (has admin sub-nav with Analytics tab - no changes needed)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove Analytics entry from sidebar bottomNavItems</name>
  <files>frontend/src/components/layout/Sidebar.tsx</files>
  <action>
  In `frontend/src/components/layout/Sidebar.tsx`:

  1. Remove the Analytics entry from the `bottomNavItems` array (line 57):
     ```
     { label: "Analytics", href: "/admin/analytics/dashboard", icon: <BarChart3 className="h-5 w-5" />, requiredRole: "admin" },
     ```
     The array should only have Import/Export, Settings, and Admin after this change.

  2. DO NOT remove the `BarChart3` import from lucide-react -- it is still used by the Insights dropdown trigger on line 144.

  That is the only change needed. The admin sub-navigation in AdminUsers.tsx already has an "Analytics" tab linking to `/admin/analytics`, so analytics remains accessible from the admin page.
  </action>
  <verify>
  - `grep -n "Analytics.*bottomNavItems\|Analytics.*admin/analytics/dashboard" frontend/src/components/layout/Sidebar.tsx` returns no matches in the bottomNavItems array
  - `grep "BarChart3" frontend/src/components/layout/Sidebar.tsx` still shows BarChart3 in imports and in the Insights trigger
  - `npx tsc --noEmit` passes with no type errors
  - The bottomNavItems array has exactly 3 entries: Import/Export, Settings, Admin
  </verify>
  <done>The Analytics tab no longer appears in the sidebar bottom navigation. The BarChart3 icon import is preserved for the Insights dropdown. Analytics remains accessible only via Admin > Analytics sub-tab.</done>
</task>

</tasks>

<verification>
- Sidebar renders without the Analytics tab in bottom navigation
- Admin page sub-navigation still shows Users, Imports, Analytics tabs
- Insights dropdown in sidebar still renders correctly with BarChart3 icon
- TypeScript compilation passes
</verification>

<success_criteria>
- bottomNavItems array contains exactly 3 items (Import/Export, Settings, Admin)
- No "Analytics" entry in sidebar bottom nav
- BarChart3 import retained for Insights dropdown
- No TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/5-remove-analytics-tab-from-left-sidebar-a/5-SUMMARY.md`
</output>
