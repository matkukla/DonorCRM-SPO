import * as React from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, UserPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useJournal, useJournalMembers } from "@/hooks/useJournals"
import { JournalGrid, EventTimelineDrawer, JournalHeader, JournalReport, AddContactsDialog } from "./components"
import { useViewAs } from "@/providers/ViewAsProvider"
import type { PipelineStage } from "@/types/journals"

/**
 * State for the timeline drawer.
 */
interface DrawerState {
  isOpen: boolean
  journalContactId: string | null
  stage: PipelineStage | null
  contactName: string
}

const initialDrawerState: DrawerState = {
  isOpen: false,
  journalContactId: null,
  stage: null,
  contactName: "",
}

/**
 * Journal detail page showing the pipeline grid.
 *
 * Route: /journals/:id
 */
export default function JournalDetail() {
  const { id } = useParams<{ id: string }>()
  const { isViewingAs } = useViewAs()

  // Fetch journal details
  const { data: journal, isLoading: journalLoading, isError: journalError } = useJournal(id ?? "")

  // Fetch journal members for grid
  const {
    data: membersData,
    isLoading: membersLoading,
    isError: membersError,
  } = useJournalMembers(id ?? "")

  // Drawer state
  const [drawer, setDrawer] = React.useState<DrawerState>(initialDrawerState)

  // Add contacts dialog state
  const [showAddContacts, setShowAddContacts] = React.useState(false)

  // Handle stage cell click - open drawer
  const handleStageCellClick = React.useCallback(
    (contactId: string, stage: PipelineStage) => {
      // Find member to get contact name and journal_contact ID
      const member = membersData?.results.find((m) => m.contact === contactId)
      if (member) {
        setDrawer({
          isOpen: true,
          journalContactId: member.id, // This is the JournalContact ID
          stage,
          contactName: member.contact_name,
        })
      }
    },
    [membersData]
  )

  // Close drawer
  const handleCloseDrawer = React.useCallback(() => {
    setDrawer(initialDrawerState)
  }, [])

  // Loading state
  if (journalLoading || membersLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          Loading journal...
        </div>
      </div>
    )
  }

  // Error state
  if (journalError || !journal) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-destructive">Failed to load journal</p>
          <Link to="/journals" className="mt-4">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Journals
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const members = membersData?.results ?? []
  const existingContactIds = members.map(m => m.contact)

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Back button and Add Contacts */}
      <div className="flex items-center justify-between">
        <Link to="/journals">
          <Button variant="ghost" size="icon" aria-label="Back to journals">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        {!isViewingAs && (
          <Button variant="outline" onClick={() => setShowAddContacts(true)}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Contacts
          </Button>
        )}
      </div>

      {/* Header with stats */}
      <JournalHeader journal={journal} members={members} />

      {/* Tabs for Grid and Reports */}
      <Tabs defaultValue="grid" className="w-full">
        <TabsList>
          <TabsTrigger value="grid">Pipeline Grid</TabsTrigger>
          <TabsTrigger value="report">Reports</TabsTrigger>
        </TabsList>

        <TabsContent value="grid" className="mt-6">
          {/* Grid */}
          <div className="border rounded-lg bg-card">
            <JournalGrid
              members={members}
              journalId={id ?? ""}
              onStageCellClick={handleStageCellClick}
              isLoading={membersLoading}
            />
          </div>

          {/* Members loading error */}
          {membersError && (
            <div className="text-center py-4 text-destructive">
              Failed to load journal members
            </div>
          )}
        </TabsContent>

        <TabsContent value="report" className="mt-6">
          <JournalReport journalId={id ?? ""} goalAmount={journal.goal_amount} />
        </TabsContent>
      </Tabs>

      {/* Timeline drawer */}
      <EventTimelineDrawer
        journalContactId={drawer.journalContactId}
        stage={drawer.stage}
        contactName={drawer.contactName}
        isOpen={drawer.isOpen}
        onClose={handleCloseDrawer}
      />

      {/* Add Contacts Dialog */}
      <AddContactsDialog
        open={showAddContacts}
        onOpenChange={setShowAddContacts}
        journalId={id ?? ""}
        existingContactIds={existingContactIds}
      />
    </div>
  )
}
