import { useState, useMemo } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
} from "@tanstack/react-table"
import { ArrowUpDown } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useMPDOverview } from "@/hooks/useMPD"
import { formatMPDCurrency, formatMonthsRemaining } from "@/api/mpd"
import type { MPDMissionaryOverview } from "@/api/mpd"

const columnHelper = createColumnHelper<MPDMissionaryOverview>()

export function MPDOverviewTable() {
  const { data, isLoading, error } = useMPDOverview()
  const [sorting, setSorting] = useState<SortingState>([])

  const columns = useMemo(
    () => [
      columnHelper.accessor("user_name", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Missionary
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor("monthly_average_snapshot", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Monthly Average (Snapshot)
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => formatMPDCurrency(info.getValue() ?? null),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<string | null>(columnId)
          const b = rowB.getValue<string | null>(columnId)
          if (a === null && b === null) return 0
          if (a === null) return 1
          if (b === null) return -1
          const numA = parseFloat(a)
          const numB = parseFloat(b)
          if (isNaN(numA) && isNaN(numB)) return 0
          if (isNaN(numA)) return 1
          if (isNaN(numB)) return -1
          return numA - numB
        },
      }),
      columnHelper.accessor("current_mpd_cap", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            MPD Cap
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => formatMPDCurrency(info.getValue()),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<string | null>(columnId)
          const b = rowB.getValue<string | null>(columnId)
          // Null sorts last
          if (a === null && b === null) return 0
          if (a === null) return 1
          if (b === null) return -1
          const numA = parseFloat(a)
          const numB = parseFloat(b)
          if (isNaN(numA) && isNaN(numB)) return 0
          if (isNaN(numA)) return 1
          if (isNaN(numB)) return -1
          return numA - numB
        },
      }),
      columnHelper.accessor("latest_roll_forward_balance", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Roll Forward Balance
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => formatMPDCurrency(info.getValue()),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<string | null>(columnId)
          const b = rowB.getValue<string | null>(columnId)
          // Null sorts last
          if (a === null && b === null) return 0
          if (a === null) return 1
          if (b === null) return -1
          const numA = parseFloat(a)
          const numB = parseFloat(b)
          if (isNaN(numA) && isNaN(numB)) return 0
          if (isNaN(numA)) return 1
          if (isNaN(numB)) return -1
          return numA - numB
        },
      }),
      columnHelper.accessor("months_remaining_rf", {
        header: ({ column }) => (
          <button
            className="flex items-center gap-2 hover:text-foreground cursor-pointer"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Months Remaining
            <ArrowUpDown className="h-4 w-4" />
          </button>
        ),
        cell: (info) => formatMonthsRemaining(info.getValue()),
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue<string>(columnId)
          const b = rowB.getValue<string>(columnId)
          // Empty strings sort last
          if (!a && !b) return 0
          if (!a) return 1
          if (!b) return -1
          // "infinite" sorts as Infinity
          const numA = a === "infinite" ? Infinity : parseFloat(a)
          const numB = b === "infinite" ? Infinity : parseFloat(b)
          if (isNaN(numA) && isNaN(numB)) return 0
          if (isNaN(numA)) return 1
          if (isNaN(numB)) return -1
          return numA - numB
        },
      }),
    ],
    []
  )

  const table = useReactTable({
    data: data?.missionaries || [],
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
      <CardHeader className="p-4 pl-7">
        <CardTitle>MPD Overview</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <p className="text-destructive text-sm py-8 text-center">
            Failed to load MPD data. Please try again.
          </p>
        ) : !data?.missionaries || data.missionaries.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            No MPD data available. Upload a Smartsheet report from the Import
            Center.
          </p>
        ) : (
          <div className="rounded-lg border">
            <Table aria-label="MPD overview">
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
