import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function DonationList() {
  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Donations</h1>
              <p className="text-muted-foreground mt-1">
                Track and manage donor contributions
              </p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Record Donation
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Coming Soon</CardTitle>
              <CardDescription>
                Donation list with date range, contact, and type filters will be implemented in Phase 13.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                This page will display all donations with filtering, summary statistics, and
                the ability to mark donations as thanked.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
