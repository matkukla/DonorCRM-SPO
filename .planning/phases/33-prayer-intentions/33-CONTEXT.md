# Phase 33: Prayer Intentions - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a full Prayer Intentions feature: dedicated Prayer page accessible from the sidebar, CRUD API with slide-in panel, status tracking (active/answered/archived), contact-level Prayer tab, Today's Focus with daily rotation, Focus Mode for guided prayer with keyboard shortcuts, and Mark as Prayed tracking. The PrayerIntention model already exists (Phase 27) with auto-creation from RE gift imports (Phase 29). This phase builds the UI and API layer.

</domain>

<decisions>
## Implementation Decisions

### Overall Design Philosophy
- "Chapel, not dashboard" — warm, calm, prayerful feel throughout
- Warm amber palette: bg-amber-50/30 background, bg-white cards with border-amber-100, amber text tones
- Serif headings (font-serif) for warmth, sans body with generous leading-relaxed
- Generous padding (p-6, p-8) — open and calm, not cramped
- Icons used sparingly: lucide-react Heart, Check, EyeOff

### Main Prayer Page (List View)
- Table rows for the intentions list (consistent with other list pages)
- Columns: title, contact name, status badge, created date, truncated description preview
- Status filter only (dropdown or toggle — no full filter bar)
- Default sort: active intentions first, then by newest within each status group
- Sidebar navigation link to access the page

### Today's Focus
- Daily prayer rotation showing a curated set of intentions to pray for
- Displayed prominently on the Prayer page (above or alongside the full list)
- Selection logic and rotation at Claude's discretion

### Focus Mode
- Guided prayer experience with keyboard shortcuts
- Full-screen or immersive view showing one intention at a time
- "Mark as Prayed" action during Focus Mode
- Completion screen showing prayed count
- Keyboard shortcut design at Claude's discretion

### Status Workflow
- Three statuses: active (green badge), answered (blue/gold badge), archived (gray badge)
- Inline status dropdown in table rows for quick changes
- Status also changeable from the edit slide-in panel
- Any status can transition to any other (fully flexible, no one-way lifecycle)
- Marking as "answered" shows optional note/description prompt before confirming
- answered_at and archived_at timestamps tracked automatically

### Create/Edit Form
- Slide-in panel from the right side
- Fields: title (required), contact picker (required), status dropdown
- Description is optional (not shown in form — title is primary)
- When creating from contact detail tab: contact auto-fills and is locked (not changeable)
- Auto-created intentions from RE imports are fully editable, no special treatment

### Contact Detail Prayer Tab
- Warm amber card layout (not a table — prayerful feel)
- Each card shows title, status badge, and created date
- Simple toggle tabs at top: All / Active / Answered / Archived
- "Add" button to create new intention (opens slide-in with contact locked)
- Inline "Prayed" button on each card to mark as prayed
- No gift linkage displayed — keep focus on prayer, not financial data

### Mark as Prayed Tracking
- lastPrayedAt timestamp tracking on each intention
- Available from: Focus Mode, contact prayer tab inline button
- Optimistic UI update on mark action

### Claude's Discretion
- Today's Focus selection algorithm and rotation logic
- Focus Mode keyboard shortcut mapping
- Loading states and skeleton design
- Exact badge color values within the amber palette
- Focus Mode transition animations
- Error state handling
- Whether description field appears as expandable on cards

</decisions>

<specifics>
## Specific Ideas

- "This tab should feel like a chapel, not a dashboard. Warm, calm, soft on the eyes. Minimal cognitive load. Something a missionary actually opens daily."
- User context: Christian missionaries raising financial support — prayer is a core part of their relationship stewardship, not secondary
- Existing data from RE imports ("Gift Specific Attributes Prayer Requests Description") should surface seamlessly alongside manually created intentions
- Reference prompt file at `prompts/prayer_intentions.md` has the full design vision including palette specifics

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-prayer-intentions*
*Context gathered: 2026-02-23*
