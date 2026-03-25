import { useState, useMemo } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { useCreateBroadcast } from "@/hooks/useBroadcasts"
import { useViewableUsers } from "@/hooks/useUsers"
import type { BroadcastTargetType } from "@/api/broadcasts"
import { broadcastTargetLabels } from "@/api/broadcasts"
import type { TaskType, TaskPriority } from "@/api/tasks"
import { taskTypeLabels, taskPriorityLabels } from "@/api/tasks"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Megaphone, ChevronDown } from "lucide-react"
import { toast } from "sonner"

interface BroadcastTaskDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Step = "form" | "confirm"

const adminTargetOptions: BroadcastTargetType[] = ["all_missionaries", "all_supervisors", "specific_users"]
const supervisorTargetOptions: BroadcastTargetType[] = ["my_team", "specific_users"]

export default function BroadcastTaskDialog({ open, onOpenChange }: BroadcastTaskDialogProps) {
  const { user } = useAuth()
  const createBroadcast = useCreateBroadcast()

  const isAdmin = user?.role === "admin"
  const isSupervisor = user?.role === "supervisor"

  const defaultTarget: BroadcastTargetType = isAdmin ? "all_missionaries" : "my_team"

  const [step, setStep] = useState<Step>("form")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [taskType, setTaskType] = useState<TaskType>("other")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [dueDate, setDueDate] = useState("")
  const [targetType, setTargetType] = useState<BroadcastTargetType>(defaultTarget)
  const [specificUserIds, setSpecificUserIds] = useState<string[]>([])

  const targetOptions = isAdmin ? adminTargetOptions : supervisorTargetOptions
  const supervisedMembers = user?.supervised_users || []
  const { data: viewableUsers } = useViewableUsers()

  // Admin uses viewable users from API; supervisor uses supervised_users from auth
  const selectableUsers = useMemo(() => {
    if (isAdmin && viewableUsers) {
      return viewableUsers.map((u) => ({ id: u.id, first_name: u.full_name, last_name: "" }))
    }
    return supervisedMembers
  }, [isAdmin, viewableUsers, supervisedMembers])

  const getRecipientLabel = (): string => {
    if (targetType === "all_missionaries") return "all missionaries"
    if (targetType === "all_supervisors") return "all supervisors"
    if (targetType === "my_team") return `${selectableUsers.length} team member${selectableUsers.length !== 1 ? "s" : ""}`
    if (targetType === "specific_users") return `${specificUserIds.length} user${specificUserIds.length !== 1 ? "s" : ""}`
    return "selected users"
  }

  const getTargetLabel = (t: BroadcastTargetType): string => {
    if (isSupervisor && t === "specific_users") return "Specific Members"
    return broadcastTargetLabels[t]
  }

  const isFormValid =
    title.trim() !== "" &&
    dueDate !== "" &&
    (targetType !== "specific_users" || specificUserIds.length > 0)

  const handleUserToggle = (userId: string) => {
    setSpecificUserIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    )
  }

  const resetForm = () => {
    setStep("form")
    setTitle("")
    setDescription("")
    setTaskType("other")
    setPriority("medium")
    setDueDate("")
    setTargetType(defaultTarget)
    setSpecificUserIds([])
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetForm()
    }
    onOpenChange(newOpen)
  }

  const handleSend = () => {
    createBroadcast.mutate(
      {
        title: title.trim(),
        description: description.trim() || undefined,
        task_type: taskType,
        priority,
        due_date: dueDate,
        target_type: targetType,
        specific_user_ids: targetType === "specific_users" ? specificUserIds : undefined,
      },
      {
        onSuccess: (data) => {
          toast.success(`Broadcast sent to ${data.recipient_count} users`)
          resetForm()
          onOpenChange(false)
        },
        onError: () => {
          toast.error("Failed to create broadcast")
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        {step === "form" ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Megaphone className="h-5 w-5" />
                Broadcast Task
              </DialogTitle>
              <DialogDescription>
                Create a task for multiple users at once.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="broadcast-title">Title *</Label>
                <Input
                  id="broadcast-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Enter task title"
                  maxLength={255}
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="broadcast-description">Description</Label>
                <textarea
                  id="broadcast-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="Add more details about this task..."
                />
              </div>

              {/* Type and Priority */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Type</Label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="secondary" className="w-full justify-between">
                        {taskTypeLabels[taskType]}
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full">
                      {(Object.keys(taskTypeLabels) as TaskType[]).map((t) => (
                        <DropdownMenuItem key={t} onClick={() => setTaskType(t)}>
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
                        {taskPriorityLabels[priority]}
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full">
                      {(Object.keys(taskPriorityLabels) as TaskPriority[]).map((p) => (
                        <DropdownMenuItem key={p} onClick={() => setPriority(p)}>
                          {taskPriorityLabels[p]}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {/* Due Date */}
              <div className="space-y-2">
                <Label htmlFor="broadcast-due-date">Due Date *</Label>
                <Input
                  id="broadcast-due-date"
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>

              {/* Target Selection */}
              <div className="space-y-2">
                <Label>Target</Label>
                <div className="flex flex-wrap gap-2">
                  {targetOptions.map((t) => (
                    <Button
                      key={t}
                      type="button"
                      variant={targetType === t ? "default" : "secondary"}
                      size="sm"
                      onClick={() => {
                        setTargetType(t)
                        if (t !== "specific_users") {
                          setSpecificUserIds([])
                        }
                      }}
                    >
                      {getTargetLabel(t)}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Specific Users Selection */}
              {targetType === "specific_users" && selectableUsers.length > 0 && (
                <div className="space-y-2">
                  <Label>Select Users</Label>
                  <div className="border rounded-lg max-h-48 overflow-y-auto">
                    {selectableUsers.map((member) => (
                      <label
                        key={member.id}
                        className="flex items-center gap-3 px-3 py-2 hover:bg-muted cursor-pointer"
                      >
                        <Checkbox
                          checked={specificUserIds.includes(String(member.id))}
                          onCheckedChange={() => handleUserToggle(String(member.id))}
                        />
                        <span className="text-sm">
                          {member.last_name ? `${member.first_name} ${member.last_name}` : member.first_name}
                        </span>
                      </label>
                    ))}
                  </div>
                  {specificUserIds.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {specificUserIds.length} user{specificUserIds.length !== 1 ? "s" : ""} selected
                    </p>
                  )}
                </div>
              )}

              {targetType === "specific_users" && selectableUsers.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Loading available users...
                </p>
              )}
            </div>

            <DialogFooter>
              <Button variant="secondary" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={() => setStep("confirm")} disabled={!isFormValid}>
                Next
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Megaphone className="h-5 w-5" />
                Confirm Broadcast
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-3 py-2">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Title</span>
                  <span className="font-medium">{title}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Due Date</span>
                  <span className="font-medium">{dueDate}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Priority</span>
                  <span className="font-medium">{taskPriorityLabels[priority]}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <span className="font-medium">{taskTypeLabels[taskType]}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Target</span>
                  <span className="font-medium">{getTargetLabel(targetType)}</span>
                </div>
              </div>

              <div className="p-3 bg-muted/50 rounded-lg text-sm">
                This will create a task for {getRecipientLabel()}. Proceed?
              </div>
            </div>

            <DialogFooter>
              <Button variant="secondary" onClick={() => setStep("form")}>
                Back
              </Button>
              <Button
                onClick={handleSend}
                disabled={createBroadcast.isPending}
              >
                {createBroadcast.isPending ? "Sending..." : "Send Broadcast"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
