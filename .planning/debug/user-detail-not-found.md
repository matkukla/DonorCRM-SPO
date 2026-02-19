---
status: diagnosed
trigger: "User Detail page shows 'User not found' for a legitimate user ID"
created: 2026-02-14T00:00:00Z
updated: 2026-02-14T00:07:30Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: Type mismatch between URL param (string) and user ID field (number) in filtering logic
test: Examining UserDetail.tsx to see how :id param is extracted and used in filter
expecting: URL param is string, user ID in data is number, strict equality fails
next_action: Read UserDetail.tsx component

## Symptoms

expected: Page loads showing user's name, email, role, and 6 metric cards when navigating to /admin/analytics/users/:id with valid user ID
actual: Page shows "User not found" for legitimate user ID
errors: No error messages reported, displays "User not found" state
reproduction: Navigate to /admin/analytics/users/:id with a valid user ID
started: UAT failure - unclear if ever worked

## Eliminated

## Evidence

- timestamp: 2026-02-14T00:01:00Z
  checked: UserDetail.tsx line 117
  found: `const user = data.users.find((u) => u.id === id)` - strict equality comparison between u.id and id param
  implication: Type mismatch will cause filter to fail if types don't match

- timestamp: 2026-02-14T00:02:00Z
  checked: UserDetail.tsx line 10
  found: `const { id } = useParams<{ id: string }>()` - URL param extracted as string type
  implication: id variable is definitely a string (e.g., "123")

- timestamp: 2026-02-14T00:03:00Z
  checked: insights.ts line 246
  found: `interface UserPerformanceItem { id: string }`
  implication: Backend returns id as string, so u.id is also string type

- timestamp: 2026-02-14T00:04:00Z
  checked: services.py line 512
  found: `'id': str(user.id)` - backend explicitly converts numeric user.id to string
  implication: Backend definitely sends string IDs

- timestamp: 2026-02-14T00:05:00Z
  checked: UserDetail.tsx line 10
  found: `const { id } = useParams<{ id: string }>()` - id typed as string, BUT could be undefined
  implication: If no param in URL, id would be undefined, comparison u.id === undefined always fails

- timestamp: 2026-02-14T00:06:00Z
  checked: Other detail pages (TaskDetail, ContactDetail, DonationDetail, PledgeDetail)
  found: All use `useParams<{ id: string }>()` but pass `id!` to hooks OR use `id ?? ""` for fallback
  implication: They handle potential undefined with non-null assertion or nullish coalescing

- timestamp: 2026-02-14T00:07:00Z
  checked: UserDetail.tsx usage pattern
  found: Does NOT pass id to hook (uses useAdminUserPerformance() with no params), filters client-side at line 117
  implication: No guard against undefined id before using in comparison

## Resolution

root_cause: React Router's useParams<{ id: string }>() runtime returns { id: string | undefined } despite the type assertion. UserDetail.tsx line 117 compares u.id === id without checking if id is defined first. When accessing the page without a valid ID param in the URL, id is undefined, causing u.id === undefined to always be false. This results in "User not found" even when the users array contains valid data. Other detail pages avoid this by using id! or id ?? "" when passing to hooks, but UserDetail uses id directly in a comparison without any guard.
fix: Add undefined check before filtering: `if (!id) { return <ErrorState /> }` OR use safe comparison: `u.id === (id ?? "")`
verification: Test with valid URL param to confirm strings match
files_changed: [frontend/src/pages/admin/analytics/UserDetail.tsx]
