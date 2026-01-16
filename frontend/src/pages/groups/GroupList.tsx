import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function GroupList() {
  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Groups</h1>
              <p className="text-muted-foreground mt-1">
                Organize contacts into groups for targeted communication
              </p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Group
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Coming Soon</CardTitle>
              <CardDescription>
                Groups CRUD and member management will be implemented in Phase 16.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                This page will display all groups with the ability to add/remove members
                and view group statistics.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
