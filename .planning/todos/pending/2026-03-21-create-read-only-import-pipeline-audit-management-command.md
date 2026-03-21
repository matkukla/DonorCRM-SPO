---
created: 2026-03-21T09:04:37.271Z
title: Create read-only import pipeline audit management command
area: backend
files:
  - apps/users/models.py
  - apps/gifts/models.py
  - apps/contacts/models.py
  - apps/imports/models.py
  - apps/imports/management/commands/
source: "GitHub Issue #24 — Import Pipe Line Audit"
---

## Problem

Before pilot launch with real missionaries, we need to verify the health of the import pipeline data — specifically solicitor linking, contact ownership, and gift credit integrity. There is no way to audit this data currently.

## Solution

Create a new read-only Django management command `audit_import_health` (zero DB writes, zero model changes, zero migrations, zero modifications to existing files).

**Command:** `python manage.py audit_import_health`
**Flags:** `--verbose` (per-record details), `--json` (structured JSON output)

**5 report sections:**
1. **Solicitor Linking** — linked vs unlinked counts, near-miss detection (case-insensitive name matching against Users and MissionaryAlias)
2. **Contact Ownership** — contacts by owner role, misattribution flags (admin-owned contacts with GiftCredits pointing to missionary solicitors)
3. **Gift Credit Integrity** — orphaned gifts, unlinked solicitor dollar totals
4. **Recurring Gift Credit Integrity** — same as above for active RecurringGifts
5. **Dashboard Impact Estimate** — per-missionary view using `donor_contact__owner=user` scoping (same path as real dashboard), flags missionaries with 0 contacts or ownership gaps

**Summary verdict:** HEALTHY (zero issues) or NEEDS ATTENTION (X issues found)

Full spec in GitHub Issue #24.
