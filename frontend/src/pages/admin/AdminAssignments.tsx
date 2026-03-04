import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAssignments, useUpdateAssignments } from "@/hooks/useUsers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useState, useEffect } from "react"
import type { AssignmentUpdate } from "@/api/users"
import { toast } from "sonner"

export default function AdminAssignments() {
  const { data, isLoading } = useAssignments()
  const updateMutation = useUpdateAssignments()

  // Per-plan state: Map-based local assignments with dirty tracking
  const [localAssignments, setLocalAssignments] = useState<
    Map<string, { supervisor_id: string | null; coach_id: string | null }>
  >(new Map())
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState("")
  const [bulkSupervisor, setBulkSupervisor] = useState<string | null>(null)
  const [bulkCoach, setBulkCoach] = useState<string | null>(null)

  // Initialize localAssignments from API data on first load
  useEffect(() => {
    if (data && localAssignments.size === 0) {
      const initial = new Map<string, { supervisor_id: string | null; coach_id: string | null }>()
      data.missionaries.forEach(m => {
        initial.set(m.id, {
          supervisor_id: m.supervisor_id,
          coach_id: m.coach_id,
        })
      })
      setLocalAssignments(initial)
    }
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

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

  const handleDropdownChange = (
    missionaryId: string,
    field: "supervisor_id" | "coach_id",
    value: string | null
  ) => {
    setLocalAssignments(prev => {
      const next = new Map(prev)
      const current = next.get(missionaryId) ?? { supervisor_id: null, coach_id: null }
      next.set(missionaryId, { ...current, [field]: value })
      return next
    })
    setDirty(prev => new Set([...prev, missionaryId]))
  }

  const handleBulkApply = (field: "supervisor_id" | "coach_id", value: string | null) => {
    setLocalAssignments(prev => {
      const next = new Map(prev)
      selectedIds.forEach(id => {
        const current = next.get(id) ?? { supervisor_id: null, coach_id: null }
        next.set(id, { ...current, [field]: value })
      })
      return next
    })
    setDirty(prev => new Set([...prev, ...selectedIds]))
  }

  const handleSave = async () => {
    const assignments: AssignmentUpdate[] = [...dirty].map(id => ({
      missionary_id: id,
      ...(localAssignments.get(id) ?? { supervisor_id: null, coach_id: null }),
    }))
    try {
      const result = await updateMutation.mutateAsync(assignments)
      setDirty(new Set())
      if (result.errors && result.errors.length > 0) {
        toast.error(`Saved with ${result.errors.length} error(s)`)
      } else {
        toast.success(`Updated ${result.updated} assignment${result.updated !== 1 ? "s" : ""}`)
      }
    } catch {
      toast.error("Failed to save assignments")
    }
  }

  const getAssignment = (id: string) =>
    localAssignments.get(id) ?? { supervisor_id: null, coach_id: null }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Admin Sub-Navigation */}
          <div className="flex gap-4 border-b border-border pb-2">
            <NavLink
              to="/admin"
              end
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

          {/* Toolbar */}
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

          {/* Bulk Bar */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3 rounded-md border border-border bg-muted/50 px-4 py-2">
              <span className="text-sm font-medium">
                {selectedIds.size} selected
              </span>
              <div className="flex items-center gap-2 ml-4">
                <span className="text-sm text-muted-foreground">Supervisor:</span>
                <Select
                  value={bulkSupervisor ?? "none"}
                  onValueChange={v => setBulkSupervisor(v === "none" ? null : v)}
                >
                  <SelectTrigger className="w-[160px] h-8 text-sm">
                    <SelectValue placeholder="Choose..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">— Unassigned</SelectItem>
                    {data?.supervisors.map(s => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.first_name} {s.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleBulkApply("supervisor_id", bulkSupervisor)}
                >
                  Apply
                </Button>
              </div>
              <div className="flex items-center gap-2 ml-2">
                <span className="text-sm text-muted-foreground">Coach:</span>
                <Select
                  value={bulkCoach ?? "none"}
                  onValueChange={v => setBulkCoach(v === "none" ? null : v)}
                >
                  <SelectTrigger className="w-[160px] h-8 text-sm">
                    <SelectValue placeholder="Choose..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">— Unassigned</SelectItem>
                    {data?.coaches.map(c => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.first_name} {c.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleBulkApply("coach_id", bulkCoach)}
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

          {/* Table */}
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-14 bg-muted rounded animate-pulse" />
              ))}
            </div>
          ) : filteredMissionaries.length > 0 ? (
            <div className="rounded-md border border-border overflow-hidden">
              {/* Table Header */}
              <div className="grid grid-cols-[40px_1fr_200px_200px_32px] items-center gap-2 px-4 py-2 bg-muted/50 text-sm font-medium text-muted-foreground border-b border-border">
                <Checkbox
                  checked={allFilteredSelected}
                  onCheckedChange={toggleSelectAll}
                  aria-label="Select all"
                />
                <span>Missionary</span>
                <span>Supervisor</span>
                <span>Coach</span>
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
                      "grid grid-cols-[40px_1fr_200px_200px_32px] items-center gap-2 px-4 py-3 border-b border-border last:border-0 transition-colors",
                      isSelected && "bg-primary/5"
                    )}
                  >
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => toggleRow(missionary.id)}
                      aria-label={`Select ${missionary.full_name}`}
                    />
                    <div className="min-w-0">
                      <p className="font-medium truncate">{missionary.full_name}</p>
                      <p className="text-sm text-muted-foreground truncate">{missionary.email}</p>
                    </div>
                    <Select
                      value={assignment.supervisor_id ?? "none"}
                      onValueChange={v =>
                        handleDropdownChange(missionary.id, "supervisor_id", v === "none" ? null : v)
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="— Unassigned" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">— Unassigned</SelectItem>
                        {data?.supervisors.map(s => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.first_name} {s.last_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select
                      value={assignment.coach_id ?? "none"}
                      onValueChange={v =>
                        handleDropdownChange(missionary.id, "coach_id", v === "none" ? null : v)
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="— Unassigned" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">— Unassigned</SelectItem>
                        {data?.coaches.map(c => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.first_name} {c.last_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {/* Dirty indicator */}
                    <div className="flex items-center justify-center">
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
          )}
        </div>
      </Container>
    </Section>
  )
}
