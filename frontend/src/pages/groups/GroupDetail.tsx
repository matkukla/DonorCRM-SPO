import { useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import {
  useGroup,
  useGroupContacts,
  useDeleteGroup,
  useRemoveContactsFromGroup,
} from "@/hooks/useGroups"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  ArrowLeft,
  Copy,
  Edit,
  Trash2,
  Users,
  Lock,
  Globe,
  UserMinus,
} from "lucide-react"
import { toast } from "sonner"
import { getGroupContactEmails } from "@/api/groups"

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // Guard: Don't render until id is available from route params
  if (!id) {
    return null
  }

  const { data: group, isLoading: isLoadingGroup, error } = useGroup(id)
  const { data: contacts, isLoading: isLoadingContacts } = useGroupContacts(id)
  const deleteMutation = useDeleteGroup()
  const removeContactsMutation = useRemoveContactsFromGroup()

  const [selectedContacts, setSelectedContacts] = useState<Set<string>>(new Set())
  const [isCopyingEmails, setIsCopyingEmails] = useState(false)

  const handleCopyEmails = async () => {
    setIsCopyingEmails(true)
    try {
      const result = await getGroupContactEmails(id)
      if (result.emails.length === 0) {
        toast.info("No emails to copy")
        return
      }
      await navigator.clipboard.writeText(result.emails.join(", "))
      toast.success(`Copied ${result.count} emails`)
    } catch {
      toast.error("Failed to copy emails")
    } finally {
      setIsCopyingEmails(false)
    }
  }

  const handleDelete = () => {
    if (group?.is_system) {
      alert("System groups cannot be deleted.")
      return
    }
    if (window.confirm(`Are you sure you want to delete "${group?.name}"? This action cannot be undone.`)) {
      deleteMutation.mutate(id, {
        onSuccess: () => navigate("/groups"),
      })
    }
  }

  const handleRemoveContacts = () => {
    if (selectedContacts.size === 0) return
    if (window.confirm(`Remove ${selectedContacts.size} contact(s) from this group?`)) {
      removeContactsMutation.mutate(
        { groupId: id, contactIds: Array.from(selectedContacts) },
        { onSuccess: () => setSelectedContacts(new Set()) }
      )
    }
  }

  const toggleContact = (contactId: string) => {
    setSelectedContacts((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(contactId)) {
        newSet.delete(contactId)
      } else {
        newSet.add(contactId)
      }
      return newSet
    })
  }

  const toggleAllContacts = () => {
    if (!contacts) return
    if (selectedContacts.size === contacts.length) {
      setSelectedContacts(new Set())
    } else {
      setSelectedContacts(new Set(contacts.map((c) => c.id)))
    }
  }

  if (isLoadingGroup) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  if (error || !group) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Group not found</h1>
            <p className="text-muted-foreground mt-2">
              The group you're looking for doesn't exist or you don't have permission to view it.
            </p>
            <Button className="mt-4" onClick={() => navigate("/groups")}>
              Back to Groups
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Link
                to="/groups"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Groups
              </Link>
              <div className="flex items-center gap-3">
                <div
                  className="w-6 h-6 rounded-full flex-shrink-0"
                  style={{ backgroundColor: group.color }}
                />
                <h1 className="text-3xl font-semibold tracking-tight">{group.name}</h1>
              </div>
              <div className="flex items-center gap-2">
                {group.is_shared ? (
                  <Badge variant="secondary" className="gap-1">
                    <Globe className="h-3 w-3" />
                    Shared
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="gap-1">
                    <Lock className="h-3 w-3" />
                    Private
                  </Badge>
                )}
                {group.is_system && <Badge variant="secondary">System</Badge>}
                <Badge variant="secondary" className="gap-1">
                  <Users className="h-3 w-3" />
                  {group.contact_count} contacts
                </Badge>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => navigate(`/groups/${id}/edit`)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              {!group.is_system && (
                <Button
                  variant="secondary"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Description */}
          {group.description && (
            <Card>
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{group.description}</p>
              </CardContent>
            </Card>
          )}

          {/* Contacts */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Contacts in this Group</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleCopyEmails}
                    disabled={isCopyingEmails}
                  >
                    <Copy className="h-4 w-4 mr-2" />
                    {isCopyingEmails ? "Copying..." : "Copy Emails"}
                  </Button>
                  {selectedContacts.size > 0 && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleRemoveContacts}
                      disabled={removeContactsMutation.isPending}
                    >
                      <UserMinus className="h-4 w-4 mr-2" />
                      Remove {selectedContacts.size} Contact(s)
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingContacts ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-muted rounded animate-pulse" />
                  ))}
                </div>
              ) : contacts && contacts.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedContacts.size === contacts.length}
                          onChange={toggleAllContacts}
                          className="rounded border-gray-300"
                        />
                      </TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Phone</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contacts.map((contact) => (
                      <TableRow
                        key={contact.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigate(`/contacts/${contact.id}`)}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedContacts.has(contact.id)}
                            onChange={() => toggleContact(contact.id)}
                            className="rounded border-gray-300"
                          />
                        </TableCell>
                        <TableCell className="font-medium">{contact.full_name}</TableCell>
                        <TableCell>{contact.email || "—"}</TableCell>
                        <TableCell>{contact.phone || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No contacts in this group yet</p>
                  <p className="text-sm mt-1">
                    Add contacts to this group from the contacts page
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Created: {formatDateTime(group.created_at)}</p>
                <p>Updated: {formatDateTime(group.updated_at)}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
