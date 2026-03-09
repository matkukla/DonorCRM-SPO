import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { NavLink, useNavigate } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAssignments, useUpdateAssignments } from "@/hooks/useUsers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Check, X, ChevronsUpDown } from "lucide-react"
import { useState, useEffect } from "react"
import type { AssignmentUpdate } from "@/api/users"
import { toast } from "sonner"

type LocalAssignment = { supervisor_ids: string[]; coach_ids: string[] }

export default function AdminAssignments() {
  const { data, isLoading } = useAssignments()
  const updateMutation = useUpdateAssignments()

  // Per-plan state: Map-based local assignments with dirty tracking
  const [localAssignments, setLocalAssignments] = useState<Map<string, LocalAssignment>>(new Map())
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  // Track rows made dirty via bulk apply (need additive=true on save)
  const [bulkDirty, setBulkDirty] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState("")
  const [viewMode, setViewMode] = useState<"missionary" | "supervisor">("missionary")

  // Bulk bar state — single supervisor/coach to add to selected missionaries
  const [bulkSupervisor, setBulkSupervisor] = useState<string | null>(null)
  const [bulkCoach, setBulkCoach] = useState<string | null>(null)
  const [bulkSupervisorOpen, setBulkSupervisorOpen] = useState(false)
  const [bulkCoachOpen, setBulkCoachOpen] = useState(false)

  // Initialize localAssignments from API data on first load
  useEffect(() => {
    if (data && localAssignments.size === 0) {
      const initial = new Map<string, LocalAssignment>()
      data.missionaries.forEach(m => {
        initial.set(m.id, {
          supervisor_ids: m.supervisor_ids ?? [],
          coach_ids: m.coach_ids ?? [],
        })
      })
      setLocalAssignments(initial)
    }
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  const navigate = useNavigate()
  const [pendingNav, setPendingNav] = useState<string | null>(null)

  // Handle NavLink clicks when dirty — intercept via onClick
  const handleNavClick = (to: string) => (e: React.MouseEvent) => {
    if (dirty.size > 0) {
      e.preventDefault()
      setPendingNav(to)
    }
  }

  // Block browser tab close / refresh when there are unsaved changes
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty.size > 0) {
        e.preventDefault()
      }
    }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [dirty.size])

  const filteredMissionaries = (data?.missionaries ?? []).filter(m =>
    m.full_name.toLowerCase().includes(search.toLowerCase()) ||
    m.email.toLowerCase().includes(search.toLowerCase())
  )

  const allFilteredSelected =
    filteredMissionaries.length > 0 &&
    filteredMissionaries.every(m => selectedIds.has(m.id))

  const toggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev)
        filteredMissionaries.forEach(m => next.delete(m.id))
        return next
      })
    } else {
      setSelectedIds(prev => {
        const next = new Set(prev)
        filteredMissionaries.forEach(m => next.add(m.id))
        return next
      })
    }
  }

  const toggleRow = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const getAssignment = (id: string): LocalAssignment =>
    localAssignments.get(id) ?? { supervisor_ids: [], coach_ids: [] }

  // Toggle a supervisor for a single missionary
  const toggleSupervisor = (missionaryId: string, missionaryName: string, supervisorId: string) => {
    setLocalAssignments(prev => {
      const next = new Map(prev)
      const current = next.get(missionaryId) ?? { supervisor_ids: [], coach_ids: [] }
      const alreadySelected = current.supervisor_ids.includes(supervisorId)
      const newSupervisorIds = alreadySelected
        ? current.supervisor_ids.filter(id => id !== supervisorId)
        : [...current.supervisor_ids, supervisorId]

      // Soft warning when reaching 5+ supervisors
      if (!alreadySelected && newSupervisorIds.length >= 5) {
        toast.warning(`${missionaryName} now has 5+ supervisors assigned`)
      }

      next.set(missionaryId, { ...current, supervisor_ids: newSupervisorIds })
      return next
    })
    setDirty(prev => new Set([...prev, missionaryId]))
    setBulkDirty(prev => { const next = new Set(prev); next.delete(missionaryId); return next })
  }

  // Toggle a coach for a single missionary
  const toggleCoach = (missionaryId: string, coachId: string) => {
    setLocalAssignments(prev => {
      const next = new Map(prev)
      const current = next.get(missionaryId) ?? { supervisor_ids: [], coach_ids: [] }
      const alreadySelected = current.coach_ids.includes(coachId)
      const newCoachIds = alreadySelected
        ? current.coach_ids.filter(id => id !== coachId)
        : [...current.coach_ids, coachId]
      next.set(missionaryId, { ...current, coach_ids: newCoachIds })
      return next
    })
    setDirty(prev => new Set([...prev, missionaryId]))
    setBulkDirty(prev => { const next = new Set(prev); next.delete(missionaryId); return next })
  }

  // Bulk apply: add a supervisor to all selected missionaries (additive)
  const handleBulkApplySupervisor = () => {
    if (!bulkSupervisor) return
    setLocalAssignments(prev => {
      const next = new Map(prev)
      selectedIds.forEach(id => {
        const current = next.get(id) ?? { supervisor_ids: [], coach_ids: [] }
        if (!current.supervisor_ids.includes(bulkSupervisor)) {
          next.set(id, { ...current, supervisor_ids: [...current.supervisor_ids, bulkSupervisor] })
        }
      })
      return next
    })
    setDirty(prev => new Set([...prev, ...selectedIds]))
    setBulkDirty(prev => new Set([...prev, ...selectedIds]))
  }

  // Bulk apply: add a coach to all selected missionaries (additive)
  const handleBulkApplyCoach = () => {
    if (!bulkCoach) return
    setLocalAssignments(prev => {
      const next = new Map(prev)
      selectedIds.forEach(id => {
        const current = next.get(id) ?? { supervisor_ids: [], coach_ids: [] }
        if (!current.coach_ids.includes(bulkCoach)) {
          next.set(id, { ...current, coach_ids: [...current.coach_ids, bulkCoach] })
        }
      })
      return next
    })
    setDirty(prev => new Set([...prev, ...selectedIds]))
    setBulkDirty(prev => new Set([...prev, ...selectedIds]))
  }

  const handleSave = async () => {
    const assignments: AssignmentUpdate[] = [...dirty].map(id => {
      const assignment = localAssignments.get(id) ?? { supervisor_ids: [], coach_ids: [] }
      return {
        missionary_id: id,
        supervisor_ids: assignment.supervisor_ids,
        coach_ids: assignment.coach_ids,
        additive: bulkDirty.has(id),
      }
    })
    try {
      const result = await updateMutation.mutateAsync(assignments)
      setDirty(new Set())
      setBulkDirty(new Set())
      if (result.errors && result.errors.length > 0) {
        toast.error(`Saved with ${result.errors.length} error(s)`)
      } else {
        toast.success(`Updated ${result.updated} assignment${result.updated !== 1 ? "s" : ""}`)
      }
    } catch {
      toast.error("Failed to save assignments")
    }
  }

  // Derive supervisor view: group missionaries under each supervisor
  const supervisorViewMap = (() => {
    const map = new Map<string, string[]>()
    data?.supervisors.forEach(s => map.set(s.id, []))
    data?.missionaries.forEach(m => {
      const assignment = localAssignments.get(m.id) ?? { supervisor_ids: [], coach_ids: [] }
      assignment.supervisor_ids.forEach(sid => {
        if (map.has(sid)) {
          map.get(sid)!.push(m.id)
        }
      })
    })
    return map
  })()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Admin Sub-Navigation */}
          <div className="flex gap-4 border-b border-border pb-2">
            <NavLink
              to="/admin"
              end
              onClick={handleNavClick("/admin")}
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Users
            </NavLink>
            <NavLink
              to="/admin/analytics"
              onClick={handleNavClick("/admin/analytics")}
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Analytics
            </NavLink>
            <NavLink
              to="/admin/assignments"
              onClick={handleNavClick("/admin/assignments")}
              className={({ isActive }) =>
                cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"
                )
              }
            >
              Assignments
            </NavLink>
          </div>

          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Assignments</h1>
            <p className="text-muted-foreground mt-1">
              Assign supervisors and coaches to each missionary
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "missionary" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("missionary")}
            >
              By Missionary
            </Button>
            <Button
              variant={viewMode === "supervisor" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("supervisor")}
            >
              By Supervisor
            </Button>
          </div>

          {/* Toolbar (missionary view only) */}
          {viewMode === "missionary" && (
            <div className="flex items-center gap-3">
              <Input
                placeholder="Search missionaries..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="max-w-sm"
              />
              <div className="flex-1" />
              <Button
                disabled={dirty.size === 0 || updateMutation.isPending}
                onClick={handleSave}
              >
                {updateMutation.isPending
                  ? "Saving..."
                  : dirty.size > 0
                  ? `Save Changes (${dirty.size})`
                  : "Save Changes"}
              </Button>
            </div>
          )}

          {/* Bulk Bar (missionary view only) */}
          {viewMode === "missionary" && selectedIds.size > 0 && (
            <div className="flex items-center gap-3 rounded-md border border-border bg-muted/50 px-4 py-2 flex-wrap">
              <span className="text-sm font-medium">
                {selectedIds.size} selected
              </span>
              {/* Bulk supervisor add */}
              <div className="flex items-center gap-2 ml-4">
                <span className="text-sm text-muted-foreground">Add supervisor:</span>
                <Popover open={bulkSupervisorOpen} onOpenChange={setBulkSupervisorOpen}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm" className="w-[160px] justify-between font-normal h-8">
                      {bulkSupervisor
                        ? (() => {
                            const s = data?.supervisors.find(s => s.id === bulkSupervisor)
                            return s ? `${s.first_name} ${s.last_name}` : "Choose..."
                          })()
                        : "Choose..."}
                      <ChevronsUpDown className="ml-2 h-3 w-3 opacity-50 shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[200px] p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Search..." />
                      <CommandList>
                        <CommandEmpty>No supervisors found.</CommandEmpty>
                        <CommandGroup>
                          {data?.supervisors.map(s => (
                            <CommandItem
                              key={s.id}
                              value={`${s.first_name} ${s.last_name} ${s.email}`}
                              onSelect={() => {
                                setBulkSupervisor(s.id)
                                setBulkSupervisorOpen(false)
                              }}
                            >
                              <Check
                                className={cn("mr-2 h-4 w-4", bulkSupervisor === s.id ? "opacity-100" : "opacity-0")}
                              />
                              {s.first_name} {s.last_name}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!bulkSupervisor}
                  onClick={handleBulkApplySupervisor}
                >
                  Apply
                </Button>
              </div>
              {/* Bulk coach add */}
              <div className="flex items-center gap-2 ml-2">
                <span className="text-sm text-muted-foreground">Add coach:</span>
                <Popover open={bulkCoachOpen} onOpenChange={setBulkCoachOpen}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm" className="w-[160px] justify-between font-normal h-8">
                      {bulkCoach
                        ? (() => {
                            const c = data?.coaches.find(c => c.id === bulkCoach)
                            return c ? `${c.first_name} ${c.last_name}` : "Choose..."
                          })()
                        : "Choose..."}
                      <ChevronsUpDown className="ml-2 h-3 w-3 opacity-50 shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[200px] p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Search..." />
                      <CommandList>
                        <CommandEmpty>No coaches found.</CommandEmpty>
                        <CommandGroup>
                          {data?.coaches.map(c => (
                            <CommandItem
                              key={c.id}
                              value={`${c.first_name} ${c.last_name} ${c.email}`}
                              onSelect={() => {
                                setBulkCoach(c.id)
                                setBulkCoachOpen(false)
                              }}
                            >
                              <Check
                                className={cn("mr-2 h-4 w-4", bulkCoach === c.id ? "opacity-100" : "opacity-0")}
                              />
                              {c.first_name} {c.last_name}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!bulkCoach}
                  onClick={handleBulkApplyCoach}
                >
                  Apply
                </Button>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto text-muted-foreground"
                onClick={() => setSelectedIds(new Set())}
              >
                Clear selection
              </Button>
            </div>
          )}

          {/* Missionary View Table */}
          {viewMode === "missionary" && (
            isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-14 bg-muted rounded animate-pulse" />
                ))}
              </div>
            ) : filteredMissionaries.length > 0 ? (
              <div className="rounded-md border border-border overflow-hidden">
                {/* Table Header */}
                <div className="grid grid-cols-[40px_1fr_1fr_1fr_32px] items-center gap-2 px-4 py-2 bg-muted/50 text-sm font-medium text-muted-foreground border-b border-border">
                  <Checkbox
                    checked={allFilteredSelected}
                    onCheckedChange={toggleSelectAll}
                    aria-label="Select all"
                  />
                  <span>Missionary</span>
                  <span>Supervisors</span>
                  <span>Coaches</span>
                  <span />
                </div>

                {/* Table Rows */}
                {filteredMissionaries.map(missionary => {
                  const assignment = getAssignment(missionary.id)
                  const isDirty = dirty.has(missionary.id)
                  const isSelected = selectedIds.has(missionary.id)

                  return (
                    <div
                      key={missionary.id}
                      className={cn(
                        "grid grid-cols-[40px_1fr_1fr_1fr_32px] items-start gap-2 px-4 py-3 border-b border-border last:border-0 transition-colors",
                        isSelected && "bg-primary/5"
                      )}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleRow(missionary.id)}
                        aria-label={`Select ${missionary.full_name}`}
                        className="mt-1"
                      />
                      <div className="min-w-0 mt-0.5">
                        <p className="font-medium truncate">{missionary.full_name}</p>
                        <p className="text-sm text-muted-foreground truncate">{missionary.email}</p>
                      </div>

                      {/* Supervisor multi-select */}
                      <SupervisorCell
                        supervisorIds={assignment.supervisor_ids}
                        allSupervisors={data?.supervisors ?? []}
                        onToggle={(supId) => toggleSupervisor(missionary.id, missionary.full_name, supId)}
                        onRemove={(supId) => toggleSupervisor(missionary.id, missionary.full_name, supId)}
                      />

                      {/* Coach multi-select */}
                      <CoachCell
                        coachIds={assignment.coach_ids}
                        allCoaches={data?.coaches ?? []}
                        onToggle={(coachId) => toggleCoach(missionary.id, coachId)}
                        onRemove={(coachId) => toggleCoach(missionary.id, coachId)}
                      />

                      {/* Dirty indicator */}
                      <div className="flex items-center justify-center mt-1">
                        {isDirty && (
                          <span
                            className="text-amber-500 text-lg leading-none"
                            title="Unsaved changes"
                            aria-label="Unsaved changes"
                          >
                            ●
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-md border border-border py-12 text-center text-muted-foreground">
                {search
                  ? "No missionaries match your search."
                  : "No missionaries found. Create missionary users to manage assignments."}
              </div>
            )
          )}

          {/* Supervisor View Table (read-only) */}
          {viewMode === "supervisor" && (
            isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-14 bg-muted rounded animate-pulse" />
                ))}
              </div>
            ) : (data?.supervisors ?? []).length > 0 ? (
              <div className="rounded-md border border-border overflow-hidden">
                {/* Table Header */}
                <div className="grid grid-cols-[1fr_2fr] items-center gap-4 px-4 py-2 bg-muted/50 text-sm font-medium text-muted-foreground border-b border-border">
                  <span>Supervisor</span>
                  <span>Assigned Missionaries</span>
                </div>
                {(data?.supervisors ?? []).map(supervisor => {
                  const missionaryIds = supervisorViewMap.get(supervisor.id) ?? []
                  return (
                    <div
                      key={supervisor.id}
                      className="grid grid-cols-[1fr_2fr] items-start gap-4 px-4 py-3 border-b border-border last:border-0"
                    >
                      <div className="min-w-0">
                        <p className="font-medium">{supervisor.first_name} {supervisor.last_name}</p>
                        <p className="text-sm text-muted-foreground truncate">{supervisor.email}</p>
                      </div>
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {missionaryIds.length === 0 ? (
                          <span className="text-sm text-muted-foreground">No missionaries assigned</span>
                        ) : (
                          missionaryIds.map(mid => {
                            const m = data?.missionaries.find(m => m.id === mid)
                            return m ? (
                              <Badge key={mid} variant="secondary">
                                {m.full_name}
                              </Badge>
                            ) : null
                          })
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-md border border-border py-12 text-center text-muted-foreground">
                No supervisors found.
              </div>
            )
          )}
          {/* Sticky Save bar — visible when missionary view has unsaved changes */}
          {viewMode === "missionary" && dirty.size > 0 && (
            <div className="sticky bottom-0 z-10 border-t border-border bg-background/95 backdrop-blur-sm py-3 -mx-4 px-4 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {dirty.size} unsaved change{dirty.size !== 1 ? "s" : ""}
              </span>
              <Button
                disabled={updateMutation.isPending}
                onClick={handleSave}
              >
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          )}
        </div>
      </Container>

      {/* Unsaved-changes navigation guard dialog */}
      {pendingNav !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background rounded-lg border border-border p-6 shadow-lg max-w-sm w-full mx-4">
            <h2 className="text-lg font-semibold mb-2">Unsaved Changes</h2>
            <p className="text-sm text-muted-foreground mb-4">
              You have {dirty.size} unsaved assignment change{dirty.size !== 1 ? "s" : ""}. Leave anyway?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setPendingNav(null)}>
                Stay
              </Button>
              <Button variant="destructive" size="sm" onClick={() => { navigate(pendingNav); setPendingNav(null) }}>
                Leave
              </Button>
            </div>
          </div>
        </div>
      )}
    </Section>
  )
}

// -- Sub-components --

interface SupervisorCellProps {
  supervisorIds: string[]
  allSupervisors: { id: string; first_name: string; last_name: string; email: string }[]
  onToggle: (supId: string) => void
  onRemove: (supId: string) => void
}

function SupervisorCell({ supervisorIds, allSupervisors, onToggle, onRemove }: SupervisorCellProps) {
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
            {supervisorIds.length > 0
              ? `${supervisorIds.length} supervisor${supervisorIds.length !== 1 ? "s" : ""}`
              : "Assign supervisor..."}
            <ChevronsUpDown className="ml-2 h-3 w-3 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search supervisors..." />
            <CommandList>
              <CommandEmpty>No supervisors found.</CommandEmpty>
              <CommandGroup>
                {allSupervisors.map(s => (
                  <CommandItem
                    key={s.id}
                    value={`${s.first_name} ${s.last_name} ${s.email}`}
                    onSelect={() => onToggle(s.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        supervisorIds.includes(s.id) ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <span>{s.first_name} {s.last_name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {supervisorIds.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {supervisorIds.map(sid => {
            const s = allSupervisors.find(s => s.id === sid)
            return s ? (
              <Badge key={sid} variant="secondary" className="gap-1 text-xs">
                {s.first_name} {s.last_name}
                <button
                  type="button"
                  className="ml-1 rounded-full outline-none hover:bg-muted"
                  onClick={() => onRemove(sid)}
                  aria-label={`Remove ${s.first_name} ${s.last_name}`}
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

interface CoachCellProps {
  coachIds: string[]
  allCoaches: { id: string; first_name: string; last_name: string; email: string }[]
  onToggle: (coachId: string) => void
  onRemove: (coachId: string) => void
}

function CoachCell({ coachIds, allCoaches, onToggle, onRemove }: CoachCellProps) {
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
            {coachIds.length > 0
              ? `${coachIds.length} coach${coachIds.length !== 1 ? "es" : ""}`
              : "Assign coach..."}
            <ChevronsUpDown className="ml-2 h-3 w-3 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search coaches..." />
            <CommandList>
              <CommandEmpty>No coaches found.</CommandEmpty>
              <CommandGroup>
                {allCoaches.map(c => (
                  <CommandItem
                    key={c.id}
                    value={`${c.first_name} ${c.last_name} ${c.email}`}
                    onSelect={() => onToggle(c.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        coachIds.includes(c.id) ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <span>{c.first_name} {c.last_name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {coachIds.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {coachIds.map(cid => {
            const c = allCoaches.find(c => c.id === cid)
            return c ? (
              <Badge key={cid} variant="secondary" className="gap-1 text-xs">
                {c.first_name} {c.last_name}
                <button
                  type="button"
                  className="ml-1 rounded-full outline-none hover:bg-muted"
                  onClick={() => onRemove(cid)}
                  aria-label={`Remove ${c.first_name} ${c.last_name}`}
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
