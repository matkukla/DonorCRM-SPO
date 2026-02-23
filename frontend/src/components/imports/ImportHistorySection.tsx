import { format } from "date-fns"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { History } from "lucide-react"
import { useImportBatches } from "@/hooks/useImports"

function statusBadge(status: string) {
  switch (status) {
    case "completed":
      return <Badge variant="success">Completed</Badge>
    case "failed":
      return <Badge variant="destructive">Failed</Badge>
    case "duplicate":
      return <Badge variant="info">Duplicate</Badge>
    case "pending":
    case "processing":
      return <Badge variant="warning">Pending</Badge>
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

export function ImportHistorySection() {
  const { data: batches, isLoading } = useImportBatches()

  const recentBatches = batches?.slice(0, 20) ?? []

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <History className="h-5 w-5 text-muted-foreground" />
          Import History
        </h2>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted animate-pulse rounded" />
          ))}
        </div>
      ) : recentBatches.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-border rounded-lg">
          <p className="text-muted-foreground">No import history yet</p>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>File</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Created</TableHead>
                <TableHead className="text-right">Updated</TableHead>
                <TableHead className="text-right">Errors</TableHead>
                <TableHead>Uploaded By</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentBatches.map((batch) => (
                <TableRow key={batch.id}>
                  <TableCell className="whitespace-nowrap">
                    {format(new Date(batch.created_at), "MMM d, yyyy h:mm a")}
                  </TableCell>
                  <TableCell>{batch.import_type_display}</TableCell>
                  <TableCell className="max-w-[200px] truncate" title={batch.filename}>
                    {batch.filename}
                  </TableCell>
                  <TableCell>{statusBadge(batch.status)}</TableCell>
                  <TableCell className="text-right">{batch.created_count}</TableCell>
                  <TableCell className="text-right">{batch.updated_count}</TableCell>
                  <TableCell className="text-right">
                    {batch.error_count > 0 ? (
                      <span className="text-destructive">{batch.error_count}</span>
                    ) : (
                      batch.error_count
                    )}
                  </TableCell>
                  <TableCell>{batch.uploaded_by}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
