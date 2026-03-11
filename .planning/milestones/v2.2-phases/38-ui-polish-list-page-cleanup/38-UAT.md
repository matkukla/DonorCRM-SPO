---
status: complete
phase: 38-ui-polish-list-page-cleanup
source: 38-01-SUMMARY.md, 38-02-SUMMARY.md, 38-03-SUMMARY.md
started: 2026-02-27T17:15:00Z
updated: 2026-02-27T17:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Gifts list page columns
expected: Open the Gifts list page. Columns should be: Donor Name, Amount, Date, Type. No Fund or Description columns visible.
result: pass

### 2. Gift Type column values
expected: The Type column shows "Credit Card", "Direct Deposit", or "Check" for gifts that have a payment type set. Gifts without a payment type show "---".
result: pass

### 3. Gift payment type filter
expected: The FilterBar on the gifts list page has a "Type" filter dropdown with options: Credit Card, Direct Deposit, Check. Selecting one filters the list to only show gifts of that payment type.
result: pass

### 4. Gift detail opens as centered Dialog
expected: Click on a gift row to open its detail. It should open as a centered overlay Dialog (not sliding in from the right side). It should have a dark semi-transparent backdrop, max height ~80% of viewport with scrolling if content is tall, and dismiss via backdrop click, close button, or Escape.
result: pass

### 5. Gift detail shows payment type
expected: The gift detail Dialog shows a "Payment Type" row displaying the payment type value (or "---" if not set).
result: pass

### 6. Gift form has payment type selector
expected: When creating or editing a gift, the form includes a "Payment Type" dropdown with options: None (empty), Credit Card, Direct Deposit, Check.
result: pass

### 7. Pledges list page — no Fund column
expected: Open the Pledges list page. The Fund column should NOT be present.
result: pass

### 8. Mobile nav opens as centered Dialog
expected: On mobile (or narrow browser width), tap the hamburger menu. The navigation should open as a centered Dialog overlay (not sliding in from the left side).
result: pass

### 9. Funnel drilldown opens as centered Dialog
expected: On the Admin Analytics Dashboard, click a funnel stage to drill down. The drilldown panel should open as a centered Dialog (not sliding from the side).
result: pass

### 10. Contact status shows "Potential Donor"
expected: On the Contacts list page, contacts that were previously labeled "Prospect" now show "Potential Donor" as their status. The filter dropdown also shows "Potential Donor" instead of "Prospect". Same in contact detail and contact form.
result: pass

### 11. Review Queue removed from sidebar
expected: The sidebar navigation should NOT have a "Review Queue" link anywhere.
result: pass

### 12. Review Queue URL redirects
expected: Navigate to /insights/review-queue in the browser. You should be automatically redirected to /admin/analytics/dashboard (not a 404).
result: pass

### 13. Activity Heatmap removed from analytics dashboard
expected: Open the Admin Analytics Dashboard. There should be no Activity Heatmap section/chart visible on the page.
result: pass

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
