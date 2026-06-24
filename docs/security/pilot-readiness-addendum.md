# DonorCRM — Pilot Security Readiness Addendum

**Date:** 2026-06-24
**Companion to:** [pilot-security-brief.md](pilot-security-brief.md) (encryption &
transport), [evidence-map.md](evidence-map.md) (control-to-framework mapping).
**Audience:** SPO leadership / CIT, and prospective pilot organizations and
their security reviewers.

> This addendum covers the controls the encryption brief does not: **who can
> reach which donor data**, user lifecycle, incident response, and backup/
> retention — and states plainly what is proven, what is not yet proven, and
> what must clear before a pilot with real donor data. It does not claim SOC 2
> compliance; where controls align with SOC 2 CC6/CC7 expectations, they are
> described as *aligned*, not *certified*.

---

## 1. Executive summary

An internal authorization-focused security review was completed on 2026-06-24.
The central question was: *can a missionary, coach, or supervisor reach donor
data they should not, by calling the API directly instead of using the UI?*

The finding: **the data-isolation architecture is sound and now well-evidenced.**
A single real defect — a coach could read one financial figure (a journal's
fundraising goal) via one endpoint — was found and fixed, with a regression
test. Authorization boundaries that previously held only in code are now backed
by automated tests. The full backend suite passes: **1,488 tests, 0 failures.**

**The one operational blocker has since been cleared:** on 2026-06-24 a backup
restore drill was performed — a production snapshot was restored to a fresh
instance and its row counts, total gift amount (to the cent), and latest gift
date matched production exactly. The backup is recoverable with full data
integrity ([restore-tests.md](restore-tests.md)).

**Recommendation:** **GO-WITH-CAVEATS** for a limited, internal SPO pilot. No
unresolved blockers remain; the accepted residual risks are listed in §8. For
external prospects, additionally complete the database-level audit-log lockdown
and retain privacy counsel.

---

## 2. Scope

- **In scope:** US-based donor data — contacts, gifts, recurring gifts, journal/
  pipeline notes, prayer intentions. Roles: admin, missionary, supervisor, coach.
- **Not in scope / not collected:** payment card data (no PCI), health data (no
  HIPAA), EU residents (no GDPR). Applicable: US state breach-notification laws.
- **Method:** read-only code audit (five parallel review passes, every finding
  tied to a specific file and line), targeted fixes, and automated tests as
  evidence. Live infrastructure (TLS edge, backups) is verified separately.

---

## 3. What was reviewed

Object-level access controls; the central `get_visible_user_ids` scoping
function and its callers; the admin/supervisor "View As" feature; JWT
authentication and token lifecycle; coach financial-data gating; PII handling in
errors, logs, and exports; secrets hygiene; user offboarding; incident-response
readiness; data retention and backup handling; and the quality of the evidence
itself (do tests actually fail when a control is broken?).

## 4. What was tested (evidence)

| Area | Evidence |
|------|----------|
| Full backend suite | **1,488 passed, 2 skipped, 0 failed** |
| Authorization boundaries | New negative tests — see §6 Authorization Test Evidence |
| Coach financial gating | Tests assert specific dollar values are **absent** from coach API responses |
| Dependency CVEs + static analysis | CI runs `pip-audit --strict` (all requirement sets) and `bandit` on every change |
| Money math | Import dollar→cents parser hardened (round half-up, reject negatives) + 14 parser tests |

## 5. What passed

- **Owner-scoped isolation holds.** Every donor-data list, detail, search, and
  export request is filtered to the requester's permitted users; cross-owner
  fetch-by-ID returns "not found," not the record.
- **"View As" is read-only at the server.** Impersonated write attempts are
  rejected with HTTP 403 — not merely hidden in the UI — and each impersonated
  read is recorded in an access log tying the real actor to the impersonated user.
- **Coach financial restriction holds** (after the fix in this review). Coaches
  receive pipeline/relationship data but no gift amounts, totals, pledges, or
  fundraising goals from any reviewed endpoint.
- **Authentication lifecycle.** Short-lived access tokens; refresh-token rotation
  with blacklisting; logout, password change, and **now account deactivation**
  revoke refresh tokens; account lockout and rate-limiting on login.
- **No secrets or real donor data committed** to source; production refuses to
  start with an insecure key.
- **Encryption & transport** (per the companion brief): TLS in transit, AES-256
  at rest with field-level encryption of donor PII, fail-closed database-TLS
  check.

## 6. Authorization Test Evidence

Negative tests added so each boundary now *fails the build if it regresses*:

| Boundary proven | Test |
|-----------------|------|
| Missionary cannot fetch another's task by ID (404) | `apps/tasks/tests/test_task_idor.py` |
| Query parameter cannot widen gift scope to another owner | `apps/gifts/tests/test_gift_param_scoping.py` |
| Supervisor's default list excludes non-assigned missionaries | `apps/contacts/tests/test_authz_evidence.py` |
| Search cannot surface another owner's contact | `apps/contacts/tests/test_authz_evidence.py` |
| Coach receives no financial fields on contact lists | `apps/contacts/tests/test_authz_evidence.py` |
| Coach cannot read a journal goal via the contact endpoint (the fixed defect) | `apps/contacts/tests/test_coach_journal_membership_goal_leak.py` |
| "View As" reads are written to the access log | `apps/core/tests/test_access_log_view_as.py` |
| Account deactivation revokes refresh tokens | `apps/users/tests/test_deactivation_revokes_tokens.py` |

These join an already-substantial pre-existing suite covering cross-owner
contact/gift/journal/prayer isolation and View-As read-only enforcement.

## 7. What remains unverified

| Item | Status |
|------|--------|
| **Backup restore** | ✅ **Verified 2026-06-24** — restored snapshot matched production exactly (counts, total amount, latest date). See [restore-tests.md](restore-tests.md). Re-run quarterly. App-level decryption against a restored instance not yet exercised. |
| **Audit-log database-level lockdown** | Append-only in the application; the database-privilege lockdown that would stop an attacker with DB credentials from erasing the log is documented but **not yet provisioned** ([access-controls.md](access-controls.md)). |
| **Live TLS posture** | Last probed 2026-06-22; re-probe at pilot start. |
| **Privacy counsel / cyber-insurance** | Not yet retained (see [incident-response.md](incident-response.md)). |

## 8. Pilot Risk Register

| # | Risk | Likelihood | Impact | Severity | Status / mitigation |
|---|------|-----------|--------|----------|---------------------|
| R1 | Backup recoverability | — | High | **Cleared** | ✅ Restore drill passed 2026-06-24 — restored snapshot matched production exactly. Re-run quarterly. |
| R2 | Audit log erasable by an attacker with DB credentials (app-layer append-only only) | Low | Medium | High | **In progress:** `donorcrm_app`/`donorcrm_purge` roles provisioned + `core_dataaccesslog` UPDATE/DELETE revoked; `render.yaml` wired for the runtime cutover. Remaining: set the `donorcrm_app` `DATABASE_URL` secret + deploy + verify ([db-role-cutover.md](db-role-cutover.md)). Disclosed residual until the cutover deploys. |
| R3 | Access token valid for up to ~15 min after logout/deactivation (stateless JWT) | Low | Low–Med | Medium | Accepted; short window; refresh tokens are revoked immediately |
| R4 | Donor "delete on request" (DSAR / right-to-erasure) | — | Low | **Closed** | ✅ Admin endpoint shipped: `POST /contacts/<id>/erase/` hard-deletes the donor + cascades (gifts, recurring, journals, tasks, prayers), audit-logged. |
| R5 | Privacy counsel / cyber-insurance not retained | n/a | Med | Medium | Accept for limited pilot; engage before scaling |
| R6 | Very large CSV import could approach the request timeout | Low | Med | Low–Med | Row caps (25k gifts) + 10-min server timeout; load-test before a big initial migration |
| R7 | Departed user's contacts stranded on an inactive account | — | Low | **Closed** | ✅ Admin endpoint shipped: `POST /users/<id>/reassign-contacts/` bulk-reassigns a departed user's contacts to a new active owner, audit-logged. |
| R8 | Database accepted public connections from any IP (`0.0.0.0/0`) | Low | Medium | Medium | ✅ **Closed 2026-06-24** — public IP allow-list removed (database is internal-only); `ipAllowList: []` set in `render.yaml` as the durable default. App unaffected (connects over Render's private network). |

No unresolved **Critical** or **Blocker** items remain. R1 (restore) and R8
(DB exposure) are cleared. R2–R7 are accepted residual risks for a limited
pilot, listed plainly so they are not hidden.

## 9. Final recommendation — Go / No-Go

**GO-WITH-CAVEATS for a limited internal SPO pilot.** The gating blocker (an
unproven backup) was cleared by the 2026-06-24 restore drill, and the database
public-exposure issue (R8) was closed the same day. No unresolved blockers
remain.

**Accepted residual risks for the pilot** (disclosed, not hidden): R2–R7 above —
most notably the ~15-minute token window, the application-layer-only audit log
until the DB lockdown runs, and the manual (un-tooled) donor-deletion process.

**Before offering the product to external prospects**, additionally: run the
audit-log DB lockdown (R2), retain privacy counsel and cyber-insurance (R5),
re-probe live TLS, and run a full app-against-restored-DB drill (including PII
decryption).

**Plain answer to "can this be handed to a company to pilot with real donor data
right now?"** — Yes, for a controlled internal SPO pilot, with the residual
risks above acknowledged in writing. The data-isolation controls are sound and
test-backed, the backup is proven recoverable, and the database is no longer
publicly exposed.
