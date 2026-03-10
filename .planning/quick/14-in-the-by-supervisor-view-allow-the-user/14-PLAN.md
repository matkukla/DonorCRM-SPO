---
phase: quick-14
plan: 14
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/admin/AdminAssignments.tsx
autonomous: true
requirements: [QUICK-14]
must_haves:
  truths:
    - "In the By Supervisor view, each supervisor row has a missionary multi-select control"
    - "Adding a missionary to a supervisor row assigns that supervisor to the missionary (and marks it dirty)"
    - "Removing a missionary badge from a supervisor row removes that supervisor from the missionary"
    - "Saving from the By Supervisor view persists changes to the backend"
    - "The sticky save bar and unsaved-changes nav guard work in the supervisor view"
  artifacts:
    - path: frontend/src/pages/admin/AdminAssignments.tsx
      provides: "Editable supervisor view with MissionaryCell sub-component"
  key_links:
    - from: "supervisor view MissionaryCell"
      to: "localAssignments Map (keyed by missionary_id)"
      via: "toggleMissionaryForSupervisor handler"
      pattern: "supervisor_ids add/remove per missionary"
---

<objective>
Make the "By Supervisor" view in AdminAssignments editable. Currently it is read-only (badges only). Users should be able to click a multi-select on each supervisor row to add or remove missionaries assigned to that supervisor.

Purpose: Supervisors are sometimes easier to assign from the supervisor's perspective ("who does this supervisor manage?") rather than from each missionary's row.
Output: Editable supervisor view with the same save/dirty/guard infrastructure as the missionary view.
</objective>

<execution_context>
@/home/matkukla/.claude/get-shit-done/workflows/execute-plan.md
@/home/matkukla/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@frontend/src/pages/admin/AdminAssignments.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add toggleMissionaryForSupervisor handler and MissionaryCell sub-component</name>
  <files>frontend/src/pages/admin/AdminAssignments.tsx</files>
  <action>
All changes are in AdminAssignments.tsx only.

**1. Add `toggleMissionaryForSupervisor` handler** (alongside `toggleSupervisor` / `toggleCoach`):

```ts
const toggleMissionaryForSupervisor = (missionaryId: string, supervisorId: string) => {
  setLocalAssignments(prev => {
    const next = new Map(prev)
    const current = next.get(missionaryId) ?? { supervisor_ids: [], coach_ids: [] }
    const alreadyAssigned = current.supervisor_ids.includes(supervisorId)
    const newSupervisorIds = alreadyAssigned
      ? current.supervisor_ids.filter(id => id !== supervisorId)
      : [...current.supervisor_ids, supervisorId]
    next.set(missionaryId, { ...current, supervisor_ids: newSupervisorIds })
    return next
  })
  setDirty(prev => new Set([...prev, missionaryId]))
  setBulkDirty(prev => { const next = new Set(prev); next.delete(missionaryId); return next })
}
```

**2. Update the supervisor view table** (lines ~534-582). Replace the read-only badge render for each supervisor row with a `MissionaryCell` component:

Current supervisor row body:
```tsx
<div className="flex flex-wrap gap-1 pt-0.5">
  {missionaryIds.length === 0 ? (
    <span className="text-sm text-muted-foreground">No missionaries assigned</span>
  ) : (
    missionaryIds.map(mid => { ... Badge ... })
  )}
</div>
```

Replace with:
```tsx
<MissionaryCell
  supervisorId={supervisor.id}
  assignedMissionaryIds={missionaryIds}
  allMissionaries={data?.missionaries ?? []}
  onToggle={(mId) => toggleMissionaryForSupervisor(mId, supervisor.id)}
  onRemove={(mId) => toggleMissionaryForSupervisor(mId, supervisor.id)}
/>
```

**3. Show sticky save bar in supervisor view too** — change the condition on the sticky bar from:
```tsx
{viewMode === "missionary" && dirty.size > 0 && (
```
to:
```tsx
{dirty.size > 0 && (
```

**4. Show nav guard dialog in supervisor view too** — the guard dialog at the bottom already fires when `pendingNav !== null` unconditionally, so no change needed there. However the `handleNavClick` check also fires unconditionally on `dirty.size > 0` — no change needed.

**5. Add `MissionaryCell` sub-component** at the bottom of the file (after `CoachCell`), modelled exactly on `SupervisorCell`:

```tsx
interface MissionaryCellProps {
  supervisorId: string
  assignedMissionaryIds: string[]
  allMissionaries: { id: string; full_name: string; email: string }[]
  onToggle: (mId: string) => void
  onRemove: (mId: string) => void
}

function MissionaryCell({ supervisorId, assignedMissionaryIds, allMissionaries, onToggle, onRemove }: MissionaryCellProps) {
  const [open, setOpen] = useState(false)
  return (
    <div className="space-y-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal h-8 text-sm"
          >
            {assignedMissionaryIds.length > 0
              ? `${assignedMissionaryIds.length} missionary${assignedMissionaryIds.length !== 1 ? "ies" : ""}`
              : "Assign missionary..."}
            <ChevronsUpDown className="ml-2 h-3 w-3 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[240px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search missionaries..." />
            <CommandList>
              <CommandEmpty>No missionaries found.</CommandEmpty>
              <CommandGroup>
                {allMissionaries.map(m => (
                  <CommandItem
                    key={m.id}
                    value={`${m.full_name} ${m.email}`}
                    onSelect={() => onToggle(m.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        assignedMissionaryIds.includes(m.id) ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <span>{m.full_name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {assignedMissionaryIds.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {assignedMissionaryIds.map(mid => {
            const m = allMissionaries.find(m => m.id === mid)
            return m ? (
              <Badge key={mid} variant="secondary" className="gap-1 text-xs">
                {m.full_name}
                <button
                  type="button"
                  className="ml-1 rounded-full outline-none hover:bg-muted"
                  onClick={() => onRemove(mid)}
                  aria-label={`Remove ${m.full_name}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ) : null
          })}
        </div>
      )}
    </div>
  )
}
```

**6. Update the supervisor view table grid** to accommodate the wider cell. Change the grid from `grid-cols-[1fr_2fr]` to `grid-cols-[1fr_2fr]` — this is fine as-is, the MissionaryCell will expand naturally. No grid change needed.

**Note on `supervisorId` prop:** `MissionaryCell` receives `supervisorId` in its props interface but does not use it in the render — it is only there for clarity. Remove it from the interface if TypeScript complains about unused props; alternatively omit it from the interface and just rely on the closure in `onToggle`/`onRemove` (preferred — simpler).

Final simplified interface (no supervisorId prop needed since it's closed over in the parent):
```tsx
interface MissionaryCellProps {
  assignedMissionaryIds: string[]
  allMissionaries: { id: string; full_name: string; email: string }[]
  onToggle: (mId: string) => void
  onRemove: (mId: string) => void
}
```
  </action>
  <verify>
    <automated>cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
    - TypeScript compiles with no errors
    - By Supervisor view shows a "Assign missionary..." popover button per supervisor row
    - Selecting a missionary from the popover adds them as a badge and marks the row dirty
    - Clicking X on a badge removes the missionary from that supervisor
    - Sticky save bar appears when dirty in supervisor view
    - Save persists changes via the existing updateMutation infrastructure
  </done>
</task>

</tasks>

<verification>
1. `cd /home/matkukla/projects/DonorCRM/frontend && npx tsc --noEmit` — no errors
2. Navigate to /admin/assignments, switch to "By Supervisor" — each supervisor row has an "Assign missionary..." button
3. Click button, select a missionary — badge appears, save bar appears at bottom
4. Click X on a badge — badge removed
5. Click "Save Changes" — toast confirms updated count, dirty indicator clears
</verification>

<success_criteria>
By Supervisor view is fully editable: missionaries can be assigned to or removed from any supervisor, and changes are saved via the existing assignment API with the same dirty-tracking and save infrastructure as the By Missionary view.
</success_criteria>

<output>
After completion, create `.planning/quick/14-in-the-by-supervisor-view-allow-the-user/14-SUMMARY.md`
</output>
