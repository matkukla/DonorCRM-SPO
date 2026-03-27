import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useDuplicateScan, useDismissDuplicate } from "@/hooks/useContacts"
import { ConfidenceBadge } from "./components/ConfidenceBadge"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { ArrowLeft, Search } from "lucide-react"
import type { DuplicatePair } from "@/api/contacts"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/shared/DataTable"

export default function DuplicateList() {
  const navigate = useNavigate()
  const { data, isLoading, isFetching, refetch } = useDuplicateScan()
  const dismissMutation = useDismissDuplicate()

  // Trigger a scan automatically on mount
  useEffect(() => {
    refetch()
  }, [refetch])

  const handleScan = async () => {
    try {
      const result = await refetch()
      if (result.data && result.data.length > 0) {
        toast(`Found ${result.data.length} potential duplicate pairs.`)
      } else {
        toast("No new duplicates found.")
      }
    } catch {
      toast.error("Unable to scan for duplicates. Please try again.")
    }
  }

  const handleDismiss = (pair: DuplicatePair) => {
    dismissMutation.mutate(
      { contact_a_id: pair.contact_a.id, contact_b_id: pair.contact_b.id },
      {
        onSuccess: () => {
          toast("Pair dismissed. They won't be flagged again.")
        },
      }
    )
  }

  const columns: ColumnDef<DuplicatePair>[] = [
    {
      id: "contact_a",
      header: "Contact A",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.contact_a.full_name}</div>
          {row.original.contact_a.email && (
            <div className="text-muted-foreground text-xs">{row.original.contact_a.email}</div>
          )}
        </div>
      ),
    },
    {
      id: "contact_b",
      header: "Contact B",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.contact_b.full_name}</div>
          {row.original.contact_b.email && (
            <div className="text-muted-foreground text-xs">{row.original.contact_b.email}</div>
          )}
        </div>
      ),
    },
    {
      id: "confidence",
      header: "Confidence",
      cell: ({ row }) => <ConfidenceBadge confidence={row.original.confidence} />,
    },
    {
      id: "reasons",
      header: "Match Reason",
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">{row.original.reasons.join(", ")}</span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              navigate(`/contacts/duplicates/${row.original.contact_a.id}--${row.original.contact_b.id}`)
            }}
          >
            Review
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              handleDismiss(row.original)
            }}
          >
            Not Duplicates
          </Button>
        </div>
      ),
    },
  ]

  const pairs = data || []

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Back link */}
          <button
            onClick={() => navigate("/contacts")}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Contacts
          </button>

          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Potential Duplicates</h1>
              <p className="text-muted-foreground mt-1">
                Review and resolve duplicate contacts
              </p>
            </div>
            <Button onClick={handleScan} disabled={isFetching}>
              <Search className="h-4 w-4 mr-2" />
              {isFetching ? "Scanning..." : "Scan for Duplicates"}
            </Button>
          </div>

          {/* Content */}
          {!isLoading && pairs.length === 0 ? (
            <div className="text-center py-16">
              <h3 className="text-lg font-medium">No duplicates found</h3>
              <p className="text-muted-foreground mt-1">
                Your contact list looks clean. Run a scan to check for new duplicates.
              </p>
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={pairs}
              isLoading={isLoading || isFetching}
              aria-label="Potential Duplicates"
            />
          )}
        </div>
      </Container>
    </Section>
  )
}
