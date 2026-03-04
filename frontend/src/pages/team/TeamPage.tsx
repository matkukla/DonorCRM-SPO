import { useNavigate } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Mail, ChevronRight } from "lucide-react"

export default function TeamPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const teamMembers = user?.supervised_users || []

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">My Team</h1>
            <p className="text-muted-foreground mt-1">
              View and support the missionaries in your team
            </p>
          </div>

          {teamMembers.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teamMembers.map((member) => (
                <Card
                  key={member.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => navigate(`/team/${member.id}`)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">
                        {member.first_name} {member.last_name}
                      </CardTitle>
                      <Badge variant="secondary">Missionary</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Mail className="h-4 w-4" />
                        {member.email}
                      </div>
                      <Button variant="ghost" size="sm">
                        View
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No team members assigned yet.
              </CardContent>
            </Card>
          )}
        </div>
      </Container>
    </Section>
  )
}
