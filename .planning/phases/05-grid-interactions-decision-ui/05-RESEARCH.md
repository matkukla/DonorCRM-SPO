# Phase 5: Grid Interactions & Decision UI - Research

**Researched:** 2026-01-24
**Domain:** React optimistic updates, toast notifications, decision dialog, progress bar, next steps checklist
**Confidence:** HIGH

## Summary

Phase 5 implements interactive grid features: decision editing dialogs, optimistic updates with rollback, stage movement with warnings, next steps checklists, and a real-time journal header with progress tracking. The codebase already has React Query 5.90.17, Dialog component, memoized grid cells, and Django backend with decision CRUD API.

The standard approach uses React Query's `useMutation` with `onMutate`/`onError`/`onSettled` callbacks for optimistic updates, Sonner for toast notifications (integrates cleanly with shadcn/ui), and shadcn/ui primitives for the decision dialog form (Dialog, Select, Progress). The decision API already supports PATCH updates with history tracking, so the frontend only needs mutation hooks with cache manipulation.

Key technical challenges include: (1) properly rolling back optimistic updates on error using React Query's context pattern, (2) efficiently invalidating journal member cache when decisions change, and (3) calculating real-time header totals from cached data without N+1 re-renders.

**Primary recommendation:** Use React Query's cache-based optimistic updates with `setQueryData` for instant UI feedback, add Sonner for toast notifications (success/error/warning), implement decision dialog with existing Dialog + new Select components, and add Progress component for header.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | 5.90.17 | Optimistic updates, cache management | Already in codebase, `useMutation` with `onMutate`/`onError` handles optimistic pattern |
| sonner | ^2.0 | Toast notifications | Recommended by shadcn/ui, simple API (`toast.success()`), no provider setup needed |
| @radix-ui/react-dialog | 1.1.15 | Modal dialogs | Already in codebase as Dialog component |
| @radix-ui/react-select | ^2.1 | Dropdown selects | Standard Radix primitive for accessible dropdowns (decision cadence/status) |
| @radix-ui/react-progress | ^1.1 | Progress bar | Standard Radix primitive for accessible progress indicators |
| @radix-ui/react-checkbox | ^1.1 | Next steps checkboxes | Standard Radix primitive for accessible checkboxes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 0.562.0 | Icons | Already in codebase, use for dialog icons, checkboxes |
| class-variance-authority | 0.7.1 | Component variants | Already in codebase for Badge, extend for status colors |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sonner | react-hot-toast | react-hot-toast is simpler but Sonner integrates with shadcn/ui themes |
| Radix Select | Dropdown Menu | Select is semantically correct for form fields, DropdownMenu for actions |
| Cache optimistic updates | UI-based optimistic via `isPending` | Cache-based allows rollback, UI-based is simpler but no rollback |

**Installation:**
```bash
npm install sonner @radix-ui/react-select @radix-ui/react-progress @radix-ui/react-checkbox
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── pages/journals/
│   ├── JournalDetail.tsx          # Updated with header + dialog state
│   └── components/
│       ├── JournalGrid.tsx        # Existing - add decision cell
│       ├── JournalHeader.tsx      # NEW - progress bar, totals
│       ├── DecisionDialog.tsx     # NEW - edit decision form
│       ├── DecisionCell.tsx       # NEW - clickable decision card
│       ├── NextStepsCell.tsx      # NEW - checklist in cell
│       ├── StageCell.tsx          # Existing - add stage movement warning
│       └── StageMovementToast.tsx # NEW - warning toast content
├── hooks/
│   └── useJournals.ts             # Add decision mutations with optimistic updates
├── api/
│   └── journals.ts                # Add decision API functions
├── components/ui/
│   ├── sonner.tsx                 # NEW - toast provider
│   ├── select.tsx                 # NEW - select component
│   ├── progress.tsx               # NEW - progress bar
│   └── checkbox.tsx               # NEW - checkbox component
└── types/
    └── journals.ts                # Add NextStep type
```

### Pattern 1: Optimistic Update with Rollback

**What:** Use React Query's `onMutate` to immediately update cache, `onError` to rollback, `onSettled` to sync

**When to use:** Any mutation that should show instant UI feedback (decision updates, next step toggles)

**Example:**
```typescript
// Source: TanStack Query Optimistic Updates Guide
// https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates

export function useUpdateDecision() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DecisionUpdate }) =>
      updateDecision(id, data),

    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["journals", journalId, "members"]
      })

      // Snapshot previous value
      const previousMembers = queryClient.getQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}]
      )

      // Optimistically update cache
      queryClient.setQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}],
        (old) => {
          if (!old) return old
          return {
            ...old,
            results: old.results.map((member) => {
              if (member.decision?.id === id) {
                return {
                  ...member,
                  decision: { ...member.decision, ...data }
                }
              }
              return member
            })
          }
        }
      )

      // Return context for rollback
      return { previousMembers }
    },

    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousMembers) {
        queryClient.setQueryData(
          ["journals", journalId, "members", {}],
          context.previousMembers
        )
      }
      // Show error toast
      toast.error("Failed to update decision")
    },

    onSettled: () => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries({
        queryKey: ["journals", journalId, "members"]
      })
    },
  })
}
```

**Critical from STATE.md:** "Phase 5: Optimistic update rollback on error (use React Query mutation onError callbacks)" - this pattern addresses that pitfall.

### Pattern 2: Toast Notifications with Sonner

**What:** Use Sonner's imperative API for success/error/warning toasts

**When to use:** After mutations complete, for stage movement warnings

**Example:**
```typescript
// Source: shadcn/ui Sonner component
// https://ui.shadcn.com/docs/components/sonner

import { toast } from "sonner"

// Success toast
toast.success("Decision updated")

// Error toast (in onError callback)
toast.error("Failed to save changes", {
  description: "Please try again or contact support."
})

// Warning toast for stage skipping
toast.warning("Skipping stages", {
  description: "Moving from Contact to Close skips Meet stage."
})

// In root layout (App.tsx)
import { Toaster } from "@/components/ui/sonner"

function App() {
  return (
    <>
      <Routes />
      <Toaster position="bottom-right" />
    </>
  )
}
```

### Pattern 3: Decision Dialog Form

**What:** Modal dialog with form fields for decision editing

**When to use:** When user clicks decision cell or "Add Decision" button

**Example:**
```typescript
// Source: Existing Dialog component + PledgeForm pattern

interface DecisionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  decision: DecisionSummary | null
  journalContactId: string
  contactName: string
}

export function DecisionDialog({
  open,
  onOpenChange,
  decision,
  journalContactId,
  contactName,
}: DecisionDialogProps) {
  const [formData, setFormData] = useState({
    amount: decision?.amount ?? "",
    cadence: decision?.cadence ?? "monthly",
    status: decision?.status ?? "pending",
  })

  const updateMutation = useUpdateDecision()
  const createMutation = useCreateDecision()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (decision) {
        await updateMutation.mutateAsync({
          id: decision.id,
          data: formData
        })
        toast.success("Decision updated")
      } else {
        await createMutation.mutateAsync({
          journal_contact: journalContactId,
          ...formData
        })
        toast.success("Decision created")
      }
      onOpenChange(false)
    } catch (error) {
      // Error handled by mutation
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {decision ? "Edit Decision" : "Add Decision"}
          </DialogTitle>
          <DialogDescription>
            {contactName}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          {/* Amount, Cadence, Status fields */}
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

### Pattern 4: Stage Movement Warning

**What:** Check if stage transition is non-sequential, show warning toast but allow save

**When to use:** When user moves contact between stages via stage cell click

**Example:**
```typescript
// Source: Requirements JRN-05

const STAGE_ORDER: Record<PipelineStage, number> = {
  contact: 1,
  meet: 2,
  close: 3,
  decision: 4,
  thank: 5,
  next_steps: 6,
}

function checkStageTransition(
  currentStage: PipelineStage,
  targetStage: PipelineStage
): { isSequential: boolean; skippedStages: string[] } {
  const currentOrder = STAGE_ORDER[currentStage]
  const targetOrder = STAGE_ORDER[targetStage]

  // Going backwards
  if (targetOrder < currentOrder) {
    return {
      isSequential: false,
      skippedStages: [], // Revisiting is allowed but warn
    }
  }

  // Skipping forward
  if (targetOrder > currentOrder + 1) {
    const skipped = Object.entries(STAGE_ORDER)
      .filter(([_, order]) => order > currentOrder && order < targetOrder)
      .map(([stage]) => STAGE_LABELS[stage as PipelineStage])
    return {
      isSequential: false,
      skippedStages: skipped,
    }
  }

  return { isSequential: true, skippedStages: [] }
}

// Usage in stage event creation
const transition = checkStageTransition(currentStage, newStage)
if (!transition.isSequential) {
  if (transition.skippedStages.length > 0) {
    toast.warning("Skipping stages", {
      description: `Skipping: ${transition.skippedStages.join(", ")}`
    })
  } else {
    toast.warning("Revisiting stage", {
      description: `Moving back to ${STAGE_LABELS[newStage]}`
    })
  }
}
// Proceed with save regardless
```

### Pattern 5: Journal Header with Real-Time Totals

**What:** Header component that displays aggregated stats from cached member data

**When to use:** Above the grid, updates automatically when cache changes

**Example:**
```typescript
// Source: Requirements JRN-14

interface JournalHeaderProps {
  journal: JournalDetail
  members: JournalMember[]
}

export function JournalHeader({ journal, members }: JournalHeaderProps) {
  // Calculate totals from cached data
  const stats = useMemo(() => {
    const decisions = members
      .map(m => m.decision)
      .filter((d): d is DecisionSummary => d !== null && d.status !== 'declined')

    const totalPledged = decisions.reduce(
      (sum, d) => sum + parseFloat(d.amount),
      0
    )
    const totalMonthly = decisions.reduce(
      (sum, d) => sum + parseFloat(d.monthly_equivalent),
      0
    )
    const decisionCount = decisions.length

    const goalAmount = parseFloat(journal.goal_amount)
    const progressPercent = goalAmount > 0
      ? Math.min((totalPledged / goalAmount) * 100, 100)
      : 0

    return { totalPledged, totalMonthly, decisionCount, progressPercent }
  }, [members, journal.goal_amount])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{journal.name}</h1>
          <p className="text-muted-foreground">
            Goal: ${parseFloat(journal.goal_amount).toLocaleString()}
          </p>
        </div>
        <div className="text-right text-sm">
          <p>{stats.decisionCount} decisions made</p>
          <p className="font-semibold">${stats.totalPledged.toLocaleString()} pledged</p>
        </div>
      </div>
      <Progress value={stats.progressPercent} className="h-2" />
      <p className="text-xs text-muted-foreground text-center">
        {stats.progressPercent.toFixed(0)}% of goal
      </p>
    </div>
  )
}
```

### Pattern 6: Next Steps Checklist Cell

**What:** Checklist component showing task items with toggle functionality

**When to use:** Next Steps column in grid

**Example:**
```typescript
// Source: Requirements JRN-06

interface NextStepsCellProps {
  journalContactId: string
  nextSteps: NextStep[]
  onToggle: (stepId: string, completed: boolean) => void
  onCreate: () => void
}

export function NextStepsCell({
  journalContactId,
  nextSteps,
  onToggle,
  onCreate,
}: NextStepsCellProps) {
  const completedCount = nextSteps.filter(s => s.completed).length
  const totalCount = nextSteps.length

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="flex items-center gap-1 text-sm">
          <CheckSquare className="h-4 w-4" />
          <span>{completedCount}/{totalCount}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-64">
        <div className="space-y-2">
          {nextSteps.map(step => (
            <div key={step.id} className="flex items-center gap-2">
              <Checkbox
                checked={step.completed}
                onCheckedChange={(checked) => onToggle(step.id, !!checked)}
              />
              <span className={step.completed ? "line-through text-muted-foreground" : ""}>
                {step.title}
              </span>
            </div>
          ))}
          <Button variant="ghost" size="sm" onClick={onCreate}>
            + Add step
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
```

### Anti-Patterns to Avoid

- **Forgetting to cancel queries in onMutate:** Without `cancelQueries`, in-flight requests can overwrite optimistic updates
- **Not returning context from onMutate:** Without context, `onError` cannot rollback
- **Mutating cache objects directly:** Always use spread/Object.assign for immutable updates in `setQueryData`
- **Showing stale error toasts:** Clear or debounce error toasts to prevent stacking
- **Re-rendering header on every cell change:** Memoize stats calculation with useMemo
- **Hard-blocking stage transitions:** Requirements say "show warning but allow save"

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimistic UI with rollback | Custom state + try/catch | React Query onMutate/onError | Handles race conditions, cache consistency, automatic retry |
| Toast notifications | Custom toast with setTimeout | Sonner | Queue management, animations, accessibility, cleanup |
| Select dropdown | Custom dropdown with state | Radix Select | Keyboard navigation, ARIA, portal rendering, scroll prevention |
| Progress bar accessibility | div with width | Radix Progress | role="progressbar", aria-valuenow, screen reader support |
| Checkbox accessibility | input type="checkbox" | Radix Checkbox | Indeterminate state, focus management, ARIA |
| Form validation | Manual if/else | Serializer validation (backend) | Already implemented in Django, return 400 with field errors |

**Key insight:** The optimistic update pattern looks simple but has edge cases (concurrent mutations, network failures, stale cache) that React Query handles. Don't implement custom state management.

## Common Pitfalls

### Pitfall 1: Optimistic Update Not Rolling Back

**What goes wrong:** Error occurs but UI stays in optimistic state, showing false data
**Why it happens:**
- `onMutate` doesn't return context
- `onError` doesn't use context to restore
- Cache key mismatch between get/set operations
**How to avoid:**
- Always return `{ previousData }` from `onMutate`
- Always restore cache in `onError` using context
- Use exact same query key for getQueryData and setQueryData
**Warning signs:**
- UI shows updated value but refresh shows old value
- Error toast appears but UI doesn't revert
- Console shows "context is undefined" in onError

### Pitfall 2: Cache Invalidation Over-Fetching

**What goes wrong:** Invalidating too many queries causes waterfall re-fetches
**Why it happens:** Using broad query key patterns like `["journals"]` instead of specific keys
**How to avoid:**
- Use specific query keys: `["journals", journalId, "members", filters]`
- Only invalidate affected queries
- Consider using `setQueryData` for related queries instead of invalidation
**Warning signs:**
- Network tab shows multiple parallel fetches after mutation
- UI flickers as data refetches
- Slow perceived performance after saves

### Pitfall 3: Toast Stack Overflow

**What goes wrong:** Multiple rapid mutations create stack of toasts
**Why it happens:** Each mutation success/error shows toast without rate limiting
**How to avoid:**
- Use Sonner's built-in deduplication with `id` prop
- Debounce rapid operations
- Use `toast.dismiss()` before showing new toast for same operation
**Warning signs:**
- Screen fills with toast notifications
- Toasts overlap or push content
- User can't dismiss toasts fast enough

### Pitfall 4: Dialog Closes Before Mutation Completes

**What goes wrong:** User sees success but data didn't save
**Why it happens:** Closing dialog in onClick before awaiting mutation
**How to avoid:**
```typescript
// BAD: Close before await
onClick={() => {
  mutation.mutate(data)
  onOpenChange(false) // Closes immediately!
}}

// GOOD: Close after await
onClick={async () => {
  await mutation.mutateAsync(data)
  onOpenChange(false) // Closes after success
}}
```
**Warning signs:**
- Dialog closes but no network request in dev tools
- Data doesn't persist after refresh
- No error shown because dialog already closed

### Pitfall 5: Header Re-Renders Cascade

**What goes wrong:** Every cell change re-renders the entire header
**Why it happens:** Stats not memoized, or dependency array includes unstable references
**How to avoid:**
- Wrap stats calculation in `useMemo` with stable dependencies
- Pass `members` as stable reference (from React Query cache)
- Avoid computing totals in render function
**Warning signs:**
- React DevTools shows header re-rendering on every interaction
- Sluggish performance when clicking grid cells
- Console logs show frequent header calculations

### Pitfall 6: Stage Warning Blocks Save

**What goes wrong:** Warning toast prevents stage transition from completing
**Why it happens:** Adding `return` after showing warning, or using `confirm()` dialog
**How to avoid:**
- Requirements explicitly say "no hard blocks"
- Show warning THEN proceed with save
- Never use blocking dialogs for stage warnings
**Warning signs:**
- Users report being "stuck" at a stage
- Stage transitions require confirmation
- Analytics can't track skipped stages (because they never happen)

## Code Examples

Verified patterns from official sources and codebase analysis:

### Decision API Functions

```typescript
// Source: Existing api/journals.ts pattern

/** Decision CRUD types */
export interface DecisionCreate {
  journal_contact: string
  amount: string
  cadence: DecisionCadence
  status: DecisionStatus
}

export interface DecisionUpdate {
  amount?: string
  cadence?: DecisionCadence
  status?: DecisionStatus
}

export interface DecisionDetail {
  id: string
  journal_contact: string
  amount: string
  cadence: DecisionCadence
  status: DecisionStatus
  monthly_equivalent: string
  created_at: string
  updated_at: string
}

/** Create a decision */
export async function createDecision(data: DecisionCreate): Promise<DecisionDetail> {
  const response = await apiClient.post<DecisionDetail>('/journals/decisions/', data)
  return response.data
}

/** Update a decision */
export async function updateDecision(
  id: string,
  data: DecisionUpdate
): Promise<DecisionDetail> {
  const response = await apiClient.patch<DecisionDetail>(
    `/journals/decisions/${id}/`,
    data
  )
  return response.data
}
```

### Decision Mutation Hooks with Optimistic Updates

```typescript
// Source: TanStack Query docs + existing hooks pattern

export function useUpdateDecision(journalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DecisionUpdate }) =>
      updateDecision(id, data),

    onMutate: async ({ id, data }) => {
      // 1. Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["journals", journalId, "members"]
      })

      // 2. Snapshot current cache
      const previousMembers = queryClient.getQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}]
      )

      // 3. Optimistically update
      queryClient.setQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}],
        (old) => {
          if (!old) return old
          return {
            ...old,
            results: old.results.map((member) =>
              member.decision?.id === id
                ? {
                    ...member,
                    decision: { ...member.decision!, ...data }
                  }
                : member
            ),
          }
        }
      )

      // 4. Return context for rollback
      return { previousMembers }
    },

    onError: (err, variables, context) => {
      // Rollback
      if (context?.previousMembers) {
        queryClient.setQueryData(
          ["journals", journalId, "members", {}],
          context.previousMembers
        )
      }
      toast.error("Failed to update decision")
    },

    onSettled: () => {
      // Sync with server
      queryClient.invalidateQueries({
        queryKey: ["journals", journalId, "members"]
      })
    },
  })
}
```

### Sonner Component Setup

```typescript
// Source: shadcn/ui Sonner docs
// frontend/src/components/ui/sonner.tsx

"use client"

import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
```

### Select Component

```typescript
// Source: shadcn/ui Select docs
// frontend/src/components/ui/select.tsx

"use client"

import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

const Select = SelectPrimitive.Root
const SelectGroup = SelectPrimitive.Group
const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        "relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
        className
      )}
      position={position}
      {...props}
    >
      <SelectPrimitive.Viewport
        className={cn(
          "p-1",
          position === "popper" &&
            "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectItem,
}
```

### Progress Component

```typescript
// Source: shadcn/ui Progress docs
// frontend/src/components/ui/progress.tsx

"use client"

import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"
import { cn } from "@/lib/utils"

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      "relative h-4 w-full overflow-hidden rounded-full bg-secondary",
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className="h-full w-full flex-1 bg-primary transition-all"
      style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
    />
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
```

### Checkbox Component

```typescript
// Source: shadcn/ui Checkbox docs
// frontend/src/components/ui/checkbox.tsx

"use client"

import * as React from "react"
import * as CheckboxPrimitive from "@radix-ui/react-checkbox"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground",
      className
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className={cn("flex items-center justify-center text-current")}
    >
      <Check className="h-4 w-4" />
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
))
Checkbox.displayName = CheckboxPrimitive.Root.displayName

export { Checkbox }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| useState + try/catch for mutations | React Query useMutation with optimistic | 2022 | Automatic rollback, cache sync, retry logic |
| react-toastify | Sonner | 2023 | Simpler API, better animations, shadcn/ui integration |
| Custom select dropdowns | Radix Select | 2021 | Full accessibility, keyboard nav, portal rendering |
| Manual progress calculation | useMemo with stable deps | Always | Prevents re-render cascade, React best practice |
| Confirm dialogs for warnings | Toast notifications | UX trend | Non-blocking, better flow, matches requirements |

**Deprecated/outdated:**
- **react-toastify:** Still works but heavier than Sonner, less modern animations
- **setState for mutation results:** React Query handles loading/error/success states
- **Manual optimistic UI:** React Query's onMutate pattern is more reliable

## Open Questions

Things that couldn't be fully resolved:

1. **Next Steps backend model**
   - What we know: Requirements say "checklist items per contact per journal"
   - What's unclear: Is there a NextStep model in Django already, or does Phase 5 need to create it?
   - Recommendation: Check if Task model can be reused (per STATE.md decision "Link journal tasks to existing Task model"). If not, plan includes model creation.

2. **Decision color coding specifics**
   - What we know: Requirements say "color coding for status (pending/active/paused/declined)"
   - What's unclear: Exact color mapping (is pending yellow? active green?)
   - Recommendation: Use semantic colors: pending=warning, active=success, paused=secondary, declined=destructive

3. **Header progress denominator**
   - What we know: Show "percentage toward goal"
   - What's unclear: Is goal based on total pledged or monthly equivalent?
   - Recommendation: Use total pledged (one-time + recurring total) against goal_amount, since goal is typically a campaign total

4. **Decision cell click behavior**
   - What we know: "User can click to open decision update dialog"
   - What's unclear: What if no decision exists - create new, or show empty dialog?
   - Recommendation: Show "Add Decision" button in empty state, dialog adapts to create vs update mode

## Sources

### Primary (HIGH confidence)
- [TanStack Query Optimistic Updates](https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates) - Official optimistic update patterns
- [TanStack Query useMutation](https://tanstack.com/query/latest/docs/framework/react/reference/useMutation) - Mutation hook API reference
- [shadcn/ui Sonner](https://ui.shadcn.com/docs/components/sonner) - Toast component integration
- [shadcn/ui Progress](https://ui.shadcn.com/docs/components/progress) - Progress bar component
- [shadcn/ui Checkbox](https://ui.shadcn.com/docs/components/checkbox) - Checkbox component
- Existing codebase: `frontend/src/hooks/usePledges.ts` - Mutation patterns
- Existing codebase: `apps/journals/views.py` - Decision API implementation
- Existing codebase: `apps/journals/serializers.py` - Decision serializer with history

### Secondary (MEDIUM confidence)
- [Sonner GitHub](https://github.com/emilkowalski/sonner) - Toast library documentation
- [Radix UI Select](https://www.radix-ui.com/primitives/docs/components/select) - Select primitive
- [Radix UI Progress](https://www.radix-ui.com/primitives/docs/components/progress) - Progress primitive
- Phase 4 RESEARCH.md - Grid patterns, memoization strategies
- Phase 3 RESEARCH.md - Decision model and API patterns

### Tertiary (LOW confidence)
- Blog posts on React Query optimistic updates (2025-2026)
- Community discussions on toast notification patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries verified via npm, shadcn/ui official docs
- Architecture: HIGH - Patterns from TanStack Query official docs, existing codebase patterns
- Pitfalls: HIGH - Critical pitfall explicitly called out in STATE.md, verified with docs
- Code examples: HIGH - Based on existing codebase patterns and official documentation

**Research date:** 2026-01-24
**Valid until:** 30 days (React Query stable, shadcn/ui stable)

**Requirements coverage:**
- JRN-05: Sequential Pipeline Flexibility - Stage transition warnings pattern
- JRN-06: Next Steps Checklist - Checkbox component, mutation hooks
- JRN-13: Decision Column Display - DecisionCell, DecisionDialog, color coding
- JRN-14: Journal Header Summary - JournalHeader with Progress, memoized totals

**Critical pitfall addressed:**
- STATE.md: "Phase 5: Optimistic update rollback on error (use React Query mutation onError callbacks)" - Full pattern documented with code examples
