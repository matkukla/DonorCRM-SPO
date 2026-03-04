import { useState, useMemo } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { formatDistanceToNow } from "date-fns"
import {
  useContact,
  useContactDonations,
  useContactPledges,
  useContactTasks,
  useContactJournals,
  useContactJournalEvents,
  useMarkContactThanked,
  useDeleteContact,
} from "@/hooks/useContacts"
import { useContactPrayers, useMarkPrayed } from "@/hooks/usePrayers"
import { PrayerCard } from "@/pages/prayer/components/PrayerCard"
import { PrayerIntentionPanel } from "@/pages/prayer/PrayerIntentionPanel"
import { LogEventDialog } from "@/pages/journals/components/LogEventDialog"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowLeft,
  BookOpen,
  Edit,
  Trash2,
  Heart,
  Mail,
  Phone,
  MapPin,
  DollarSign,
  FileText,
  CheckSquare,
  Plus,
} from "lucide-react"
import type { ContactStatus } from "@/api/contacts"
import type { PrayerIntention, PrayerIntentionStatus } from "@/api/prayers"
import { formatLocalDate } from "@/lib/utils"

const statusLabels: Record<ContactStatus, string> = {
  prospect: "Potential Donor",
  donor: "Donor",
  lapsed: "Lapsed",
  major_donor: "Major Donor",
  deceased: "Deceased",
}

const statusVariants: Record<ContactStatus, "default" | "secondary" | "success" | "warning" | "info"> = {
  prospect: "secondary",
  donor: "success",
  lapsed: "warning",
  major_donor: "info",
  deceased: "secondary",
}

function formatCurrency(amount: string | number | null): string {
  if (amount === null) return "—"
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export default function ContactDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const { data: contact, isLoading, error } = useContact(id!)
  const { data: donations } = useContactDonations(id!)
  const { data: pledges } = useContactPledges(id!)
  const { data: tasks } = useContactTasks(id!)
  const { data: journals } = useContactJournals(id!)
  const {
    data: journalEventsData,
    fetchNextPage: fetchNextEvents,
    hasNextPage: hasMoreEvents,
    isFetchingNextPage: isFetchingMoreEvents,
  } = useContactJournalEvents(id!)

  const journalEvents = useMemo(() => {
    if (!journalEventsData?.pages) return []
    return journalEventsData.pages.flatMap((page) => page.results)
  }, [journalEventsData])

  const [logEventOpen, setLogEventOpen] = useState(false)

  // Prayer tab state
  const { data: contactPrayers } = useContactPrayers(id!)
  const markPrayedMutation = useMarkPrayed()
  const [prayerFilter, setPrayerFilter] = useState<"all" | PrayerIntentionStatus>("all")
  const [prayerPanelOpen, setPrayerPanelOpen] = useState(false)
  const [editingPrayer, setEditingPrayer] = useState<PrayerIntention | undefined>()

  const filteredPrayers = useMemo(() => {
    const prayers = contactPrayers?.results ?? []
    if (prayerFilter === "all") return prayers
    return prayers.filter((p) => p.status === prayerFilter)
  }, [contactPrayers, prayerFilter])

  const isCoach = user?.role === "coach"
  const showFinancialTabs = !isCoach || String(contact?.owner) === String(user?.id)
  const isReadOnly = (user?.role === "supervisor" || user?.role === "coach") && contact?.owner !== undefined && String(contact?.owner) !== String(user?.id)

  const markThankedMutation = useMarkContactThanked()
  const deleteMutation = useDeleteContact()

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this contact? This action cannot be undone.")) {
      deleteMutation.mutate(id!, {
        onSuccess: () => navigate("/contacts"),
      })
    }
  }

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

  if (error || !contact) {
    return (
      <Section>
        <Container>
          <div className="text-center py-12">
            <h1 className="text-2xl font-semibold">Contact not found</h1>
            <p className="text-muted-foreground mt-2">
              The contact you're looking for doesn't exist or you don't have permission to view it.
            </p>
            <Button className="mt-4" onClick={() => navigate("/contacts")}>
              Back to Contacts
            </Button>
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Link
                to="/contacts"
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Contacts
              </Link>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-semibold tracking-tight">
                  {contact.full_name}
                </h1>
                <Badge variant={statusVariants[contact.status]}>
                  {statusLabels[contact.status]}
                </Badge>
                {contact.needs_thank_you && (
                  <Badge variant="warning" className="gap-1">
                    <Heart className="h-3 w-3" />
                    Needs Thank You
                  </Badge>
                )}
              </div>
              <p className="text-muted-foreground">
                Owner: {contact.owner_name}
              </p>
            </div>
            {!isReadOnly && (
              <div className="flex gap-2">
                {contact.needs_thank_you && (
                  <Button
                    variant="secondary"
                    onClick={() => markThankedMutation.mutate(id!)}
                    disabled={markThankedMutation.isPending}
                  >
                    <Heart className="h-4 w-4 mr-2" />
                    Mark Thanked
                  </Button>
                )}
                <Button variant="secondary" onClick={() => navigate(`/contacts/${id}/edit`)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Summary Cards */}
          <div className="grid gap-6 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Given</CardDescription>
                <CardTitle className="text-2xl">
                  {formatCurrency(contact.total_given)}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Gift Count</CardDescription>
                <CardTitle className="text-2xl">{contact.gift_count}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Last Gift</CardDescription>
                <CardTitle className="text-2xl">
                  {formatCurrency(contact.last_gift_amount)}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {formatLocalDate(contact.last_gift_date)}
                </p>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Monthly Pledge</CardDescription>
                <CardTitle className="text-2xl">
                  {contact.has_active_pledge
                    ? formatCurrency(contact.monthly_pledge_amount)
                    : "—"}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="overview">
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="journal">Journal</TabsTrigger>
              {showFinancialTabs && (
                <TabsTrigger value="donations">
                  Donations ({donations?.length || 0})
                </TabsTrigger>
              )}
              {showFinancialTabs && (
                <TabsTrigger value="pledges">
                  Pledges ({pledges?.length || 0})
                </TabsTrigger>
              )}
              <TabsTrigger value="tasks">
                Tasks ({tasks?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="prayer" className="flex items-center gap-1.5">
                <Heart className="h-4 w-4" /> Prayer
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-6">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Contact Info */}
                <Card>
                  <CardHeader>
                    <CardTitle>Contact Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {contact.email && (
                      <div className="flex items-center gap-3">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <a href={`mailto:${contact.email}`} className="text-primary hover:underline">
                          {contact.email}
                        </a>
                      </div>
                    )}
                    {contact.phone && (
                      <div className="flex items-center gap-3">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        <a href={`tel:${contact.phone}`} className="hover:underline">
                          {contact.phone}
                        </a>
                      </div>
                    )}
                    {contact.phone_secondary && (
                      <div className="flex items-center gap-3">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        <a href={`tel:${contact.phone_secondary}`} className="hover:underline">
                          {contact.phone_secondary}
                        </a>
                      </div>
                    )}
                    {contact.full_address && (
                      <div className="flex items-start gap-3">
                        <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <span>{contact.full_address}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Groups & Notes */}
                <Card>
                  <CardHeader>
                    <CardTitle>Groups & Notes</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {contact.groups.length > 0 && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Groups</p>
                        <div className="flex flex-wrap gap-2">
                          {contact.groups.map((group) => (
                            <Badge key={group.id} variant="secondary">
                              {group.name}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {contact.notes && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">Notes</p>
                        <p className="whitespace-pre-wrap">{contact.notes}</p>
                      </div>
                    )}
                    {!contact.groups.length && !contact.notes && (
                      <p className="text-muted-foreground">No groups or notes.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="donations" className="mt-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Donation History</CardTitle>
                  {!isReadOnly && (
                    <Button size="sm" onClick={() => navigate(`/donations/new?contact=${id}`)}>
                      <DollarSign className="h-4 w-4 mr-2" />
                      Record Donation
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {donations?.length ? (
                    <div className="space-y-2">
                      {donations.map((donation: { id: string; amount_dollars: string; gift_date: string; description: string; fund_name: string | null }) => (
                        <div
                          key={donation.id}
                          className="flex items-center justify-between py-2 border-b last:border-0"
                        >
                          <div>
                            <p className="font-medium">{formatCurrency(donation.amount_dollars)}</p>
                            <p className="text-sm text-muted-foreground">
                              {formatLocalDate(donation.gift_date)}{donation.description ? ` · ${donation.description}` : ""}
                            </p>
                          </div>
                          {donation.fund_name && (
                            <span className="text-sm text-muted-foreground">{donation.fund_name}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">
                      No donations recorded yet.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="pledges" className="mt-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Pledges</CardTitle>
                  {!isReadOnly && (
                    <Button size="sm" onClick={() => navigate(`/pledges/new?contact=${id}`)}>
                      <FileText className="h-4 w-4 mr-2" />
                      Create Pledge
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {pledges?.length ? (
                    <div className="space-y-2">
                      {pledges.map((pledge: { id: string; amount_dollars: string; frequency: string; status: string }) => (
                        <div
                          key={pledge.id}
                          className="flex items-center justify-between py-2 border-b last:border-0"
                        >
                          <div>
                            <p className="font-medium">
                              {formatCurrency(pledge.amount_dollars)} / {pledge.frequency}
                            </p>
                            <p className="text-sm text-muted-foreground capitalize">
                              {pledge.status}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">
                      No pledges recorded yet.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="tasks" className="mt-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Tasks</CardTitle>
                  {!isReadOnly && (
                    <Button size="sm" onClick={() => navigate(`/tasks/new?contact=${id}`)}>
                      <CheckSquare className="h-4 w-4 mr-2" />
                      Add Task
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {tasks?.length ? (
                    <div className="space-y-2">
                      {tasks.map((task: { id: string; title: string; due_date: string; status: string; priority: string }) => (
                        <div
                          key={task.id}
                          className="flex items-center justify-between py-2 border-b last:border-0"
                        >
                          <div>
                            <p className="font-medium">{task.title}</p>
                            <p className="text-sm text-muted-foreground">
                              Due: {formatLocalDate(task.due_date)} · {task.priority}
                            </p>
                          </div>
                          <Badge variant={task.status === "completed" ? "success" : "secondary"}>
                            {task.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">
                      No tasks assigned yet.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="prayer" className="mt-6">
              <div className="bg-amber-50/30 dark:bg-amber-950/10 rounded-xl p-6">
                {/* Toggle filter tabs + Add button */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex gap-1 bg-amber-100/50 dark:bg-amber-900/30 rounded-lg p-1">
                    {(["all", "active", "answered", "archived"] as const).map(
                      (filter) => (
                        <button
                          key={filter}
                          onClick={() => setPrayerFilter(filter)}
                          className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                            prayerFilter === filter
                              ? "bg-white dark:bg-card text-amber-900 dark:text-amber-100 shadow-sm font-medium"
                              : "text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200"
                          }`}
                        >
                          {filter.charAt(0).toUpperCase() + filter.slice(1)}
                        </button>
                      ),
                    )}
                  </div>
                  {!isReadOnly && (
                    <Button
                      size="sm"
                      onClick={() => {
                        setEditingPrayer(undefined)
                        setPrayerPanelOpen(true)
                      }}
                      className="gap-1.5"
                    >
                      <Plus className="h-4 w-4" />
                      Add
                    </Button>
                  )}
                </div>

                {/* Prayer cards grid */}
                {filteredPrayers.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredPrayers.map((intention) => (
                      <PrayerCard
                        key={intention.id}
                        intention={intention}
                        onPrayed={(pId) => markPrayedMutation.mutate(pId)}
                        onEdit={(p) => {
                          setEditingPrayer(p)
                          setPrayerPanelOpen(true)
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-amber-700/70 dark:text-amber-400/50 text-center py-8 leading-relaxed">
                    No prayer intentions for this contact.
                  </p>
                )}
              </div>

              <PrayerIntentionPanel
                open={prayerPanelOpen}
                onClose={() => {
                  setPrayerPanelOpen(false)
                  setEditingPrayer(undefined)
                }}
                intention={editingPrayer}
                lockedContactId={id}
                lockedContactName={contact.full_name}
              />
            </TabsContent>

            <TabsContent value="journal" className="mt-6 space-y-6">
              {/* Event Timeline */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Journal</CardTitle>
                    <CardDescription>
                      Interaction timeline across all campaigns
                    </CardDescription>
                  </div>
                  {!isReadOnly && (
                    <Button size="sm" onClick={() => setLogEventOpen(true)}>
                      <BookOpen className="h-4 w-4 mr-2" />
                      Log Event
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {journalEvents.length > 0 ? (
                    <div className="space-y-1">
                      {journalEvents.map((event, index) => {
                        const eventTypeLabel = event.event_type
                          .split("_")
                          .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(" ")
                        const stageLabel = event.stage
                          .split("_")
                          .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(" ")
                        const relativeTime = formatDistanceToNow(new Date(event.created_at), {
                          addSuffix: true,
                        })
                        const isLast = index === journalEvents.length - 1 && !hasMoreEvents

                        return (
                          <div key={event.id} className="relative pl-6 pb-6">
                            {!isLast && (
                              <div className="absolute left-[9px] top-4 bottom-0 w-[2px] bg-border" />
                            )}
                            <div className="absolute left-0 top-1 w-[18px] h-[18px] rounded-full border-2 border-border bg-background flex items-center justify-center">
                              <div className="w-2 h-2 rounded-full bg-primary" />
                            </div>
                            <div className="pt-0">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant="secondary" className="text-xs">
                                    {eventTypeLabel}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">
                                    {stageLabel}
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {event.journal_name}
                                  </span>
                                </div>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                  {relativeTime}
                                </span>
                              </div>
                              {event.notes && (
                                <p className="mt-1 text-sm text-foreground line-clamp-2">
                                  {event.notes}
                                </p>
                              )}
                            </div>
                          </div>
                        )
                      })}
                      {hasMoreEvents && (
                        <div className="pt-2">
                          <Button
                            onClick={() => fetchNextEvents()}
                            disabled={isFetchingMoreEvents}
                            variant="outline"
                            className="w-full"
                          >
                            {isFetchingMoreEvents ? "Loading..." : "Load More"}
                          </Button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">
                      No journal events yet. Click "Log Event" to record your first interaction.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Campaign Memberships */}
              {journals && journals.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Campaign Memberships</CardTitle>
                    <CardDescription>
                      Journals this contact is currently enrolled in
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {journals.map((membership) => (
                        <div
                          key={membership.id}
                          className="flex items-center justify-between py-3 border-b last:border-0"
                        >
                          <div className="space-y-1">
                            <Link
                              to={`/journals/${membership.journal_id}`}
                              className="font-medium hover:underline"
                            >
                              {membership.journal_name}
                            </Link>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Badge variant="secondary">
                                {membership.current_stage.charAt(0).toUpperCase() + membership.current_stage.slice(1).replace('_', ' ')}
                              </Badge>
                              {membership.deadline && (
                                <span>Due: {formatLocalDate(membership.deadline)}</span>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            {membership.decision ? (
                              <div>
                                <p className="font-medium">
                                  {formatCurrency(membership.decision.amount)}
                                  <span className="text-muted-foreground font-normal">
                                    /{membership.decision.cadence.replace('_', '-')}
                                  </span>
                                </p>
                                <Badge
                                  variant={
                                    membership.decision.status === 'active' ? 'success' :
                                    membership.decision.status === 'pending' ? 'warning' :
                                    membership.decision.status === 'declined' ? 'destructive' :
                                    'secondary'
                                  }
                                >
                                  {membership.decision.status}
                                </Badge>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">No decision</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <LogEventDialog
                open={logEventOpen}
                onOpenChange={setLogEventOpen}
                contactId={id}
              />
            </TabsContent>
          </Tabs>
        </div>
      </Container>
    </Section>
  )
}
