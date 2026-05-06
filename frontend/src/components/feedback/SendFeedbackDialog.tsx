import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useCreateFeedback } from "@/hooks/useFeedback"
import { cn } from "@/lib/utils"
import type { FeedbackType } from "@/api/feedback"

interface SendFeedbackDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface TypeOption {
  value: FeedbackType
  label: string
}

const TYPE_OPTIONS: ReadonlyArray<TypeOption> = [
  { value: "bug", label: "Bug" },
  { value: "feature", label: "Feature Request" },
  { value: "other", label: "Other" },
]

const TITLE_MAX = 255

export function SendFeedbackDialog({
  open,
  onOpenChange,
}: SendFeedbackDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        {/* Remount on each open so form state resets cleanly */}
        {open && <SendFeedbackForm onClose={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

interface SendFeedbackFormProps {
  onClose: () => void
}

function SendFeedbackForm({ onClose }: SendFeedbackFormProps) {
  const [type, setType] = useState<FeedbackType>("bug")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")

  const createMutation = useCreateFeedback()

  const trimmedTitle = title.trim()
  const trimmedDescription = description.trim()
  const canSubmit =
    trimmedTitle.length > 0 &&
    trimmedDescription.length > 0 &&
    !createMutation.isPending

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!canSubmit) return

    createMutation.mutate(
      {
        type,
        title: trimmedTitle,
        description: trimmedDescription,
        page_url: window.location.pathname + window.location.search,
      },
      {
        onSuccess: () => onClose(),
      },
    )
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Send Feedback</DialogTitle>
        <DialogDescription className="sr-only">
          Submit a bug report, feature request, or other feedback.
        </DialogDescription>
      </DialogHeader>

      <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label>Type</Label>
            <div role="radiogroup" aria-label="Feedback type" className="flex flex-wrap gap-2">
              {TYPE_OPTIONS.map((option) => {
                const isSelected = type === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => setType(option.value)}
                    className={cn(
                      "px-4 py-1.5 rounded-full border text-sm font-medium transition-colors",
                      isSelected
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-background text-foreground border-input hover:bg-muted",
                    )}
                  >
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="feedback-title">Title</Label>
            <Input
              id="feedback-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Brief summary"
              maxLength={TITLE_MAX}
              required
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="feedback-description">Description</Label>
            <textarea
              id="feedback-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What happened? What did you expect?"
              rows={5}
              required
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={createMutation.isPending}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={!canSubmit}>
            {createMutation.isPending ? "Sending..." : "Submit"}
          </Button>
        </DialogFooter>
      </form>
    </>
  )
}
