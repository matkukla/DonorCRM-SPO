# Project Research Summary

**Project:** DonorCRM v2.0 — RE Import Pipeline, Prayer Intentions, Dashboard Drag-and-Drop
**Domain:** Missionary CRM with Raiser's Edge integration, gift credit attribution, spiritual care tooling
**Researched:** 2026-02-20
**Confidence:** HIGH

## Executive Summary

DonorCRM v2.0 introduces a Raiser's Edge CSV import pipeline alongside the existing SPO import system, adds a Prayer Intentions feature powered by gift descriptions, and makes dashboard tiles draggable. The central architectural decision — confirmed by full codebase analysis across 77+ dependent files — is to add Gift/RecurringGift/Solicitor/GiftCredit models alongside the existing Donation/Pledge models rather than replacing them. A rename or replacement would require coordinated changes in 35+ backend files and 36+ frontend files spanning 8 Django apps, with high regression risk and zero user-visible benefit. The dual-model approach keeps all existing functionality intact while the RE pipeline writes exclusively to the new models; contact stats are unified by updating the single `Contact.update_giving_stats()` method to query both sources.

The recommended implementation sequence follows strict data dependency order: schema additions come first (additive-only migrations, no destructive changes), then the RE import backend (with SHA256 dedup and gift row grouping), then contact stat unification, then the import UI, then Prayer Intentions, and finally draggable dashboard tiles. This ordering reflects that the import pipeline is the primary data source for everything else — stats, prayers, and UI all depend on having imported data to work with. The only new frontend dependency for the entire milestone is `@dnd-kit/core` + `@dnd-kit/sortable` + `@dnd-kit/utilities` (3 packages totaling ~15KB); the backend requires zero new Python packages, leveraging stdlib `hashlib` and `csv` plus the existing Django migration framework.

The primary risk for this milestone is the RE CSV parsing layer. Raiser's Edge exports present four distinct failure modes: Windows-1252 encoding (smart quotes, accented names), multi-row split gifts that naive parsers duplicate, unstable SHA256 hashes caused by BOM markers and line-ending variations, and date format ambiguity between MM/DD/YYYY and DD/MM/YYYY. Every one of these must be handled in the import utility layer before integration tests run with real RE data. The solicitor-to-user name matching pattern (normalized exact match with an unmatched queue for ambiguous cases) is already proven in the MPD import and must be replicated exactly — fuzzy matching is explicitly ruled out as too prone to false positives that silently credit gifts to wrong missionaries.

## Key Findings

### Recommended Stack

The v2.0 milestone requires minimal stack additions. The backend requires zero new Python packages: `hashlib` (stdlib, Python 3.12 built-in) handles SHA256 file deduplication, Python's `csv.DictReader` (already used across the existing import pipeline) handles RE CSV parsing correctly by default, and Django's migration framework handles the additive schema changes. The one encoding caution: all RE import views must use `file.read().decode('utf-8-sig')` rather than plain `utf-8` to strip the Windows BOM bytes that RE/Excel emit, then fall back to `windows-1252` if UTF-8 decoding fails entirely.

On the frontend, the only new dependency is the `@dnd-kit` family: `@dnd-kit/core@6.3.1`, `@dnd-kit/sortable@10.0.0`, `@dnd-kit/utilities@3.2.2`. All three have `react: ">=16.8.0"` peer dependencies, which React 19.2.0 satisfies without `--legacy-peer-deps`. The alternatives are explicitly excluded: `react-beautiful-dnd` is archived, `@dnd-kit/react` is pre-1.0 with an unstable API, `@atlaskit/pragmatic-drag-and-drop` has known grid sort bugs.

**Core technologies:**
- `hashlib` (Python stdlib): SHA256 content hashing for ImportBatch dedup — zero dependency, C-implemented, ~15ms for 10MB files
- `csv.DictReader` (Python stdlib): RE CSV parsing — already in use throughout the codebase, handles RE quoting correctly by default
- Django additive migrations (`CreateModel`, `AddField`): schema additions only, no data migrations needed since Gift/RecurringGift are new tables alongside existing ones
- `@dnd-kit/core` + `@dnd-kit/sortable`: drag-and-drop dashboard tiles — React 19 compatible, native grid sorting strategy (`rectSortingStrategy`), keyboard accessible
- Django `through` model (`GiftCredit`): many-to-many Gift-to-Solicitor with per-solicitor amounts — standard ORM pattern, queryable and aggregatable via Django ORM `Sum()`

### Expected Features

**Must have (table stakes):**
- RE CSV import pipeline supporting all 4 types (Constituent, Solicitor, Gift, Recurring Gift) with exact RE header matching
- SHA256 file deduplication via ImportBatch model (UNIQUE on `import_type` + `sha256`, normalized before hashing)
- Gift row grouping by Gift ID before processing (RE exports one row per solicitor credit, not one row per gift)
- GiftCredit junction model for many-to-many Gift-to-Solicitor with per-solicitor credited amounts in cents
- Merge-only contact updates from Constituent import (never overwrite existing data with empty RE fields)
- Row-level error collection (continue on error, report all issues at end — never abort on first row failure)
- Idempotent upserts via external IDs (`update_or_create` on `external_gift_id` / `external_constituent_id`)
- PrayerIntention model with auto-creation from non-empty Gift description fields during import
- Today's Focus view with daily prayer list (prioritize un-prayed, oldest, round-robin across contacts)
- Manual prayer intention creation and "mark as prayed" action with `last_prayed_at` timestamp
- Draggable dashboard tiles with session-only state (`useState` only — resets on refresh, no persistence)
- Contact stat unification: `update_giving_stats()` queries both `self.donations` (existing) and `self.re_gifts` (new)

**Should have (differentiators):**
- Prayer page with chapel-like UX — amber palette, serif headings, generous spacing, deliberately distinct from dense CRM screens
- Solicitor-to-User auto-linking via normalized name matching (exact match only; ambiguous names go to unmatched queue for admin review)
- Visual drag feedback (DragOverlay ghost) and smooth tile reorder animations via dnd-kit transforms
- Import history view showing past ImportBatch records with status, row counts, and error logs
- Prayer Focus Mode with keyboard navigation (spacebar to mark prayed, arrow keys to move through queue)

**Defer to v2.1+:**
- Generic CSV import layer for contacts/donations (most users use RE imports; lower priority)
- Persistent tile order (explicitly out of scope per PROJECT.md — session-only is the decision)
- Prayer completion statistics ("you prayed for 12 people this week")
- Old Donation/Pledge table cleanup (keep as read-only backup during v2.0; drop in v2.1 after validation)
- `SolicitorAlias` table for manual admin linking of unmatched solicitors (admin resolves via UI in v2.1)

### Architecture Approach

The architecture is a dual-model additive system: Gift/RecurringGift/Solicitor/GiftCredit are added alongside the existing Donation/Pledge models, writing to separate tables, with Contact acting as the unified stat aggregation layer. Two new Django apps are created (`apps.solicitors`, `apps.prayer`) while new gift/recurring gift models are added directly to existing `apps.donations` and `apps.pledges` modules to avoid circular imports. The import app is extended with parallel RE-specific files (`re_services.py`, `re_views.py`, `re_utils.py`) without touching the existing SPO pipeline. Approximately 35 existing backend files and 36 existing frontend files remain completely unchanged.

**Major components:**
1. `apps.solicitors` (new app) — Solicitor model with `normalized_name` matching and `OneToOneField` User link; standalone app to avoid circular FK between donations and pledges
2. `apps.prayer` (new app) — PrayerIntention model, Today's Focus API, mark-as-prayed; dedicated route `/prayer` with chapel-like UX separate from dense CRM screens
3. `apps/imports/re_utils.py` (new file) — Shared parsing layer: `compute_import_hash()` (normalized, not raw bytes), `decode_csv_bytes()` (cascading UTF-8-sig > UTF-8 > Windows-1252), `parse_re_date()` (US formats only: `MM/DD/YYYY`, `YYYY-MM-DD`), `parse_currency()`
4. `apps/imports/re_services.py` (new file) — RE import pipeline: constituent importer (merge-only updates), solicitor importer (normalized upsert), gift importer (group by Gift ID, upsert Gift + GiftCredits), recurring gift importer (same pattern)
5. `apps/imports/re_views.py` (new file) — 4 import API endpoints + batch list/detail; all admin-only
6. `apps/contacts/models.py` — Modified `update_giving_stats()` to query both `self.donations` and `self.re_gifts`; this is the only existing method that changes
7. `Gift` + `GiftCredit` in `apps.donations` (new classes in existing file) — RE-specific gift with `fund_split_amount_cents` (integer cents, not decimal) and M2M solicitor credits via `through` model
8. `RecurringGift` + `RecurringGiftCredit` in `apps.pledges` (new classes in existing file) — RE recurring gifts with installment fields; same pattern as Gift
9. `ImportBatch` in `apps.imports` (new model in existing file) — parallel to existing ImportRun, with SHA256 dedup and 4-type status tracking (`constituent`, `solicitor`, `gift`, `recurring_gift`)
10. `Dashboard.tsx` (modified) — wrapped in `DndContext` + `SortableContext` with `rectSortingStrategy`; individual tile components themselves unchanged

### Critical Pitfalls

1. **Replacing Donation with Gift (77+ dependent references)** — Do NOT rename or replace. Add Gift/RecurringGift as new models alongside existing ones. Django's `RenameModel` migration handles the DB table but not string-based `related_name`, signal senders, EventType enum values, or frontend API paths. ~35 backend + 36 frontend files would require coordinated changes with total regression risk on every existing feature.

2. **SHA256 hash instability from encoding variations** — Do NOT hash raw file bytes. Normalize first: decode with `utf-8-sig` (strips BOM), normalize line endings (`\r\n` -> `\n`), strip trailing whitespace, then hash the canonical form. The same logical CSV file produces different raw byte sequences based on whether it passed through Excel, Git, or a text editor. This produces false positives (same data flagged as new) and false negatives (duplicate data not detected).

3. **RE multi-row split gifts creating duplicate records** — Group all CSV rows by Gift ID using `defaultdict(list)` BEFORE creating any Gift records. RE exports one row per solicitor credit, not one row per gift. The naive "one row = one record" approach causes unique constraint violations on `external_gift_id` and inflates `gift_count` on contacts.

4. **Windows-1252 encoding breaking the parser** — Use cascading decode: try `utf-8-sig` first (handles BOM), then `utf-8`, then fall back to `windows-1252`. RE is a Windows application; names with accents (José), smart quotes in notes, and em-dashes in addresses use byte values that are invalid UTF-8 and will raise `UnicodeDecodeError` if decoded as UTF-8.

5. **Contact stats not updating when Gift records are created** — Wire Gift `post_save`/`post_delete` signals in `donations/signals.py` from day one (Phase 1). The existing `update_giving_stats()` only queries `self.donations.all()`. Until updated to also query `self.re_gifts`, any Gift records created through the new pipeline will show $0 on the dashboard. During bulk imports, disable signals and recalculate stats once per affected contact at batch completion.

6. **Solicitor false-matching crediting gifts to wrong missionaries** — Use exact normalized name matching only (lowercase, strip titles/suffixes/punctuation, handle "Last, First" RE format). When multiple users match or zero users match, send to unmatched queue for admin review. Never use fuzzy matching — a false positive silently inflates one missionary's support total while zeroing out another's, creating data integrity errors that are hard to detect and hard to undo.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation Schema (Additive Models + Migrations)

**Rationale:** All subsequent phases depend on new tables existing. Creating models before any import logic ensures clean dependency ordering and zero risk to existing functionality. All changes are additive: new tables via `CreateModel`, new nullable fields on Contact via `AddField`. No existing table structure changes.

**Delivers:** Seven new Django models fully migrated — Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor, PrayerIntention, ImportBatch. Four new Contact fields (`external_constituent_id`, `organization_name`, `address_line_2`, `re_last_changed_at`). Two new Django apps registered in settings (`apps.solicitors`, `apps.prayer`).

**Addresses:** RE import table stakes (models are the prerequisite), gift credit splitting (GiftCredit through model), prayer intentions (PrayerIntention model)

**Avoids:** Pitfall #1 (no rename/replace of Donation — additive only), Pitfall #7 from PITFALLS.md (additive schema means no UUID conflicts, no GenericForeignKey migration needed)

**Research flag:** Standard Django patterns — skip research-phase. `CreateModel` and `AddField` migrations are well-documented and already used throughout the codebase.

### Phase 2: RE Import Backend

**Rationale:** The import pipeline is the primary way data enters the new models. Building and testing this before any UI ensures the backend is solid before the frontend is built on top of it. Real RE CSV edge cases (encoding, split gifts, date formats) must be discovered in backend unit tests, not during UI integration testing.

**Delivers:** `re_utils.py` (SHA256 normalized hashing, cascading encoding decode, RE-specific date parser, currency parser), `re_services.py` (constituent, solicitor, gift, recurring_gift importers with row grouping and merge-only updates), `re_views.py` (4 import endpoints + batch list/detail), URL routing in `imports/urls.py`. Fully tested with real RE CSV fixtures including split gifts, accented names, and BOM variants.

**Uses:** Python `hashlib` (stdlib), Python `csv.DictReader` (with `utf-8-sig` + `windows-1252` fallback), Django ORM `update_or_create` for idempotent upserts

**Avoids:** Pitfall #3 (normalized SHA256 before hashing), Pitfall #4 (cascading encoding detection), Pitfall #5 (gift row grouping before record creation), Pitfall #6 (exact normalized solicitor matching with unmatched queue), Pitfall #9 from PITFALLS.md (US-only date formats for RE imports)

**Research flag:** Well-documented service layer patterns. However, validate with REAL RE CSV files before considering this phase complete — edge cases only manifest with actual production exports.

### Phase 3: Contact Stat Unification

**Rationale:** Dashboard and insights already read contact-level aggregate stats (`total_given`, `gift_count`, `last_gift_date`). By updating `update_giving_stats()` to query both Donation and Gift sources, the existing UI automatically reflects RE gift data without any frontend changes. This must come before the import UI so that when admins import their first RE file, the dashboard immediately shows correct numbers.

**Delivers:** Modified `Contact.update_giving_stats()` querying both `self.donations` and `self.re_gifts`, merging results (sum totals, min of first dates, max of last dates). New Gift `post_save`/`post_delete` signals in `donations/signals.py`. Management command `recalculate_contact_stats` for post-import backfill. Tests verifying stats are correct with Donation-only, Gift-only, and combined data.

**Avoids:** Pitfall #2 from PITFALLS.md (stats hardcoded to donations showing $0 after RE import), Pitfall #10 from PITFALLS.md (signal storms during bulk import — use `disable_donation_signals()` equivalent + batch recalc once per contact at end)

**Research flag:** Standard pattern — skip research-phase. The existing `disable_donation_signals()` threading.local mechanism is the model to replicate for Gift signals. The stat merge logic is straightforward aggregate arithmetic.

### Phase 4: RE Import UI (Frontend)

**Rationale:** The stable backend from Phase 2 provides the API. Build the admin-facing import interface now. This is low-risk (new page, minimal changes to existing files) and delivers the complete import workflow end-to-end.

**Delivers:** `REImport.tsx` page at `/admin/re-import` with 4 tabs (Constituent, Solicitor, Gift, Recurring Gift), file upload with drag-drop per tab, import result banners (success/error/already-processed), required header reference per import type, import order guidance (constituents before gifts), import history list showing past ImportBatch records. RE import tile added to `ImportCenter.tsx`. Route added to `App.tsx`.

**Avoids:** Architecture anti-pattern #5 from ARCHITECTURE.md (UI built before backend is tested with real data)

**Research flag:** Standard React + TanStack Query patterns — skip research-phase. File upload pattern already exists in the SPO import pages; extend that pattern.

### Phase 5: Prayer Intentions

**Rationale:** Prayer is a standalone feature with its own page, API, and UX philosophy. It depends on Gift import (Phase 2) for auto-creation from gift descriptions and on the PrayerIntention model (Phase 1). No dependencies on Phases 3 or 4 — can be parallelized with Phase 4 if capacity allows.

**Delivers:** Backend prayer CRUD API (`/api/v1/prayer/intentions/`), Today's Focus endpoint, mark-as-prayed action. Post-import hook in `re_services.py` creating PrayerIntentions from non-empty Gift descriptions (deduplicated by `contact` + `text` to prevent re-import duplicates). `PrayerPage.tsx` at `/prayer` with chapel-like UX (amber palette, serif headings, calming design). Prayer nav item in `Sidebar.tsx`. Route in `App.tsx`.

**Avoids:** Architecture anti-pattern #4 from ARCHITECTURE.md (prayer as a Contact tab — must be a dedicated route to preserve the chapel UX). UX pitfall of auto-creating prayer intentions from RE description codes rather than actual prayer text (filter: only auto-create when the description contains text that reads as a prayer request).

**Research flag:** UX philosophy and verification checklist are detailed in `prompts/prayer_intentions.md`. Skip research-phase; follow the spec closely. The Today's Focus algorithm (prioritize un-prayed, oldest, round-robin) needs implementation but not research.

### Phase 6: Dashboard Draggable Tiles

**Rationale:** Fully independent of all other v2.0 work — no model dependencies, no data requirements. The lowest-risk phase: wrapping existing tile components in `SortableContext` is additive, and the individual tile components themselves need no changes. Placed last because it is UX polish rather than data infrastructure.

**Delivers:** `DndContext` + `SortableContext` with `rectSortingStrategy` wrapping the existing dashboard grid. `useState` for tile order (session-only — resets on refresh, no persistence). `DragOverlay` for visual ghost feedback during drag. Drag handle indicator on tile headers to prevent accidental drags. `@dnd-kit/core@6.3.1` + `@dnd-kit/sortable@10.0.0` + `@dnd-kit/utilities@3.2.2` installed via npm.

**Uses:** `@dnd-kit` family (the only new npm dependency for the entire v2.0 milestone)

**Avoids:** Using archived `react-beautiful-dnd`, using pre-1.0 `@dnd-kit/react` (missing "use client" for React 19, no stable sortable example), adding localStorage persistence (explicitly out of scope per PROJECT.md)

**Research flag:** Standard dnd-kit sortable grid pattern — skip research-phase. Docs at dndkit.com are comprehensive; `rectSortingStrategy` + `closestCenter` collision detection is the documented approach for grid reorder.

### Phase Ordering Rationale

- **Models before everything:** All import logic, stats, and UI depend on tables existing — additive schema changes are safe to ship and cannot regress existing functionality
- **Import backend before import UI:** Real RE CSV edge cases must be discovered in service layer unit tests before UI integration obscures root causes
- **Stats unification before import UI:** The first admin import should immediately show correct dashboard numbers — discovering the stat bug after the UI ships creates a confusing "import worked but dashboard shows $0" failure mode
- **Prayer and draggable tiles last:** Both are independent of the data pipeline and can slide without blocking the core RE import milestone if earlier phases encounter delays
- **Prayer can parallelize with Phase 4:** Once Phase 1 and Phase 2 are complete, Prayer Intentions has no dependency on the import UI or stat unification

### Research Flags

**Needs additional research during planning:**
- **Phase 2 RE import backend:** Validate actual RE CSV column ordering and real-world encoding behavior with production-exported files before finalizing header validation logic. The exact headers are specified in `prompts/CSV_import_system_2.md` but encoding and column ordering behavior vary by RE configuration and export method.

**Standard patterns (skip research-phase):**
- **Phase 1** (Foundation Schema): Django `CreateModel` and `AddField` migrations are thoroughly documented; pattern is already used throughout the codebase
- **Phase 3** (Contact Stat Unification): Pattern exactly mirrors the existing `update_giving_stats()` + signals architecture; extension, not new pattern
- **Phase 4** (RE Import UI): Standard React file upload + TanStack Query patterns already in use in SPO import pages
- **Phase 5** (Prayer Intentions): Feature spec detailed in `prompts/prayer_intentions.md`; UX philosophy is clear and actionable
- **Phase 6** (Dashboard Draggable Tiles): dnd-kit sortable grid is a documented, straightforward integration with `rectSortingStrategy`

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Only 1 new npm dependency (3 packages); all peer deps verified via npm CLI; Python additions are stdlib only with no version concerns |
| Features | HIGH | Exact CSV headers confirmed from production RE exports in `prompts/CSV_import_system_2.md`; prayer feature spec from `prompts/prayer_intentions.md` |
| Architecture | HIGH | Based on full codebase analysis of 35+ backend files and 36+ frontend files; dual-model additive decision is conclusive with quantified blast-radius |
| Pitfalls | HIGH | Each pitfall verified against actual code paths (`apps/donations/signals.py`, `contacts/models.py:152-188`, etc.) and RE-specific external research on encoding/split-gift behavior |

**Overall confidence:** HIGH

### Gaps to Address

- **SHA256 normalization with real RE files:** The normalized hashing strategy (strip BOM, normalize line endings, sort rows before hashing) is theoretically sound but should be validated against actual RE-exported CSV files in multiple conditions (direct RE export, via Excel, via email attachment) before the ImportBatch unique constraint is enforced. False positives (duplicate detection when the file is actually new) are more disruptive than false negatives.

- **Solicitor name format from RE ("Last, First" vs "First Last"):** Research indicates RE may export `Smith, John` or `John Smith` depending on configuration and export template. The `parse_solicitor_name()` function handles both cases, but the actual format used by this specific RE installation should be confirmed with an admin before Phase 2 ships.

- **Prayer intention deduplication boundary:** The spec deduplicates by `(contact, text)` to prevent re-import duplicates. If the same prayer text appears across multiple gifts from the same donor, the dedup logic must decide whether to create one intention or multiple. Confirm the intended behavior with the product owner before building the post-import hook in `re_services.py`.

- **`external_id` vs `external_constituent_id` scoping:** The existing `external_id` on Contact is owner-scoped (unique per owner + external_id). The new `external_constituent_id` is globally unique. The Constituent importer must write to `external_constituent_id` only — confirm this does not conflict with any existing code that reads `external_id` expecting the RE constituent ID.

## Sources

### Primary (HIGH confidence)
- `prompts/CSV_import_system_1.md`, `prompts/CSV_import_system_2.md` — Exact RE CSV headers, model schemas, import logic (production specs)
- `prompts/prayer_intentions.md` — Prayer UX philosophy and verification checklist
- Codebase analysis: `apps/contacts/models.py:152-188`, `apps/donations/signals.py`, `apps/dashboard/services.py`, `apps/insights/services.py`, `apps/imports/services.py` — existing architecture patterns and dependency graph
- npm CLI: `@dnd-kit/core@6.3.1`, `@dnd-kit/sortable@10.0.0` peer deps verified via `npm view`
- Python 3.12 docs: `hashlib`, `csv` module — stdlib availability and behavior confirmed

### Secondary (MEDIUM confidence)
- [Blackbaud community: RENXT-I-8179](https://renxt.ideas.aha.io/ideas/RENXT-I-8179) — split gifts export to multiple rows per solicitor credit
- [Arkus: Why RE Migrations are Difficult](https://www.arkusinc.com/archive/2020/its-not-just-your-org-why-raisers-edge-migrations-are-difficult) — gift complexity, denormalized exports, encoding
- [devgem.io: SHA256 and line endings](https://www.devgem.io/posts/resolving-sha256-hash-mismatch-in-net-tests-line-endings-matter) — hash instability from CRLF vs LF normalization
- [Wikipedia: Windows-1252](https://en.wikipedia.org/wiki/Windows-1252) — byte values for smart quotes, accented characters vs UTF-8
- [HackSoft: Django model renaming](https://www.hacksoft.io/blog/renaming-models-in-django-without-heavy-data-migrations) — RenameModel limitations vs new model strategy
- [dnd-kit docs: sortable](https://dndkit.com/presets/sortable) — SortableContext, useSortable, rectSortingStrategy

### Tertiary (LOW confidence — assumptions to validate)
- RE exports in Windows-1252 by default (web research consensus; specific RE version or export template may differ)
- Solicitor name format ("Last, First" vs "First Last") is installation-specific and not globally documented

---
*Research completed: 2026-02-20*
*Ready for roadmap: yes*
