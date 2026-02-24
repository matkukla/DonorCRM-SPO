import { useState, useMemo } from "react"
import { format } from "date-fns"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
} from "@tanstack/react-table"
import { ArrowUpDown, Eye, Download } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAdminTeamActivity, useExportTeamActivity } from "@/hooks/useInsights"
import type { TeamActivityItem } from "@/api/insights"

const columnHelper = createColumnHelper<TeamActivityItem>()

const eventTypeBadgeVariant = (eventType: string) => {
  const mapping: Record<string, "success" | "warning" | "info" | "secondary"> = {
    success: "success",
    warning: "warning",
    info: "info",
  }
  return mapping[eventType] || "secondary"
}

interface TeamActivityTableProps {
  dateParams?: { date_from?: string; date_to?: string }
  onUserDrilldown?: (userId: string) => void
}

export function TeamActivityTable({ dateParams, onUserDrilldown }: TeamActivityTableProps) {
  const { data, isLoading } = useAdminTeamActivity({ ...dateParams, limit: 50 })
  const exportMutation = useExportTeamActivity()
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }])

  const columns = useMemo(() => {
    const baseColumns = [
      columnHelper.accessor("created_at", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Date
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => format(new Date(info.getValue()), "MMM d, yyyy h:mm a"),
      }),
      columnHelper.accessor("user_name", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            User
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor("event_type", {
        header: "Event",
        cell: (info) => (
          <Badge variant={eventTypeBadgeVariant(info.getValue())}>
            {info.getValue()}
          </Badge>
        ),
      }),
      columnHelper.accessor("title", {
        header: "Description",
        cell: (info) => info.getValue(),
      }),
    ]

    // Conditionally add Actions column if onUserDrilldown is provided
    if (onUserDrilldown) {
      baseColumns.push(
        columnHelper.display({
          id: "actions",
          header: "Actions",
          cell: ({ row }) => (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onUserDrilldown(row.original.user_id)}
            >
              <Eye className="h-4 w-4 mr-1" />
              Quick View
            </Button>
          ),
        }) as any
      )
    }

    return baseColumns
  }, [onUserDrilldown])

  const table = useReactTable({
    data: data?.activities || [],
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Recent Team Activity</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportMutation.mutate(dateParams)}
            disabled={exportMutation.isPending}
          >
            <Download className="h-4 w-4 mr-2" />
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : !data?.activities || data.activities.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            No recent activity
          </p>
        ) : (
          <div className="rounded-lg border">
            <Table aria-label="Team activity">
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
