# Data Classification

Each model field in DonorCRM is classified by sensitivity. Classification
drives encryption, access control, and retention policy.

**Scope assumed:** US-based donors only (no PCI / HIPAA / GDPR scope per
2026-05-07 product confirmation). State breach notification laws apply
across all 50 states.

## Tiers

| Tier | Definition | At-rest encryption | Transit | Notes |
|------|-----------|--------------------|---------|-------|
| **Public** | OK to expose externally without redaction | None | TLS 1.2+ | E.g. published org name |
| **Internal** | Operational data; not user-identifying | None | TLS 1.2+ | E.g. tags, status enums |
| **Confidential** | Donor-identifying or relationship data | Field-level AES-256-GCM | TLS 1.3 | Default for donor PII |
| **Restricted** | Highly sensitive (auth secrets, future card data) | Application-layer AES-256-GCM + KMS (Phase 5) | TLS 1.3 | Auth tokens, future PCI scope |

## Encrypted fields (live)

| Field | Tier | Blind index? | Migration |
|-------|------|--------------|-----------|
| `Contact.notes` | Confidential | — | `contacts/0011_alter_contact_notes` |
| `Contact.phone_secondary` | Confidential | `phone_secondary_hash` | `contacts/0012` then `0014` |
| `Contact.street_address` | Confidential | — | `contacts/0012_encrypt_pii_phase_3a` |
| `Contact.email` | Confidential | `email_hash` (unique-per-owner) | `contacts/0013_encrypt_email_with_blind_index` |
| `Contact.phone` | Confidential | `phone_hash` | `contacts/0014_encrypt_phone_and_descriptions` |
| `JournalStageEvent.notes` | Confidential | — | `journals/0007_encrypt_pii_phase_3a` |
| `PrayerIntention.description` | Confidential (deeply personal) | — (Python-side dedup) | `prayers/0004_encrypt_phone_and_descriptions` |
| `Gift.description` | Confidential | — | `gifts/0008_encrypt_phone_and_descriptions` |
| `RecurringGift.description` | Confidential | — | `gifts/0008_encrypt_phone_and_descriptions` |

## Confidential fields intentionally left as plaintext

| Field | Rationale |
|-------|-----------|
| `Contact.first_name`, `last_name`, `organization_name` | Encrypting these would kill typeahead substring search and break the alphabetical ordering on the contacts list (`ORDER BY ciphertext` → random order). State breach safe-harbor language typically keys off "name + identifier" pairs; name alone is lower-sensitivity. UX cost > regulatory benefit for US-only scope. |
| `Contact.city`, `state`, `postal_code`, `country` | Coarse-grained; low identifying value in isolation; commonly used in filters. |
| `User.email` | Used as login identifier; touches django-axes, password reset, JWT subject. Phase 8 (deferred). |
| `Solicitor.normalized_name` and similar internal-relationship fields | Not donor PII. |

## Confidential fields where encryption is unlikely to be worthwhile

| Field | Reason |
|-------|--------|
| `Contact.city`, `state`, `postal_code`, `country` | Coarse-grained; low identification value alone; commonly used in filters |
| `*_at` timestamps | Not directly identifying; high query value |
| `*_id` foreign keys | Not identifying without the related row |
| `*_cents` money fields | Aggregate views and reports require equality/comparison; would block dashboards |

If an auditor or customer requires these encrypted, the path is blind-index
or homomorphic schemes — cost outweighs benefit at the current scale.

## Restricted (auth secrets — already protected via Django defaults)

| Item | Storage |
|------|---------|
| User passwords | Hashed via Django default hasher (Argon2/PBKDF2 in prod) |
| JWT signing secret | `SECRET_KEY` env var; never logged |
| PII encryption keys | `DJANGO_PII_ENCRYPTION_KEYS` env var; see [key-management.md](key-management.md) |
| OAuth client secrets | `RE_CLIENT_SECRET` etc. env vars |

## Public / Internal — explicitly NOT encrypted

`status`, `stage`, `event_type`, tags, denormalized counters, `is_archived`,
foreign-key columns, system timestamps. Encrypting these would impose query
overhead with no privacy benefit.

## Per-tier policy summary

| Tier | Logging allowed? | Sentry breadcrumbs allowed? | Export to CSV allowed? |
|------|------------------|------------------------------|-----------------------|
| Public | yes | yes | yes |
| Internal | yes (no values in error messages) | yes | yes |
| Confidential | actor IDs only, never values | scrubbed via `before_send` hook | role-gated; logged via access audit (Phase 6) |
| Restricted | never | never | never |

## Review cadence

Re-classify when adding any new model field that may contain donor input.
Annual review minimum.
