---
phase: quick
plan: 260323-cnr
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/users/goal_services.py
  - apps/users/views_goals.py
  - apps/users/tests/test_goal_services.py
  - frontend/src/api/goals.ts
  - frontend/src/pages/goal/GoalPage.tsx
  - frontend/src/pages/journals/components/JournalHeader.tsx
autonomous: true
requirements: ["GH-26"]

must_haves:
  truths:
    - "Goal page shows a Decisions Progress bar below the Meetings bar"
    - "Bar shows monthly-normalized decision amounts (active + pending) from selected journals vs journal goal_amount sums"
    - "One-time decisions divided by 12, monthly at face value, quarterly / 3, annual / 12"
    - "Journal header has an inline-editable goal amount field"
    - "View As mode: progress bar displays, journal goal amount is read-only"
    - "Empty states: no goals set shows 0% + helpful message; no journals selected shows 0% + message"
  artifacts:
    - path: "apps/users/goal_services.py"
      provides: "get_decisions_progress(user) service function"
      contains: "get_decisions_progress"
    - path: "apps/users/views_goals.py"
      provides: "Extended GoalView GET response with decisions fields"
      contains: "decisions_current"
    - path: "frontend/src/pages/goal/GoalPage.tsx"
      provides: "Decisions progress bar in Progress card"
      contains: "Decisions"
  key_links:
    - from: "apps/users/views_goals.py"
      to: "apps/users/goal_services.py"
      via: "get_decisions_progress(request.user)"
      pattern: "get_decisions_progress"
    - from: "frontend/src/pages/goal/GoalPage.tsx"
      to: "frontend/src/api/goals.ts"
      via: "GoalData type with decisions_current, decisions_goal, decisions_percentage"
      pattern: "decisions_current"
---

<objective>
Add a "Decisions Progress" bar to the Goal page and an editable goal amount field to the journal header. GitHub Issue #26.

Purpose: Missionaries need visibility into how their journal decisions track against journal goal amounts, complementing the existing support progress bar.
Output: Backend service function + API extension + frontend progress bar + inline journal goal editing.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@prompts/progress_bar_prompt.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From apps/journals/models.py — Journal.goal_amount is DecimalField in DOLLARS (not cents):
```python
goal_amount = models.DecimalField('goal amount', max_digits=10, decimal_places=2,
    validators=[MinValueValidator(Decimal('0.01'))], help_text='Fundraising goal for this journal')
```

From apps/journals/models.py — Decision model:
```python
class DecisionCadence(models.TextChoices):
    ONE_TIME = 'one_time', 'One-Time'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    ANNUAL = 'annual', 'Annual'

class DecisionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    DECLINED = 'declined', 'Declined'

class Decision(TimeStampedModel):
    journal_contact = ForeignKey('JournalContact', related_name='decisions')
    amount = DecimalField(max_digits=10, decimal_places=2)  # dollars
    cadence = CharField(choices=DecisionCadence.choices)
    status = CharField(choices=DecisionStatus.choices, default='pending')

    @property
    def monthly_equivalent(self):
        multipliers = {ONE_TIME: 0, MONTHLY: 1, QUARTERLY: 1/3, ANNUAL: 1/12}
        return round(self.amount * multiplier, 2)
```

NOTE: Decision.monthly_equivalent treats ONE_TIME as multiplier 0 (not /12). The issue spec says one-time should be /12. We must NOT use the model property — compute in the service function with correct multipliers.

From apps/users/goal_services.py — existing get_goal_progress(user):
```python
def get_goal_progress(user):
    # Returns dict with: monthly_support_goal_cents, goal_weeks, selected_journal_ids,
    # effective_monthly_support, recurring_monthly, one_time_monthly, calls_count, meetings_count
```

From apps/users/views_goals.py — GoalView:
```python
class GoalView(APIView):
    def get(self, request):
        data = get_goal_progress(request.user)
        return Response(data)
    def patch(self, request): ...
```

From apps/users/models.py — GoalJournalSelection:
```python
# Links user to selected journals for goal tracking
GoalJournalSelection.objects.filter(user=user).values_list('journal_id', flat=True)
```

From frontend/src/api/goals.ts — GoalData interface:
```typescript
export interface GoalData {
  monthly_support_goal_cents: number
  goal_weeks: number
  selected_journal_ids: string[]
  effective_monthly_support: number
  recurring_monthly: number
  one_time_monthly: number
  calls_count: number
  meetings_count: number
}
```

From frontend/src/components/goal/GoalProgressBar.tsx:
```typescript
interface GoalProgressBarProps {
  value: number          // 0-100+
  colorVariant?: "support" | "default"
  disabled?: boolean
  label?: string
  className?: string
}
```

From frontend/src/pages/journals/components/JournalHeader.tsx:
```typescript
export function JournalHeader({ journal, members }: JournalHeaderProps)
// Currently displays goal_amount read-only in the header
```

From frontend/src/hooks/useJournals.ts:
```typescript
export function useUpdateJournal()  // mutation hook for PATCH /journals/:id/
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — get_decisions_progress service + extend GoalView API response</name>
  <files>apps/users/goal_services.py, apps/users/views_goals.py, apps/users/tests/test_goal_services.py</files>
  <behavior>
    - Test: no selected journals returns decisions_current=0.0, decisions_goal=0.0, decisions_percentage=0.0
    - Test: one journal with goal_amount=5000, two decisions (one monthly $200 active, one one_time $1200 pending) returns decisions_current=300.0 ($200 + $1200/12), decisions_goal=5000.0
    - Test: quarterly $300 active decision returns monthly equiv of $100 (300/3)
    - Test: annual $1200 active decision returns monthly equiv of $100 (1200/12)
    - Test: declined/paused decisions are excluded from decisions_current
    - Test: only decisions from selected journals are counted (scoping)
    - Test: multiple selected journals sum their goal_amounts for decisions_goal
    - Test: journals with no goal_amount (edge: all journals have goal_amount due to NOT NULL, but 0.01 minimum exists — test with low values)
    - Test: GET /api/v1/goals/me/ response includes decisions_current, decisions_goal, decisions_percentage
  </behavior>
  <action>
    1. In apps/users/goal_services.py, add a new function `get_decisions_progress(user)`:
       - Query selected_journal_ids from GoalJournalSelection.objects.filter(user=user)
       - If no selected journals, return {decisions_current: 0.0, decisions_goal: 0.0, decisions_percentage: 0.0}
       - Query Decision objects where:
         - journal_contact__journal_id__in=selected_journal_ids
         - journal_contact__journal__owner=user (ownership scoping)
         - status__in=['active', 'pending'] (the "yes + pending" statuses)
       - For each decision, compute monthly equivalent using these multipliers (NOT the model property which treats one_time as 0):
         - monthly: amount * 1
         - one_time: amount / 12
         - quarterly: amount / 3
         - annual: amount / 12
       - Use Django aggregate with Case/When for efficient SQL computation, or iterate in Python for clarity. Given potentially small dataset per user, Python iteration with .values_list('amount', 'cadence') is fine.
       - Sum Journal.goal_amount for selected journals (this is DecimalField in dollars). Convert to float for decisions_goal.
       - Compute decisions_percentage: (decisions_current / decisions_goal) * 100 if decisions_goal > 0, else 0.0
       - Return all three values as floats (dollars, not cents — consistent with effective_monthly_support in the same API response)

    2. In apps/users/views_goals.py, update the GoalView.get() method:
       - After `data = get_goal_progress(request.user)`, call `decisions = get_decisions_progress(request.user)`
       - Merge decisions dict into data: `data.update(decisions)`
       - Return Response(data)
       - Also update the patch() method's return to include decisions data (it already calls get_goal_progress at the end — add get_decisions_progress merge there too)
       - Import get_decisions_progress at top of file

    3. Add tests in apps/users/tests/test_goal_services.py covering the behaviors listed above. Follow existing test patterns (use _make_journal, _select_journals helpers). Create Decision objects via Decision.objects.create(journal_contact=jc, amount=Decimal('...'), cadence='monthly', status='active').

    IMPORTANT: All money values in the response are in DOLLARS (float), matching the existing effective_monthly_support pattern. Journal.goal_amount is already in dollars (DecimalField). Decision.amount is already in dollars. No cents conversion needed.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM && python -m pytest apps/users/tests/test_goal_services.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    - get_decisions_progress(user) returns correct monthly-normalized totals for active+pending decisions
    - One-time / 12, monthly * 1, quarterly / 3, annual / 12
    - Declined and paused decisions excluded
    - GET /api/v1/goals/me/ response includes decisions_current, decisions_goal, decisions_percentage
    - PATCH /api/v1/goals/me/ response also includes the three new fields
    - All existing tests still pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — Decisions progress bar on Goal page + inline journal goal editing</name>
  <files>frontend/src/api/goals.ts, frontend/src/pages/goal/GoalPage.tsx, frontend/src/pages/journals/components/JournalHeader.tsx</files>
  <action>
    1. In frontend/src/api/goals.ts, extend GoalData interface with three new fields:
       ```typescript
       decisions_current: number    // dollars (float)
       decisions_goal: number       // dollars (float)
       decisions_percentage: number // 0-100+ (float)
       ```

    2. In frontend/src/pages/goal/GoalPage.tsx, add a "Decisions" progress bar as a 4th row in the Progress card, below Meetings:
       - Follow the exact same pattern as the Monthly Support row (Row 1):
         - Label: "Decisions"
         - Right side: `${formatCurrency(goalData.decisions_current)} / ${formatCurrency(goalData.decisions_goal)}` or "-- / --" when no data
         - GoalProgressBar with colorVariant="default" (blue, not the support dynamic color)
         - disabled={!!emptyState} same as other bars
       - Compute decisionsPct: goalData.decisions_goal > 0 ? Math.round((goalData.decisions_current / goalData.decisions_goal) * 100) : 0
       - Empty state messages following existing pattern:
         - emptyState === "no_goal": "Set a goal amount above to see your decisions progress"
         - emptyState === "no_journals": "Select journals above to see your decisions progress"
         - Additional: if goalData exists and goalData.decisions_goal === 0 and emptyState is null (has main goal + journals but no journal goals set): show "Set goal amounts on your journals to track decision progress"

    3. In frontend/src/pages/journals/components/JournalHeader.tsx, add an inline-editable goal amount:
       - Import useState from React, useUpdateJournal from @/hooks/useJournals, useViewAs from @/providers/ViewAsProvider, Input from @/components/ui/input, Button from @/components/ui/button, Pencil and Check icons from lucide-react
       - Add an edit mode toggle for goal_amount in the header. When not editing, show the current "Goal: $X" text with a small pencil icon button next to it (hidden in View As mode). When editing, show an Input[type=number] with a check/save button.
       - On save: call useUpdateJournal with { id: journal.id, data: { goal_amount: newValue } }. The Journal serializer already accepts goal_amount as a string decimal.
       - In View As mode (isViewingAs): hide the edit button entirely, show goal amount as read-only text only.
       - Keep the component focused — the edit interaction is: click pencil -> input appears -> type value -> click check or press Enter -> saves via PATCH -> reverts to display mode.
       - Accept the JournalHeader component props. The journal.id is available from the JournalDetail type which extends JournalListItem and has `id: string`.
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit 2>&1 | tail -20</automated>
  </verify>
  <done>
    - GoalData TypeScript interface includes decisions_current, decisions_goal, decisions_percentage
    - Goal page Progress card has 4 rows: Monthly Support, Calls, Meetings, Decisions
    - Decisions bar shows $X / $Y formatted, with GoalProgressBar fill based on decisions_percentage
    - Empty state messages display correctly for no-goal, no-journals, and no-journal-goals scenarios
    - JournalHeader has inline edit for goal amount with pencil icon trigger
    - View As mode: decisions bar displays, journal goal edit is hidden
    - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
1. `cd /home/matkukla/projects/DonorCRM && python -m pytest apps/users/tests/test_goal_services.py -x -v` — all new and existing tests pass
2. `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` — no type errors
3. Manual: Visit Goal page, verify 4 progress bars visible in Progress section
4. Manual: Visit a journal detail page, click pencil on goal amount, edit, save — value persists on refresh
5. Manual: Toggle View As mode — goal page shows decisions bar read-only, journal header shows goal without edit button
</verification>

<success_criteria>
- GET /api/v1/goals/me/ returns decisions_current, decisions_goal, decisions_percentage alongside existing fields
- Goal page displays Decisions progress bar as 4th row in Progress card
- Monthly-normalized: monthly * 1, one_time / 12, quarterly / 3, annual / 12
- Only active + pending decisions counted
- Journal goal amounts editable inline in JournalHeader
- View As mode: bar displays, edit hidden
- Existing support/calls/meetings progress bars unchanged
- All tests pass, TypeScript compiles
</success_criteria>

<output>
After completion, create `.planning/quick/260323-cnr-add-decisions-progress-bar-to-goal-page-/260323-cnr-SUMMARY.md`
</output>
