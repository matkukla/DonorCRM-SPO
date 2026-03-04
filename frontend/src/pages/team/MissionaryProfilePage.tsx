import { useParams, Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useUser } from "@/hooks/useUsers"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Mail } from "lucide-react"

export default function MissionaryProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const { user: currentUser } = useAuth()
  const { data: profileUser, isLoading } = useUser(userId ?? "")

  // Check access — supervisor/coach can only see their supervised_users
  const hasAccess = currentUser?.supervised_users?.some(u => u.id === userId)

  if (isLoading) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  if (!hasAccess || !profileUser) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Not found</h1>
            <p className="text-muted-foreground mt-2">
              This missionary is not in your team or does not exist.
            </p>
            <Link to="/team">
              <Button className="mt-4">Back to Team</Button>
            </Link>
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div>
            <Link
              to="/team"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to Team
            </Link>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">{profileUser.full_name}</CardTitle>
                  <CardDescription className="flex items-center gap-2 mt-1">
                    <Mail className="h-4 w-4" />
                    {profileUser.email}
                  </CardDescription>
                </div>
                <Badge variant="secondary">Missionary</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Detailed missionary profile coming soon.
              </p>
            </CardContent>
          </Card>
        </div>
      </Container>
    </Section>
  )
}
