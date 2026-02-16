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
import { useAddContactToJournal } from "@/hooks/useJournals"

export interface AddContactsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  journalId: string
  existingContactIds: string[]
}

export const AddContactsDialog = React.memo(function AddContactsDialog({
  open,
  onOpenChange,
  journalId,
  existingContactIds,
}: AddContactsDialogProps) {
  const [searchTerm, setSearchTerm] = React.useState("")
  const [debouncedSearch, setDebouncedSearch] = React.useState("")

  // Debounce search term
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTerm])

  // Fetch contacts with search filter
  const { data: contactsData, isLoading } = useContacts({
    search: debouncedSearch || undefined,
  })

  const addContactMutation = useAddContactToJournal(journalId)

  // Reset search when dialog closes
  React.useEffect(() => {
    if (!open) {
      setSearchTerm("")
      setDebouncedSearch("")
    }
  }, [open])

  const contacts = contactsData?.results ?? []

  const handleAddContact = (contactId: string) => {
    addContactMutation.mutate(contactId)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add Contacts to Journal</DialogTitle>
          <DialogDescription>
            Search for contacts to add to this journal
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search Input */}
          <div className="space-y-2">
            <Label htmlFor="search">Search Contacts</Label>
            <Input
              id="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name or email..."
            />
          </div>

          {/* Contact List */}
          <div className="max-h-[400px] overflow-y-auto space-y-2">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading contacts...
              </div>
            ) : contacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {debouncedSearch ? "No contacts found" : "Start typing to search"}
              </div>
            ) : (
              contacts.map((contact) => {
                const isAlreadyAdded = existingContactIds.includes(contact.id)
                const isAdding = addContactMutation.isPending

                return (
                  <div
                    key={contact.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="font-medium">{contact.full_name}</div>
                      {contact.email && (
                        <div className="text-sm text-muted-foreground">
                          {contact.email}
                        </div>
                      )}
                    </div>
                    {isAlreadyAdded ? (
                      <Badge variant="secondary">Already added</Badge>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleAddContact(contact.id)}
                        disabled={isAdding}
                      >
                        {isAdding ? "Adding..." : "Add"}
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
