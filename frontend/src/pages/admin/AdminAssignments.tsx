import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAssignments, useUpdateAssignments } from "@/hooks/useUsers"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useState } from "react"
import type { AssignmentUpdate } from "@/api/users"
import { toast } from "sonner"

export default function AdminAssignments() {
  const { data, isLoading } = useAssignments()
  const updateMutation = useUpdateAssignments()

  // Local state: assignment overrides before saving
  const [overrides, setOverrides] = useState<Record<string, { supervisor_id: string | null; coach_id: string | null }>>({})

  const getAssignment = (missionaryId: string) => {
    if (overrides[missionaryId]) return overrides[missionaryId]
    const missionary = data?.missionaries.find(m => m.id === missionaryId)
    return {
      supervisor_id: missionary?.supervisor_id ?? null,
      coach_id: missionary?.coach_id ?? null,
    }
  }

  const setOverride = (missionaryId: string, field: "supervisor_id" | "coach_id", value: string | null) => {
    setOverrides(prev => ({
      ...prev,
      [missionaryId]: {
        ...getAssignment(missionaryId),
        [field]: value,
      },
    }))
  }

  const handleSave = async () => {
    if (!data) return
    const assignments: AssignmentUpdate[] = data.missionaries.map(m => {
      const override = overrides[m.id]
      return {
        missionary_id: m.id,
        supervisor_id: override ? override.supervisor_id : m.supervisor_id,
        coach_id: override ? override.coach_id : m.coach_id,
      }
    })
    try {
      const result = await updateMutation.mutateAsync(assignments)
      setOverrides({})
      toast.success(`Updated ${result.updated} assignments`)
    } catch {
      toast.error("Failed to save assignments")
    }
  }

  const hasChanges = Object.keys(overrides).length > 0

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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Assignments</h1>
              <p className="text-muted-foreground mt-1">
                Assign supervisors and coaches to missionaries
              </p>
            </div>
            {hasChanges && (
              <Button onClick={handleSave} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-muted rounded animate-pulse" />
              ))}
            </div>
          ) : data && data.missionaries.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Missionary Assignments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.missionaries.map(missionary => {
                    const assignment = getAssignment(missionary.id)
                    return (
                      <div key={missionary.id} className="flex items-center gap-4 py-2 border-b last:border-0">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium">{missionary.full_name}</p>
                          <p className="text-sm text-muted-foreground">{missionary.email}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">Supervisor</p>
                            <Select
                              value={assignment.supervisor_id ?? "none"}
                              onValueChange={(v) => setOverride(missionary.id, "supervisor_id", v === "none" ? null : v)}
                            >
                              <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="None" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="none">None</SelectItem>
                                {data.supervisors.map(s => (
                                  <SelectItem key={s.id} value={s.id}>
                                    {s.first_name} {s.last_name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">Coach</p>
                            <Select
                              value={assignment.coach_id ?? "none"}
                              onValueChange={(v) => setOverride(missionary.id, "coach_id", v === "none" ? null : v)}
                            >
                              <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="None" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="none">None</SelectItem>
                                {data.coaches.map(c => (
                                  <SelectItem key={c.id} value={c.id}>
                                    {c.first_name} {c.last_name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No missionaries found. Create missionary users to manage assignments.
              </CardContent>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  )
}
