import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useGroups } from "@/hooks/useGroups"
import { useAddContactsToGroup } from "@/hooks/useGroups"
import { toast } from "sonner"

interface AddToGroupDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contactIds: string[]
  onSuccess?: () => void
}

export function AddToGroupDialog({
  open,
  onOpenChange,
  contactIds,
  onSuccess,
}: AddToGroupDialogProps) {
  const { data: groups, isLoading } = useGroups()
  const addMutation = useAddContactsToGroup()

  const handleAdd = (groupId: string, groupName: string) => {
    addMutation.mutate(
      { groupId, contactIds },
      {
        onSuccess: () => {
          toast.success(`Added ${contactIds.length} contact${contactIds.length === 1 ? "" : "s"} to "${groupName}"`)
          onOpenChange(false)
          onSuccess?.()
        },
        onError: () => {
          toast.error("Failed to add contacts to group")
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Add to Group</DialogTitle>
          <DialogDescription>
            Select a group to add {contactIds.length} contact{contactIds.length === 1 ? "" : "s"} to.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1 max-h-72 overflow-y-auto">
          {isLoading ? (
            <p className="text-sm text-muted-foreground text-center py-6">Loading groups...</p>
          ) : !groups?.length ? (
            <p className="text-sm text-muted-foreground text-center py-6">No groups yet</p>
          ) : (
            groups.map((group) => (
              <button
                key={group.id}
                onClick={() => handleAdd(group.id, group.name)}
                disabled={addMutation.isPending}
                className="flex items-center gap-3 w-full rounded-md px-3 py-2.5 text-sm hover:bg-muted transition-colors disabled:opacity-50 text-left"
              >
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: group.color }}
                />
                <span className="flex-1 truncate">{group.name}</span>
                <span className="text-xs text-muted-foreground">{group.contact_count}</span>
              </button>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
