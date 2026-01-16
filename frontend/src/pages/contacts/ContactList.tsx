import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function ContactList() {
  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Contacts</h1>
              <p className="text-muted-foreground mt-1">
                Manage your donors and supporters
              </p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Contact
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Coming Soon</CardTitle>
              <CardDescription>
                Contact list with search, filters, and pagination will be implemented in Phase 12.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                This page will display a data table with all contacts, including filtering by name,
                email, tags, and donation history.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
