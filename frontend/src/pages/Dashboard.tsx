import { useAuth } from "@/providers/AuthProvider"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"

/**
 * Dashboard Page - Placeholder
 * Will be expanded in Phase 11 with widgets and statistics
 */
export default function Dashboard() {
  const { user } = useAuth()

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

          {/* Placeholder Cards */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader>
                <CardDescription>Total Contacts</CardDescription>
                <CardTitle className="text-3xl">--</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Donations This Month</CardDescription>
                <CardTitle className="text-3xl">$--</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Active Pledges</CardDescription>
                <CardTitle className="text-3xl">--</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Overdue Tasks</CardDescription>
                <CardTitle className="text-3xl">--</CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Info Card */}
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>
                Your dashboard will show key metrics and action items here.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Dashboard widgets will be implemented in Phase 11. Use the sidebar
                to navigate to different sections of the application.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
