import { useEffect, useRef, useState } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { useViewAs } from "@/providers/ViewAsProvider"
import { markEventsSeen } from "@/api/dashboard"
import { useDashboardSummary } from "@/hooks/useDashboard"
import { useDashboardLayout } from "@/hooks/useDashboard"
import { useViewableUsers } from "@/hooks/useUsers"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { StatCard } from "@/components/dashboard/StatCard"
import { RecentDonations } from "@/components/dashboard/RecentDonations"
import { NeedsAttention } from "@/components/dashboard/NeedsAttention"
import { SupportProgress } from "@/components/dashboard/SupportProgress"
import { LateDonations } from "@/components/dashboard/LateDonations"
import { GivingSummaryCard } from "@/components/dashboard/GivingSummaryCard"
import { MonthlyGiftsCard } from "@/components/dashboard/MonthlyGiftsCard"
import { SortableDashboardTile } from "@/components/dashboard/SortableDashboardTile"
import { LogEventDialog } from "@/pages/journals/components/LogEventDialog"
import { useMPDMyData, useMPDOverview } from "@/hooks/useMPD"
import { MPDStatsInline } from "@/components/mpd/MPDStatsInline"
import { MPDOverviewTable } from "@/components/mpd/MPDOverviewTable"
import { Users, DollarSign, FileText, CheckSquare, RotateCcw, ChevronDown, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { cn } from "@/lib/utils"
import { DndContext, DragOverlay, closestCenter, MouseSensor, TouchSensor, useSensor, useSensors } from "@dnd-kit/core"
import type { DragStartEvent, DragEndEvent } from "@dnd-kit/core"
import { SortableContext, arrayMove, rectSortingStrategy } from "@dnd-kit/sortable"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

const TILE_SIZES: Record<string, number> = {
  "giving-summary": 2,
  "monthly-gifts": 2,
  "thank-you": 1,
  "recent-donations-stat": 1,
  "active-pledges": 1,
  "needs-attention-stat": 1,
  "needs-attention": 2,
  "support-progress": 2,
  "recent-donations": 2,
  "late-donations": 2,
  "mpd-financial-overview": 4,
  "mpd-overview-table": 4,
}

export default function Dashboard() {
  const { user } = useAuth()
  const isSupervisorOrAdmin = user?.role === "admin" || user?.role === "supervisor" || user?.role === "coach"
  const { viewAsUserId, viewAsUserName, setViewAsUser, exitViewAs, isViewingAs } = useViewAs()
  const effectiveUserId = viewAsUserId || undefined

  // Fetch viewable users for the dropdown (scoped by backend to role)
  const { data: viewableUsers } = useViewableUsers()
  const missionaryOptions = viewableUsers || []

  const { data, isLoading, error } = useDashboardSummary(effectiveUserId)
  const { data: mpdData, isLoading: mpdLoading } = useMPDMyData()
  const { data: mpdOverviewData, isLoading: mpdOverviewLoading } = useMPDOverview({ enabled: user?.role === "admin" })
  const [quickLogContactId, setQuickLogContactId] = useState<string | null>(null)

  const [viewingPickerOpen, setViewingPickerOpen] = useState(false)
  const { tileOrder, setTileOrder, resetToDefault, isDragEnabled } = useDashboardLayout(effectiveUserId)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [dragWidth, setDragWidth] = useState<number>(0)

  const sensors = useSensors(
    useSensor(MouseSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    })
  )

  // Mark events as seen once after dashboard data loads (QAL-09)
  // Skip when viewing another user's dashboard
  const markedSeen = useRef(false)

  useEffect(() => {
    if (data && !isLoading && !markedSeen.current && !isViewingAs) {
      markedSeen.current = true
      markEventsSeen().catch(() => {
        // Silently ignore -- marking seen is best-effort
      })
    }
  }, [data, isLoading, isViewingAs])

  // Use backend-aggregated total (includes ALL gifts, not just first 10)
  const totalDonationsThisMonth = data?.recent_gifts_total || 0

  // Name comes directly from context (stored when setViewAsUser was called)
  const selectedUserName = viewAsUserName

  // With X-View-As-User-Id header, mpdData is already scoped to the viewed missionary
  const effectiveMpdData = mpdData
  const effectiveMpdHasData = mpdData?.has_data

  function handleDragStart(event: DragStartEvent) {
    const id = event.active.id as string
    setActiveId(id)
    const el = document.querySelector(`[data-tile-id="${id}"]`)
    if (el) setDragWidth(el.getBoundingClientRect().width)
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)
    if (!over || active.id === over.id) return
    const oldIndex = tileOrder.indexOf(active.id as string)
    const newIndex = tileOrder.indexOf(over.id as string)
    if (oldIndex !== -1 && newIndex !== -1) {
      setTileOrder(arrayMove(tileOrder, oldIndex, newIndex))
    }
  }

  function renderTileById(tileId: string): React.ReactNode {
    switch (tileId) {
      // Giving section
      case "giving-summary": return <GivingSummaryCard userId={effectiveUserId} />
      case "monthly-gifts": return <MonthlyGiftsCard userId={effectiveUserId} />
      // Stat cards
      case "thank-you":
        return <StatCard title="Thank You Queue" value={data?.thank_you_count || 0} icon={Users} isLoading={isLoading} description="need acknowledgment" />
      case "recent-donations-stat":
        return <StatCard title="Recent Donations" value={formatCurrency(totalDonationsThisMonth)} icon={DollarSign} isLoading={isLoading} description="last 30 days" />
      case "active-pledges":
        return <StatCard title="Active Pledges" value={data?.support_progress?.active_pledge_count || 0} icon={FileText} isLoading={isLoading} />
      case "needs-attention-stat":
        return <StatCard title="Items Needing Attention" value={(data?.needs_attention?.overdue_task_count || 0) + (data?.needs_attention?.tasks_due_today_count || 0) + (data?.needs_attention?.thank_you_needed_count || 0)} icon={CheckSquare} isLoading={isLoading} />
      // Content section
      case "needs-attention":
        return <NeedsAttention overdueTasks={data?.needs_attention?.overdue_tasks || []} overdueTaskCount={data?.needs_attention?.overdue_task_count || 0} latePledges={data?.needs_attention?.late_pledges || []} latePledgeCount={data?.needs_attention?.late_pledge_count || 0} thankYouNeeded={data?.needs_attention?.thank_you_needed || []} thankYouCount={data?.needs_attention?.thank_you_needed_count || 0} isLoading={isLoading} />
      case "support-progress":
        return <SupportProgress data={data?.support_progress || null} isLoading={isLoading} />
      case "recent-donations":
        return <RecentDonations donations={data?.recent_gifts || []} isLoading={isLoading} />
      case "late-donations":
        return <LateDonations donations={data?.late_donations || []} totalCount={data?.late_donations_count || 0} isLoading={isLoading} onQuickLog={(contactId) => setQuickLogContactId(contactId)} />
      case "mpd-financial-overview": {
        if (mpdLoading) return (
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-muted rounded-lg animate-pulse" />
            ))}
          </div>
        )
        if (!effectiveMpdHasData || !effectiveMpdData) return null
        return (
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <MPDStatsInline
              monthlyAverage={(effectiveMpdData as { monthly_average?: string | null }).monthly_average}
              currentMpdCap={(effectiveMpdData as { current_mpd_cap?: string | null }).current_mpd_cap}
              latestRollForwardBalance={(effectiveMpdData as { latest_roll_forward_balance?: string | null }).latest_roll_forward_balance}
              monthsRemainingRf={(effectiveMpdData as { months_remaining_rf?: string }).months_remaining_rf}
            />
          </div>
        )
      }
      case "mpd-overview-table":
        if (user?.role !== "admin" || isViewingAs) return null
        return <MPDOverviewTable />
      default: return null
    }
  }

  function getTileClasses(id: string) {
    const size = TILE_SIZES[id]
    if (size === 4) return "col-span-2 lg:col-span-4"
    if (size === 2) return "col-span-2 min-h-[280px] [&>*]:h-full"
    return "col-span-1 min-h-[120px] [&>*]:h-full"
  }

  // Render tile grid -- either with DnD (own dashboard) or static (viewing other)
  function renderTileGrid() {
    const grid = (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tileOrder.map((id) => {
          const content = renderTileById(id)
          if (content === null) return null
          return isDragEnabled ? (
            <SortableDashboardTile
              key={id}
              id={id}
              className={getTileClasses(id)}
            >
              {content}
            </SortableDashboardTile>
          ) : (
            <div
              key={id}
              className={getTileClasses(id)}
            >
              {content}
            </div>
          )
        })}
      </div>
    )

    if (!isDragEnabled) return grid

    return (
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={() => setActiveId(null)}
      >
        <SortableContext items={tileOrder} strategy={rectSortingStrategy}>
          {grid}
        </SortableContext>

        {/* Ghost overlay -- semi-transparent copy follows cursor */}
        <DragOverlay>
          {activeId ? (
            <div
              className="opacity-60 shadow-xl rounded-lg pointer-events-none"
              style={{ width: dragWidth || undefined }}
            >
              {renderTileById(activeId)}
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
              <p className="text-muted-foreground mt-1">
                Welcome back, {user?.first_name || "User"}
              </p>
            </div>
            {!isViewingAs && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetToDefault}
                className="text-muted-foreground hover:text-foreground"
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Reset layout
              </Button>
            )}
          </div>

          {/* Missionary Selector */}
          {isSupervisorOrAdmin && missionaryOptions.length > 0 && (
            <div className="flex items-center gap-3">
              <Label className="text-sm font-medium whitespace-nowrap">Viewing:</Label>
              <Popover open={viewingPickerOpen} onOpenChange={setViewingPickerOpen}>
                <PopoverTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    {isViewingAs ? selectedUserName : "My Dashboard"}
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56 p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search..." />
                    <CommandList>
                      <CommandEmpty>No results found.</CommandEmpty>
                      <CommandGroup>
                        <CommandItem
                          value="my-dashboard"
                          onSelect={() => { exitViewAs(); setViewingPickerOpen(false) }}
                        >
                          <Check className={cn("mr-2 h-4 w-4", !isViewingAs ? "opacity-100" : "opacity-0")} />
                          My Dashboard
                        </CommandItem>
                        {missionaryOptions.map((u) => (
                          <CommandItem
                            key={u.id}
                            value={`${u.full_name} ${u.id}`}
                            onSelect={() => { setViewAsUser(u.id, u.full_name); setViewingPickerOpen(false) }}
                          >
                            <Check className={cn("mr-2 h-4 w-4", viewAsUserId === u.id ? "opacity-100" : "opacity-0")} />
                            {u.full_name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load dashboard data. Please try again.
            </div>
          )}

          {renderTileGrid()}
        </div>

        {/* Quick Log dialog for Late Donations */}
        <LogEventDialog
          open={!!quickLogContactId}
          onOpenChange={(open) => !open && setQuickLogContactId(null)}
          contactId={quickLogContactId || undefined}
        />
      </Container>
    </Section>
  )
}
