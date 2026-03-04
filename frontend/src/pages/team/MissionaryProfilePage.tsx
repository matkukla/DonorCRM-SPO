import { Link, useParams } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { useContacts } from "@/hooks/useContacts"
import { useJournals } from "@/hooks/useJournals"
import { useTasks } from "@/hooks/useTasks"
import { useGifts } from "@/hooks/useGifts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ArrowLeft, Mail } from "lucide-react"
import { formatLocalDate } from "@/lib/utils"

const PAGE_SIZE = "50"

export default function MissionaryProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const { user } = useAuth()

  // Derive missionary from auth context supervised_users list
  const missionary = user?.supervised_users?.find((u) => u.id === userId) ?? null
  const hasAccess = !!missionary
  const isCoach = user?.role === "coach"

  // All hooks must be called unconditionally (Rules of Hooks).
  // Pass empty params when not authorized; queries won't fire with no owner.
  const ownerParam = hasAccess && userId ? userId : ""

  const { data: contactsData, isLoading: contactsLoading } = useContacts(
    ownerParam ? { owner: ownerParam, page_size: PAGE_SIZE } : {}
  )
  const { data: journalsData, isLoading: journalsLoading } = useJournals(
    ownerParam ? { owner: ownerParam, page_size: PAGE_SIZE } : {}
  )
  const { data: tasksData, isLoading: tasksLoading } = useTasks(
    ownerParam ? { owner: ownerParam, page_size: Number(PAGE_SIZE) } : {}
  )
  // Donations: only for supervisor role, not coach
  const { data: giftsData, isLoading: giftsLoading } = useGifts(
    ownerParam && !isCoach ? { owner: ownerParam, page_size: PAGE_SIZE } : {}
  )

  // Show 403 if userId not in supervised_users
  if (!hasAccess) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Not Authorized</h1>
            <p className="text-muted-foreground mt-2">
              This missionary is not in your team or does not exist.
            </p>
            <Button asChild className="mt-4">
              <Link to="/team">Back to My Team</Link>
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  const contacts = contactsData?.results ?? []
  const journals = journalsData?.results ?? []
  const tasks = tasksData?.results ?? []
  const gifts = giftsData?.results ?? []

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Back link */}
          <Link
            to="/team"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to My Team
          </Link>

          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              {missionary.first_name} {missionary.last_name}
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <Badge variant="secondary">Missionary</Badge>
              <span className="flex items-center gap-1 text-sm text-muted-foreground">
                <Mail className="h-4 w-4" />
                {missionary.email}
              </span>
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="contacts">
            <TabsList>
              <TabsTrigger value="contacts">
                Contacts
                {contactsData && (
                  <span className="ml-1.5 text-xs opacity-60">
                    ({contactsData.count})
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="journals">
                Journals
                {journalsData && (
                  <span className="ml-1.5 text-xs opacity-60">
                    ({journalsData.count})
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="tasks">
                Tasks
                {tasksData && (
                  <span className="ml-1.5 text-xs opacity-60">
                    ({tasksData.count})
                  </span>
                )}
              </TabsTrigger>
              {!isCoach && (
                <TabsTrigger value="donations">
                  Donations
                  {giftsData && (
                    <span className="ml-1.5 text-xs opacity-60">
                      ({giftsData.count})
                    </span>
                  )}
                </TabsTrigger>
              )}
            </TabsList>

            {/* Contacts tab */}
            <TabsContent value="contacts" className="mt-4">
              {contactsLoading ? (
                <LoadingRows />
              ) : contacts.length === 0 ? (
                <EmptyState message="No contacts found" />
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {contacts.map((contact) => (
                        <TableRow key={contact.id}>
                          <TableCell className="font-medium">
                            {contact.full_name}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {contact.email ?? "\u2014"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{contact.status}</Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/contacts/${contact.id}`}>View</Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            {/* Journals tab */}
            <TabsContent value="journals" className="mt-4">
              {journalsLoading ? (
                <LoadingRows />
              ) : journals.length === 0 ? (
                <EmptyState message="No journals found" />
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Goal</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {journals.map((journal) => (
                        <TableRow key={journal.id}>
                          <TableCell className="font-medium">
                            {journal.name}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {journal.goal_amount
                              ? Number(journal.goal_amount).toLocaleString("en-US", {
                                  style: "currency",
                                  currency: "USD",
                                  minimumFractionDigits: 0,
                                  maximumFractionDigits: 0,
                                })
                              : "\u2014"}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/journals/${journal.id}`}>View</Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            {/* Tasks tab */}
            <TabsContent value="tasks" className="mt-4">
              {tasksLoading ? (
                <LoadingRows />
              ) : tasks.length === 0 ? (
                <EmptyState message="No tasks found" />
              ) : (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Task</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Due</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tasks.map((task) => (
                        <TableRow key={task.id}>
                          <TableCell className="font-medium">
                            {task.title}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{task.status}</Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatLocalDate(task.due_date)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/tasks/${task.id}`}>View</Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            {/* Donations tab — supervisor only */}
            {!isCoach && (
              <TabsContent value="donations" className="mt-4">
                {giftsLoading ? (
                  <LoadingRows />
                ) : gifts.length === 0 ? (
                  <EmptyState message="No donations found" />
                ) : (
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Donor</TableHead>
                          <TableHead>Amount</TableHead>
                          <TableHead>Date</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {gifts.map((gift) => (
                          <TableRow key={gift.id}>
                            <TableCell className="font-medium">
                              {gift.donor_contact_name}
                            </TableCell>
                            <TableCell>
                              {Number(gift.amount_dollars).toLocaleString("en-US", {
                                style: "currency",
                                currency: "USD",
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {formatLocalDate(gift.gift_date)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </TabsContent>
            )}
          </Tabs>
        </div>
      </Container>
    </Section>
  )
}

function LoadingRows() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-10 bg-muted rounded animate-pulse" />
      ))}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-10 text-muted-foreground">{message}</div>
  )
}
