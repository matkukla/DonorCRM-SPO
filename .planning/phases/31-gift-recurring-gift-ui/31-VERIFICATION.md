---
phase: 31-gift-recurring-gift-ui
verified: 2026-02-23T18:15:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/12
  gaps_closed:
    - "GiftSerializer.fields raised AssertionError — fix confirmed in commit 40e5a4f; now binds 12 fields cleanly"
    - "GiftCreditReadSerializer.fields raised AssertionError — same fix; now binds 5 fields cleanly"
    - "RecurringGiftSerializer.fields raised AssertionError — same fix; now binds 16 fields cleanly"
    - "All Gift/RecurringGift API endpoints unblocked; all 5 previously-BLOCKED requirements now SATISFIED"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Navigate to /donations in the running app and check if the list loads data"
    expected: "Table loads with Donor Name, Amount, Date, Fund, Description columns; clicking a row opens slide-in panel"
    why_human: "Requires live server with DB data; serializer fix confirmed programmatically but real request-response cycle needs human confirmation"
  - test: "Open a donation that has GiftCredit records assigned"
    expected: "Solicitor Credits section visible in slide-in panel with Solicitor Name, Amount, Percentage columns; section hidden for donations with no credits"
    why_human: "Requires specific test data with GiftCredit records; section conditional on credits.length > 0"
  - test: "Navigate to /pledges and open the filter dropdowns"
    expected: "Status has 5 options (Active, Held, Completed, Cancelled, Terminated); Frequency has 8 options including Weekly, Monthly, Quarterly, Annual"
    why_human: "Visual verification in running app; dropdown options rendered client-side"
  - test: "Navigate to the Dashboard and check the NeedsAttention card"
    expected: "Amber-colored card always visible with text 'Late detection coming soon'"
    why_human: "Visual rendering (color, layout) and exact text placement require running app"
---

# Phase 31: Gift/RecurringGift UI Verification Report

**Phase Goal:** Frontend pages, filters, detail views, and exports work against the Gift/RecurringGift models while keeping all visible text as "Donations" and "Pledges"
**Verified:** 2026-02-23T18:15:00Z
**Status:** human_needed — all automated checks pass; awaiting live-app confirmation
**Re-verification:** Yes — after gap closure (commit 40e5a4f)

## Re-verification Summary

The previous verification (score 9/12, status gaps_found) identified a single root-cause bug: three `DecimalField` declarations in `apps/gifts/serializers.py` had redundant `source='amount_dollars'` arguments. DRF raises `AssertionError` at field-binding time when `source` matches the field name, blocking every Gift/RecurringGift API endpoint and causing all five UI-GIFT-01 through UI-GIFT-05 requirements to be BLOCKED.

Commit 40e5a4f removed `source='amount_dollars'` from:
- `GiftSerializer.amount_dollars` (formerly lines 13-15)
- `GiftCreditReadSerializer.amount_dollars` (formerly lines 42-44)
- `RecurringGiftSerializer.amount_dollars` (formerly lines 93-95)

**Programmatic verification confirms the fix is complete:**

| Serializer | Fields | Status |
|-----------|--------|--------|
| GiftSerializer | 12 | OK |
| GiftDetailSerializer | 13 | OK |
| GiftCreditReadSerializer | 5 | OK |
| RecurringGiftSerializer | 16 | OK |
| GiftCreateSerializer | 7 | OK |
| RecurringGiftCreateSerializer | 10 | OK |

Additional checks:
- `manage.py check` — no issues
- `tsc --noEmit` — zero errors
- `GiftDetailView.get_serializer_class()` on GET — returns `GiftDetailSerializer` (correct)
- `GiftListCreateView.get_serializer_class()` on GET — returns `GiftSerializer` (correct)
- `GiftListCreateView.get_serializer_class()` on POST — returns `GiftCreateSerializer` (correct)
- `RecurringGiftListCreateView.get_serializer_class()` on GET — returns `RecurringGiftSerializer` (correct)
- No regressions detected in previously-passing items.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gift detail API endpoint returns solicitor credit breakdown | VERIFIED | GiftDetailSerializer().fields: OK (13 fields including credits); GiftDetailView returns GiftDetailSerializer for GET; prefetch_related('credits__solicitor') present |
| 2 | Gift/RecurringGift list endpoints support text search and column ordering | VERIFIED | GiftSerializer().fields: OK (12 fields); GiftListCreateView has SearchFilter + OrderingFilter + search_fields + ordering_fields defined |
| 3 | CSV export endpoints exist for gifts and recurring gifts | VERIFIED | apps/gifts/export_views.py: GiftExportCSVView and RecurringGiftExportCSVView; StreamingHttpResponse; bypass serializer — use model properties directly |
| 4 | Frontend has correct TypeScript types matching Gift/RecurringGift serializer output | VERIFIED | gifts.ts exports Gift, GiftCredit, GiftWithCredits, RecurringGift; tsc --noEmit passes with zero errors |
| 5 | Frontend hooks exist for gift CRUD, recurring gift CRUD, and gift detail with credits | VERIFIED | useGifts.ts: useGifts, useGift, useCreateGift, useUpdateGift, useDeleteGift + 5 RecurringGift equivalents |
| 6 | Donations list page loads data from Gift model via /donations/ API | VERIFIED | DonationList.tsx uses useGifts; api/gifts.ts path is /donations/; giftFilterParsers wired |
| 7 | Slide-in detail panel shows solicitor credits | VERIFIED | DonationDetail.tsx: useGift hook; SheetContent; credits table conditional on gift.credits.length > 0 |
| 8 | Donation form creates gifts with amount_cents conversion | VERIFIED | DonationForm.tsx: amount_cents = Math.round(parseFloat(formData.amount) * 100) |
| 9 | Pledges list page loads RecurringGift data with expanded status/frequency options | VERIFIED | PledgeList.tsx: useRecurringGifts + recurringGiftFilterParsers; 5 statuses, 8 frequencies in dropdowns |
| 10 | Contact detail Donations tab shows Gift model data (amount_dollars, gift_date) | VERIFIED | ContactDetail.tsx: type annotation includes amount_dollars, gift_date, fund_name |
| 11 | Contact detail Pledges tab shows RecurringGift data without is_late | VERIFIED | ContactDetail.tsx: type uses amount_dollars, frequency, status — no is_late field |
| 12 | Dashboard NeedsAttention shows "Late detection coming soon" placeholder | VERIFIED | NeedsAttention.tsx: exact text match; always rendered via `|| true` guard |

**Score:** 12/12 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/gifts/serializers.py` | GiftDetailSerializer with nested GiftCreditReadSerializer | VERIFIED | All 6 serializers bind fields without error post-fix; GiftDetailSerializer has 13 fields including credits |
| `apps/gifts/views.py` | List/Detail views for Gift and RecurringGift | VERIFIED | GiftListCreateView, GiftDetailView, RecurringGiftListCreateView, RecurringGiftDetailView all present with correct serializer selection |
| `apps/gifts/export_views.py` | CSV export views for Gift and RecurringGift | VERIFIED | GiftExportCSVView and RecurringGiftExportCSVView; StreamingHttpResponse; model property access |
| `frontend/src/api/gifts.ts` | Gift/RecurringGift types and API functions | VERIFIED | Gift, GiftCredit, GiftWithCredits, RecurringGift types; /donations/ and /pledges/recurring/ paths correct |
| `frontend/src/hooks/useGifts.ts` | React Query hooks for gifts | VERIFIED | 10 hooks total (useGifts, useGift, useCreateGift, useUpdateGift, useDeleteGift + 5 RecurringGift) |
| `frontend/src/pages/donations/DonationList.tsx` | Donations list with Gift model data | VERIFIED | 288 lines; useGifts, giftFilterParsers, Gift columns |
| `frontend/src/pages/donations/DonationDetail.tsx` | Slide-in panel with solicitor credits | VERIFIED | SheetContent, useGift, credits table conditional on gift.credits.length > 0 |
| `frontend/src/pages/donations/DonationForm.tsx` | Donation form with amount_cents | VERIFIED | amount_cents conversion correct; no donation_type/payment_method |
| `frontend/src/pages/pledges/PledgeList.tsx` | Pledges list with RecurringGift data | VERIFIED | 240 lines; useRecurringGifts, recurringGiftFilterParsers, /pledges/recurring/export/csv/ |
| `frontend/src/pages/pledges/PledgeDetail.tsx` | Pledge detail with RecurringGift fields | VERIFIED | useRecurringGift; no is_late/fulfillment; amount_dollars, frequency, status |
| `frontend/src/pages/pledges/PledgeForm.tsx` | Pledge form with amount_cents conversion | VERIFIED | amount_cents = Math.round(parseFloat * 100); all 8 frequency, 5 status options |
| `frontend/src/pages/contacts/ContactDetail.tsx` | Contact detail with Gift/RecurringGift tabs | VERIFIED | amount_dollars and gift_date in Donations tab; amount_dollars, frequency, status in Pledges tab |
| `frontend/src/components/dashboard/NeedsAttention.tsx` | Late detection placeholder | VERIFIED | "Late detection coming soon" always rendered; hasItems always true |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/api/gifts.ts` | `/donations/` (backend alias) | `apiClient.get("/donations/")` | WIRED | Exact path confirmed |
| `frontend/src/api/gifts.ts` | `/pledges/recurring/` (backend alias) | `apiClient.get("/pledges/recurring/")` | WIRED | Exact path confirmed |
| `apps/gifts/views.py` | `GiftDetailSerializer` | get_serializer_class for GET /id/ | WIRED | Returns GiftDetailSerializer for GET; prefetch_related('credits__solicitor') in get_queryset |
| `apps/gifts/views.py` | `GiftSerializer` | get_serializer_class for GET list | WIRED | Returns GiftSerializer for GET list; confirmed via shell |
| `DonationList.tsx` | `useGifts` | useGifts hook | WIRED | Import + usage confirmed |
| `DonationList.tsx` | `giftFilterParsers` | Filter state | WIRED | Import + usage confirmed |
| `DonationDetail.tsx` | `useGift` | GiftWithCredits hook | WIRED | Import + usage confirmed |
| `PledgeList.tsx` | `useRecurringGifts` | RecurringGift hook | WIRED | Import + usage confirmed |
| `PledgeList.tsx` | `/pledges/recurring/export/csv/` | exportUrl in FilterBar | WIRED | Exact URL present |
| `ContactDetail.tsx` | `useContactDonations / useContactPledges` | Contact hooks | WIRED | Imports and usage confirmed |
| `config/api_urls.py` | `apps/gifts/urls` | /donations/ and /pledges/ aliases | WIRED | Both aliases confirmed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-GIFT-01 | 31-02 | Rewire Donations pages to query Gift API, keep "Donations" labels | SATISFIED | DonationList.tsx uses useGifts via /donations/; GiftSerializer binds 12 fields cleanly post-fix |
| UI-GIFT-02 | 31-03 | Rewire Pledges pages to query RecurringGift API, keep "Pledges" labels | SATISFIED | PledgeList.tsx uses useRecurringGifts via /pledges/recurring/; RecurringGiftSerializer binds 16 fields cleanly |
| UI-GIFT-03 | 31-01, 31-02 | Gifts list page with filters for Gift model fields | SATISFIED | giftFilterParsers correct; SearchFilter + OrderingFilter on GiftListCreateView; serializer unblocked |
| UI-GIFT-04 | 31-01, 31-03 | RecurringGifts list page with filters | SATISFIED | recurringGiftFilterParsers correct; SearchFilter + OrderingFilter on RecurringGiftListCreateView; serializer unblocked |
| UI-GIFT-05 | 31-01, 31-02 | Gift detail view with solicitor credit breakdown | SATISFIED | GiftDetailSerializer has credits field (13 total); GiftDetailView returns GiftDetailSerializer for GET; DonationDetail.tsx renders credits conditionally |
| UI-GIFT-06 | 31-03 | Contact detail Gifts tab showing gifts linked to contact | SATISFIED | ContactDetail.tsx renders amount_dollars, gift_date, fund_name; no is_late |
| UI-GIFT-07 | 31-01 | CSV exports using Gift/RecurringGift data | SATISFIED | export_views.py bypasses serializer; uses model properties directly |
| DASH-02 | 31-03 | Dashboard summary cards query Gift/RecurringGift | SATISFIED | NeedsAttention placeholder confirmed; dashboard service pre-verified in Phase 30 |

**Summary:** All 8 requirements satisfied. The serializer fix in commit 40e5a4f unblocked UI-GIFT-01 through UI-GIFT-05. UI-GIFT-06, UI-GIFT-07, and DASH-02 were already satisfied in the initial pass.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `frontend/src/components/dashboard/NeedsAttention.tsx` | `\|\| true /* always show late pledges placeholder */` | WARNING | Intentional workaround; disables the "All caught up!" empty state permanently. Acceptable for this phase — a future phase should remove this when late detection is implemented |

No blockers found. The previous BLOCKER (redundant `source='amount_dollars'` on DecimalField) is resolved.

---

## Human Verification Required

### 1. Donations List Page Functionality

**Test:** Start the Django dev server and frontend dev server. Navigate to `/donations` in the browser.
**Expected:** Table loads with Donor Name, Amount, Date, Fund, Description columns. Clicking a row opens a slide-in panel with donation details.
**Why human:** Requires live server with database data; serializer fix confirmed programmatically but the full HTTP request-response cycle needs live confirmation.

### 2. Solicitor Credits Display

**Test:** Open a donation that has GiftCredit records assigned (create one via admin if needed).
**Expected:** "Solicitor Credits" section visible in the slide-in panel with Solicitor Name, Amount, Percentage columns. Section must be hidden (not rendered) for donations with no credits.
**Why human:** Requires specific test data with GiftCredit records; credits section is conditional on `gift.credits.length > 0`.

### 3. Pledges Page Filter Dropdowns

**Test:** Navigate to `/pledges` and open the Status and Frequency filter dropdowns.
**Expected:** Status has 5 options (Active, Held, Completed, Cancelled, Terminated). Frequency has 8 options including Weekly, Monthly, Quarterly, Annual.
**Why human:** Visual verification in running app; dropdown option counts and labels require browser rendering.

### 4. Dashboard NeedsAttention Card

**Test:** Navigate to the Dashboard.
**Expected:** An amber-colored "NeedsAttention" card is always visible with the text "Late detection coming soon".
**Why human:** Visual rendering (amber color, card layout) and exact text placement require running app.

---

## Gaps Summary

No gaps remain. All 12 automated must-haves are verified. All 8 requirements are satisfied. The single root-cause bug identified in the initial verification was fixed in commit 40e5a4f — removing three redundant `source='amount_dollars'` keyword arguments from DRF DecimalField declarations. Serializer field-binding now succeeds for all six serializers in `apps/gifts/serializers.py`.

Four human verification items remain — these are visual and live-app confirmations, not code gaps. The codebase is ready for live testing.

---

_Verified: 2026-02-23T18:15:00Z_
_Verifier: Claude (gsd-verifier)_
