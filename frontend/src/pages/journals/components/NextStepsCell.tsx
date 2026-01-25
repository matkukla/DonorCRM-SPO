import * as React from "react"
import { CheckSquare, Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  useNextSteps,
  useCreateNextStep,
  useUpdateNextStep,
  useDeleteNextStep,
} from "@/hooks/useJournals"
import type { NextStep } from "@/types/journals"

export interface NextStepsCellProps {
  /** Journal contact ID to fetch/manage next steps */
  journalContactId: string
}

/**
 * Next steps checklist cell for the journal grid.
 *
 * Per JRN-06:
 * - User can create, edit, and mark complete checklist items per contact per journal
 * - Next Steps are independent items (not single boolean)
 * - Visible in journal grid
 *
 * Shows count badge, opens popover with full checklist on click.
 */
export const NextStepsCell = React.memo(function NextStepsCell({
  journalContactId,
}: NextStepsCellProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [newStepTitle, setNewStepTitle] = React.useState("")

  // Fetch next steps only when popover is open
  const { data: stepsData, isLoading } = useNextSteps(journalContactId, {
    enabled: isOpen,
  })

  const createMutation = useCreateNextStep(journalContactId)
  const updateMutation = useUpdateNextStep(journalContactId)
  const deleteMutation = useDeleteNextStep(journalContactId)

  const steps = stepsData?.results ?? []
  const completedCount = steps.filter((s) => s.completed).length
  const totalCount = steps.length

  const handleToggle = React.useCallback(
    (step: NextStep) => {
      updateMutation.mutate({
        id: step.id,
        data: { completed: !step.completed },
      })
    },
    [updateMutation]
  )

  const handleCreate = React.useCallback(() => {
    if (!newStepTitle.trim()) return
    createMutation.mutate(
      {
        journal_contact: journalContactId,
        title: newStepTitle.trim(),
      },
      {
        onSuccess: () => setNewStepTitle(""),
      }
    )
  }, [journalContactId, newStepTitle, createMutation])

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault()
        handleCreate()
      }
    },
    [handleCreate]
  )

  const handleDelete = React.useCallback(
    (stepId: string) => {
      deleteMutation.mutate(stepId)
    },
    [deleteMutation]
  )

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          className="flex items-center gap-1 text-sm px-2 py-1 rounded hover:bg-accent transition-colors"
          aria-label={`${completedCount} of ${totalCount} next steps complete`}
        >
          <CheckSquare className="h-4 w-4" />
          {totalCount > 0 ? (
            <span className="tabular-nums">
              {completedCount}/{totalCount}
            </span>
          ) : (
            <span className="text-muted-foreground">0</span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72" align="start">
        <div className="space-y-3">
          <h4 className="font-medium text-sm">Next Steps</h4>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : steps.length === 0 ? (
            <p className="text-sm text-muted-foreground">No next steps yet</p>
          ) : (
            <ul className="space-y-2">
              {steps.map((step) => (
                <li key={step.id} className="flex items-start gap-2 group">
                  <Checkbox
                    checked={step.completed}
                    onCheckedChange={() => handleToggle(step)}
                    className="mt-0.5"
                    disabled={updateMutation.isPending}
                  />
                  <span
                    className={
                      step.completed
                        ? "line-through text-muted-foreground flex-1 text-sm"
                        : "flex-1 text-sm"
                    }
                  >
                    {step.title}
                  </span>
                  <button
                    onClick={() => handleDelete(step.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                    aria-label="Delete step"
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Add new step */}
          <div className="flex gap-2 pt-2 border-t">
            <Input
              value={newStepTitle}
              onChange={(e) => setNewStepTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Add a step..."
              className="h-8 text-sm"
              disabled={createMutation.isPending}
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCreate}
              disabled={!newStepTitle.trim() || createMutation.isPending}
              className="h-8 px-2"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
})
