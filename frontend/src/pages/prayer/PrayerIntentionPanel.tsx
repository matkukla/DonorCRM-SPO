import { useState, useEffect, useRef } from "react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Trash2 } from "lucide-react"
import { useSearchContacts } from "@/hooks/useContacts"
import { useCreatePrayer, useUpdatePrayer, useDeletePrayer } from "@/hooks/usePrayers"
import type { PrayerIntention, PrayerIntentionStatus } from "@/api/prayers"

interface PrayerIntentionPanelProps {
  open: boolean
  onClose: () => void
  intention?: PrayerIntention
  lockedContactId?: string
  lockedContactName?: string
}

export function PrayerIntentionPanel({
  open,
  onClose,
  intention,
  lockedContactId,
  lockedContactName,
}: PrayerIntentionPanelProps) {
  const isEdit = !!intention

  const [title, setTitle] = useState("")
  const [status, setStatus] = useState<PrayerIntentionStatus>("active")
  const [contactId, setContactId] = useState("")
  const [contactSearch, setContactSearch] = useState("")
  const [contactName, setContactName] = useState("")
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: searchResults } = useSearchContacts(contactSearch)
  const createMutation = useCreatePrayer()
  const updateMutation = useUpdatePrayer()
  const deleteMutation = useDeletePrayer()

  // Reset form when panel opens/changes
  useEffect(() => {
    if (open) {
      if (intention) {
        setTitle(intention.title)
        setStatus(intention.status)
        setContactId(intention.contact)
        setContactName(intention.contact_name)
        setContactSearch("")
      } else {
        setTitle("")
        setStatus("active")
        if (lockedContactId) {
          setContactId(lockedContactId)
          setContactName(lockedContactName || "")
        } else {
          setContactId("")
          setContactName("")
        }
        setContactSearch("")
      }
      setShowDropdown(false)
    }
  }, [open, intention, lockedContactId, lockedContactName])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !contactId) return

    if (isEdit) {
      updateMutation.mutate(
        {
          id: intention.id,
          data: { title: title.trim(), status, contact: contactId },
        },
        { onSuccess: () => onClose() },
      )
    } else {
      createMutation.mutate(
        { title: title.trim(), contact: contactId, status },
        { onSuccess: () => onClose() },
      )
    }
  }

  const handleDelete = () => {
    if (!intention) return
    if (window.confirm("Are you sure you want to delete this prayer intention?")) {
      deleteMutation.mutate(intention.id, { onSuccess: () => onClose() })
    }
  }

  const selectContact = (id: string, name: string) => {
    setContactId(id)
    setContactName(name)
    setContactSearch("")
    setShowDropdown(false)
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          <DialogHeader>
            <DialogTitle className="font-serif text-amber-900 dark:text-amber-100">
              {isEdit ? "Edit Prayer Intention" : "Add Prayer Intention"}
            </DialogTitle>
            <DialogDescription className="text-amber-700/80 dark:text-amber-400/60">
              {isEdit
                ? "Update this prayer intention."
                : "Create a new prayer intention for a contact."}
            </DialogDescription>
          </DialogHeader>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="prayer-title">Prayer Intention</Label>
            <Input
              id="prayer-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What to pray for..."
              required
            />
          </div>

          {/* Contact picker */}
          <div className="space-y-2">
            <Label>Contact</Label>
            {lockedContactId ? (
              <p className="text-sm font-medium py-2 px-3 bg-muted rounded-lg">
                {lockedContactName || contactName}
              </p>
            ) : (
              <div className="relative" ref={dropdownRef}>
                {contactId && contactName && !showDropdown ? (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium flex-1 py-2 px-3 bg-muted rounded-lg">
                      {contactName}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setContactId("")
                        setContactName("")
                        setContactSearch("")
                        setShowDropdown(true)
                      }}
                    >
                      Change
                    </Button>
                  </div>
                ) : (
                  <>
                    <Input
                      value={contactSearch}
                      onChange={(e) => {
                        setContactSearch(e.target.value)
                        setShowDropdown(true)
                      }}
                      onFocus={() => contactSearch.length >= 2 && setShowDropdown(true)}
                      placeholder="Search contacts..."
                    />
                    {showDropdown && searchResults && searchResults.length > 0 && (
                      <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {searchResults.map((contact) => (
                          <button
                            key={contact.id}
                            type="button"
                            className="w-full text-left px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                            onMouseDown={(e) => {
                              e.preventDefault()
                              selectContact(contact.id, contact.full_name)
                            }}
                          >
                            {contact.full_name}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Status — only on edit; new intentions default to "active" */}
          {isEdit && (
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={status}
                onValueChange={(v) => setStatus(v as PrayerIntentionStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="answered">Answered</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-4">
            <Button
              type="submit"
              disabled={isPending || !title.trim() || !contactId}
              className="flex-1"
            >
              {isPending
                ? "Saving..."
                : isEdit
                  ? "Save Changes"
                  : "Add Prayer"}
            </Button>
            {isEdit && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="text-destructive hover:text-destructive"
                aria-label="Delete prayer intention"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
