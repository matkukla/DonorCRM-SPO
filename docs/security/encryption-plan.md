# Encryption Migration Plan

Strategic sequencing for moving DonorCRM PII columns to field-level encryption.
Companion to [encryption-rollout.md](encryption-rollout.md), which is the
operational runbook (the *how*). This document is the *what* and *when*.

**Status:** drafted 2026-05-07 after audit-driven investigation of actual
model surface.

## Why this plan exists

The original security audit listed 7 candidate columns to encrypt. After
reading the models and grepping the codebase, several of those candidates
turned out to either not exist as named or have hard query/constraint
dependencies that block a naive `TextField → EncryptedTextField` swap.

This plan corrects the audit's assumptions, sequences the work into shippable
phases, and explicitly defers the columns that need real refactoring rather
than a swap.

## Field reality check

| Audit assumed                        | Actual field on model                       | Search? | Filter? | Unique? | Indexed? | Phase  |
|--------------------------------------|---------------------------------------------|---------|---------|---------|----------|--------|
| `Contact.notes`                      | `Contact.notes`                             | no      | no      | no      | no       | **1A** |
| `Contact.address`                    | `Contact.street_address` (also `city`/`state`/`postal_code`) | no | no | no | no | **1A** |
| `Contact.email`                      | `Contact.email`                             | yes (`__icontains`, `__iexact`) | yes | yes (per-owner conditional) | yes (`models.Index(fields=['email'])`) | **1B** |
| `Contact.phone`                      | `Contact.phone`                             | yes (`__icontains`) | no | no | no | **1B** |
| `Gift.notes`                         | actual field is `Gift.description`          | yes (`search_fields`) | no | no | no | **1B/defer** |
| `PrayerIntention.description`        | exists                                      | no in views/admin, but `__iexact` used 3× in import dedup (`apps/imports/re_services.py`, `apps/imports/spo_services.py`) | no | no | no | **defer** |
| `JournalEntry.body`                  | model doesn't exist; closest analogue is `JournalEvent.notes` | TBD | TBD | no | no | **1A pending verification** |

**Key insight**: only ~3 columns are actually safe to swap today. The rest
either need a blind-index (`_hash`) sidecar column or a refactor of the code
that depends on substring/iexact lookups. Pretending otherwise risks shipping
encrypted columns that silently break dedup or search.

## Phase 1A — Sleeper migration

**Goal:** encrypt fields with zero query/filter/constraint dependencies.
Behavior is identical from any user-facing or admin perspective. Only
difference is ciphertext at rest.

### Targets

1. `Contact.notes`
2. `Contact.street_address`
3. `JournalEvent.notes` (after grep verifies no search/filter usage)
4. Sweep for any other `TextField('notes', ...)` or similar low-stakes
   text fields with no query usage

### Per-column procedure

Each column is its own commit and can ship independently. The procedure:

1. Swap `models.TextField` → `apps.core.encryption.EncryptedTextField` in
   the model.
2. Run `python manage.py makemigrations` to produce an `AlterField`.
3. **Hand-edit the migration** to add a `RunPython` data step that batches
   through existing rows and re-saves them. The legacy-plaintext sentinel
   in `EncryptedTextField.from_db_value` returns plaintext for the read,
   then `get_prep_value` encrypts on the save.
4. Mark the migration `atomic = False` so each batch commits independently
   — a 50k-row table will not lock for the duration.
5. Add tests covering: round-trip, legacy plaintext passthrough, behavior
   when `PII_ENCRYPTION_KEYS` is unset.
6. Deploy + verify in production with `psql` that the column starts with
   `gAAAAA…`.
7. Mark the column complete in this doc.

### Rollback plan

If the migration fails partway, the legacy-plaintext sentinel ensures
already-migrated rows remain readable. Rerun the migration to pick up where
it left off — the `RunPython` step is idempotent because already-encrypted
values are still re-encrypted (under the same current key, producing
different bytes but identical plaintext on read).

To fully revert: write a reverse data migration that decrypts every value,
then `AlterField` the column back to `TextField`. This loses no data because
the cipher is round-trippable.

### What's in this PR

`Contact.notes` only — proof of pattern, end-to-end:
- Swap field type
- Generate + hand-edit migration
- Tests
- Production-rollout note added below when complete

The other Phase 1A columns are documented here as a checklist, to be
delivered as 1-3 follow-up PRs by another contributor or session. The
recipe is identical; the diff per column is small.

### Phase 1A checklist

- [ ] `Contact.notes` (this PR)
- [ ] `Contact.street_address`
- [ ] `JournalEvent.notes` (verify no search usage first)
- [ ] Sweep for additional candidates and add to this list

## Phase 1B — Blind-index migration

**Goal:** encrypt fields that need to remain queryable. Each column gets a
sidecar `_hash` column holding a deterministic hash of the value, used for
equality lookups.

### Pattern

```python
class Contact(...):
    email = EncryptedTextField(...)            # ciphertext
    email_hash = models.BinaryField(           # SHA-256 over normalized email
        unique=True, null=True, db_index=True,
    )
```

What it costs:

- **Equality lookups** (`Contact.objects.filter(email_hash=hash_email("a@b.com"))`)
  work via the hash. Existing `__iexact` callsites must be rewritten.
- **Substring search** (`__icontains`) is **lost**. No blind-index scheme
  supports `%foo%`. Three escape hatches:
  - Replace with full-value-equality + suggestions (acceptable for `email`
    since users typically type the whole address).
  - Server-side decrypt-then-grep over the visible scope (acceptable for
    `phone` if scope is small; slow if not).
  - Drop the search (acceptable when search is convenience-only).
- **Unique constraints** become unique on the hash column instead of the
  value column. The conditional unique constraint
  `unique_contact_email_per_owner` migrates to use `email_hash`.

### Why per-column PRs

Each Phase 1B column requires:

- New migration adding the `_hash` column
- Backfill management command that hashes existing values
- Code changes at every callsite that does `__iexact` / `__icontains`
- Test updates (especially `apps/imports/re_services.py` and
  `apps/imports/spo_services.py` dedup paths)
- A documented decision about the substring-search UX change

These are not type swaps; they are feature redesigns. The diffs and
review surface are commensurate.

### Sequencing within Phase 1B

1. **`Contact.email` first** — highest sensitivity, most-used search field,
   highest payoff for encryption. Plan ~1-2 weeks of focused work; touches
   import dedup in 3+ services. Substring search likely becomes "exact-match
   + recent-values dropdown" or similar UX change. **Open question**: how
   to preserve `email__icontains` behavior in the global contact search.
2. **`Contact.phone` second** — lower volume of dependent code. Substring
   search probably moves to "last-4-digits hash" since users typically
   search phones by tail.
3. **`Gift.description`** — re-evaluate. This is *long-form text*, not an
   identifier. Blind-indexing only supports exact match, which doesn't help
   for free-text. Realistic options:
   - Drop search and accept the UX regression
   - Decrypt-on-the-fly over the visible scope (likely fine for typical
     query volumes — gifts are filtered by date/contact first)
   - Leave unencrypted and document the residual risk

### Phase 1B checklist

- [ ] `Contact.email` (largest piece, separate PR)
- [ ] `Contact.phone` (separate PR)
- [ ] `Gift.description` (decision required: encrypt-with-decrypt-search vs leave)

## Phase 2 — KMS envelope encryption

Documented in [encryption-rollout.md](encryption-rollout.md). Not in scope
for any near-term planning. The trigger to revisit Phase 2 is one of:

- A SOC 2 audit findings list that requires it
- A customer security questionnaire that asks specifically about KMS
- Evidence that a competitor's app-server compromise exposed PII

## Defer-and-document set

Columns the audit named that this plan explicitly does NOT encrypt in any
phase, with reasoning:

- **`PrayerIntention.description`** — Used in 3 dedup-on-iexact paths in
  the import services. Encrypting it without a blind-index breaks idempotent
  imports. Adding a blind-index is doable but a long-form free-text hash
  has limited security value (no two prayer intentions are likely to be
  identical anyway, so the hash leaks the singleton/non-singleton status of
  every value). **Recommendation**: refactor import dedup to use a stable
  external identifier instead of text comparison, then revisit. Tracked here,
  not in any phase.
- **`User.email`** — Used as login identifier. django-axes lockup keys on
  username. Encrypting it would require a hashed-login flow and breaks
  password-reset / email-verification. **Defer to Phase 3** with a normalized
  hash column.

## Operational notes

- This plan assumes `PII_ENCRYPTION_KEYS` is already set in Render env on
  every service running Django code (web + any worker/beat). If not, see
  [encryption-rollout.md](encryption-rollout.md) Step 2.
- Each migration must be tested against a Render preview environment before
  the production deploy. The preview env should have a non-trivial sample
  of real data shape (use a redacted snapshot).
- Production verification = `psql` query confirming the migrated column
  starts with `gAAAAA…`. Add this as the final step of every Phase 1A/1B
  deploy checklist item.
- The encryption module's legacy-plaintext sentinel (the `gAAAAA` prefix
  check in `EncryptedTextField.from_db_value`) is what makes per-column
  rolling deploys safe. Do **not** remove the sentinel until every column
  is fully migrated; it costs a single string-prefix check per row read.

## Status log

| Date | Phase | Column | Status |
|------|-------|--------|--------|
| 2026-05-07 | 1A | `Contact.notes` | in progress (this PR) |
