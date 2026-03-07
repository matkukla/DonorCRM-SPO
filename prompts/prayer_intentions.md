You are a senior product engineer + UX designer building a "Prayer Intentions" tab for DonorCRM.

CRITICAL RULES (READ FIRST)
DO NOT:
❌ Modify existing journal, contact, or dashboard code
❌ Change existing API contracts
❌ Break existing features
❌ Over-engineer - keep it simple and prayerful
❌ Add heavy dependencies unless necessary
DO:
✅ Follow existing app patterns (routing, layout, auth, components)
✅ Use existing UI components (Button, Card, etc.) when available
✅ Connect to existing prayer data from Raiser's Edge imports
✅ Build in phases, verify each before continuing
✅ Keep the UI genuinely calming and prayerful
CONTEXT
Who uses this: Christian missionaries raising financial support.

Why it matters: Missionaries are called to pray for their partners, not just ask them for money. This feature helps them steward those relationships spiritually.

Existing data: We already import "Gift Specific Attributes Prayer Requests Description" from Raiser's Edge. This data should be surfaced here!

Design philosophy: This tab should feel like a chapel, not a dashboard. Warm, calm, soft on the eyes. Minimal cognitive load. Something a missionary actually opens daily.

VISUAL DESIGN NOTES
Palette:

Background: bg-amber-50/30 (warm parchment)
Cards: bg-white with border-amber-100
Text: text-amber-900 (headings), text-amber-700 (body)
Accents: bg-amber-200, text-amber-600
Typography:

Headings: font-serif for warmth
Body: Default sans with generous leading-relaxed
Spacing:

Generous padding (p-6, p-8)
Feels open and calm, not cramped
Icons:

Use sparingly: 🙏 ✓ (or lucide-react: Heart, Check, EyeOff)
VERIFICATION CHECKLIST
Phase 1-2 (Backend)
[ ] Prisma migration runs
[ ] GET /api/prayer/focus returns data
[ ] POST /api/prayer/intentions/:id/prayed updates lastPrayedAt
Phase 3-5 (Frontend)
[ ] /prayer page loads without errors
[ ] Today's Focus shows intentions
[ ] "Mark as prayed" works (optimistic update)
[ ] Focus Mode opens and keyboard shortcuts work
[ ] Completion screen shows prayed count
Phase 6-7 (Integration)
[ ] Nav item appears
[ ] Existing prayer requests from imports are visible
UX Feel
[ ] Page feels calm, not clinical
[ ] Focus Mode feels like guided prayer
[ ] No dense tables or aggressive colors
