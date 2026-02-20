# Feature Landscape

**Domain:** DonorCRM v2.0 -- RE Import, Gift Credits, Prayer Intentions, Draggable Dashboard
**Researched:** 2026-02-20
**Overall confidence:** HIGH (exact CSV headers, data model specs, and UX requirements confirmed via project prompts and external research)

---

## 1. Raiser's Edge CSV Import Pipeline

### Context

The existing SPO import system (Funds, Entities, Transactions, Pledges) is being **replaced** with a Raiser's Edge-compatible pipeline. The new system imports 4 CSV types that RE admins export daily (5 days/week). The exact CSV headers are fixed -- they come from Raiser's Edge and cannot be modified.

### Table Stakes

Features users (admins importing CSVs) absolutely expect.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 4 CSV type support (Constituent, Solicitor, Gift, Recurring Gift) | These are the exact exports RE produces | High | Each type has different headers, validation rules, and FK relationships |
| Exact RE header matching | Headers come from RE exports, cannot be changed | Low | Must match exactly: "Constituent ID", "Gift Date", "Fund Split Amount", etc. |
| SHA256 file deduplication (ImportBatch) | Admins upload daily; same file must not be re-imported | Med | UNIQUE(type, sha256) constraint prevents duplicate processing |
| Row-level error collection (continue on error) | Admin needs to see ALL errors at once, not one-at-a-time | Med | Never stop on row error -- process all rows, collect errors, return report |
| Import order enforcement (Constituents -> Solicitors -> Gifts -> Recurring Gifts) | Gifts reference Constituents by external ID; must exist first | Low | UI displays order, Gift import skips rows where Constituent ID is missing |
| Gift row grouping by Gift ID | RE exports multiple rows per gift (one per solicitor credit) | High | Must GROUP by Gift ID, create one Gift record + multiple GiftCredit records |
| Idempotent upserts via external IDs | Safe to run daily without duplicating data | Med | Match by externalGiftId/externalConstituentId, update if exists |
| Import result reporting (created/updated/skipped/errors) | Admin needs to know what happened | Low | Return totals object + row-level errors with row numbers |
| Already-processed detection | Re-uploading same file should tell admin it was already imported | Low | SHA256 match returns cached result with alreadyProcessed flag |

### Differentiators

Features that set the import apart from basic CSV upload.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Prayer intention auto-creation from gift descriptions | RE "Gift Specific Attributes Prayer Requests Description" field creates PrayerIntention records automatically | Med | Unique to missionary CRM -- connects financial data to spiritual care |
| Solicitor-to-User auto-linking | Match imported Solicitor names to existing User accounts (missionaries) | Med | normalizedName matching; enables gift credit attribution to actual users |
| Merge-only updates (never overwrite with null) | Existing data preserved when RE export has empty fields | Low | Critical for maintaining manually-entered data alongside imports |
| Generic CSV import layer (contacts, donations) | For orgs not using RE, or for manual data entry via CSV | Med | Separate from RE pipeline; user-scoped processing |

### Anti-Features

Features to explicitly NOT build for v2.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Import undo/rollback | Massive complexity, ImportBatch records are immutable | Admin re-uploads corrected file; SHA256 dedup prevents exact-file reprocessing |
| Automated RE API connection | Requires Blackbaud API credentials, OAuth setup, rate limiting | Manual CSV upload is sufficient for daily workflow |
| Column mapping UI for RE imports | RE headers are fixed and known; mapping adds unnecessary complexity | Validate exact headers, reject if missing |
| Async/Celery import processing | Overkill for the file sizes being imported (<10MB, <5000 rows) | Synchronous processing with file size limit (10 MB) |
| Import scheduling/cron | Admin manually exports from RE daily | Manual upload with Import Center UI |

### Exact CSV Headers (from project specs -- HIGH confidence)

**Constituent CSV:**
- Constituent Date Last Changed, Constituent ID, First Name, Last Name, Organization Name, Address Line 1, Address Line 2, City, State, ZIP, Country, Phone, Email

**Solicitor CSV:**
- Name

**Gift CSV:**
- Gift ID, Gift Date Last Changed, Gift Date, Gift Type, Fund ID, Fund Split Amount, Constituent ID, Gift Is Anonymous, Solicitor Name, Solicitor Amount, Gift Payment Type, Gift Specific Attributes Prayer Requests Description

**Recurring Gift CSV:**
- Gift ID, Gift Date Last Changed, Gift Date, Gift Type, Gift First Installment Due, Last Installment/Payment Date Due, Gift Installment Frequency, Number of Installments Scheduled, Gift First Installment Due_1, Fund ID, Constituent ID, Gift Is Anonymous, Solicitor Name, Solicitor Amount, Gift Payment Type, Gift Status, Gift Status Date, Gift Specific Attributes Prayer Requests Description

---

## 2. Gift Credit Splitting

### Context

In Raiser's Edge, one gift can credit multiple missionaries (solicitors). The RE CSV exports this as **multiple rows with the same Gift ID** but different Solicitor Name/Solicitor Amount values. This is the core data relationship that makes DonorCRM valuable for missionary organizations -- each missionary sees the gifts they are credited for, even when the donor gave to a shared fund.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| GiftCredit junction model (Gift <-> Solicitor many-to-many) | One gift credits multiple missionaries | Med | Fields: giftId, solicitorId, solicitorName, solicitorAmountCents |
| RecurringGiftCredit (same pattern for recurring gifts) | Recurring gifts also have multiple solicitor credits | Med | Identical structure to GiftCredit but FK to RecurringGift |
| Credit amounts in cents | Each solicitor's credited amount may differ from total gift amount | Low | e.g., $200 gift with $100 to Missionary A and $100 to Missionary B |
| Display credits on gift detail | Missionary sees who else was credited for same gift | Low | List of solicitor names + amounts on gift detail view |
| Per-missionary gift totals | Each missionary sees total gifts credited to them | Med | SUM(GiftCredit.solicitorAmountCents) WHERE solicitorId matches User |
| Owner-scoped gift visibility | Missionaries see gifts credited to them, admin sees all | Med | Filter gifts through GiftCredit -> Solicitor -> User relationship |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Visual credit breakdown on gift card | Show "You: $100 / Total: $200" with proportional bar | Low | Makes split nature immediately clear |
| Dashboard summary using credited amounts | Dashboard shows missionary's credited total, not raw gift total | Med | Must aggregate through GiftCredit, not Gift directly |
| Solicitor-to-User auto-linking | Solicitor records auto-link to User accounts by normalized name matching | Med | Enables "my gifts" view without manual assignment |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Manual credit splitting UI | Credits come from RE imports, not manual entry | Import-only creation; manual gifts use existing Donation model |
| Percentage-based splits | RE provides absolute amounts per solicitor | Store cents, not percentages |
| Credit editing | Would desync from RE data on next import | Credits are immutable once imported; re-import to update |

### UI Display Pattern

Based on nonprofit CRM research (Beacon CRM, Neon CRM, Salesforce NPSP), the standard pattern for displaying gift credits is:

**Gift Detail View:**
```
Gift #G003 -- $200.00 -- 01/17/2024
  Donor: John Smith
  Fund: FUND002

  Credit Split:
  +---------------------+----------+
  | Missionary          | Amount   |
  +---------------------+----------+
  | John Missionary     | $100.00  |
  | Jane Evangelist     | $100.00  |
  +---------------------+----------+
```

**Gift List View (per missionary):**
- Show only gifts where the current user has a GiftCredit record
- Display the solicitor amount (credited amount), not the total gift amount
- Badge or indicator when gift is split across multiple missionaries

---

## 3. Prayer Intentions

### Context

Missionaries are called to pray for their financial partners, not just ask them for money. The "Gift Specific Attributes Prayer Requests Description" field from RE imports contains prayer requests that donors submit with their gifts. This feature surfaces those requests and lets missionaries track their prayer life around donor relationships.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| PrayerIntention model tied to Contact | Each prayer intention belongs to a specific donor/contact | Low | Fields: contactId, text, source (manual/import), status |
| Status tracking (active/prayed/answered) | Missionaries need to know what they have and have not prayed for | Low | Simple status field with transitions |
| Auto-creation from RE gift descriptions | Import pipeline creates PrayerIntention from non-empty "Prayer Requests Description" | Med | During Gift/RecurringGift import, if description field is non-empty, create PrayerIntention |
| Manual intention creation | Missionaries add prayer requests from conversations, not just imports | Low | Simple form: contact selector + text input |
| Today's Focus view | Daily curated list of intentions to pray through | Med | Algorithm: prioritize un-prayed, oldest, round-robin across contacts |
| "Mark as prayed" action | Track that missionary prayed for this intention today | Low | Updates lastPrayedAt timestamp, optimistic UI update |
| Contact detail integration (Prayer tab) | See all prayer intentions for a specific contact | Low | New tab on contact detail page, list of intentions with status |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Focus Mode (guided prayer experience) | Immersive, one-at-a-time prayer walkthrough with keyboard shortcuts | Med | Full-screen card, arrow keys to navigate, spacebar to mark prayed |
| Warm/calming visual design | Page should feel like a chapel, not a dashboard | Low | Amber palette, serif headings, generous spacing, minimal cognitive load |
| Completion screen | After praying through Today's Focus, show count of prayers completed | Low | Motivational, not gamified -- "You prayed for 12 people today" |
| Prayer history per contact | Timeline of when missionary prayed for each contact | Low | Uses lastPrayedAt timestamps to show prayer frequency |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Prayer reminders/notifications | No email infrastructure; push notifications add complexity | Today's Focus page is the reminder -- open daily |
| Prayer group sharing | Multi-user prayer lists add permission complexity | Each missionary manages their own prayer life |
| Prayer request submission by donors | Would require donor-facing portal | Prayer data comes from RE imports or manual missionary entry |
| Answered prayer analytics | Could feel like gamification of spiritual practice | Simple "answered" status is sufficient |
| Expiration/archival automation | Prayer intentions should not expire automatically | Manual status changes only |

### Common Patterns from Church CRM Research

Based on research of Planning Center, Echo Prayer, ChurchCMS, Breeze, and iPrayerworks:

1. **Status model**: Active -> Prayed -> Answered (with "Prayed" being repeatable, not terminal)
2. **Source tracking**: Distinguish between imported requests and manually entered ones
3. **Daily focus**: Curate a manageable subset of prayer intentions for daily use (not the full list)
4. **Warm UI**: Every successful church prayer tool emphasizes calm, inviting design over data density
5. **Contact linkage**: Prayer requests always tie to a person, enabling relational context

### Data Flow: Import-to-Prayer Pipeline

```
RE Gift CSV -> Gift Import Service
  -> If "Gift Specific Attributes Prayer Requests Description" is non-empty:
    -> Find Contact by externalConstituentId
    -> Create PrayerIntention(contact=contact, text=description, source='import')
    -> Deduplicate by (contact, text) to avoid duplicates on re-import
```

---

## 4. Draggable Dashboard Tiles

### Context

The existing Dashboard has a fixed layout with hardcoded grid positions. v2.0 adds the ability for users to drag and reorder dashboard tiles to customize their view. Per PROJECT.md, this is **session-only with no persistence** -- tile order resets on page refresh.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Drag-and-drop reorder of dashboard tiles | Users can arrange tiles to prioritize what matters to them | Med | Use dnd-kit with rectSortingStrategy for grid-based sorting |
| Visual drag feedback (ghost/overlay) | User needs to see what they are dragging and where it will land | Low | DragOverlay component from dnd-kit |
| Smooth animations on reorder | Tiles should animate to new positions, not jump | Low | Built into dnd-kit's transform/transition system |
| Session-only state (no persistence) | Tile order resets on page refresh | Low | useState only -- no localStorage, no API call, no URL params |
| Touch and pointer support | Works on both desktop mouse and mobile touch | Low | dnd-kit's PointerSensor and TouchSensor handle this |
| Keyboard accessibility | Drag-and-drop should work with keyboard only | Low | dnd-kit has built-in KeyboardSensor with ARIA announcements |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Drag handle indicator | Small grip icon on tile header to indicate draggability | Low | Prevents accidental drags when clicking tile content |
| Tile span awareness | Tiles that span 2 columns (e.g., GivingSummaryCard) should maintain their width during drag | Med | May need custom collision detection for mixed-size tiles |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Persistent tile order (localStorage or API) | Adds complexity; PROJECT.md explicitly says session-only | Reset to default order on page refresh |
| Tile resizing | react-grid-layout supports this but adds significant complexity | Fixed tile sizes, drag to reorder only |
| Tile add/remove | Would require tile visibility preferences and persistence | All tiles always visible |
| Multi-column drag (changing tile width) | Complex collision detection for variable-width items | Fixed column spans per tile |
| Responsive breakpoint layouts | Would need separate layout configs per breakpoint | Keep existing responsive grid; drag only changes order within current breakpoint |

### Library Choice: dnd-kit

**Use `@dnd-kit/core` + `@dnd-kit/sortable` because:**

1. Modern, lightweight, actively maintained (unlike react-beautiful-dnd which is deprecated)
2. Built-in sortable preset with `rectSortingStrategy` for grids
3. Keyboard + screen reader accessibility out of the box
4. No jQuery or legacy dependencies
5. Already the React ecosystem standard for drag-and-drop in 2025-2026

**NOT react-grid-layout because:**
- Includes resizing which we do not need and cannot easily disable
- Heavier bundle size for features we will not use
- Designed for persistent layout management, not session-only reorder

### Implementation Pattern

```tsx
// Dashboard.tsx -- conceptual pattern
const [tileOrder, setTileOrder] = useState([
  'giving-summary', 'monthly-gifts', 'thank-you-queue',
  'recent-donations', 'active-pledges', 'needs-attention',
  'support-progress', 'journal-activity', 'late-donations',
  'mpd-overview'
]);

// DndContext + SortableContext with rectSortingStrategy
// Each tile wrapped in useSortable hook
// onDragEnd -> arrayMove(tileOrder, oldIndex, newIndex)
// State resets on page refresh (no persistence)
```

### Existing Dashboard Tiles to Make Draggable

Based on the current Dashboard.tsx:

| Tile | Current Grid Position | Spans |
|------|----------------------|-------|
| GivingSummaryCard | lg:grid-cols-2 (left) | Full width of column |
| MonthlyGiftsCard | lg:grid-cols-2 (right) | Full width of column |
| StatCard x4 | md:grid-cols-2 lg:grid-cols-4 | 1 column each |
| MPDStatsInline | md:grid-cols-3 | 1 column each (3 cards) |
| NeedsAttention | lg:grid-cols-2 (left) | Full width of column |
| SupportProgress | lg:grid-cols-2 (left) | Full width of column |
| RecentDonations | lg:grid-cols-2 (right) | Full width of column |
| RecentJournalActivity | lg:grid-cols-2 (right) | Full width of column |
| LateDonations | lg:grid-cols-2 (right) | Full width of column |

**Simplification for v2.0:** Treat all tiles as equal-width items in a single sortable list. The existing CSS grid layout with `lg:grid-cols-2` naturally places items in two columns. Reordering changes which tiles appear in which column based on DOM order.

---

## 5. Supporting Features (Data Migration and UI Rename)

### Data Migration: Donations -> Gifts, Pledges -> RecurringGifts

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Migrate existing Donation records to Gift model | Preserve all historical data | High | Map fields: amount, date, contact, external_id, fund, etc. |
| Migrate existing Pledge records to RecurringGift model | Preserve pledge histories | High | Map fields: amount, frequency, status, contact, etc. |
| Preserve denormalized Contact stats | total_given, gift_count, etc. must remain accurate | Med | Recalculate from new Gift model after migration |
| Update all dashboard queries to use Gift model | Dashboard aggregations reference donations table | Med | Services.py functions must query Gift + GiftCredit instead of Donation |

### UI Rename: "Donations" -> "Gifts", "Pledges" -> "Recurring Gifts"

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Navigation label changes | Consistency with RE terminology | Low | Sidebar, breadcrumbs, page titles |
| List page headers | "Gifts" instead of "Donations" | Low | Find-replace across page components |
| Filter labels | Update all filter option labels | Low | FilterBar configurations |
| CSV export headers | Export column names match new terminology | Low | Serializer field labels |

---

## Feature Dependencies

```
                    +-------------------+
                    |  Contact Model    |
                    |  (existing, add   |
                    |  externalConstID) |
                    +-------------------+
                         |          |
              +----------+          +----------+
              |                                |
     +--------v--------+             +--------v--------+
     | Solicitor Model |             | PrayerIntention |
     | (new)           |             | Model (new)     |
     +---------+-------+             +-----------------+
               |                              ^
     +---------v-------+                      |
     | Gift Model      |---------------------+
     | (new)           |  auto-creates from
     +---------+-------+  description field
               |
     +---------v-------+
     | GiftCredit      |
     | (new, junction) |
     +-----------------+

     RecurringGift + RecurringGiftCredit follow same pattern as Gift + GiftCredit

     Draggable Dashboard Tiles: No model dependencies. Frontend-only feature.
```

**Build order constraints:**
1. **Contact model updates** (add externalConstituentId) must come first
2. **Solicitor model** before Gift import (solicitors referenced in gift rows)
3. **Gift + GiftCredit models** before Gift import service
4. **RecurringGift + RecurringGiftCredit** before Recurring Gift import service
5. **Import services** (Constituent -> Solicitor -> Gift -> Recurring Gift) in dependency order
6. **Data migration** (Donation -> Gift, Pledge -> RecurringGift) after new models exist
7. **PrayerIntention model** can be built in parallel with or after Gift import
8. **Prayer auto-creation** requires Gift import service to be functional
9. **Draggable dashboard** is fully independent -- can be built at any point
10. **UI rename** should happen after data migration so old pages still work during transition

---

## MVP Recommendation

### Must Have (v2.0 Launch):

1. **New data models** (Solicitor, Gift, GiftCredit, RecurringGift, RecurringGiftCredit, ImportBatch, PrayerIntention) -- Foundation for everything else.
2. **RE Import Pipeline** (all 4 types with row grouping and SHA256 dedup) -- Core value. Without it, no RE data enters the system.
3. **Gift credit splitting** (display + per-missionary visibility) -- Meaningless to import gifts without proper credit attribution.
4. **Data migration** (existing Donations -> Gifts, Pledges -> RecurringGifts) -- Existing data must be preserved.
5. **UI updates** (rename Donations -> Gifts, Pledges -> Recurring Gifts, update all dependent features) -- Consistency with new model names.
6. **Prayer Intentions** (model + auto-creation from imports + Today's Focus view + Contact tab) -- Unique differentiator.
7. **Draggable dashboard tiles** (session-only with dnd-kit) -- Low complexity, high perceived polish.

### Defer to v2.1:

- **Generic CSV import layer** (contacts, donations): Most users will use RE imports. Separate generic layer is lower priority.
- **Focus Mode for prayer**: The Today's Focus list view is sufficient for launch. Full immersive Focus Mode with keyboard shortcuts is polish.
- **Persistent tile order**: Explicitly out of scope per PROJECT.md. Session-only is the decision.
- **Prayer completion statistics**: "You prayed for 12 people this week" -- nice but not launch-critical.

---

## Sources

### Raiser's Edge CSV Format
- [Exporting Raiser's Edge for CiviCRM (Megaphone)](https://hq.megaphonetech.com/projects/commons/wiki/Exporting_Raisers_Edge_for_CiviCRM) -- RE export structure, table relationships, CONSTIT_SOLICITORS table
- [Split Gift Import (Blackbaud KB)](https://blackbaud.my.salesforce-sites.com/bbknowledge/articles/Article/38556) -- GSplitFund, GSplitAmt, GSplitCamp headers
- [RE NXT Gift Export (GiveCampus)](https://support.givecampus.com/hc/en-us/articles/29093884332311-Raiser-s-Edge-NXT-Integration-Gift-Export-Setup-Management) -- Gift export field list
- [Importing Recurring Gift Schedules (Omatic)](https://omaticsoftware.com/blog/importing-recurring-gift-schedules-to-the-raisers-edge/) -- Recurring gift field structure
- [RE NXT Split Gift Export Ideas (Blackbaud)](https://renxt.ideas.aha.io/ideas/RENXT-I-8179) -- Split gift export to multiple rows behavior
- [Split Gift Mapping (Zeidman/Importacular)](https://www.zeidman.info/docs/importacular-user-guide-3/import-to-gift/split-gift-mapping/) -- Split gift data model
- [Fundraising Report Card RE Setup](https://fundraisingreportcard.com/help/raisers-edge/) -- Constituent ID, Gift Date, Gift Amount field names
- [Recurring Gift Schedules (RE-Decoded)](https://www.re-decoded.com/2009/08/recurring-gift-schedules/) -- GIFT_fld_Installment_Frequency, GIFT_fld_Date_1st_Pay
- Project prompts: `/prompts/CSV_import_system_1.md`, `/prompts/CSV_import_system_2.md` -- Exact CSV headers and data model specs (HIGH confidence)

### Gift Credit Splitting
- [Nonprofit Gift Coding: Solicitor Credit vs. Soft Credit (LinkedIn)](https://www.linkedin.com/pulse/nonprofit-gift-coding-solicitor-credit-vs-soft-rebel-saffold-iii) -- Hard/soft credit patterns in nonprofit CRMs
- [Recording Soft Credits (Beacon CRM)](https://guide.beaconcrm.org/en/articles/6817580-recording-soft-credits) -- Split payment UI pattern
- [Why You Should Use Soft Credits (Neon One)](https://neonone.com/resources/blog/soft-credits/) -- Soft credit reporting patterns
- [RE NXT Solicitor Ideas (Blackbaud)](https://renxt.ideas.aha.io/ideas/NXT-I-42) -- Solicitor/Fundraiser type in RE
- [Hard or Soft Credit (FreeLikeAPuppy)](https://www.freelikeapuppy.tech/post/hard-or-soft-credit-where-credit-is-due-part-1) -- Credit types explained
- [Salesforce NPSP Soft Credits (Mirketa)](https://mirketa.com/unleashing-soft-credit-and-marketing-gift-in-nonprofit-cloud-a-revolutionary-approach-to-fundraising/) -- Salesforce soft credit model

### Prayer Intentions
- [Echo Prayer App](https://www.echoprayer.com/) -- Prayer status tracking, reminders, "mark as answered"
- [iPrayerworks](https://iprayerworks.com/requests.cfm) -- Prayer request management for prayer teams
- [ChurchSpring Prayer Tool](https://churchspring.com/prayer/) -- Prayer status updates, member profile integration
- [Planning Center People](https://www.planningcenter.com/people) -- Prayer request via forms, workflow automation, note notifications
- [Breeze ChMS Prayer Requests](https://support.breezechms.com/hc/en-us/articles/360019590934-Storing-Prayer-Requests) -- Prayer request storage patterns
- [DonorElf](https://www.donorelf.com/) -- Missionary CRM with prayer partner tracking
- [ChurchCMS E-Prayers](https://churchcms.app/features) -- Prayer request broadcast and community prayer
- Project prompt: `/prompts/prayer_intentions.md` -- UX design philosophy and visual specs (HIGH confidence)

### Draggable Dashboard Tiles
- [dnd-kit Official Docs - Sortable](https://dndkit.com/presets/sortable) -- rectSortingStrategy, useSortable hook, closestCenter collision detection
- [Top 5 Drag-and-Drop Libraries for React (2026)](https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react) -- Library comparison, dnd-kit recommended
- [Interactive Dashboards with React-Grid-Layout (ilert)](https://www.ilert.com/blog/building-interactive-dashboards-why-react-grid-layout-was-our-best-choice) -- Dashboard tile UX patterns, library evaluation criteria
- [dnd-kit GitHub](https://github.com/clauderic/dnd-kit) -- Library features, accessibility, grid support
- [Building Customizable Dashboard Widgets (AntStack)](https://medium.com/@antstack/building-customizable-dashboard-widgets-using-react-grid-layout-234f7857c124) -- Dashboard widget UX patterns
- [Drag and Drop Dashboards with React DnD (Ensolvers)](https://www.ensolvers.com/post/drag-and-drop-dashboards-with-react-dnd) -- Dashboard drag-and-drop architecture
- [The Ultimate Drag-and-Drop Toolkit: dnd-kit (BrightCoding)](http://www.blog.brightcoding.dev/2025/08/21/the-ultimate-drag-and-drop-toolkit-for-react-a-deep-dive-into-dnd-kit) -- Deep dive into dnd-kit API

---
*Feature landscape research for: DonorCRM v2.0*
*Researched: 2026-02-20*
*Confidence: HIGH (project prompts provide exact specs; external research validates patterns)*
