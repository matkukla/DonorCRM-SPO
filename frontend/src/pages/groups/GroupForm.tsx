import { useState, useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useGroup, useUpdateGroup } from "@/hooks/useGroups"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft } from "lucide-react"

const DEFAULT_COLORS = [
  "#6366f1", // Indigo
  "#8b5cf6", // Violet
  "#ec4899", // Pink
  "#ef4444", // Red
  "#f97316", // Orange
  "#eab308", // Yellow
  "#22c55e", // Green
  "#14b8a6", // Teal
  "#0ea5e9", // Sky
]

export default function GroupForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: existingGroup, isLoading: isLoadingGroup } = useGroup(id || "")
  const updateMutation = useUpdateGroup()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [color, setColor] = useState(DEFAULT_COLORS[0])
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingGroup) {
      setName(existingGroup.name)
      setDescription(existingGroup.description || "")
      setColor(existingGroup.color)
    }
  }, [existingGroup])

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!name.trim()) {
      newErrors.name = "Name is required"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      await updateMutation.mutateAsync({
        id: id!,
        data: { name, description, color },
      })
      navigate(`/groups/${id}`)
    } catch {
      // Error is handled by the mutation
    }
  }

  if (isLoadingGroup) {
    return (
      <Section>
        <Container>
          <div className="max-w-2xl mx-auto">
            <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
            <div className="h-96 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  if (!existingGroup) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Group not found</h1>
            <p className="text-muted-foreground mt-2">
              The group you're trying to edit doesn't exist.
            </p>
            <Button className="mt-4" onClick={() => navigate("/groups")}>
              Back to Groups
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </button>
            <h1 className="text-3xl font-semibold tracking-tight">Edit Group</h1>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Group Details</CardTitle>
                  <CardDescription>Update the group information</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value)
                        if (errors.name) setErrors((prev) => ({ ...prev, name: "" }))
                      }}
                      className={errors.name ? "border-destructive" : ""}
                      placeholder="Group name"
                    />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <textarea
                      id="description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={3}
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="Optional description"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Color</Label>
                    <div className="flex gap-2 flex-wrap">
                      {DEFAULT_COLORS.map((c) => (
                        <button
                          key={c}
                          type="button"
                          className={`w-8 h-8 rounded-full border-2 transition-all ${
                            color === c
                              ? "border-foreground scale-110"
                              : "border-transparent hover:scale-105"
                          }`}
                          style={{ backgroundColor: c }}
                          onClick={() => setColor(c)}
                        />
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Actions */}
              <div className="flex justify-end gap-4">
                <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </Container>
    </Section>
  )
}
