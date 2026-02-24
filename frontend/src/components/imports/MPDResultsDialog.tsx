import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { CheckCircle, AlertTriangle, FileSpreadsheet } from "lucide-react"
import type { MPDUploadResult } from "@/api/mpd"
import { formatMPDCurrency } from "@/api/mpd"

interface MPDResultsDialogProps {
  open: boolean
  onClose: () => void
  result: MPDUploadResult
}

export function MPDResultsDialog({ open, onClose, result }: MPDResultsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            MPD Import Results
          </DialogTitle>
          <DialogDescription>
            Summary of the Smartsheet MPD report upload
          </DialogDescription>
        </DialogHeader>

        {/* Summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-semibold">{result.total_rows}</p>
            <p className="text-xs text-muted-foreground">Total Rows</p>
          </div>
          <div className="rounded-lg border p-3 text-center bg-green-50 dark:bg-green-950/50">
            <p className="text-2xl font-semibold text-green-600 dark:text-green-400">
              {result.matched_count}
            </p>
            <p className="text-xs text-muted-foreground">Matched</p>
          </div>
          <div
            className={`rounded-lg border p-3 text-center ${
              result.unmatched_count > 0
                ? "bg-amber-50 dark:bg-amber-950/50"
                : ""
            }`}
          >
            <p
              className={`text-2xl font-semibold ${
                result.unmatched_count > 0
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-muted-foreground"
              }`}
            >
              {result.unmatched_count}
            </p>
            <p className="text-xs text-muted-foreground">Unmatched</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-semibold text-blue-600 dark:text-blue-400">
              {result.snapshot_count}
            </p>
            <p className="text-xs text-muted-foreground">Snapshots Created</p>
          </div>
        </div>

        {/* Success / warning indicator */}
        {result.unmatched_count === 0 ? (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-800">
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0" />
            <p className="text-sm text-green-800 dark:text-green-200">
              All rows matched successfully to existing missionaries.
            </p>
          </div>
        ) : (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800">
            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-amber-800 dark:text-amber-200">
              {result.unmatched_count} row{result.unmatched_count !== 1 ? "s" : ""} could not be
              matched to existing users. Review the details below.
            </p>
          </div>
        )}

        {/* Unmatched rows table */}
        {result.unmatched_rows.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Unmatched Rows</h3>
            <div className="rounded-md border">
              <Table aria-label="Unmatched import rows">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">Row</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">MPD Cap</TableHead>
                    <TableHead className="text-right">Roll Forward Balance</TableHead>
                    <TableHead className="text-right">Months Remaining</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.unmatched_rows.map((row) => (
                    <TableRow key={row.row}>
                      <TableCell className="text-muted-foreground">{row.row}</TableCell>
                      <TableCell className="font-medium">
                        {row.first_name} {row.last_name}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMPDCurrency(row.current_mpd_cap)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMPDCurrency(row.latest_roll_forward_balance)}
                      </TableCell>
                      <TableCell className="text-right">
                        {row.months_remaining_rf || "--"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* Error message if upload failed */}
        {result.error && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-800 dark:text-red-200">{result.error}</p>
          </div>
        )}

        <DialogFooter>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
