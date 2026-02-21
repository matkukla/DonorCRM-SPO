# Phase 29: RE Import Pipeline (Gifts & Recurring Gifts) - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Import RE Gift and Recurring Gift CSV files into DonorCRM. Create Gift/GiftCredit and RecurringGift/RecurringGiftCredit records with correct multi-row grouping by Gift ID, solicitor credit splitting, and automatic PrayerIntention creation from gift descriptions. Reuses Phase 28 infrastructure (SHA256 dedup, row-level error collection, encoding detection). UI for imports is a separate phase (Phase 32).

</domain>

<decisions>
## Implementation Decisions

### Multi-row grouping
- Rows sharing a Gift ID are collapsed into one Gift record + multiple GiftCredit records (one per solicitor row)
- Gift amount comes from a dedicated amount column (first row of the group), NOT summed from credits
- Same grouping pattern applies to Recurring Gifts (group by Recurring Gift ID, first row = amount, credits per solicitor) — Claude adapts based on actual RE CSV format differences
- If a gift group references a Contact (Constituent ID) not found in DonorCRM: skip the entire gift group, log the error, continue processing remaining rows
- Reuse Phase 28's ImportBatch types (`RE_GIFT`, `RE_RECURRING_GIFT`) and the existing SHA256 dedup/error collection infrastructure

### Prayer auto-detection
- The RE CSV column `"Gift Specific Attributes Prayer Requests Description"` drives auto-creation
- Any non-empty value in that column creates a PrayerIntention — no heavyweight keyword filtering
- Apply a stoplist + basic sanity checks (e.g., skip values that are just whitespace, punctuation, or common non-prayer noise)
- PrayerIntention title: first ~50-80 chars of the description text, truncated cleanly
- PrayerIntention description: full text from the CSV column
- Dedupe by contact + normalized description text — same donor with same prayer text across multiple gifts = one PrayerIntention
- **Model change required:** PrayerIntention.gift FK → M2M relationship with Gift, so multiple gifts can link to one prayer intention
- New PrayerIntentions default to status=ACTIVE

### Claude's Discretion
- Solicitor matching: how to handle gift rows referencing solicitors not in the Solicitor table (auto-create vs skip credit, following Phase 28 patterns)
- Recurring Gift CSV format adaptation: same core pattern as gifts, but adapt field mapping for installment-specific columns (frequency, start_date, end_date, status)
- Stoplist contents for prayer description filtering
- Fund matching/creation from CSV fund columns
- Exact error message wording for row-level failures

</decisions>

<specifics>
## Specific Ideas

- The prayer description column is specifically named `"Gift Specific Attributes Prayer Requests Description"` in RE exports
- Prayer feature has a deliberate "chapel, not dashboard" design philosophy — auto-created intentions should be clean and prayerful, not cluttered with import metadata
- See `prompts/prayer_intentions.md` for the broader prayer feature vision

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-re-import-gifts-recurring*
*Context gathered: 2026-02-20*
