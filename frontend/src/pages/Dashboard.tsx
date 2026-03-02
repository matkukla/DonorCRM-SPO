import { useEffect, useRef, useState } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { markEventsSeen } from "@/api/dashboard"
import { useDashboardSummary } from "@/hooks/useDashboard"
import { useDashboardLayout } from "@/hooks/useDashboard"
import { useUsers } from "@/hooks/useUsers"
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
import { useMPDMyData } from "@/hooks/useMPD"
import { MPDStatsInline } from "@/components/mpd/MPDStatsInline"
import { Users, DollarSign, FileText, CheckSquare, RotateCcw, ChevronDown, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { DndContext, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core"
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
}

export default function Dashboard() {
  const { user } = useAuth()
  const isSupervisorOrAdmin = user?.role === "admin" || user?.role === "mission_supervisor"
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const isViewingOther = selectedUserId !== null && selectedUserId !== user?.id
  const effectiveUserId = selectedUserId || undefined

  // For admin: fetch all users for the dropdown
  // For supervisor: use supervised_users from auth user
  const { data: allUsers } = useUsers()
  const missionaryOptions = user?.role === "admin"
    ? (allUsers?.filter((u) => u.id !== user.id && u.is_active) || [])
    : (user?.supervised_users || [])

  const { data, isLoading, error } = useDashboardSummary(effectiveUserId)
  const { data: mpdData, isLoading: mpdLoading } = useMPDMyData()
  const [quickLogContactId, setQuickLogContactId] = useState<string | null>(null)

  const { tileOrder, setTileOrder, resetToDefault, isDragEnabled } = useDashboardLayout(effectiveUserId)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [dragWidth, setDragWidth] = useState<number>(0)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  )

  // Mark events as seen once after dashboard data loads (QAL-09)
  // Skip when viewing another user's dashboard
  const markedSeen = useRef(false)

  useEffect(() => {
    if (data && !isLoading && !markedSeen.current && !isViewingOther) {
      markedSeen.current = true
      markEventsSeen().catch(() => {
        // Silently ignore -- marking seen is best-effort
      })
    }
  }, [data, isLoading, isViewingOther])

  // Calculate total donations this month from recent gifts
  const totalDonationsThisMonth = data?.recent_gifts?.reduce((sum, gift) => {
    return sum + parseFloat(gift.amount)
  }, 0) || 0

  // Get name of the selected missionary for display
  const selectedUserName = isViewingOther
    ? (() => {
        const found = missionaryOptions.find((u) => u.id === selectedUserId)
        return found ? `${found.first_name} ${found.last_name}` : "Unknown"
      })()
    : null

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
        return <StatCard title="Items Needing Attention" value={(data?.needs_attention?.overdue_task_count || 0) + (data?.needs_attention?.late_pledge_count || 0)} icon={CheckSquare} isLoading={isLoading} />
      // Content section
      case "needs-attention":
        return <NeedsAttention overdueTasks={data?.needs_attention?.overdue_tasks || []} overdueTaskCount={data?.needs_attention?.overdue_task_count || 0} latePledges={data?.needs_attention?.late_pledges || []} latePledgeCount={data?.needs_attention?.late_pledge_count || 0} thankYouNeeded={data?.needs_attention?.thank_you_needed || []} thankYouCount={data?.needs_attention?.thank_you_needed_count || 0} isLoading={isLoading} />
      case "support-progress":
        return <SupportProgress data={data?.support_progress || null} isLoading={isLoading} />
      case "recent-donations":
        return <RecentDonations donations={data?.recent_gifts || []} isLoading={isLoading} />
      case "late-donations":
        return <LateDonations donations={data?.late_donations || []} totalCount={data?.late_donations_count || 0} isLoading={isLoading} onQuickLog={(contactId) => setQuickLogContactId(contactId)} />
      default: return null
    }
  }

  // Render tile grid -- either with DnD (own dashboard) or static (viewing other)
  function renderTileGrid() {
    const grid = (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tileOrder.map((id) =>
          isDragEnabled ? (
            <SortableDashboardTile
              key={id}
              id={id}
              className={TILE_SIZES[id] === 2 ? "col-span-2" : "col-span-1"}
            >
              {renderTileById(id)}
            </SortableDashboardTile>
          ) : (
            <div
              key={id}
              className={TILE_SIZES[id] === 2 ? "col-span-2" : "col-span-1"}
            >
              {renderTileById(id)}
            </div>
          )
        )}
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
            {!isViewingOther && (
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
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="secondary" size="sm" className="gap-2">
                    {isViewingOther ? selectedUserName : "My Dashboard"}
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => setSelectedUserId(null)}>
                    My Dashboard
                  </DropdownMenuItem>
                  {missionaryOptions.map((u) => (
                    <DropdownMenuItem key={u.id} onClick={() => setSelectedUserId(u.id)}>
                      {u.first_name} {u.last_name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}

          {/* Read-only banner when viewing another user */}
          {isViewingOther && selectedUserName && (
            <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border rounded-md text-sm text-muted-foreground">
              <Info className="h-4 w-4 shrink-0" />
              Viewing {selectedUserName}&apos;s dashboard (read-only)
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load dashboard data. Please try again.
            </div>
          )}

          {renderTileGrid()}

          {/* MPD Section -- NOT draggable (Fragment children, conditional) */}
          {!isViewingOther && (
            <>
              {mpdLoading ? (
                <div className="grid gap-3 md:grid-cols-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-24 bg-muted rounded-lg animate-pulse" />
                  ))}
                </div>
              ) : mpdData?.has_data ? (
                <div className="space-y-2">
                  <h2 className="text-lg font-semibold">MPD Financial Overview</h2>
                  <div className="grid gap-3 md:grid-cols-3">
                    <MPDStatsInline
                      currentMpdCap={mpdData.current_mpd_cap}
                      latestRollForwardBalance={mpdData.latest_roll_forward_balance}
                      monthsRemainingRf={mpdData.months_remaining_rf}
                    />
                  </div>
                </div>
              ) : null}
            </>
          )}
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
