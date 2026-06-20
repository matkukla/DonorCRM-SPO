# 1. A supervisor's dashboard scope equals their View-As assignment boundary

Date: 2026-06-19

## Status

Accepted

## Context

The dashboard target-user resolver (`_resolve_target_user` in
`apps/dashboard/views.py`) lets a requester pull another user's dashboard via
`?user_id=`. As written, it grants **admin and supervisor** the right to select
*any* active user, and it performs the existence lookup before any permission
check (a non-existent id returns 404, a real-but-forbidden id would otherwise
return data).

Separately, the View-As middleware (`apps/core/middleware.py`) already enforces a
narrower rule for supervisors: a supervisor may impersonate only a **missionary
assigned to them**, tested by `viewer.supervised_users.filter(pk=target.pk).exists()`,
and never another supervisor.

This left two doors to the same room with different locks: View-As restricted a
supervisor to assigned missionaries, but the dashboard `?user_id=` selector let
the same supervisor read *anyone's* dashboard. A supervisor could therefore see a
non-assigned missionary's — or another supervisor's — dashboard, bypassing the
assignment boundary the org relies on.

## Decision

A supervisor's dashboard scope is **identical to their View-As boundary**: they may
view the dashboard only of missionaries assigned to them (the same
`supervised_users` set), and nothing else. Specifically:

- **Admin** may select any active user (unchanged).
- **Supervisor** may select only their assigned missionaries; any other id —
  unassigned missionary, another supervisor, or non-existent — returns **403**.
- **All other roles** are limited to their `get_visible_user_ids()` set (unchanged).
- The permission check runs **before** the existence lookup, so a forbidden or
  non-existent id is indistinguishable (both 403) — no user enumeration.
- The same rule applies to every surface that resolves a target user, including the
  per-user dashboard-layout endpoint.

## Consequences

- The dashboard selector and the View-As middleware now enforce one boundary, so a
  supervisor cannot use one path to escape the other.
- The two code paths must stay in sync. The assignment predicate
  (`supervised_users`) is the single source of truth; both call sites reference it.
- Bad-id responses change from 404 to 403 for supervisors, removing an enumeration
  signal but altering an observable status code — a behavior change to test for.
- This is a security boundary: a regression silently re-opens cross-supervisor and
  cross-missionary dashboard access, so it is covered by an API test that fails when
  the guard is reverted (per the project's #1 test rule).

## Alternatives considered

- **Trust supervisors org-wide (keep current behavior).** Rejected: SPO supervisors
  oversee an assigned team, not the whole org; org-wide visibility is a back door,
  not a feature.
- **Let a supervisor also see peer supervisors' teams.** Rejected: no SPO hierarchy
  requires it, and it would widen the blast radius of a compromised supervisor account.
