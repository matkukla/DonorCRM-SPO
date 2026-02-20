---
phase: 27-foundation-models
verified: 2026-02-20T23:15:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 27: Foundation Models Verification Report

**Phase Goal:** All new data models exist in the database so that import pipeline, migration, and UI phases have tables to write to
**Verified:** 2026-02-20T23:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gift model exists with external_gift_id, donor_contact FK, fund FK, amount_cents, gift_date, description | VERIFIED | `apps/gifts/models.py` lines 94-161; donor_contact is CASCADE (not null) per user decision |
| 2 | GiftCredit junction model exists linking Gift to Solicitor with per-credit amount_cents | VERIFIED | `apps/gifts/models.py` lines 167-208; UniqueConstraint on (gift, solicitor) |
| 3 | RecurringGift model exists with installment fields (frequency, start_date, end_date), status tracking, and external_gift_id | VERIFIED | `apps/gifts/models.py` lines 215-300; all 5 RecurringGiftStatus + 8 RecurringGiftFrequency choices |
| 4 | RecurringGiftCredit junction model exists linking RecurringGift to Solicitor with per-credit amount_cents | VERIFIED | `apps/gifts/models.py` lines 307-347; UniqueConstraint on (recurring_gift, solicitor) |
| 5 | Solicitor model exists with normalized_name, optional OneToOneField to User, and external_solicitor_id | VERIFIED | `apps/gifts/models.py` lines 44-87; conditional UniqueConstraint on external_solicitor_id |
| 6 | All five gifts models inherit from TimeStampedModel (UUID PK, timestamps) | VERIFIED | All 5 classes inherit TimeStampedModel; migration confirms UUID PK with `uuid.uuid4` default |
| 7 | Django admin registrations exist for all five gift models | VERIFIED | `apps/gifts/admin.py` — @admin.register for Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit |
| 8 | ImportBatch model exists with SHA256 hash field unique per import_type, status tracking, summary JSON, and row counts | VERIFIED | `apps/imports/models.py` lines 211-279; UniqueConstraint name='unique_import_batch_hash_per_type' on (import_type, sha256_hash) |
| 9 | PrayerIntention model exists with required contact FK, title, description, status (active/answered/archived), and optional gift FK | VERIFIED | `apps/prayers/models.py` lines 19-74; contact is CASCADE not-null, gift is SET_NULL nullable |
| 10 | Contact model has external_constituent_id and organization_name fields | VERIFIED | `apps/contacts/models.py` lines 45-59; conditional UniqueConstraint on external_constituent_id |
| 11 | All new migrations apply successfully with zero errors | VERIFIED | `showmigrations`: gifts [X] 0001_initial, prayers [X] 0001_initial, imports [X] 0003_importbatch_and_more, contacts [X] 0006_contact_external_constituent_id_and_more |
| 12 | Django system check passes with no issues | VERIFIED | `python manage.py check` → "System check identified no issues (0 silenced)" |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/gifts/models.py` | Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit | VERIFIED | All 5 model classes present and substantive |
| `apps/gifts/admin.py` | Admin registrations for all 5 gift models | VERIFIED | @admin.register for all 5 with list_display, search, filters |
| `apps/gifts/apps.py` | GiftsConfig Django app config | VERIFIED | class GiftsConfig with name='apps.gifts' |
| `apps/gifts/__init__.py` | Empty app init | VERIFIED | File exists |
| `apps/gifts/migrations/0001_initial.py` | Initial migration for all 5 gift models | VERIFIED | Applied [X]; creates gifts, gift_credits, solicitors, recurring_gifts, recurring_gift_credits tables |
| `apps/prayers/models.py` | PrayerIntention model with status tracking | VERIFIED | class PrayerIntention(TimeStampedModel) with required contact FK |
| `apps/prayers/admin.py` | PrayerIntention admin registration | VERIFIED | @admin.register(PrayerIntention) |
| `apps/prayers/apps.py` | PrayersConfig Django app config | VERIFIED | class PrayersConfig with name='apps.prayers' |
| `apps/prayers/migrations/0001_initial.py` | Initial migration for PrayerIntention | VERIFIED | Applied [X] |
| `apps/imports/models.py` | ImportBatch model with SHA256 dedup | VERIFIED | class ImportBatch(TimeStampedModel) with UniqueConstraint on (import_type, sha256_hash) |
| `apps/imports/migrations/0003_importbatch_and_more.py` | ImportBatch migration | VERIFIED | Applied [X] |
| `apps/contacts/models.py` | Contact with external_constituent_id and organization_name | VERIFIED | Both fields present; conditional UniqueConstraint on external_constituent_id |
| `apps/contacts/migrations/0006_contact_external_constituent_id_and_more.py` | Contact field additions migration | VERIFIED | Applied [X] |
| `config/settings/base.py` | INSTALLED_APPS includes apps.gifts and apps.prayers | VERIFIED | Both 'apps.gifts' and 'apps.prayers' found in LOCAL_APPS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/gifts/models.py` | `apps/contacts/models.py` | ForeignKey donor_contact | WIRED | `ForeignKey('contacts.Contact', on_delete=models.CASCADE, related_name='gifts')` on Gift and RecurringGift |
| `apps/gifts/models.py` | `apps/imports/models.py` | ForeignKey fund | WIRED | `ForeignKey('imports.Fund', on_delete=models.SET_NULL, null=True)` on Gift and RecurringGift |
| `apps/gifts/models.py` | `apps/users/models.py` | OneToOneField user on Solicitor | WIRED | `OneToOneField('users.User', on_delete=models.SET_NULL, null=True, related_name='solicitor_profile')` |
| `apps/prayers/models.py` | `apps/contacts/models.py` | ForeignKey contact (required) | WIRED | `ForeignKey('contacts.Contact', on_delete=models.CASCADE)` — not nullable |
| `apps/prayers/models.py` | `apps/gifts/models.py` | ForeignKey gift (optional) | WIRED | `ForeignKey('gifts.Gift', on_delete=models.SET_NULL, null=True, blank=True)` |
| `apps/imports/models.py` | `apps/users/models.py` | ForeignKey uploaded_by on ImportBatch | WIRED | `ForeignKey('users.User', on_delete=models.PROTECT, related_name='import_batches')` |
| Migration `gifts/0001_initial.py` | Contacts migration 0006 + Imports migration 0003 | Migration dependencies | WIRED | `dependencies = [("contacts", "0006_..."), ("imports", "0003_...")]` |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|---------|
| MODEL-01 | Gift model replaces Donation with externalGiftId, donorContact FK, solicitor credit support, cents-based amounts | SATISFIED | Gift model: external_gift_id, donor_contact FK (CASCADE), fund FK, amount_cents (PositiveBigIntegerField), GiftCredit junction |
| MODEL-02 | GiftCredit junction model links Gift to Solicitor with per-credit amount | SATISFIED | GiftCredit: FK to Gift, FK to Solicitor (PROTECT), amount_cents, UniqueConstraint (gift, solicitor) |
| MODEL-03 | RecurringGift model replaces Pledge with installment fields, status tracking, and externalGiftId | SATISFIED | RecurringGift: frequency (8 choices), start_date, end_date, status (5 choices), external_gift_id |
| MODEL-04 | RecurringGiftCredit junction model links RecurringGift to Solicitor | SATISFIED | RecurringGiftCredit: FK to RecurringGift, FK to Solicitor (PROTECT), amount_cents, UniqueConstraint |
| MODEL-05 | Solicitor model with normalized name matching and auto-linking to User accounts | SATISFIED | Solicitor: normalized_name (db_index), user (OneToOneField, nullable), external_solicitor_id, conditional UniqueConstraint |
| MODEL-06 | ImportBatch model with SHA256 file deduplication, status tracking, and summary JSON | SATISFIED | ImportBatch: sha256_hash, UniqueConstraint(import_type, sha256_hash), 5 status choices, summary JSONField |
| MODEL-07 | PrayerIntention model tied to Contact with title, description, status (active/answered/archived), and optional Gift link | SATISFIED | PrayerIntention: contact FK (CASCADE, required), gift FK (SET_NULL, optional), title, description, 3-state status, answered_at, archived_at |
| MODEL-08 | Contact model updated with externalConstituentId, organizationName, and address fields | SATISFIED | external_constituent_id (CharField, db_index, conditional UniqueConstraint), organization_name (CharField) added in migration 0006; address fields (street_address, city, state, postal_code, country) pre-existed from 0001_initial — CONTEXT.md grants discretion on address field granularity |

### Anti-Patterns Found

None detected. No TODO/FIXME/placeholder comments, no empty implementations, no stub return values in any of the 7 files examined.

### Human Verification Required

None. All model-level checks are fully verifiable programmatically. Migration application confirmed via `showmigrations`. Django system check confirmed via `manage.py check`.

### Gaps Summary

No gaps. All 8 requirement IDs (MODEL-01 through MODEL-08) are fully satisfied. All 5 gift models, PrayerIntention, ImportBatch, and Contact field additions are present in the codebase, correctly wired via ForeignKey relationships, and reflected in applied database migrations.

**MODEL-08 address fields clarification:** REQUIREMENTS.md states "address fields" as part of MODEL-08. The Contact model's address fields (street_address, city, state, postal_code, country) pre-existed Phase 27, created in 0001_initial. Phase 27 adds external_constituent_id and organization_name. The 27-CONTEXT.md explicitly grants "Claude's discretion" on "Contact address field granularity" — this confirms address field handling was a design decision, not a new delivery requirement for Phase 27. MODEL-08 is satisfied.

---

_Verified: 2026-02-20T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
