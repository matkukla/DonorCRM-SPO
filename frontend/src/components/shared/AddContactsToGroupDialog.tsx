import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { useContacts } from "@/hooks/useContacts"
import { useAddContactsToGroup } from "@/hooks/useGroups"
import { toast } from "sonner"

interface AddContactsToGroupDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  groupId: string
  groupName: string
  existingContactIds: string[]
}

export const AddContactsToGroupDialog = React.memo(function AddContactsToGroupDialog({
  open,
  onOpenChange,
  groupId,
  groupName,
  existingContactIds,
}: AddContactsToGroupDialogProps) {
  const [searchTerm, setSearchTerm] = React.useState("")
  const [debouncedSearch, setDebouncedSearch] = React.useState("")

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  const { data: contactsData, isLoading } = useContacts(
    { search: debouncedSearch },
    { enabled: open }
  )

  const addMutation = useAddContactsToGroup()
  const [pendingIds, setPendingIds] = React.useState<Set<string>>(new Set())
  const [locallyAdded, setLocallyAdded] = React.useState<Set<string>>(new Set())

  React.useEffect(() => {
    if (!open) {
      setSearchTerm("")
      setDebouncedSearch("")
      setLocallyAdded(new Set())
    }
  }, [open])

  const contacts = contactsData?.results ?? []

  const handleAdd = (contactId: string, contactName: string) => {
    setPendingIds((prev) => new Set(prev).add(contactId))
    addMutation.mutate(
      { groupId, contactIds: [contactId] },
      {
        onSuccess: () => {
          setLocallyAdded((prev) => new Set(prev).add(contactId))
          toast.success(`Added ${contactName} to "${groupName}"`)
        },
        onError: () => {
          toast.error("Failed to add contact")
        },
        onSettled: () => {
          setPendingIds((prev) => {
            const next = new Set(prev)
            next.delete(contactId)
            return next
          })
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add Contacts</DialogTitle>
          <DialogDescription>
            Search for contacts to add to this group
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="contact-search">Search Contacts</Label>
            <Input
              id="contact-search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name or email..."
            />
          </div>

          <div className="max-h-[400px] overflow-y-auto space-y-2">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading contacts...
              </div>
            ) : contacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {debouncedSearch ? "No contacts found" : "No contacts yet"}
              </div>
            ) : (
              contacts.map((contact) => {
                const alreadyInGroup = existingContactIds.includes(contact.id) || locallyAdded.has(contact.id)
                return (
                  <div
                    key={contact.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{contact.full_name}</div>
                      {contact.email && (
                        <div className="text-sm text-muted-foreground truncate">
                          {contact.email}
                        </div>
                      )}
                    </div>
                    {alreadyInGroup ? (
                      <Badge variant="secondary" className="ml-3 flex-shrink-0">In group</Badge>
                    ) : (
                      <Button
                        size="sm"
                        className="ml-3 flex-shrink-0"
                        onClick={() => handleAdd(contact.id, contact.full_name)}
                        disabled={pendingIds.has(contact.id)}
                      >
                        Add
                      </Button>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
})
