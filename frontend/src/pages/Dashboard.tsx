import { useEffect, useRef, useState } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { markEventsSeen } from "@/api/dashboard"
import { useDashboardSummary } from "@/hooks/useDashboard"
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
import { Users, DollarSign, FileText, CheckSquare } from "lucide-react"
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

const DEFAULT_GIVING_ORDER = ["giving-summary", "monthly-gifts"] as const
const DEFAULT_STATS_ORDER = ["thank-you", "recent-donations-stat", "active-pledges", "needs-attention-stat"] as const
const DEFAULT_CONTENT_ORDER = ["needs-attention", "support-progress", "recent-donations", "late-donations"] as const

export default function Dashboard() {
  const { user } = useAuth()
  const { data, isLoading, error } = useDashboardSummary()
  const { data: mpdData, isLoading: mpdLoading } = useMPDMyData()
  const [quickLogContactId, setQuickLogContactId] = useState<string | null>(null)

  const [givingOrder, setGivingOrder] = useState<string[]>([...DEFAULT_GIVING_ORDER])
  const [statsOrder, setStatsOrder] = useState<string[]>([...DEFAULT_STATS_ORDER])
  const [contentOrder, setContentOrder] = useState<string[]>([...DEFAULT_CONTENT_ORDER])
  const [activeId, setActiveId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  )

  // Mark events as seen once after dashboard data loads (QAL-09)
  const markedSeen = useRef(false)

  useEffect(() => {
    if (data && !isLoading && !markedSeen.current) {
      markedSeen.current = true
      markEventsSeen().catch(() => {
        // Silently ignore -- marking seen is best-effort
      })
    }
  }, [data, isLoading])

  // Calculate total donations this month from recent gifts
  const totalDonationsThisMonth = data?.recent_gifts?.reduce((sum, gift) => {
    return sum + parseFloat(gift.amount)
  }, 0) || 0

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string)
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)

    if (!over || active.id === over.id) return

    // Try reorder in each section -- only the one containing the item will match
    const tryReorder = (
      order: string[],
      setOrder: React.Dispatch<React.SetStateAction<string[]>>
    ) => {
      const oldIndex = order.indexOf(active.id as string)
      const newIndex = order.indexOf(over.id as string)
      if (oldIndex !== -1 && newIndex !== -1) {
        setOrder(arrayMove(order, oldIndex, newIndex))
      }
    }

    tryReorder(givingOrder, setGivingOrder)
    tryReorder(statsOrder, setStatsOrder)
    tryReorder(contentOrder, setContentOrder)
  }

  function renderTileById(tileId: string): React.ReactNode {
    switch (tileId) {
      // Giving section
      case "giving-summary": return <GivingSummaryCard />
      case "monthly-gifts": return <MonthlyGiftsCard />
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

  return (
    <Section>
      <Container>
        <div className="space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Welcome back, {user?.first_name || "User"}
            </p>
          </div>

          {/* Error State */}
          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load dashboard data. Please try again.
            </div>
          )}

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={() => setActiveId(null)}
          >
            {/* Giving Widgets */}
            <SortableContext items={givingOrder} strategy={rectSortingStrategy}>
              <div className="grid gap-6 lg:grid-cols-2">
                {givingOrder.map((id) => (
                  <SortableDashboardTile key={id} id={id}>
                    {renderTileById(id)}
                  </SortableDashboardTile>
                ))}
              </div>
            </SortableContext>

            {/* Stat Cards */}
            <SortableContext items={statsOrder} strategy={rectSortingStrategy}>
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                {statsOrder.map((id) => (
                  <SortableDashboardTile key={id} id={id}>
                    {renderTileById(id)}
                  </SortableDashboardTile>
                ))}
              </div>
            </SortableContext>

            {/* MPD Section -- NOT draggable (Fragment children, conditional) */}
            {mpdLoading ? (
              <div className="grid gap-4 md:grid-cols-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-24 bg-muted rounded-lg animate-pulse" />
                ))}
              </div>
            ) : mpdData?.has_data ? (
              <div className="space-y-2">
                <h2 className="text-lg font-semibold">MPD Financial Overview</h2>
                <div className="grid gap-4 md:grid-cols-3">
                  <MPDStatsInline
                    currentMpdCap={mpdData.current_mpd_cap}
                    latestRollForwardBalance={mpdData.latest_roll_forward_balance}
                    monthsRemainingRf={mpdData.months_remaining_rf}
                  />
                </div>
              </div>
            ) : null}

            {/* Main Content -- flat grid, no left/right column split */}
            <SortableContext items={contentOrder} strategy={rectSortingStrategy}>
              <div className="grid gap-6 lg:grid-cols-2">
                {contentOrder.map((id) => (
                  <SortableDashboardTile key={id} id={id}>
                    {renderTileById(id)}
                  </SortableDashboardTile>
                ))}
              </div>
            </SortableContext>

            {/* Ghost overlay -- semi-transparent copy follows cursor */}
            <DragOverlay>
              {activeId ? (
                <div className="opacity-60 shadow-xl rounded-lg pointer-events-none">
                  {renderTileById(activeId)}
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
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
