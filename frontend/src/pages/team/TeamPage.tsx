import { useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export default function TeamPage() {
  const { user } = useAuth()
  const [search, setSearch] = useState("")
  const teamMembers = user?.supervised_users || []

  const filtered = teamMembers.filter((m) => {
    const fullName = `${m.first_name} ${m.last_name}`.toLowerCase()
    const q = search.toLowerCase()
    return fullName.includes(q) || m.email.toLowerCase().includes(q)
  })

  const subtitle =
    user?.role === "coach"
      ? "Your coachees"
      : "Missionaries under your supervision"

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">My Team</h1>
            <p className="text-muted-foreground mt-1">{subtitle}</p>
          </div>

          {/* Search */}
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search missionaries..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Table or empty state */}
          {teamMembers.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No missionaries assigned yet.
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No missionaries match your search.
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((missionary) => (
                    <TableRow key={missionary.id}>
                      <TableCell className="font-medium">
                        {missionary.first_name} {missionary.last_name}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {missionary.email}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/team/${missionary.id}`}>
                            View Profile &rarr;
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

        </div>

      </Container>
    </Section>
  )
}
