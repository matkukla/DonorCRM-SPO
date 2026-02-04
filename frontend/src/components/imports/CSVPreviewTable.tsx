import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface CSVPreviewTableProps {
  headers: string[]
  rows: Record<string, string>[]
  maxRows?: number
}

/**
 * Displays CSV preview with first N rows
 * Headers are from first row, data from parsed rows
 */
export function CSVPreviewTable({ headers, rows, maxRows = 25 }: CSVPreviewTableProps) {
  const displayRows = rows.slice(0, maxRows)

  if (headers.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No data to preview
      </p>
    )
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="max-h-[400px] overflow-auto">
        <Table>
          <TableHeader className="sticky top-0 bg-muted">
            <TableRow>
              <TableHead className="w-12 text-center">#</TableHead>
              {headers.map((header) => (
                <TableHead key={header} className="min-w-[100px]">
                  {header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayRows.map((row, rowIndex) => (
              <TableRow key={rowIndex}>
                <TableCell className="text-center text-muted-foreground">
                  {rowIndex + 1}
                </TableCell>
                {headers.map((header) => (
                  <TableCell key={header} className="max-w-[200px] truncate">
                    {row[header] || "-"}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {rows.length > maxRows && (
        <p className="text-sm text-muted-foreground text-center py-2 border-t bg-muted">
          Showing {maxRows} of {rows.length} rows
        </p>
      )}
    </div>
  )
}
