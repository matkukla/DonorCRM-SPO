# DonorCRM Edge Case Audit

**Date:** 2026-02-11
**Scope:** Full-stack audit — backend models/views/serializers/signals, frontend API client/pages/components
**Scale assumption:** 200 missionaries, 50k+ contacts, years of donation history

---

## 1. JOURNAL SYSTEM

### 1.1 N+1 Query Storm in Journal Grid (CRITICAL)

**File:** [serializers.py:101-140](apps/journals/serializers.py#L101-L140)

**Scenario:** Loading the journal grid with 50 contacts.

**What happens:** `get_stage_events()` runs per JournalContact:
- 1 aggregate query (line 110: `.values('stage').annotate(...)`)
- Up to 6 more queries (line 130: `.filter(stage=stage).order_by('-created_at').first()` per stage with events)

For 50 contacts: **up to 351 queries per page load.** Plus `get_decision()` (line 142) adds another query per contact (line 147: `obj.decisions.first()`) with no `prefetch_related`.

**What should happen:** Prefetch stage events and decisions in the view's `get_queryset()`, aggregate in Python.

**Risk at scale:** HIGH — page load time degrades linearly with contacts. At 100 contacts, expect 700+ queries and multi-second responses.

**Fix:** Add `prefetch_related('stage_events', 'decisions')` to `JournalContactListCreateView.get_queryset()`, rewrite `get_stage_events()` to use prefetched data.

---

### 1.2 Decision Update Race Condition (HIGH)

**File:** [serializers.py:295-332](apps/journals/serializers.py#L295-L332)

**Scenario:** Two admins update the same decision simultaneously (e.g., both change amount from $100 to different values).

**What happens:** Both read `getattr(instance, field)` at line 308 and see `$100`. Both create history records saying "changed from $100." Both write their new values. Last write wins — one update is silently lost, and the history shows two changes from the same value.

**What should happen:** `select_for_update()` on the instance inside `transaction.atomic()` to serialize concurrent writes.

**Risk at scale:** MEDIUM — unlikely for single-user journals, but possible with admin access or rapid double-clicks.

**Fix:** Add `instance = Decision.objects.select_for_update().get(pk=instance.pk)` inside the `transaction.atomic()` block at line 303.

---

### 1.3 Cross-User Contact Access in Stage Events (CRITICAL)

**File:** [serializers.py:218-234](apps/journals/serializers.py#L218-L234)

**Scenario:** Fundraiser A creates a stage event passing `contact_id` of a contact owned by Fundraiser B.

**What happens:** Line 221 does `Contact.objects.get(id=contact_id)` with **no owner filter**. The contact is linked to Fundraiser A's journal, and the stage event is created. Fundraiser A now has Fundraiser B's contact data in their journal.

**What should happen:** Filter by `owner=user` or check permission before linking.

**Risk at scale:** HIGH — any authenticated user can reference any contact UUID. UUIDs are not secret if exposed in API responses.

**Fix:** Change line 221 to `Contact.objects.get(id=contact_id, owner=user)`.

---

### 1.4 Analytics Endpoints Return Unbounded Data (MODERATE)

**File:** [views.py:427-530](apps/journals/views.py#L427-L530)

**Scenario:** User with years of journal history requests analytics.

**What happens:** `decision_trends()`, `stage_activity()`, and `pipeline_breakdown()` return full result sets with no pagination or date windowing. `next_steps_queue()` has a `[:20]` slice, but the others don't.

**Risk at scale:** LOW to MEDIUM — grows slowly, but after 3+ years of data, response sizes could be significant.

**Fix:** Add default date range filtering (e.g., last 12 months) to analytics endpoints.

---

### 1.5 `is_staff` vs `role` Inconsistency (MODERATE)

**File:** [views.py:536](apps/journals/views.py#L536)

**Scenario:** Admin user has `role='admin'` but `is_staff=False` (or vice versa).

**What happens:** `admin_summary` checks `request.user.is_staff` while every other admin check in the codebase uses `request.user.role == 'admin'`. A user could pass one check but fail the other.

**Fix:** Change to `request.user.role == 'admin'` for consistency.

---

## 2. CONTACT SYSTEM

### 2.1 Race Condition in update_giving_stats() (CRITICAL)

**File:** [models.py:152-181](apps/contacts/models.py#L152-L181)

**Scenario:** Bulk CSV import creates 50 donations for the same contact. Each `Donation.objects.create()` triggers the `post_save` signal, which calls `update_giving_stats()`.

**What happens:** Multiple signal handlers run concurrently (or in rapid sequence). Each:
1. Reads aggregate stats (lines 158-163)
2. Sets fields on `self` (lines 165-176)
3. Saves (lines 178-181)

The signal handler (signals.py:17-22) also does a **second save** immediately after (`needs_thank_you = True`, `contact.save()`). This second save can overwrite the first call's stat updates since it doesn't use `update_fields` that include the stat fields.

**What should happen:** Either use `F()` expressions for atomic updates, or wrap in `select_for_update()`, or disable signals during bulk import and call `update_giving_stats()` once at the end.

**Risk at scale:** HIGH during imports. Low during normal one-at-a-time donation entry.

**Fix (minimal):** In the import service, disable signals and call `update_giving_stats()` once per affected contact after import completes. (The SPO import in `apps/imports/services.py` already has a `update_contact_stats_for_import()` function that does this for transactions — verify it's called and that the signal path is safe for single donations.)

---

### 2.2 ListAPIView Bypasses Object-Level Permissions (HIGH)

**File:** [views.py:139-171](apps/contacts/views.py#L139-L171)

**Scenario:** Fundraiser A calls `GET /api/v1/contacts/{B's_contact_uuid}/donations/`.

**What happens:** `ContactDonationsView` and `ContactPledgesView` use `IsContactOwnerOrReadAccess`, but this permission class only implements `has_object_permission()` — which DRF only calls via `get_object()`. Since `ListAPIView` never calls `get_object()`, the permission is **never evaluated**. The queryset (line 149) filters only by `contact_id` with no owner check.

**Result:** Any authenticated user can view any contact's donations and pledges by UUID.

**What should happen:** Filter queryset by `contact__owner=request.user` (or allow admin/finance roles to see all).

**Risk at scale:** HIGH — data leak across missionaries. UUID enumeration is the only barrier.

**Fix:** Override `get_queryset()` to include owner filtering, or implement `has_permission()` in the permission class to check the contact's owner from the URL kwargs.

---

### 2.3 ContactEmailsView Loads All Emails Into Memory (LOW)

**File:** [views.py:200-218](apps/contacts/views.py#L200-L218)

**Scenario:** Organization with 30k contacts, admin requests all emails.

**What happens:** Line 213 calls `list(queryset.values_list(...))` — materializes entire result set.

**Risk at scale:** LOW — only admins use this, and email strings are small.

**Fix:** Add pagination if this endpoint will be used by non-admin roles.

---

## 3. DONATIONS & PLEDGES

### 3.1 Float Arithmetic for Money (MODERATE)

**File:** [pledges/models.py:137-146](apps/pledges/models.py#L137-L146)

**Scenario:** Pledge amount is `$333.33` monthly. Calculate annual equivalent.

**What happens:** `float(self.amount) * multipliers.get(...)` uses float division (`1/3`, `1/12`). This introduces floating-point errors: `$333.33 * 12 / 3` might produce `$1333.3199999...` instead of `$1333.32`.

Compare with `Decision.monthly_equivalent` in journals/models.py:281-291, which correctly uses `Decimal`.

**Used in:**
- `PledgeSummaryView` (pledges/views.py:202)
- `get_support_progress()` (dashboard/services.py:147)
- `get_giving_summary()` (dashboard/services.py:226)

**Risk at scale:** MEDIUM — penny discrepancies in dashboard totals. Not a data integrity issue (stored values are fine), but displayed totals may be slightly wrong.

**Fix:** Replace `float(self.amount) * multipliers.get(...)` with `Decimal(str(self.amount)) * Decimal(str(multipliers.get(...)))`.

---

### 3.2 record_fulfillment() Uses += Without Locking (HIGH)

**File:** [pledges/models.py:191-198](apps/pledges/models.py#L191-L198)

**Scenario:** Two donations linked to the same pledge arrive in quick succession.

**What happens:** Line 194: `self.total_received += donation.amount` is a read-modify-write. Both signal handlers read the same `total_received`, both add their donation amount, and the second save overwrites the first. Result: one donation's amount is lost from `total_received`.

**Fix:** Use `Pledge.objects.filter(pk=self.pk).update(total_received=F('total_received') + donation.amount)` then `self.refresh_from_db()`.

---

### 3.3 Stats Not Updated on Donation Edit (MODERATE)

**File:** [signals.py:13](apps/donations/signals.py#L13)

**Scenario:** Finance user edits a $500 donation to $50 (correcting a typo).

**What happens:** Line 13: `if not created: return` — signal short-circuits. Contact stats (`total_given`, `last_gift_amount`) remain stale until a new donation is created.

**Risk at scale:** MEDIUM — finance corrections are normal operations. Users will see incorrect totals.

**Fix:** Remove the `if not created: return` guard, or add a separate `update_giving_stats()` call for updates.

---

### 3.4 Unvalidated int() Cast on Query Params (MODERATE)

**File:** [donations/views.py:167](apps/donations/views.py#L167), [dashboard/views.py:96,155,211](apps/dashboard/views.py)

**Scenario:** Client sends `?days=abc`.

**What happens:** `int(request.query_params.get('days', 30))` raises `ValueError` → unhandled → 500 error.

**Fix:** Wrap in try/except with default fallback: `try: days = int(...) except ValueError: days = 30`.

---

### 3.5 No Maximum Amount Validation on API (LOW)

**File:** [donations/serializers.py:41-66](apps/donations/serializers.py#L41-L66)

**Scenario:** User submits donation of `$99,999,999.99` via API.

**What happens:** The import service validates max `$9,999,999.99`, but the API serializer has no max. The model field uses `max_digits=12, decimal_places=2`, so up to `$9,999,999,999.99` is technically possible.

**Risk:** LOW — requires intentional misuse, easily caught in review.

---

### 3.6 Missing select_related on LatePledgesView (LOW)

**File:** pledges/views.py:163-175

**What happens:** Serializer accesses `contact.full_name` without `select_related('contact')` — N+1 query.

**Fix:** Add `.select_related('contact')` to the queryset.

---

## 4. AUTH & PERMISSIONS

### 4.1 IsContactOwnerOrReadAccess Never Fires on List Views (HIGH)

**File:** [permissions.py:65-98](apps/core/permissions.py#L65-L98)

This is the root cause of issue 2.2. The permission class only implements `has_object_permission()`, not `has_permission()`. DRF's `ListAPIView` never calls `get_object()`, so object-level permissions are never checked.

**Affected views:**
- `ContactDonationsView` (contacts/views.py:143)
- `ContactPledgesView` (contacts/views.py:161)
- `ContactJournalEventsView` (contacts/views.py:296)

**Fix:** Either add `has_permission()` that checks the contact from URL kwargs, or add owner filtering to each view's `get_queryset()`.

---

### 4.2 Inconsistent Role Access Patterns (MODERATE)

| Resource | Who sees all? | Check method |
|----------|--------------|--------------|
| Contacts | admin, finance, read_only | queryset filter |
| Donations | admin, finance, read_only | queryset filter |
| Journals | admin only | queryset filter |
| Journal admin_summary | `is_staff` | `request.user.is_staff` |
| Contact journal events | admin only | `request.user.role == 'admin'` |

Whether `finance` and `read_only` should see cross-user journal data is a business decision, but the inconsistency suggests this wasn't deliberately designed.

---

## 5. DASHBOARD

### 5.1 Side Effect on GET Request (MODERATE)

**File:** [dashboard/views.py:36](apps/dashboard/views.py#L36)

**Scenario:** Frontend polls dashboard, or user refreshes page.

**What happens:** `mark_events_as_not_new(user)` runs on every GET. Events are marked as "seen" before the user actually reads them. If the request fails after marking, events are lost as "new."

**Fix:** Move to a separate POST endpoint (e.g., `POST /api/v1/dashboard/mark-read/`).

---

### 5.2 Dashboard Makes 10+ Redundant Queries (MODERATE)

**File:** [dashboard/services.py:294-353](apps/dashboard/services.py#L294-L353)

`get_dashboard_summary()` calls 7+ service functions, each building independent querysets. The Pledge table is queried at least 3 times. The Contact table at least twice.

**Risk at scale:** MEDIUM — adds ~200ms latency per dashboard load at 200 users.

**Fix:** Share base querysets across service functions, or use a single aggregated query.

---

## 6. IMPORT SYSTEM

### 6.1 Entire CSV Loaded Into Memory (HIGH)

**File:** [imports/views.py:78,159,315,405,499,616](apps/imports/views.py)

**Scenario:** Admin uploads a 50MB CSV file.

**What happens:** `file.read().decode('utf-8')` at every import view loads the entire file into a Python string. Then `io.StringIO()` creates a second copy. No `FILE_UPLOAD_MAX_MEMORY_SIZE` configured.

**Risk at scale:** HIGH — a single large upload could exhaust server memory on Render's free tier (512MB).

**Fix:** Add `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10MB) to settings. Add explicit file size check before `file.read()`.

---

### 6.2 Async Bulk Import Skips All Signals (HIGH)

**File:** [imports/tasks.py:209](apps/imports/tasks.py#L209)

**Scenario:** Async donation import uses `bulk_create()`.

**What happens:** `post_save` signals don't fire for `bulk_create()`. Contact stats (`total_given`, etc.), `needs_thank_you`, pledge `record_fulfillment()`, and Event creation are all skipped.

**Result:** After an async import, all contact giving stats are stale, no thank-you reminders appear, pledge fulfillment isn't tracked, and no events are logged.

**Note:** Celery is currently disabled in production, so this is dormant. But it will break when re-enabled.

**Fix:** After `bulk_create()`, manually call `update_giving_stats()` for all affected contacts (similar to the SPO import pattern).

---

### 6.3 CSV Export Doesn't Sanitize Output (LOW)

**File:** imports/services.py:364-438

**Scenario:** A contact's name is `=CMD("calc")`.

**What happens:** Import validates against formula characters, but export does not sanitize. Opening the exported CSV in Excel could trigger CSV injection.

**Fix:** Prefix cell values starting with `=`, `+`, `-`, `@` with a single quote in export functions.

---

## 7. FRONTEND

### 7.1 Multi-Tab Token Refresh Race (MODERATE)

**File:** [client.ts:55-124](frontend/src/api/client.ts#L55-L124)

**Scenario:** User has two tabs open. Access token expires. Both tabs send a request simultaneously.

**What happens:** `isRefreshing` is per-page state. Both tabs independently try to refresh. Tab A succeeds and gets new access token. Tab B sends the same refresh token — which may have been rotated/blacklisted — and gets a 401. Tab B redirects to login.

**Risk at scale:** MEDIUM — common user behavior, jarring UX.

**Fix:** Use a BroadcastChannel or localStorage event to coordinate refresh across tabs.

---

### 7.2 No Frontend Route Guards for Roles (HIGH)

**Scenario:** `read_only` user navigates directly to `/contacts/new` or `/admin/imports`.

**What happens:** The page renders. The user fills out the form. They submit. The backend rejects it with 403. The user sees an error toast (if error handling exists) or a silent failure.

**What should happen:** Routes should check the user's role and redirect or show "not authorized" before rendering forms.

**Risk at scale:** HIGH — confusing UX. Users waste time filling forms they can't submit.

**Fix:** Add role-based route guards that check `user.role` before rendering protected routes.

---

### 7.3 No Error Boundary (MODERATE)

**Scenario:** Any unhandled React error (null reference, failed render).

**What happens:** Entire app crashes to white screen. No recovery except browser refresh.

**Fix:** Add a React Error Boundary at the app root with a user-friendly fallback UI.

---

### 7.4 Double-Submit on Mutations (MODERATE)

**Scenario:** User double-clicks "Create Journal" or "Log Stage Event" on slow connection.

**What happens:** If mutation buttons don't check `isPending` state from React Query, two requests fire. Two journals/events are created.

**Risk:** Depends on which mutations have `disabled={isPending}` — needs per-component audit. The `ImportDialog` has good loading state management (useReducer state machine), but simpler forms may not.

**Fix:** Ensure all mutation triggers check `isPending` and disable the button during requests.

---

## TOP 10 RISK LIST

Ranked by (likelihood at 200 users) x (impact):

| Rank | Issue | Likelihood | Impact | Category |
|------|-------|-----------|--------|----------|
| 1 | **Journal grid N+1 queries** (1.1) | Every page load | Slow UI, potential timeout | Performance |
| 2 | **ListAPIView permission bypass** (2.2/4.1) | Any curious user | Cross-user data exposure | Security |
| 3 | **Cross-user contact in stage events** (1.3) | Malicious or confused user | Data leak, wrong journal entries | Security |
| 4 | **update_giving_stats() race** (2.1) | Every bulk import | Incorrect donation totals | Data Integrity |
| 5 | **record_fulfillment() race** (3.2) | Concurrent donations | Lost pledge tracking | Data Integrity |
| 6 | **No CSV file size limit** (6.1) | One large upload | Server OOM crash | Availability |
| 7 | **Missing frontend route guards** (7.2) | read_only users daily | Confusing UX, wasted time | UX |
| 8 | **Stats not updated on edit** (3.3) | Finance corrections | Stale totals until next donation | Data Integrity |
| 9 | **Float money arithmetic** (3.1) | Every dashboard load | Penny discrepancies in totals | Data Integrity |
| 10 | **Dashboard GET side effect** (5.1) | Every dashboard view | Events marked read prematurely | UX |

---

## FIX ORDER PLAN

### Wave 1: Security (fix immediately)

1. **Add owner filter to ContactDonationsView and ContactPledgesView** — change `get_queryset()` to filter by `contact__owner=request.user` for non-admin roles. (~10 lines)

2. **Add owner check to stage event contact_id path** — change line 221 in serializers.py to `Contact.objects.get(id=contact_id, owner=user)`. (1 line)

3. **Fix `is_staff` vs `role` inconsistency** — change views.py:536 to `request.user.role == 'admin'`. (1 line)

### Wave 2: Performance (fix before 200 users)

4. **Fix journal grid N+1** — add `prefetch_related('stage_events', 'decisions')` to view queryset, rewrite `get_stage_events()` and `get_decision()` to use prefetched data. (~40 lines)

5. **Add CSV file size limit** — add `DATA_UPLOAD_MAX_MEMORY_SIZE` to settings, add explicit size check in import views. (~5 lines)

6. **Fix dashboard redundant queries** — share base querysets in `get_dashboard_summary()`. (~20 lines)

### Wave 3: Data Integrity (fix before production data)

7. **Fix record_fulfillment() to use F()** — replace `self.total_received += donation.amount` with `F()` expression. (~5 lines)

8. **Fix float money to Decimal** — replace `float(self.amount)` with `Decimal` in `monthly_equivalent`. (~5 lines)

9. **Handle donation edit stat updates** — remove `if not created: return` guard in signal, or add explicit stat refresh. (~3 lines)

10. **Fix unvalidated int() casts** — wrap in try/except across views. (~10 lines)

### Wave 4: UX & Resilience (fix before user rollout)

11. **Add frontend route guards** — role-based redirect in router config. (~20 lines)

12. **Add React Error Boundary** — wrap app root with fallback UI. (~15 lines)

13. **Move dashboard mark-read to POST** — separate endpoint for side effect. (~10 lines)

14. **Add double-submit protection** — audit all mutation buttons for `isPending` check. (~varies)

### Wave 5: Future-Proofing (fix before re-enabling Celery)

15. **Fix async import signal skip** — add manual stat updates after `bulk_create()`. (~15 lines)

16. **Add CSV export sanitization** — prefix formula characters in export. (~10 lines)

---

## SCALABILITY RISKS AT 200+ MISSIONARIES

| Risk | Trigger Point | Mitigation |
|------|--------------|------------|
| Journal grid N+1 | 50+ contacts per journal | Prefetch + annotate (Wave 2) |
| Dashboard query count | 200 concurrent users | Cache dashboard with 30s TTL, or share querysets |
| Pledge summary loads all into Python | 1000+ active pledges | SQL aggregation with CASE/WHEN |
| Import memory usage | 10k+ row CSV | Streaming parser or file size cap |
| Contact stat races | Bulk operations | Disable signals during bulk, update once at end |
| Single Render free-tier instance | 50+ concurrent requests | Scale to starter plan, add connection pooling |

---

*End of audit. No changes were made to any files.*
