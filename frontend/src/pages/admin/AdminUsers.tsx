import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plus } from "lucide-react"

export default function AdminUsers() {
  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">User Management</h1>
              <p className="text-muted-foreground mt-1">
                Manage system users and their roles
              </p>
            </div>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add User
            </Button>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Coming Soon</CardTitle>
              <CardDescription>
                Admin user management will be implemented in Phase 16.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                This page will allow administrators to create, edit, and deactivate users,
                as well as manage their roles (admin, staff, viewer).
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
