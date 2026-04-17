import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react"

// Augment tanstack column meta to include our server sort key
declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    serverSortKey?: string
  }
}

const SELECT_COLUMN_ID = "__select__"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  isLoading?: boolean
  // Pagination
  pageCount?: number
  pageIndex?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  totalCount?: number
  // Row click
  onRowClick?: (row: TData) => void
  // Server-side sorting
  ordering?: string | null
  onOrderingChange?: (ordering: string | null) => void
  // Row selection
  enableSelection?: boolean
  selectedRows?: Set<string>
  onSelectionChange?: (selected: Set<string>) => void
  getRowId?: (row: TData) => string
  // Accessibility
  "aria-label"?: string
}

/**
 * Parse a DRF ordering string like "-gift_date" into { field, direction }.
 */
function parseOrdering(ordering: string | null | undefined): { field: string; direction: "asc" | "desc" } | null {
  if (!ordering) return null
  if (ordering.startsWith("-")) {
    return { field: ordering.slice(1), direction: "desc" }
  }
  return { field: ordering, direction: "asc" }
}

export function DataTable<TData, TValue>({
  columns,
  data,
  isLoading,
  pageCount = 1,
  pageIndex = 0,
  pageSize = 20,
  onPageChange,
  totalCount,
  onRowClick,
  ordering,
  onOrderingChange,
  enableSelection,
  selectedRows,
  onSelectionChange,
  getRowId,
  "aria-label": ariaLabel,
}: DataTableProps<TData, TValue>) {
  const currentSort = parseOrdering(ordering)

  const handleSort = (serverSortKey: string) => {
    if (!onOrderingChange) return
    if (currentSort?.field === serverSortKey) {
      if (currentSort.direction === "asc") {
        onOrderingChange(`-${serverSortKey}`)
      } else {
        onOrderingChange(null)
      }
    } else {
      onOrderingChange(serverSortKey)
    }
  }

  const allRowIds = enableSelection && getRowId ? data.map(getRowId) : []
  const allSelected = allRowIds.length > 0 && allRowIds.every((id) => selectedRows?.has(id))
  const someSelected = !allSelected && allRowIds.some((id) => selectedRows?.has(id))

  const toggleAll = () => {
    if (!onSelectionChange) return
    if (allSelected) {
      const next = new Set(selectedRows)
      allRowIds.forEach((id) => next.delete(id))
      onSelectionChange(next)
    } else {
      const next = new Set(selectedRows)
      allRowIds.forEach((id) => next.add(id))
      onSelectionChange(next)
    }
  }

  const toggleRow = (id: string) => {
    if (!onSelectionChange || !selectedRows) return
    const next = new Set(selectedRows)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    onSelectionChange(next)
  }

  const selectionColumn: ColumnDef<TData, unknown> = {
    id: SELECT_COLUMN_ID,
    header: () => (
      <input
        type="checkbox"
        checked={allSelected}
        ref={(el) => { if (el) el.indeterminate = someSelected }}
        onChange={toggleAll}
        className="rounded border-border"
        aria-label="Select all rows"
      />
    ),
    cell: ({ row }) => {
      const rowId = getRowId ? getRowId(row.original) : ""
      return (
        <input
          type="checkbox"
          checked={selectedRows?.has(rowId) ?? false}
          onChange={() => toggleRow(rowId)}
          className="rounded border-border"
          aria-label={`Select row ${rowId}`}
        />
      )
    },
  }

  const effectiveColumns: ColumnDef<TData, unknown>[] = enableSelection
    ? [selectionColumn, ...(columns as ColumnDef<TData, unknown>[])]
    : (columns as ColumnDef<TData, unknown>[])

  const table = useReactTable({
    data,
    columns: effectiveColumns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount,
  })

  const startItem = pageIndex * pageSize + 1
  const endItem = Math.min((pageIndex + 1) * pageSize, totalCount || 0)

  return (
    <div className="space-y-4">
      <div className="rounded-lg border">
        <Table aria-label={ariaLabel}>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const serverSortKey = header.column.columnDef.meta?.serverSortKey
                  const isSortable = !!serverSortKey && !!onOrderingChange
                  const isActive = serverSortKey ? currentSort?.field === serverSortKey : false
                  const direction = isActive ? currentSort?.direction : undefined

                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder ? null : isSortable ? (
                        <button
                          className="flex items-center gap-1 hover:text-foreground transition-colors cursor-pointer select-none"
                          onClick={() => handleSort(serverSortKey!)}
                          aria-label={`Sort by ${typeof header.column.columnDef.header === "string" ? header.column.columnDef.header : serverSortKey}${direction === "asc" ? ", currently ascending" : direction === "desc" ? ", currently descending" : ""}`}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          {direction === "asc" ? (
                            <ArrowUp className="h-4 w-4 text-foreground" />
                          ) : direction === "desc" ? (
                            <ArrowDown className="h-4 w-4 text-foreground" />
                          ) : (
                            <ArrowUpDown className="h-3.5 w-3.5 opacity-50" />
                          )}
                        </button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <TableRow key={i}>
                  {effectiveColumns.map((_, j) => (
                    <TableCell key={j}>
                      <div className="h-4 w-full bg-muted rounded animate-pulse" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  onClick={() => onRowClick?.(row.original)}
                  className={onRowClick ? "cursor-pointer" : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      onClick={cell.column.id === SELECT_COLUMN_ID ? (e) => e.stopPropagation() : undefined}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={effectiveColumns.length}
                  className="h-24 text-center text-muted-foreground"
                >
                  No results found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {onPageChange && totalCount !== undefined && totalCount > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {startItem} to {endItem} of {totalCount} results
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onPageChange(pageIndex - 1)}
              disabled={pageIndex === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onPageChange(pageIndex + 1)}
              disabled={pageIndex >= pageCount - 1}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
