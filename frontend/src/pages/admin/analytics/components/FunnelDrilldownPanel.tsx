import { format } from "date-fns"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAdminStageContacts } from "@/hooks/useInsights"

const STAGE_LABELS: Record<string, string> = {
  contact: "Contact",
  meet: "Meet",
  close: "Close",
  decision: "Decision",
  thank: "Thank",
  next_steps: "Next Steps",
  none: "No Activity",
}

interface FunnelDrilldownPanelProps {
  open: boolean
  stage: string | null
  onClose: () => void
}

export function FunnelDrilldownPanel({ open, stage, onClose }: FunnelDrilldownPanelProps) {
  const { data, isLoading } = useAdminStageContacts(stage)

  const stageLabel = stage ? STAGE_LABELS[stage] || stage : "Stage"

  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Contacts in {stageLabel}</SheetTitle>
          <SheetDescription>
            {data?.total_count || 0} contacts currently in this pipeline stage
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-muted rounded animate-pulse" />
              ))}
            </div>
          ) : !data?.contacts || data.contacts.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No contacts in this stage
            </p>
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Owner</TableHead>
                    <TableHead>Last Activity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.contacts.map((contact) => (
                    <TableRow key={contact.id}>
                      <TableCell className="font-medium">{contact.full_name}</TableCell>
                      <TableCell>{contact.owner_name}</TableCell>
                      <TableCell>
                        {contact.last_activity_date
                          ? format(new Date(contact.last_activity_date), "MMM d, yyyy")
                          : "No activity"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
