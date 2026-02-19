import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useUsers } from "@/hooks/useUsers"
import { useContacts, useMarkContactThanked } from "@/hooks/useContacts"
import { useFilterParams, contactFilterParsers } from "@/hooks/useFilterParams"
import { contactPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { DataTable } from "@/components/shared/DataTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatLocalDate } from "@/lib/utils"
import { Plus, Search, Filter, MoreHorizontal, Heart, Mail, Phone, BookOpen, Copy } from "lucide-react"
import { toast } from "sonner"
import { LogEventDialog } from "@/pages/journals/components/LogEventDialog"
import { getContactEmails } from "@/api/contacts"
import type { ColumnDef } from "@tanstack/react-table"
import type { ContactListItem, ContactStatus } from "@/api/contacts"

const PAGE_SIZE = 20

const statusLabels: Record<ContactStatus, string> = {
  prospect: "Prospect",
  donor: "Donor",
  lapsed: "Lapsed",
  major_donor: "Major Donor",
  deceased: "Deceased",
}

const statusVariants: Record<ContactStatus, "default" | "secondary" | "success" | "warning" | "info"> = {
  prospect: "secondary",
  donor: "success",
  lapsed: "warning",
  major_donor: "info",
  deceased: "secondary",
}

function formatCurrency(amount: string | number): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export default function ContactList() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === "admin"

  const {
    filters,
    setFilters,
    clearAll,
    activeFilters,
    toQueryParams,
  } = useFilterParams(contactFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: String(PAGE_SIZE) }
  const { data, isLoading } = useContacts(queryParams)

  const markThankedMutation = useMarkContactThanked()
  const { data: usersData } = useUsers()
  const [logEventContactId, setLogEventContactId] = useState<string | null>(null)
  const [isCopyingEmails, setIsCopyingEmails] = useState(false)

  const handleCopyEmails = async () => {
    setIsCopyingEmails(true)
    try {
      const result = await getContactEmails()
      if (result.emails.length === 0) {
        toast.info("No emails to copy")
        return
      }
      await navigator.clipboard.writeText(result.emails.join(", "))
      toast.success(`Copied ${result.count} emails`)
    } catch {
      toast.error("Failed to copy emails")
    } finally {
      setIsCopyingEmails(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  const handlePageChange = (newPage: number) => {
    setFilters({ page: newPage + 1 })
  }

  const handleRowClick = (contact: ContactListItem) => {
    navigate(`/contacts/${contact.id}`)
  }

  const columns: ColumnDef<ContactListItem>[] = [
    {
      accessorKey: "full_name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.full_name}</div>
          {row.original.email && (
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Mail className="h-3 w-3" />
              {row.original.email}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: "phone",
      header: "Phone",
      cell: ({ row }) =>
        row.original.phone ? (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Phone className="h-3 w-3" />
            {row.original.phone}
          </div>
        ) : (
          <span className="text-muted-foreground">{"\u2014"}</span>
        ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={statusVariants[row.original.status]}>
          {statusLabels[row.original.status]}
        </Badge>
      ),
    },
    {
      accessorKey: "total_given",
      header: "Total Given",
      cell: ({ row }) => (
        <span className="font-medium">
          {formatCurrency(row.original.total_given)}
        </span>
      ),
    },
    {
      accessorKey: "last_gift_date",
      header: "Last Gift",
      cell: ({ row }) => formatLocalDate(row.original.last_gift_date),
    },
    {
      accessorKey: "needs_thank_you",
      header: "",
      cell: ({ row }) =>
        row.original.needs_thank_you && (
          <Badge variant="warning" className="gap-1">
            <Heart className="h-3 w-3" />
            Thank
          </Badge>
        ),
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                navigate(`/contacts/${row.original.id}`)
              }}
            >
              View details
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                setLogEventContactId(row.original.id)
              }}
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Log Entry
            </DropdownMenuItem>
            {row.original.needs_thank_you && (
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  markThankedMutation.mutate(row.original.id)
                }}
              >
                Mark as thanked
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  const pageCount = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Contacts</h1>
              <p className="text-muted-foreground mt-1">
                Manage your donors and supporters
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleCopyEmails} disabled={isCopyingEmails}>
                <Copy className="h-4 w-4 mr-2" />
                {isCopyingEmails ? "Copying..." : "Copy Emails"}
              </Button>
              <Button onClick={() => navigate("/contacts/new")}>
                <Plus className="h-4 w-4 mr-2" />
                Add Contact
              </Button>
            </div>
          </div>

          {/* Filters */}
          <FilterBar
            activeFilters={activeFilters}
            onClearAll={clearAll}
            onRemoveFilter={(key) => setFilters({ [key]: null, page: 1 })}
            filterLabels={{
              search: "Search",
              status: "Status",
              needs_thank_you: "Needs Thank You",
              last_gift_after: "Gift From",
              last_gift_before: "Gift To",
              group: "Group",
              ordering: "Sort",
              owner: "Owner",
            }}
            filterValueLabels={{
              status: {
                prospect: "Prospect",
                donor: "Donor",
                lapsed: "Lapsed",
                major_donor: "Major Donor",
                deceased: "Deceased",
              },
            }}
            presets={contactPresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/contacts/export/csv/"
            exportParams={toQueryParams()}
          >
            {/* Search input */}
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-[200px]">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or email..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            {/* Status dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="sm" className="gap-2">
                  <Filter className="h-4 w-4" />
                  {filters.status ? statusLabels[filters.status as ContactStatus] || filters.status : "All Status"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setFilters({ status: null, page: 1 })}>
                  All Status
                </DropdownMenuItem>
                {(Object.keys(statusLabels) as ContactStatus[]).map((s) => (
                  <DropdownMenuItem key={s} onClick={() => setFilters({ status: s, page: 1 })}>
                    {statusLabels[s]}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Thank You toggle button */}
            <Button
              variant={filters.needs_thank_you ? "default" : "secondary"}
              size="sm"
              onClick={() => setFilters({
                needs_thank_you: filters.needs_thank_you ? null : true,
                page: 1,
              })}
              className="gap-2"
            >
              <Heart className="h-4 w-4" />
              Needs Thank You
            </Button>

            {/* Admin owner dropdown */}
            {isAdmin && usersData && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    <Filter className="h-4 w-4" />
                    {filters.owner
                      ? usersData.find((u) => String(u.id) === filters.owner)?.full_name || "Owner"
                      : "All Owners"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setFilters({ owner: null, page: 1 })}>
                    All Owners
                  </DropdownMenuItem>
                  {usersData.map((u) => (
                    <DropdownMenuItem key={u.id} onClick={() => setFilters({ owner: String(u.id), page: 1 })}>
                      {u.full_name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </FilterBar>

          {/* Data Table */}
          <DataTable
            columns={columns}
            data={data?.results || []}
            isLoading={isLoading}
            pageCount={pageCount}
            pageIndex={filters.page - 1}
            pageSize={PAGE_SIZE}
            totalCount={data?.count}
            onPageChange={handlePageChange}
            onRowClick={handleRowClick}
          />
        </div>

        <LogEventDialog
          open={!!logEventContactId}
          onOpenChange={(open) => !open && setLogEventContactId(null)}
          contactId={logEventContactId || undefined}
        />
      </Container>
    </Section>
  )
}
