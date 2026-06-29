import * as React from "react"
import { useNavigate } from "react-router-dom"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { useCreateJournal } from "@/hooks/useJournals"
import { toast } from "sonner"

export interface CreateJournalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export const CreateJournalDialog = React.memo(function CreateJournalDialog({
  open,
  onOpenChange,
}: CreateJournalDialogProps) {
  const navigate = useNavigate()
  const [name, setName] = React.useState("")
  const [goalAmount, setGoalAmount] = React.useState("")
  const [deadline, setDeadline] = React.useState("")

  const createJournalMutation = useCreateJournal()
  const isPending = createJournalMutation.isPending
  const isSubmittingRef = React.useRef(false)

  // Reset form when dialog closes
  React.useEffect(() => {
    if (!open) {
      setName("")
      setGoalAmount("")
      setDeadline("")
    }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Synchronous guard — prevents double-submit before isPending re-renders
    if (isSubmittingRef.current) return
    isSubmittingRef.current = true

    if (!name || !goalAmount) {
      toast.error("Name and goal amount are required")
      isSubmittingRef.current = false
      return
    }

    try {
      const result = await createJournalMutation.mutateAsync({
        name,
        goal_amount: goalAmount,
        deadline: deadline || null,
      })
      toast.success("Journal created")
      onOpenChange(false)
      navigate(`/journals/${result.id}`)
    } catch {
      toast.error("Failed to create journal")
    } finally {
      isSubmittingRef.current = false
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create New Journal</DialogTitle>
          <DialogDescription>
            Create a new fundraising pipeline journal
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. 2024 Support Raising Campaign"
              required
            />
          </div>

          {/* Goal Amount */}
          <div className="space-y-2">
            <Label htmlFor="goal-amount">
              Goal Amount <span className="text-destructive">*</span>
            </Label>
            <Input
              id="goal-amount"
              type="text"
              inputMode="decimal"
              value={goalAmount}
              onChange={(e) => setGoalAmount(e.target.value)}
              placeholder="e.g. 50000.00"
              required
            />
          </div>

          {/* Deadline */}
          <div className="space-y-2">
            <Label htmlFor="deadline">Deadline (optional)</Label>
            <Input
              id="deadline"
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || !name || !goalAmount}>
              {isPending ? "Creating..." : "Create Journal"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
})
