import { useState, useMemo, useCallback } from "react"
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
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
import { ArrowLeft } from "lucide-react"
import { toast } from "sonner"
import { MergeFieldRow } from "./components/MergeFieldRow"
import type { ContactDetail } from "@/api/contacts"

const MERGE_FIELDS = [
  { key: "first_name", label: "First Name" },
  { key: "last_name", label: "Last Name" },
  { key: "organization_name", label: "Organization" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "phone_secondary", label: "Secondary Phone" },
  { key: "street_address", label: "Street Address" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "postal_code", label: "Postal Code" },
  { key: "country", label: "Country" },
  { key: "status", label: "Status" },
  { key: "notes", label: "Notes" },
  { key: "external_id", label: "External ID" },
  { key: "external_constituent_id", label: "Constituent ID" },
] as const

type MergeFieldKey = (typeof MERGE_FIELDS)[number]["key"]

function getFieldValue(contact: ContactDetail, key: string): string | null {
  return (contact as unknown as Record<string, string | null>)[key] ?? null
}

export default function DuplicateMergeView() {
  const { pairId } = useParams<{ pairId: string }>()
  const navigate = useNavigate()

  // Parse pair ID: "leftId--rightId"
  const [leftId, rightId] = useMemo(() => {
    if (!pairId) return ["", ""]
    const parts = pairId.split("--")
    return [parts[0] || "", parts[1] || ""]
  }, [pairId])

  // Load both contacts
  const { data: leftContact, isLoading: leftLoading, isError: leftError } = useContact(leftId)
  const { data: rightContact, isLoading: rightLoading, isError: rightError } = useContact(rightId)

  // State
  const [survivorSide, setSurvivorSide] = useState<"left" | "right" | null>(null)
  const [fieldOverrides, setFieldOverrides] = useState<Record<MergeFieldKey, "left" | "right">>({} as Record<MergeFieldKey, "left" | "right">)

  // Determine which side is the loser (for related records)
  const loserSide = survivorSide === "left" ? "right" : survivorSide === "right" ? "left" : null
  const loserId = loserSide === "left" ? leftId : loserSide === "right" ? rightId : ""

  // Load related records for the loser (records that will be migrated)
  const { data: loserDonations } = useContactDonations(loserId)
  const { data: loserPledges } = useContactPledges(loserId)
  const { data: loserTasks } = useContactTasks(loserId)
  const { data: loserJournals } = useContactJournals(loserId)

  const mergeMutation = useMergeContacts()
  const dismissMutation = useDismissDuplicate()

  // Calculate related records counts
  const donationsList = Array.isArray(loserDonations?.results) ? loserDonations.results : Array.isArray(loserDonations) ? loserDonations : []
  const pledgesList = Array.isArray(loserPledges?.results) ? loserPledges.results : Array.isArray(loserPledges) ? loserPledges : []
  const tasksList = Array.isArray(loserTasks?.results) ? loserTasks.results : Array.isArray(loserTasks) ? loserTasks : []
  const journalsList = Array.isArray(loserJournals) ? loserJournals : []

  const giftsCount = donationsList.length
  const giftsTotal = donationsList.reduce(
    (sum: number, g: Record<string, unknown>) => sum + (Number(g.amount_dollars ?? g.amount ?? 0)),
    0
  )
  const recurringGiftsCount = pledgesList.length
  const tasksCount = tasksList.length
  const journalEntriesCount = journalsList.length

  const handleSurvivorChange = useCallback((side: "left" | "right") => {
    setSurvivorSide(side)
    // Reset all field overrides to the new survivor's side
    const newOverrides: Record<string, "left" | "right"> = {}
    for (const field of MERGE_FIELDS) {
      newOverrides[field.key] = side
    }
    setFieldOverrides(newOverrides as Record<MergeFieldKey, "left" | "right">)
  }, [])

  const handleFieldSideChange = useCallback((field: string, side: "left" | "right") => {
    setFieldOverrides((prev) => ({ ...prev, [field]: side }))
  }, [])

  const handleMerge = async () => {
    if (!survivorSide || !leftContact || !rightContact) return

    const survivorId = survivorSide === "left" ? leftId : rightId
    const loserId = survivorSide === "left" ? rightId : leftId

    // Build field_overrides: only include fields where the override differs from survivor's side
    const overrides: Record<string, "right"> = {}
    for (const field of MERGE_FIELDS) {
      const overrideSide = fieldOverrides[field.key]
      if (overrideSide && overrideSide !== survivorSide) {
        // Backend expects "right" = use loser's value; the filter above ensures only loser fields are included
        overrides[field.key] = "right"
      }
    }

    try {
      await mergeMutation.mutateAsync({
        survivor_id: survivorId,
        loser_id: loserId,
        field_overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
      })
      toast.success("Contacts merged successfully.")
      navigate("/contacts/duplicates")
    } catch {
      toast.error("Failed to merge contacts. No changes were made.")
    }
  }

  const handleKeepBoth = async () => {
    try {
      await dismissMutation.mutateAsync({
        contact_a_id: leftId,
        contact_b_id: rightId,
      })
      toast("Pair dismissed. They won't be flagged again.")
    } catch {
      // Dismiss failed silently, navigate anyway
    }
    navigate("/contacts/duplicates")
  }

  // Loading state
  if (leftLoading || rightLoading) {
    return (
      <Section>
        <Container>
          <div className="max-w-4xl mx-auto">
            <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
            <div className="h-96 bg-muted rounded animate-pulse mb-6" />
            <div className="h-96 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  // Error state
  if (leftError || rightError || !leftContact || !rightContact) {
    return (
      <Section>
        <Container>
          <div className="max-w-4xl mx-auto text-center py-16">
            <h2 className="text-lg font-medium">Unable to load contacts</h2>
            <p className="text-muted-foreground mt-1">
              One or both contacts could not be found.
            </p>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => navigate("/contacts/duplicates")}
            >
              Back to Duplicates
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  const survivorName =
    survivorSide === "left"
      ? leftContact.full_name
      : survivorSide === "right"
        ? rightContact.full_name
        : ""
  const loserName =
    survivorSide === "left"
      ? rightContact.full_name
      : survivorSide === "right"
        ? leftContact.full_name
        : ""

  const isMerging = mergeMutation.isPending
  const isDismissing = dismissMutation.isPending

  return (
    <Section>
      <Container>
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Back link */}
          <button
            onClick={() => navigate("/contacts/duplicates")}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Duplicates
          </button>

          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              Merge Contacts
            </h1>
            <p className="text-muted-foreground mt-1">
              Compare and merge duplicate records
            </p>
          </div>

          {/* Survivor Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Choose which contact to keep</CardTitle>
              <CardDescription>
                The selected contact will be preserved. All records from the other contact will be migrated.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RadioGroup
                value={survivorSide ?? ""}
                onValueChange={(v) => handleSurvivorChange(v as "left" | "right")}
                disabled={isMerging}
              >
                <div className="flex items-center gap-2 min-h-[44px]">
                  <RadioGroupItem value="left" id="survivor-left" />
                  <Label htmlFor="survivor-left" className="cursor-pointer text-sm">
                    Keep Left: {leftContact.full_name}
                  </Label>
                </div>
                <div className="flex items-center gap-2 min-h-[44px]">
                  <RadioGroupItem value="right" id="survivor-right" />
                  <Label htmlFor="survivor-right" className="cursor-pointer text-sm">
                    Keep Right: {rightContact.full_name}
                  </Label>
                </div>
              </RadioGroup>
            </CardContent>
          </Card>

          {/* Field Comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Field Comparison</CardTitle>
              <CardDescription>
                Review and choose values for each field. Fields with identical values are shown once.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[160px]">Field</TableHead>
                    <TableHead>Left ({leftContact.full_name})</TableHead>
                    <TableHead>Right ({rightContact.full_name})</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {MERGE_FIELDS.map((field) => (
                    <MergeFieldRow
                      key={field.key}
                      label={field.label}
                      fieldName={field.key}
                      leftValue={getFieldValue(leftContact, field.key)}
                      rightValue={getFieldValue(rightContact, field.key)}
                      selectedSide={fieldOverrides[field.key] ?? survivorSide ?? "left"}
                      onSideChange={handleFieldSideChange}
                      disabled={!survivorSide || isMerging}
                    />
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Records to Migrate */}
          {survivorSide && (
            <Card>
              <CardHeader>
                <CardTitle>Records to Migrate</CardTitle>
                <CardDescription>
                  From &ldquo;{loserName}&rdquo; to &ldquo;{survivorName}&rdquo;:
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <span className="font-medium">{giftsCount}</span> Gifts
                    {giftsCount > 0 && (
                      <span className="text-muted-foreground">
                        (${giftsTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} total)
                      </span>
                    )}
                  </li>
                  <li>
                    <span className="font-medium">{recurringGiftsCount}</span> Recurring Gifts
                  </li>
                  <li>
                    <span className="font-medium">{tasksCount}</span> Tasks
                  </li>
                  <li>
                    <span className="font-medium">{journalEntriesCount}</span> Journal Entries
                  </li>
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-between pb-8">
            <Button
              variant="secondary"
              onClick={handleKeepBoth}
              disabled={isMerging || isDismissing}
            >
              {isDismissing ? "Dismissing..." : "Keep Both Contacts"}
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button disabled={!survivorSide || isMerging}>
                  {isMerging ? "Merging..." : "Merge Contacts"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Merge these contacts?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will merge &ldquo;{loserName}&rdquo; into &ldquo;{survivorName}&rdquo;.
                    All related records (gifts, tasks, journal entries) will be moved to the
                    surviving contact. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleMerge}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Yes, Merge Contacts
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </Container>
    </Section>
  )
}
