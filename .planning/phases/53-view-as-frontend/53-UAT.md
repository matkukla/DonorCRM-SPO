---
status: complete
phase: 53-view-as-frontend
source: 53-01-SUMMARY.md, 53-02-SUMMARY.md, 53-03-SUMMARY.md
started: 2026-03-17T15:30:00Z
updated: 2026-03-24T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Dashboard Missionary Picker (Admin/Supervisor)
expected: As an admin or supervisor, the Dashboard shows a "Viewing:" label with a dropdown button defaulting to "My Dashboard". Clicking it opens a searchable list of missionaries. Selecting one updates the button label to that missionary's name and loads their dashboard data.
result: pass

### 2. Amber View As Banner
expected: After selecting a missionary from the picker, an amber banner appears at the top of every page (below the header) showing "Viewing [Missionary Name] · Read Only" with an Eye icon and an "Exit" button. Navigating to other pages (Contacts, Donations, etc.) keeps the banner visible.
result: pass

### 3. Exit View As
expected: Clicking "Exit" in the amber banner (or selecting "My Dashboard" from the picker) dismisses the banner, resets the dropdown to "My Dashboard", and reloads the dashboard with your own data.
result: pass

### 4. Session Persistence on Refresh
expected: While in View As mode, refreshing the page keeps View As active — the amber banner still shows the missionary's name and the dashboard still shows their data. The session is not lost on browser refresh.
result: pass

### 5. Sidebar Hides Admin Items in View As Mode
expected: While viewing as a missionary, the sidebar hides the "Import/Export" nav item and the "Admin" nav item. The "Transactions" item is also hidden from the Insights section. All other nav items remain visible.
result: pass

### 6. Contacts List Shows Missionary's Contacts
expected: Navigating to /contacts while in View As mode shows the selected missionary's contacts, not your own. The page displays in read-only mode.
result: pass

### 7. Create Buttons Hidden in View As Mode
expected: While in View As mode, the following create/action buttons are hidden across pages: "Add Contact" (ContactList), "Record Donation" (DonationList), "Create Pledge" (PledgeList), "Create Task" (TaskList), "New Journal" (JournalList), "Add Prayer" (PrayerList). Row-level edit actions (Log Entry, Mark Thanked, Edit Task, Mark Complete) are also hidden.
result: pass

### 8. Goal Page Read-Only in View As Mode
expected: Navigating to /goal while in View As mode shows the missionary's goal data in read-only mode — no edit controls are active.
result: pass

### 9. Logout Clears View As Session
expected: Logging out while in View As mode clears the session — after logging back in, the dashboard shows your own data with no amber banner visible.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "Logging out while in View As mode clears the session — after logging back in, the dashboard shows your own data with no amber banner visible"
  status: resolved
  reason: "Fixed — AuthProvider.logout() now dispatches viewas:clear CustomEvent; ViewAsProvider listens and resets state"
  severity: major
  test: 9
