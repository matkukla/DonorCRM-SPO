# Phase 33: Prayer Intentions - Research

**Researched:** 2026-02-23
**Domain:** Full-stack CRUD feature (Django REST + React/shadcn) with custom UX theming
**Confidence:** HIGH

## Summary

Phase 33 builds the UI and API layer on top of the existing PrayerIntention model (created in Phase 27, with import auto-creation in Phase 29). The model is fully migrated with status tracking, M2M gift linkage, and contact FK. This phase needs: Django REST serializers/views/urls, frontend API client/hooks, a dedicated Prayer page with table list, a slide-in create/edit panel, a contact detail Prayer tab with warm card layout, Today's Focus with rotation algorithm, Focus Mode with keyboard navigation, and Mark as Prayed tracking (requires a new `last_prayed_at` field via migration).

The existing codebase has well-established patterns for every component needed. The primary engineering challenge is the warm "chapel" aesthetic that departs from the standard dashboard styling, the Focus Mode (full-screen guided experience with keyboard shortcuts), and the Today's Focus daily rotation algorithm -- all of which are UI-only complexity with no external library dependencies.

**Primary recommendation:** Follow existing Django REST + React patterns exactly for the CRUD layer (serializer, views, urls, api client, hooks, list page). Layer the warm amber theming as Tailwind utility classes. Add `last_prayed_at` DateTimeField to the model via migration. Build Focus Mode as a React overlay component with `useEffect` keyboard listeners.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- "Chapel, not dashboard" -- warm, calm, prayerful feel throughout
- Warm amber palette: bg-amber-50/30 background, bg-white cards with border-amber-100, amber text tones
- Serif headings (font-serif) for warmth, sans body with generous leading-relaxed
- Generous padding (p-6, p-8) -- open and calm, not cramped
- Icons used sparingly: lucide-react Heart, Check, EyeOff
- Main Prayer Page: Table rows for intentions list (consistent with other list pages)
- Columns: title, contact name, status badge, created date, truncated description preview
- Status filter only (dropdown or toggle -- no full filter bar)
- Default sort: active intentions first, then by newest within each status group
- Sidebar navigation link to access the page
- Today's Focus: Daily prayer rotation showing curated set of intentions, displayed prominently on the Prayer page
- Focus Mode: Guided prayer experience with keyboard shortcuts, full-screen or immersive view showing one intention at a time, "Mark as Prayed" action, completion screen showing prayed count
- Three statuses: active (green badge), answered (blue/gold badge), archived (gray badge)
- Inline status dropdown in table rows for quick changes
- Status also changeable from the edit slide-in panel
- Any status can transition to any other (fully flexible, no one-way lifecycle)
- Marking as "answered" shows optional note/description prompt before confirming
- answered_at and archived_at timestamps tracked automatically
- Slide-in panel from right side for create/edit
- Fields: title (required), contact picker (required), status dropdown
- Description is optional (not shown in form -- title is primary)
- When creating from contact detail tab: contact auto-fills and is locked
- Auto-created intentions from RE imports are fully editable, no special treatment
- Contact Detail Prayer Tab: Warm amber card layout (not a table)
- Each card shows title, status badge, and created date
- Simple toggle tabs at top: All / Active / Answered / Archived
- "Add" button to create new intention (opens slide-in with contact locked)
- Inline "Prayed" button on each card to mark as prayed
- No gift linkage displayed
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRAY-01 | Prayer Intentions page accessible from main sidebar with list of all intentions | Sidebar uses `navItems` array in `Sidebar.tsx`; add route in `App.tsx`; list page follows `TaskList.tsx` pattern with DataTable |
| PRAY-02 | User can create, edit, and delete prayer intentions manually | Slide-in Sheet panel (existing `sheet.tsx` component); Django REST ListCreateAPIView + RetrieveUpdateDestroyAPIView; contact picker pattern from TaskForm/DonationForm |
| PRAY-03 | Prayer intention status tracking (active, answered, archived) | PrayerIntentionStatus enum already exists in model; add inline status dropdown in table rows; auto-set answered_at/archived_at timestamps in serializer save logic |
| PRAY-04 | Prayer tab on Contact detail page showing intentions for that contact | Add tab in ContactDetail.tsx TabsList; backend endpoint at `contacts/<uuid>/prayer-intentions/`; warm card layout per design decisions |
| PRAY-05 | Prayer intentions created from RE gift imports linked to donor contact | Already implemented in Phase 29 (`_maybe_create_prayer_intention` in `re_services.py`); this requirement is satisfied -- verify visibility in new UI |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django REST Framework | (existing) | API views, serializers | All other apps use DRF generics |
| django-filter | 24.3 | Query filtering | Used by Gift/Task views for filterset_class |
| React | (existing) | UI framework | Project standard |
| @tanstack/react-query | (existing) | Data fetching/caching | All hooks use useQuery/useMutation pattern |
| @tanstack/react-table | (existing) | Table rendering | DataTable component wraps this |
| shadcn/ui | (existing) | UI components | Sheet, Badge, Card, Tabs, Select, Button all available |
| Tailwind CSS | (existing) | Styling | All components use utility classes |
| lucide-react | (existing) | Icons | Heart, Check, EyeOff per user decision |
| sonner | (existing) | Toast notifications | Used throughout for success/error toasts |
| nuqs | (existing) | URL state management | Used by filter infrastructure |
| date-fns | (existing) | Date formatting | formatDistanceToNow, etc. |

### No New Libraries Needed
This phase requires zero new dependencies. All UI components (Sheet, Badge, Card, Tabs, Select, Dialog, Table) are already installed via shadcn/ui. The warm amber styling is achieved entirely through Tailwind utility classes. Focus Mode keyboard handling uses native `useEffect` + `addEventListener`.

## Architecture Patterns

### Backend Structure (New Files in `apps/prayers/`)
```
apps/prayers/
├── __init__.py          # exists
├── admin.py             # exists
├── apps.py              # exists
├── models.py            # exists - add last_prayed_at field
├── serializers.py       # NEW
├── views.py             # NEW
├── urls.py              # NEW
├── filters.py           # NEW (simple status filter)
└── migrations/
    ├── 0001_initial.py  # exists
    ├── 0002_*.py        # exists (gift M2M migration)
    └── 0003_*.py        # NEW (add last_prayed_at)
```

### Frontend Structure (New Files)
```
frontend/src/
├── api/
│   └── prayers.ts                    # NEW - API client + types
├── hooks/
│   └── usePrayers.ts                 # NEW - React Query hooks
└── pages/
    └── prayer/
        ├── PrayerList.tsx            # NEW - Main page with table + Today's Focus
        ├── PrayerIntentionPanel.tsx   # NEW - Slide-in create/edit Sheet
        ├── PrayerFocusMode.tsx        # NEW - Full-screen guided prayer
        └── components/
            ├── TodaysFocus.tsx        # NEW - Focus card section
            ├── StatusBadge.tsx        # NEW - Amber-themed status badges
            └── PrayerCard.tsx         # NEW - Card for contact tab
```

### Pattern 1: Django REST CRUD (follows Gift/Task pattern)
**What:** ListCreateAPIView + RetrieveUpdateDestroyAPIView with owner scoping through contact.owner
**When to use:** All prayer intention endpoints
**Key difference from other apps:** PrayerIntention has no direct `owner` field. Access scoping must filter through `contact__owner=user`. This matches how ContactGiftsView scopes via `donor_contact__owner`.

```python
# Serializer pattern
class PrayerIntentionSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)

    class Meta:
        model = PrayerIntention
        fields = ['id', 'contact', 'contact_name', 'title', 'description',
                  'status', 'last_prayed_at', 'answered_at', 'archived_at',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'answered_at', 'archived_at', 'last_prayed_at',
                           'created_at', 'updated_at']

# View scoping pattern
class PrayerIntentionListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        user = self.request.user
        qs = PrayerIntention.objects.select_related('contact').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(contact__owner=user)
        return qs
```

### Pattern 2: Slide-in Sheet Panel (follows DonationDetail pattern)
**What:** shadcn Sheet component from the right side for create/edit
**When to use:** Prayer intention create and edit forms
**Example:** DonationDetailPanel in `DonationDetail.tsx` uses `Sheet` + `SheetContent side="right"`.

```tsx
// Sheet panel pattern
<Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
  <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
    <SheetHeader>
      <SheetTitle>{isEdit ? 'Edit' : 'New'} Prayer Intention</SheetTitle>
    </SheetHeader>
    {/* Form fields */}
  </SheetContent>
</Sheet>
```

### Pattern 3: Contact Search Picker (follows TaskForm/DonationForm pattern)
**What:** Text input with dropdown search using `useSearchContacts` hook
**When to use:** Contact picker in the prayer intention create/edit panel
**Existing code:** `frontend/src/hooks/useContacts.ts` exports `useSearchContacts(query)` which calls `/contacts/search/?q=query`. Pattern is duplicated in TaskForm, DonationForm, PledgeForm.

### Pattern 4: Contact Sub-resource Tab (follows ContactDetail.tsx pattern)
**What:** Add Prayer tab to ContactDetail with backend endpoint
**When to use:** Contact-level prayer intention viewing
**Backend:** Add `ContactPrayerIntentionsView` in contacts views, URL at `contacts/<uuid>/prayer-intentions/`
**Frontend:** Add `useContactPrayerIntentions(id)` hook, add tab in ContactDetail.tsx TabsList

### Pattern 5: Inline Status Change (new pattern for this phase)
**What:** Status dropdown directly in table rows for quick status changes
**When to use:** Main prayer list table rows
**Implementation:** Use shadcn `Select` component in the table cell, call PATCH endpoint on change. Auto-set `answered_at`/`archived_at` in the serializer's `update()` method based on status transitions.

### Pattern 6: Today's Focus Selection Algorithm (Claude's Discretion)
**Recommendation:** Deterministic daily rotation based on date hash.
- Query all active intentions for the user
- Use current date as seed: `hash(date.today().isoformat() + user.id)` to select N intentions
- Show 3-5 intentions per day (configurable)
- Prioritize: never-prayed-for intentions first, then longest since last prayed
- API endpoint: `GET /api/v1/prayers/focus/` returns today's curated set
- Alternative simpler approach: just use `(date ordinal + user_id_hash) % count` to rotate through all active intentions

### Pattern 7: Focus Mode Keyboard Shortcuts (Claude's Discretion)
**Recommendation:**
- Arrow Right / Space: Next intention
- Arrow Left: Previous intention
- P or Enter: Mark as Prayed
- S: Skip (move to next without marking)
- Escape: Exit Focus Mode
- Implementation: `useEffect` with `keydown` listener, cleanup on unmount

### Pattern 8: Optimistic UI for Mark as Prayed
**What:** Update UI immediately before server confirms
**When to use:** "Mark as Prayed" button in Focus Mode and contact Prayer tab
**Implementation:** Use `useMutation` with `onMutate` to optimistically update the query cache, `onError` to rollback.

```tsx
const markPrayedMutation = useMutation({
  mutationFn: (id: string) => markPrayed(id),
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: ['prayers'] })
    const previous = queryClient.getQueryData(['prayers'])
    // Optimistically update
    queryClient.setQueryData(['prayers'], (old) => /* update last_prayed_at */)
    return { previous }
  },
  onError: (err, id, context) => {
    queryClient.setQueryData(['prayers'], context?.previous)
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['prayers'] })
  },
})
```

### Anti-Patterns to Avoid
- **Direct owner field on PrayerIntention:** The model scopes through `contact.owner`. Do NOT add an `owner` FK to the prayer model -- it would duplicate ownership and risk inconsistency.
- **Separate pages for create/edit:** Use the slide-in Sheet panel, not a dedicated page route. This keeps the prayer page feeling lightweight.
- **Complex filter bar for prayer list:** User explicitly decided "status filter only" -- do not add the full FilterBar component used on Donation/Pledge pages.
- **Displaying gift linkage in UI:** User explicitly decided "No gift linkage displayed -- keep focus on prayer, not financial data."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table rendering | Custom table HTML | DataTable + @tanstack/react-table | Pagination, sorting already handled |
| Slide-in panel | Custom drawer | shadcn Sheet component | Animation, accessibility, overlay built-in |
| Contact picker | Custom autocomplete | Existing useSearchContacts pattern | Already working in 3 forms |
| Status badges | Custom badge styles | shadcn Badge with variant | Consistent with rest of app |
| Toast notifications | Custom alert system | sonner toast | Already configured globally |
| URL state | Custom useState | nuqs (if filters grow) or useSearchParams | URL bookmarkability |
| Date formatting | Manual formatting | formatLocalDate from utils.ts | Handles UTC date bug (MEMORY.md) |

**Key insight:** Every UI component needed already exists in the project. The only novel pieces are the warm amber styling (Tailwind classes), Focus Mode (keyboard event handling), and Today's Focus (selection algorithm).

## Common Pitfalls

### Pitfall 1: UTC Date Display Bug
**What goes wrong:** Date-only strings like "2026-02-01" parsed as UTC midnight display as previous day in US timezones
**Why it happens:** `new Date("2026-02-01")` interprets as UTC, not local
**How to avoid:** Use `formatLocalDate()` from `frontend/src/lib/utils.ts` for all date-only displays. This is documented in MEMORY.md.
**Warning signs:** Dates appearing one day off in the UI

### Pitfall 2: Owner Scoping Through Contact FK
**What goes wrong:** Prayer intentions from other users' contacts leak into the current user's view
**Why it happens:** PrayerIntention has no direct `owner` field; scoping must go through `contact__owner`
**How to avoid:** Every queryset MUST filter `contact__owner=user` for non-admin users. Use `select_related('contact')` to avoid N+1 queries.
**Warning signs:** Users seeing intentions they didn't create

### Pitfall 3: answered_at / archived_at Timestamp Drift
**What goes wrong:** Timestamps don't get set/cleared when status changes
**Why it happens:** Status can transition in any direction (answered -> active, etc.)
**How to avoid:** Handle in serializer's `update()` method or model `save()` override:
  - If status changes TO answered: set `answered_at = now()`, clear `archived_at`
  - If status changes TO archived: set `archived_at = now()`, clear `answered_at`
  - If status changes TO active: clear both `answered_at` and `archived_at`
**Warning signs:** Stale timestamps on intentions that were re-activated

### Pitfall 4: React Query Stale Cache Key Collisions
**What goes wrong:** Different filter states return cached data from wrong query
**Why it happens:** Query keys with `undefined` values get stripped by JSON serialization (MEMORY.md)
**How to avoid:** Pass clean `Record<string, string>` as query keys, not objects with undefined values
**Warning signs:** List not updating when filter changes

### Pitfall 5: Focus Mode Keyboard Event Leaking
**What goes wrong:** Arrow keys scroll the page, or keyboard events fire after Focus Mode closes
**Why it happens:** Event listeners not properly cleaned up or not calling `preventDefault()`
**How to avoid:** Return cleanup function from `useEffect`; call `e.preventDefault()` for handled keys; check a ref/state for active mode
**Warning signs:** Page scrolling during Focus Mode, or ghost events after closing

### Pitfall 6: Missing Migration for last_prayed_at
**What goes wrong:** Frontend expects `last_prayed_at` field but API returns no such field
**Why it happens:** The existing model doesn't have this field -- it must be added via migration
**How to avoid:** Create migration 0003 adding `last_prayed_at = DateTimeField(null=True, blank=True)` before building the API
**Warning signs:** 500 errors or missing field in API response

## Code Examples

### Backend: Status Timestamp Auto-Management
```python
# In serializers.py
from django.utils import timezone

class PrayerIntentionSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        if new_status and new_status != instance.status:
            now = timezone.now()
            if new_status == PrayerIntentionStatus.ANSWERED:
                validated_data['answered_at'] = now
                validated_data['archived_at'] = None
            elif new_status == PrayerIntentionStatus.ARCHIVED:
                validated_data['archived_at'] = now
                validated_data['answered_at'] = None
            elif new_status == PrayerIntentionStatus.ACTIVE:
                validated_data['answered_at'] = None
                validated_data['archived_at'] = None
        return super().update(instance, validated_data)
```

### Backend: Mark as Prayed Endpoint
```python
# Custom action endpoint
class MarkPrayedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        qs = PrayerIntention.objects.filter(pk=pk)
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(contact__owner=user)
        intention = qs.first()
        if not intention:
            return Response({'detail': 'Not found.'}, status=404)
        intention.last_prayed_at = timezone.now()
        intention.save(update_fields=['last_prayed_at', 'updated_at'])
        return Response({'detail': 'Marked as prayed.'})
```

### Backend: Today's Focus Selection
```python
# In views.py
import hashlib

class TodaysFocusView(generics.ListAPIView):
    serializer_class = PrayerIntentionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = date.today()

        qs = PrayerIntention.objects.filter(
            status=PrayerIntentionStatus.ACTIVE,
            contact__owner=user,
        ).select_related('contact')

        # Prioritize: never prayed first, then oldest last_prayed_at
        qs = qs.order_by(
            models.F('last_prayed_at').asc(nulls_first=True),
            'created_at',
        )

        # Deterministic daily offset using date + user id
        seed = f"{today.isoformat()}-{user.pk}"
        hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        total = qs.count()

        if total == 0:
            return qs.none()

        focus_count = min(5, total)
        offset = hash_val % max(1, total - focus_count + 1)
        return qs[offset:offset + focus_count]
```

### Frontend: Warm Amber Theming Classes
```tsx
// Reusable class patterns for the "chapel" aesthetic
const amberPageClasses = "bg-amber-50/30 min-h-screen"
const amberCardClasses = "bg-white border-amber-100 shadow-sm"
const amberHeadingClasses = "font-serif text-amber-900"
const amberBodyClasses = "text-amber-700 leading-relaxed"
const amberAccentClasses = "bg-amber-200 text-amber-600"

// Status badge mapping
const statusBadgeVariants = {
  active: "bg-green-100 text-green-800 border-green-200",
  answered: "bg-blue-100 text-blue-800 border-blue-200",  // or gold
  archived: "bg-gray-100 text-gray-600 border-gray-200",
}
```

### Frontend: Focus Mode Keyboard Handler
```tsx
useEffect(() => {
  if (!isFocusModeOpen) return

  const handleKeyDown = (e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowRight':
      case ' ':
        e.preventDefault()
        goToNext()
        break
      case 'ArrowLeft':
        e.preventDefault()
        goToPrevious()
        break
      case 'p':
      case 'Enter':
        e.preventDefault()
        markAsPrayed(currentIntention.id)
        break
      case 'Escape':
        e.preventDefault()
        closeFocusMode()
        break
    }
  }

  window.addEventListener('keydown', handleKeyDown)
  return () => window.removeEventListener('keydown', handleKeyDown)
}, [isFocusModeOpen, currentIndex])
```

### URL Registration Pattern
```python
# config/api_urls.py - add:
path('prayers/', include('apps.prayers.urls')),

# apps/prayers/urls.py
app_name = 'prayers'
urlpatterns = [
    path('', PrayerIntentionListCreateView.as_view(), name='prayer-list'),
    path('focus/', TodaysFocusView.as_view(), name='prayer-focus'),
    path('<uuid:pk>/', PrayerIntentionDetailView.as_view(), name='prayer-detail'),
    path('<uuid:pk>/prayed/', MarkPrayedView.as_view(), name='prayer-mark-prayed'),
]

# Also add to contacts/urls.py:
path('<uuid:pk>/prayer-intentions/', ContactPrayerIntentionsView.as_view(), name='contact-prayers'),
```

### Route and Sidebar Registration
```tsx
// App.tsx - add route:
<Route path="/prayer" element={<ProtectedPage><PrayerList /></ProtectedPage>} />

// Sidebar.tsx - add to navItems array (after Journals):
{ label: "Prayer", href: "/prayer", icon: <Heart className="h-5 w-5" /> },
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom drawer components | shadcn Sheet (Radix Dialog) | shadcn v0.5+ | Accessible slide-in panels with animation |
| useState for URL filters | nuqs URL state management | Project v1.2 | Bookmarkable filter states |
| Manual form state | Controlled inputs with useState | Project convention | No form library needed for simple forms |

## Open Questions

1. **Today's Focus count**
   - What we know: User wants "a curated set" of intentions to pray for daily
   - What's unclear: Exactly how many (3? 5? All active?)
   - Recommendation: Default to 5, or all active if fewer than 5. This is Claude's discretion per CONTEXT.md.

2. **Focus Mode visual design**
   - What we know: Full-screen or immersive view, one intention at a time, keyboard shortcuts
   - What's unclear: Whether it should be a modal overlay, a dedicated route, or a portal
   - Recommendation: Full-viewport overlay (z-50 fixed inset-0) with the amber theming. This avoids route changes and preserves list page state underneath.

3. **"Answered" note/description prompt**
   - What we know: Marking as "answered" shows optional note/description prompt before confirming
   - What's unclear: Whether this updates the existing `description` field or is a separate field
   - Recommendation: Show a Dialog with an optional textarea. If filled, append to or replace the `description` field. No new model field needed.

4. **Default sort implementation**
   - What we know: "Active intentions first, then by newest within each status group"
   - What's unclear: Whether to use Django queryset ordering or a custom `Case/When`
   - Recommendation: Use Django `Case/When` ordering: `Case(When(status='active', then=0), When(status='answered', then=1), When(status='archived', then=2))` followed by `-created_at`.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `apps/prayers/models.py` - existing PrayerIntention model structure
- Codebase analysis: `apps/prayers/migrations/` - 2 existing migrations (initial + M2M)
- Codebase analysis: `apps/gifts/views.py`, `apps/tasks/views.py` - DRF view patterns
- Codebase analysis: `apps/gifts/serializers.py`, `apps/tasks/serializers.py` - Serializer patterns
- Codebase analysis: `frontend/src/pages/tasks/TaskList.tsx` - List page with DataTable pattern
- Codebase analysis: `frontend/src/pages/donations/DonationDetail.tsx` - Sheet slide-in panel pattern
- Codebase analysis: `frontend/src/pages/contacts/ContactDetail.tsx` - Contact detail tabs pattern
- Codebase analysis: `frontend/src/components/layout/Sidebar.tsx` - Navigation structure
- Codebase analysis: `frontend/src/App.tsx` - Route registration pattern
- Codebase analysis: `apps/imports/re_services.py` - Prayer auto-creation from RE imports (PRAY-05)
- Codebase analysis: `frontend/src/components/ui/sheet.tsx` - shadcn Sheet component (Radix Dialog)

### Secondary (MEDIUM confidence)
- `prompts/prayer_intentions.md` - User's design vision document with palette specifics
- `.planning/phases/33-prayer-intentions/33-CONTEXT.md` - User decisions from discussion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, zero new deps
- Architecture: HIGH - Every pattern has direct codebase precedent
- Pitfalls: HIGH - Known issues documented in MEMORY.md + codebase patterns well-understood
- Focus Mode/Today's Focus: MEDIUM - Novel features without direct codebase precedent, but straightforward React patterns

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable -- no external dependencies or version concerns)
