import { useState } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"
import { usePrayers, useUpdatePrayer } from "@/hooks/usePrayers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { FilterCombobox } from "@/components/shared/FilterCombobox"
import { Plus, Search, ChevronLeft, ChevronRight, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"
import { TodaysFocus } from "./components/TodaysFocus"
import { StatusBadge } from "./components/StatusBadge"
import { PrayerIntentionPanel } from "./PrayerIntentionPanel"
import { PrayerFocusMode } from "./PrayerFocusMode"
import { BeginPrayerDialog } from "./components/BeginPrayerDialog"
import type { PrayerIntention, PrayerIntentionStatus } from "@/api/prayers"

const PAGE_SIZE = 20

export default function PrayerList() {
  const { user } = useAuth()
  const { isViewingAs } = useViewAs()
  const canSeeOwner = user?.role === "admin" || user?.role === "supervisor" || user?.role === "coach"
  const ownerOptions = user?.role === "admin"
    ? [] // admin sees all; no dropdown without usersData
    : (user?.role === "supervisor" || user?.role === "coach")
      ? [
          { id: String(user.id), full_name: `${user.first_name} ${user.last_name}` },
          ...(user.supervised_users?.map((u) => ({
            id: String(u.id),
            full_name: `${u.first_name} ${u.last_name}`,
          })) || []),
        ]
      : []

  // Panel state
  const [panelOpen, setPanelOpen] = useState(false)
  const [selectedIntention, setSelectedIntention] = useState<PrayerIntention | undefined>()
  const [focusModeOpen, setFocusModeOpen] = useState(false)
  const [beginPrayerDialogOpen, setBeginPrayerDialogOpen] = useState(false)
  const [selectedIntentions, setSelectedIntentions] = useState<PrayerIntention[]>([])

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [page, setPage] = useState(1)
  const [ownerFilter, setOwnerFilter] = useState<string | null>(null)
  const [ordering, setOrdering] = useState<string | null>(null)

  // Answered note dialog state
  const [noteDialogOpen, setNoteDialogOpen] = useState(false)
  const [noteDialogIntention, setNoteDialogIntention] = useState<PrayerIntention | null>(null)
  const [answeredNote, setAnsweredNote] = useState("")

  // Build query params
  const params: Record<string, string> = { page: String(page), page_size: String(PAGE_SIZE) }
  if (statusFilter !== "all") params.status = statusFilter
  if (searchQuery) params.search = searchQuery
  if (ownerFilter) params.owner = ownerFilter
  if (ordering) params.ordering = ordering

  const { data, isLoading } = usePrayers(params)
  const { data: activeIntentionsData } = usePrayers({ status: "active", page_size: "1" })
  const updateMutation = useUpdatePrayer()

  const openCreate = () => {
    setSelectedIntention(undefined)
    setPanelOpen(true)
  }

  const openEdit = (intention: PrayerIntention) => {
    setSelectedIntention(intention)
    setPanelOpen(true)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInput)
    setPage(1)
  }

  const handleOrderingChange = (sortKey: string) => {
    setOrdering((prev) => {
      if (!prev || (prev !== sortKey && prev !== `-${sortKey}`)) return sortKey
      if (prev === sortKey) return `-${sortKey}`
      return null // was desc, clear
    })
    setPage(1)
  }

  const getSortIcon = (sortKey: string) => {
    if (ordering === sortKey) return <ArrowUp className="h-3.5 w-3.5 inline ml-1" />
    if (ordering === `-${sortKey}`) return <ArrowDown className="h-3.5 w-3.5 inline ml-1" />
    return <ArrowUpDown className="h-3 w-3 inline ml-1 opacity-50" />
  }

  const handleStatusFilterChange = (value: string) => {
    setStatusFilter(value)
    setPage(1)
  }

  const handleInlineStatusChange = (intention: PrayerIntention, newStatus: string) => {
    if (newStatus === "answered" && intention.status !== "answered") {
      // Show the note dialog before changing to answered
      setNoteDialogIntention(intention)
      setAnsweredNote("")
      setNoteDialogOpen(true)
      return
    }

    updateMutation.mutate({
      id: intention.id,
      data: { status: newStatus as PrayerIntentionStatus },
    })
  }

  const handleAnsweredConfirm = () => {
    if (!noteDialogIntention) return
    const data: { status: PrayerIntentionStatus; description?: string } = {
      status: "answered",
    }
    if (answeredNote.trim()) {
      data.description = answeredNote.trim()
    }
    updateMutation.mutate(
      { id: noteDialogIntention.id, data },
      {
        onSuccess: () => {
          setNoteDialogOpen(false)
          setNoteDialogIntention(null)
          setAnsweredNote("")
        },
      },
    )
  }

  const handleAnsweredSkip = () => {
    if (!noteDialogIntention) return
    updateMutation.mutate(
      { id: noteDialogIntention.id, data: { status: "answered" } },
      {
        onSuccess: () => {
          setNoteDialogOpen(false)
          setNoteDialogIntention(null)
          setAnsweredNote("")
        },
      },
    )
  }

  const handleBeginPrayer = () => {
    if (!activeIntentionsData || activeIntentionsData.count === 0) {
      setSelectedIntentions([])
      setFocusModeOpen(true)
      return
    }
    setBeginPrayerDialogOpen(true)
  }

  const handleStartPrayer = (intentions: PrayerIntention[]) => {
    setSelectedIntentions(intentions)
    setBeginPrayerDialogOpen(false)
    setFocusModeOpen(true)
  }

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 1

  return (
    <div className="bg-amber-50/30 dark:bg-amber-950/10 min-h-screen">
      <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="font-serif text-2xl text-amber-900 dark:text-amber-100">
            Prayer Intentions
          </h1>
          <p className="text-amber-700 dark:text-amber-300 leading-relaxed mt-1">
            A quiet place to hold your prayer intentions and lift them up daily.
          </p>
        </div>

        {/* Today's Focus */}
        <TodaysFocus onBeginPrayer={handleBeginPrayer} />

        {/* Controls bar */}
        <div className="flex flex-wrap items-center gap-3">
          {!isViewingAs && (
            <Button onClick={openCreate} className="gap-1.5">
              <Plus className="h-4 w-4" />
              Add Prayer
            </Button>
          )}

          <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="answered">Answered</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>

          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search prayers..."
                className="pl-9 w-56"
              />
            </div>
            <Button type="submit" variant="secondary">
              Search
            </Button>
          </form>

          {/* Owner filter (supervisor) */}
          {canSeeOwner && ownerOptions.length > 0 && (
            <FilterCombobox
              value={ownerFilter}
              onSelect={(value) => { setOwnerFilter(value); setPage(1) }}
              options={ownerOptions.map((u) => ({ value: u.id, label: u.full_name }))}
              allLabel="All Owners"
              searchPlaceholder="Search owners..."
            />
          )}
        </div>

        {/* Table */}
        <div className="bg-white dark:bg-card border border-amber-100 dark:border-amber-800 rounded-xl shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-amber-700/60 dark:text-amber-400/40">
              Loading prayer intentions...
            </div>
          ) : !data || data.results.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-amber-700/70 dark:text-amber-400/50 leading-relaxed">
                No prayer intentions yet. Add your first prayer intention to get
                started.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" aria-label="Prayer intentions">
                <thead>
                  <tr className="border-b border-amber-100 dark:border-amber-800">
                    <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                      Title
                    </th>
                    <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                      Contact
                    </th>
                    <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                      <button
                        className="flex items-center gap-0.5 hover:text-amber-950 dark:hover:text-amber-100 transition-colors cursor-pointer select-none"
                        onClick={() => handleOrderingChange("status")}
                      >
                        Status
                        {getSortIcon("status")}
                      </button>
                    </th>
                    {canSeeOwner && (
                      <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                        Owner
                      </th>
                    )}
                    <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                      <button
                        className="flex items-center gap-0.5 hover:text-amber-950 dark:hover:text-amber-100 transition-colors cursor-pointer select-none"
                        onClick={() => handleOrderingChange("created_at")}
                      >
                        Created
                        {getSortIcon("created_at")}
                      </button>
                    </th>
                    <th scope="col" className="text-left px-4 py-3 text-sm font-medium text-amber-800 dark:text-amber-300">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((intention) => (
                    <tr
                      key={intention.id}
                      className={`border-b border-amber-50 dark:border-amber-900/30 hover:bg-amber-50/50 dark:hover:bg-amber-950/30 transition-colors ${isViewingAs ? "" : "cursor-pointer"}`}
                      onClick={() => !isViewingAs && openEdit(intention)}
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium text-amber-900 dark:text-amber-100">
                          {intention.title}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-amber-700 dark:text-amber-300">
                        {intention.contact_name}
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        {isViewingAs ? (
                          <StatusBadge status={intention.status} />
                        ) : (
                          <Select
                            value={intention.status}
                            onValueChange={(v) =>
                              handleInlineStatusChange(intention, v)
                            }
                          >
                            <SelectTrigger className="w-[120px] h-8 text-xs border-amber-200 dark:border-amber-800">
                              <StatusBadge status={intention.status} />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="active">Active</SelectItem>
                              <SelectItem value="answered">Answered</SelectItem>
                              <SelectItem value="archived">Archived</SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </td>
                      {canSeeOwner && (
                        <td className="px-4 py-3 text-sm text-amber-700/80 dark:text-amber-400/60">
                          {intention.owner_name}
                        </td>
                      )}
                      <td className="px-4 py-3 text-sm text-amber-700/80 dark:text-amber-400/60">
                        {formatLocalDate(intention.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-amber-700/60 dark:text-amber-400/40 max-w-[200px]">
                        <span className="line-clamp-1">
                          {intention.description || "\u2014"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {data && totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-amber-700/70 dark:text-amber-400/50">
              {data.count} intention{data.count !== 1 ? "s" : ""} total
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-amber-700 dark:text-amber-300">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Focus Mode overlay */}
      <PrayerFocusMode
        open={focusModeOpen}
        onClose={() => setFocusModeOpen(false)}
        intentions={selectedIntentions}
      />

      {/* Begin Prayer selection dialog */}
      <BeginPrayerDialog
        open={beginPrayerDialogOpen}
        onClose={() => setBeginPrayerDialogOpen(false)}
        onStartPrayer={handleStartPrayer}
      />

      {/* Slide-in panel */}
      <PrayerIntentionPanel
        open={panelOpen}
        onClose={() => {
          setPanelOpen(false)
          setSelectedIntention(undefined)
        }}
        intention={selectedIntention}
      />

      {/* Answered note dialog */}
      <Dialog open={noteDialogOpen} onOpenChange={setNoteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-amber-900 dark:text-amber-100">
              Prayer Answered
            </DialogTitle>
            <DialogDescription>
              Would you like to add a note about how this prayer was answered?
              This is optional.
            </DialogDescription>
          </DialogHeader>
          <div>
            <textarea
              value={answeredNote}
              onChange={(e) => setAnsweredNote(e.target.value)}
              placeholder="How was this prayer answered..."
              className="flex w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 min-h-[100px] resize-y"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={handleAnsweredSkip}
              disabled={updateMutation.isPending}
            >
              Skip
            </Button>
            <Button
              type="button"
              onClick={handleAnsweredConfirm}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? "Saving..." : "Save Note"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
