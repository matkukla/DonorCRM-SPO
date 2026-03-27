import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ConfidenceBadge } from "./ConfidenceBadge"
import type { DuplicateMatch } from "@/api/contacts"

interface DuplicateWarningDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  matches: DuplicateMatch[]
  onKeepEditing: () => void
  onCreateAnyway: () => void
  isCreating: boolean
}

export function DuplicateWarningDialog({
  open,
  onOpenChange,
  matches,
  onKeepEditing,
  onCreateAnyway,
  isCreating,
}: DuplicateWarningDialogProps) {
  // Show at most 3 matches (per CONTEXT.md locked decision)
  const visibleMatches = matches.slice(0, 3)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Possible Duplicates Found</DialogTitle>
          <DialogDescription>
            We found contacts that may be duplicates of the one you're creating.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 my-4">
          {visibleMatches.map((match) => (
            <Card key={match.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-sm">{match.full_name}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      {match.email && <span>{match.email}</span>}
                      {match.phone && <span>{match.phone}</span>}
                    </div>
                  </div>
                  <ConfidenceBadge confidence={match.confidence} />
                </div>
                <div className="mt-2">
                  <a
                    href={`/contacts/${match.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    View Contact
                  </a>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <DialogFooter className="flex gap-2 sm:justify-between">
          <Button variant="secondary" onClick={onKeepEditing} disabled={isCreating}>
            Keep Editing
          </Button>
          <Button onClick={onCreateAnyway} disabled={isCreating}>
            {isCreating ? "Creating..." : "Create Anyway"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
