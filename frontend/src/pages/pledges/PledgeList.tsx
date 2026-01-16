import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function PledgeList() {
  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Pledges</h1>
              <p className="text-muted-foreground mt-1">
                Manage recurring and one-time pledge commitments
              </p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Pledge
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Coming Soon</CardTitle>
              <CardDescription>
                Pledge list with status and frequency filters will be implemented in Phase 14.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                This page will display all pledges with late pledge highlighting and
                actions to pause, resume, or cancel pledges.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
