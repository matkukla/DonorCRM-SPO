import { useState, useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useTask, useCreateTask, useUpdateTask } from "@/hooks/useTasks"
import { useSearchContacts } from "@/hooks/useContacts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ArrowLeft, ChevronDown, Search, X } from "lucide-react"
import type { TaskType, TaskPriority, TaskCreate } from "@/api/tasks"
import { taskTypeLabels, taskPriorityLabels } from "@/api/tasks"

export default function TaskForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const preselectedContactId = searchParams.get("contact")

  const { data: existingTask, isLoading: isLoadingTask } = useTask(id || "")
  const createMutation = useCreateTask()
  const updateMutation = useUpdateTask()

  const [contactSearch, setContactSearch] = useState("")
  const [selectedContact, setSelectedContact] = useState<{ id: string; name: string } | null>(null)
  const [showContactDropdown, setShowContactDropdown] = useState(false)

  const { data: contactResults } = useSearchContacts(contactSearch)

  const [formData, setFormData] = useState<TaskCreate>({
    contact: preselectedContactId || undefined,
    title: "",
    description: "",
    task_type: "other",
    priority: "medium",
    due_date: new Date().toISOString().split("T")[0],
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingTask) {
      setFormData({
        contact: existingTask.contact || undefined,
        title: existingTask.title,
        description: existingTask.description || "",
        task_type: existingTask.task_type,
        priority: existingTask.priority,
        due_date: existingTask.due_date,
        due_time: existingTask.due_time || undefined,
        reminder_date: existingTask.reminder_date || undefined,
      })
      if (existingTask.contact && existingTask.contact_name) {
        setSelectedContact({
          id: existingTask.contact,
          name: existingTask.contact_name,
        })
      }
    }
  }, [existingTask])

  useEffect(() => {
    if (preselectedContactId && contactResults) {
      const contact = contactResults.find((c) => c.id === preselectedContactId)
      if (contact) {
        setSelectedContact({ id: contact.id, name: contact.full_name })
        setFormData((prev) => ({ ...prev, contact: contact.id }))
      }
    }
  }, [preselectedContactId, contactResults])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }))
    }
  }

  const handleContactSelect = (contact: { id: string; full_name: string }) => {
    setSelectedContact({ id: contact.id, name: contact.full_name })
    setFormData((prev) => ({ ...prev, contact: contact.id }))
    setContactSearch("")
    setShowContactDropdown(false)
  }

  const handleClearContact = () => {
    setSelectedContact(null)
    setFormData((prev) => ({ ...prev, contact: undefined }))
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.title.trim()) {
      newErrors.title = "Title is required"
    }
    if (!formData.due_date) {
      newErrors.due_date = "Due date is required"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: id!, data: formData })
        navigate(`/tasks/${id}`)
      } else {
        const newTask = await createMutation.mutateAsync(formData)
        navigate(`/tasks/${newTask.id}`)
      }
    } catch {
      // Error is handled by the mutation
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (isEditing && isLoadingTask) {
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
            <h1 className="text-3xl font-semibold tracking-tight">
              {isEditing ? "Edit Task" : "Create Task"}
            </h1>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Task Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Task Details</CardTitle>
                  <CardDescription>What needs to be done?</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="title">Title *</Label>
                    <Input
                      id="title"
                      name="title"
                      value={formData.title}
                      onChange={handleChange}
                      className={errors.title ? "border-destructive" : ""}
                      placeholder="Enter task title"
                    />
                    {errors.title && (
                      <p className="text-sm text-destructive">{errors.title}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <textarea
                      id="description"
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows={3}
                      className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder="Add more details about this task..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Type</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {taskTypeLabels[formData.task_type]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(taskTypeLabels) as TaskType[]).map((t) => (
                            <DropdownMenuItem
                              key={t}
                              onClick={() => setFormData((prev) => ({ ...prev, task_type: t }))}
                            >
                              {taskTypeLabels[t]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <div className="space-y-2">
                      <Label>Priority</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {taskPriorityLabels[formData.priority]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(taskPriorityLabels) as TaskPriority[]).map((p) => (
                            <DropdownMenuItem
                              key={p}
                              onClick={() => setFormData((prev) => ({ ...prev, priority: p }))}
                            >
                              {taskPriorityLabels[p]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Related Contact */}
              <Card>
                <CardHeader>
                  <CardTitle>Related Contact</CardTitle>
                  <CardDescription>Optionally link this task to a contact</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label>Contact</Label>
                    {selectedContact ? (
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <span className="font-medium">{selectedContact.name}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={handleClearContact}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search for a contact..."
                          value={contactSearch}
                          onChange={(e) => {
                            setContactSearch(e.target.value)
                            setShowContactDropdown(true)
                          }}
                          onFocus={() => setShowContactDropdown(true)}
                          className="pl-9"
                        />
                        {showContactDropdown && contactResults && contactResults.length > 0 && (
                          <div className="absolute z-10 w-full mt-1 bg-background border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                            {contactResults.map((contact) => (
                              <button
                                key={contact.id}
                                type="button"
                                className="w-full px-4 py-2 text-left hover:bg-muted"
                                onClick={() => handleContactSelect(contact)}
                              >
                                <div className="font-medium">{contact.full_name}</div>
                                {contact.email && (
                                  <div className="text-sm text-muted-foreground">{contact.email}</div>
                                )}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Schedule */}
              <Card>
                <CardHeader>
                  <CardTitle>Schedule</CardTitle>
                  <CardDescription>When is this task due?</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="due_date">Due Date *</Label>
                      <Input
                        id="due_date"
                        name="due_date"
                        type="date"
                        value={formData.due_date}
                        onChange={handleChange}
                        className={errors.due_date ? "border-destructive" : ""}
                      />
                      {errors.due_date && (
                        <p className="text-sm text-destructive">{errors.due_date}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="due_time">Due Time (optional)</Label>
                      <Input
                        id="due_time"
                        name="due_time"
                        type="time"
                        value={formData.due_time || ""}
                        onChange={handleChange}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="reminder_date">Reminder Date (optional)</Label>
                    <Input
                      id="reminder_date"
                      name="reminder_date"
                      type="date"
                      value={formData.reminder_date || ""}
                      onChange={handleChange}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Actions */}
              <div className="flex justify-end gap-4">
                <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : isEditing ? "Save Changes" : "Create Task"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </Container>
    </Section>
  )
}
