import { useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useBroadcasts } from "@/hooks/useBroadcasts"
import { broadcastTargetLabels } from "@/api/broadcasts"
import type { BroadcastTask } from "@/api/broadcasts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Search, Megaphone } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"
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
  const { data: broadcastsData } = useBroadcasts({ page_size: 10 })
  const broadcasts = broadcastsData?.results || []

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

          {/* Broadcast Tasks Section */}
          {user?.role === "supervisor" && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-semibold tracking-tight flex items-center gap-2">
                  <Megaphone className="h-5 w-5" />
                  Broadcast Tasks
                </h2>
                <p className="text-muted-foreground text-sm mt-1">
                  Tasks you've sent to your team
                </p>
              </div>

              {broadcasts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border rounded-md">
                  No broadcast tasks sent yet.
                </div>
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Task</TableHead>
                        <TableHead>Target</TableHead>
                        <TableHead>Due Date</TableHead>
                        <TableHead>Completion</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {broadcasts.map((b: BroadcastTask) => {
                        const pct = b.total_count > 0 ? Math.round((b.completed_count / b.total_count) * 100) : 0
                        return (
                          <TableRow key={b.id}>
                            <TableCell className="font-medium">{b.title}</TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {broadcastTargetLabels[b.target_type]}
                            </TableCell>
                            <TableCell>{formatLocalDate(b.due_date)}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium tabular-nums">
                                  {b.completed_count}/{b.total_count}
                                </span>
                                <Progress value={pct} className="h-2 w-20" />
                              </div>
                            </TableCell>
                            <TableCell>
                              {b.is_cancelled ? (
                                <Badge variant="destructive">Cancelled</Badge>
                              ) : b.completed_count === b.total_count && b.total_count > 0 ? (
                                <Badge variant="success">Complete</Badge>
                              ) : (
                                <Badge variant="secondary">Active</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </div>
      </Container>
    </Section>
  )
}
