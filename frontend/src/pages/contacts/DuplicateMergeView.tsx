import { useState, useMemo } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
  useContact,
  useContactDonations,
  useContactPledges,
  useContactTasks,
  useContactJournals,
  useMergeContacts,
  useDismissDuplicate,
} from "@/hooks/useContacts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { ArrowLeft, Check } from "lucide-react"
import { toast } from "sonner"
import type { ContactDetail } from "@/api/contacts"

const DISPLAY_FIELDS = [
  { key: "first_name", label: "First Name" },
  { key: "last_name", label: "Last Name" },
  { key: "organization_name", label: "Organization" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "phone_secondary", label: "Secondary Phone" },
  { key: "street_address", label: "Address" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "postal_code", label: "Postal Code" },
  { key: "country", label: "Country" },
  { key: "status", label: "Status" },
  { key: "notes", label: "Notes" },
] as const

function val(contact: ContactDetail, key: string): string {
  return String((contact as unknown as Record<string, unknown>)[key] ?? "").trim()
}

export default function DuplicateMergeView() {
  const { pairId } = useParams<{ pairId: string }>()
  const navigate = useNavigate()

  const [leftId, rightId] = useMemo(() => {
    if (!pairId) return ["", ""]
    const parts = pairId.split("--")
    return [parts[0] || "", parts[1] || ""]
  }, [pairId])

  const { data: leftContact, isLoading: leftLoading, isError: leftError } = useContact(leftId)
  const { data: rightContact, isLoading: rightLoading, isError: rightError } = useContact(rightId)

  const [survivorSide, setSurvivorSide] = useState<"left" | "right" | null>(null)

  const loserId = survivorSide === "left" ? rightId : survivorSide === "right" ? leftId : ""
  const { data: loserDonations } = useContactDonations(loserId)
  const { data: loserPledges } = useContactPledges(loserId)
  const { data: loserTasks } = useContactTasks(loserId)
  const { data: loserJournals } = useContactJournals(loserId)

  const mergeMutation = useMergeContacts()
  const dismissMutation = useDismissDuplicate()

  // Counts for "records to migrate"
  const giftsCount = (Array.isArray(loserDonations?.results) ? loserDonations.results : Array.isArray(loserDonations) ? loserDonations : []).length
  const recurringCount = (Array.isArray(loserPledges?.results) ? loserPledges.results : Array.isArray(loserPledges) ? loserPledges : []).length
  const tasksCount = (Array.isArray(loserTasks?.results) ? loserTasks.results : Array.isArray(loserTasks) ? loserTasks : []).length
  const journalsCount = (Array.isArray(loserJournals) ? loserJournals : []).length

  // Auto-fill preview: which blank fields on the survivor will be filled from loser
  const autoFillFields = useMemo(() => {
    if (!survivorSide || !leftContact || !rightContact) return []
    const survivor = survivorSide === "left" ? leftContact : rightContact
    const loser = survivorSide === "left" ? rightContact : leftContact
    return DISPLAY_FIELDS.filter((f) => !val(survivor, f.key) && val(loser, f.key)).map((f) => ({
      label: f.label,
      value: val(loser, f.key),
    }))
  }, [survivorSide, leftContact, rightContact])

  const survivorName = survivorSide === "left" ? leftContact?.full_name : survivorSide === "right" ? rightContact?.full_name : ""
  const loserName = survivorSide === "left" ? rightContact?.full_name : survivorSide === "right" ? leftContact?.full_name : ""

  const handleMerge = async () => {
    if (!survivorSide || !leftContact || !rightContact) return
    try {
      await mergeMutation.mutateAsync({
        survivor_id: survivorSide === "left" ? leftId : rightId,
        loser_id: survivorSide === "left" ? rightId : leftId,
      })
      toast.success("Contacts merged successfully.")
      navigate("/contacts/duplicates")
    } catch {
      toast.error("Failed to merge contacts. No changes were made.")
    }
  }

  const handleKeepBoth = async () => {
    try {
      await dismissMutation.mutateAsync({ contact_a_id: leftId, contact_b_id: rightId })
      toast("Pair dismissed. They won't be flagged again.")
    } catch { /* navigate anyway */ }
    navigate("/contacts/duplicates")
  }

  if (leftLoading || rightLoading) {
    return (
      <Section><Container>
        <div className="max-w-4xl mx-auto">
          <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-80 bg-muted rounded animate-pulse" />
            <div className="h-80 bg-muted rounded animate-pulse" />
          </div>
        </div>
      </Container></Section>
    )
  }

  if (leftError || rightError || !leftContact || !rightContact) {
    return (
      <Section><Container>
        <div className="max-w-4xl mx-auto text-center py-16">
          <h2 className="text-lg font-medium">Unable to load contacts</h2>
          <p className="text-muted-foreground mt-1">One or both contacts could not be found.</p>
          <Button variant="secondary" className="mt-4" onClick={() => navigate("/contacts/duplicates")}>Back to Duplicates</Button>
        </div>
      </Container></Section>
    )
  }

  const isMerging = mergeMutation.isPending

  return (
    <Section>
      <Container>
        <div className="max-w-4xl mx-auto space-y-6">
          <button onClick={() => navigate("/contacts/duplicates")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" /> Back to Duplicates
          </button>

          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Merge Contacts</h1>
            <p className="text-muted-foreground mt-1">Pick which contact to keep. Empty fields will be filled from the other record.</p>
          </div>

          {/* Side-by-side contact cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ContactCard contact={leftContact} other={rightContact} selected={survivorSide === "left"} onSelect={() => setSurvivorSide("left")} disabled={isMerging} />
            <ContactCard contact={rightContact} other={leftContact} selected={survivorSide === "right"} onSelect={() => setSurvivorSide("right")} disabled={isMerging} />
          </div>

          {/* Auto-fill preview */}
          {survivorSide && autoFillFields.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-base">Fields to auto-fill from {loserName}</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {autoFillFields.map((f) => (
                    <li key={f.label} className="flex gap-2">
                      <span className="text-muted-foreground w-32 shrink-0">{f.label}:</span>
                      <span className="font-medium text-green-700 dark:text-green-400">{f.value}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Records to migrate */}
          {survivorSide && (giftsCount + recurringCount + tasksCount + journalsCount > 0) && (
            <Card>
              <CardHeader><CardTitle className="text-base">Records to migrate from {loserName}</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {giftsCount > 0 && <li><span className="font-medium">{giftsCount}</span> Gifts</li>}
                  {recurringCount > 0 && <li><span className="font-medium">{recurringCount}</span> Recurring Gifts</li>}
                  {tasksCount > 0 && <li><span className="font-medium">{tasksCount}</span> Tasks</li>}
                  {journalsCount > 0 && <li><span className="font-medium">{journalsCount}</span> Journal Entries</li>}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Footer actions */}
          <div className="flex items-center justify-between pb-8">
            <Button variant="secondary" onClick={handleKeepBoth} disabled={isMerging || dismissMutation.isPending}>
              {dismissMutation.isPending ? "Dismissing..." : "Keep Both Contacts"}
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button disabled={!survivorSide || isMerging}>{isMerging ? "Merging..." : "Merge Contacts"}</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Merge these contacts?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will merge &ldquo;{loserName}&rdquo; into &ldquo;{survivorName}&rdquo;.
                    All related records will be moved to the surviving contact. Empty fields on the survivor will be filled from the merged record. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep Both Contacts</AlertDialogCancel>
                  <AlertDialogAction onClick={handleMerge} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Yes, Merge Contacts</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </Container>
    </Section>
  )
}

/** Side-by-side contact card with diff highlighting */
function ContactCard({ contact, other, selected, onSelect, disabled }: {
  contact: ContactDetail
  other: ContactDetail
  selected: boolean
  onSelect: () => void
  disabled: boolean
}) {
  return (
    <Card className={selected ? "ring-2 ring-primary" : "opacity-80 hover:opacity-100 transition-opacity"}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          {contact.full_name || contact.organization_name || "Unnamed"}
          {selected && <Check className="h-5 w-5 text-primary" />}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-sm">
        {DISPLAY_FIELDS.map((f) => {
          const v = val(contact, f.key)
          const otherV = val(other, f.key)
          if (!v && !otherV) return null
          const differs = v && otherV && v !== otherV
          return (
            <div key={f.key} className={`flex gap-2 py-0.5 px-1 rounded ${differs ? "bg-amber-50 dark:bg-amber-950/20" : ""}`}>
              <span className="text-muted-foreground w-28 shrink-0">{f.label}</span>
              <span className={v ? "font-medium" : "text-muted-foreground italic"}>{v || "—"}</span>
            </div>
          )
        })}
        <Button className="w-full mt-4" variant={selected ? "default" : "outline"} onClick={onSelect} disabled={disabled}>
          {selected ? "Keeping this contact" : "Keep this contact"}
        </Button>
      </CardContent>
    </Card>
  )
}
