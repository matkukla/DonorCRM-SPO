import { useAuth } from "@/providers/AuthProvider"
import { useDashboardSummary } from "@/hooks/useDashboard"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { StatCard } from "@/components/dashboard/StatCard"
import { RecentDonations } from "@/components/dashboard/RecentDonations"
import { NeedsAttention } from "@/components/dashboard/NeedsAttention"
import { SupportProgress } from "@/components/dashboard/SupportProgress"
import { AtRiskDonors } from "@/components/dashboard/AtRiskDonors"
import { Users, DollarSign, FileText, CheckSquare } from "lucide-react"

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export default function Dashboard() {
  const { user } = useAuth()
  const { data, isLoading, error } = useDashboardSummary()

  // Calculate total donations this month from recent gifts
  const totalDonationsThisMonth = data?.recent_gifts?.reduce((sum, gift) => {
    return sum + parseFloat(gift.amount)
  }, 0) || 0

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

          {/* Stat Cards */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Thank You Queue"
              value={data?.thank_you_count || 0}
              icon={Users}
              isLoading={isLoading}
              description="need acknowledgment"
            />
            <StatCard
              title="Recent Donations"
              value={formatCurrency(totalDonationsThisMonth)}
              icon={DollarSign}
              isLoading={isLoading}
              description="last 30 days"
            />
            <StatCard
              title="Active Pledges"
              value={data?.support_progress?.active_pledge_count || 0}
              icon={FileText}
              isLoading={isLoading}
            />
            <StatCard
              title="Items Needing Attention"
              value={
                (data?.needs_attention?.overdue_task_count || 0) +
                (data?.needs_attention?.late_pledge_count || 0)
              }
              icon={CheckSquare}
              isLoading={isLoading}
            />
          </div>

          {/* Main Content Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Left Column */}
            <div className="space-y-6">
              <NeedsAttention
                overdueTasks={data?.needs_attention?.overdue_tasks || []}
                overdueTaskCount={data?.needs_attention?.overdue_task_count || 0}
                latePledges={data?.needs_attention?.late_pledges || []}
                latePledgeCount={data?.needs_attention?.late_pledge_count || 0}
                thankYouNeeded={data?.needs_attention?.thank_you_needed || []}
                thankYouCount={data?.needs_attention?.thank_you_needed_count || 0}
                isLoading={isLoading}
              />
              <SupportProgress
                data={data?.support_progress || null}
                isLoading={isLoading}
              />
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <RecentDonations
                donations={data?.recent_gifts || []}
                isLoading={isLoading}
              />
              <AtRiskDonors
                donors={data?.at_risk_donors || []}
                totalCount={data?.at_risk_count || 0}
                isLoading={isLoading}
              />
            </div>
          </div>
        </div>
      </Container>
    </Section>
  )
}
