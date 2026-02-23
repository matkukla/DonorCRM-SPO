import { useState, useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useRecurringGift, useCreateRecurringGift, useUpdateRecurringGift } from "@/hooks/useGifts"
import { useSearchContacts } from "@/hooks/useContacts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ArrowLeft, ChevronDown, Search } from "lucide-react"
import type { RecurringGiftFrequency, RecurringGiftStatus } from "@/api/gifts"
import { recurringGiftFrequencyLabels, recurringGiftStatusLabels } from "@/api/gifts"

interface FormData {
  donor_contact: string
  amount: string  // Dollar string for the input
  frequency: RecurringGiftFrequency
  status: RecurringGiftStatus
  start_date: string
  end_date: string
  description: string
}

export default function PledgeForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const preselectedContactId = searchParams.get("contact")

  const { data: existingRG, isLoading: isLoadingRG } = useRecurringGift(id || null)
  const createMutation = useCreateRecurringGift()
  const updateMutation = useUpdateRecurringGift()

  const [contactSearch, setContactSearch] = useState("")
  const [selectedContact, setSelectedContact] = useState<{ id: string; name: string } | null>(null)
  const [showContactDropdown, setShowContactDropdown] = useState(false)

  const { data: contactResults } = useSearchContacts(contactSearch)

  const [formData, setFormData] = useState<FormData>({
    donor_contact: preselectedContactId || "",
    amount: "",
    frequency: "monthly",
    status: "active",
    start_date: new Date().toISOString().split("T")[0],
    end_date: "",
    description: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingRG) {
      setFormData({
        donor_contact: existingRG.donor_contact,
        amount: existingRG.amount_dollars,
        frequency: existingRG.frequency,
        status: existingRG.status,
        start_date: existingRG.start_date,
        end_date: existingRG.end_date || "",
        description: existingRG.description || "",
      })
      setSelectedContact({
        id: existingRG.donor_contact,
        name: existingRG.donor_contact_name,
      })
    }
  }, [existingRG])

  useEffect(() => {
    if (preselectedContactId && contactResults) {
      const contact = contactResults.find((c) => c.id === preselectedContactId)
      if (contact) {
        setSelectedContact({ id: contact.id, name: contact.full_name })
        setFormData((prev) => ({ ...prev, donor_contact: contact.id }))
      }
    }
  }, [preselectedContactId, contactResults])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }))
    }
  }

  const handleContactSelect = (contact: { id: string; full_name: string }) => {
    setSelectedContact({ id: contact.id, name: contact.full_name })
    setFormData((prev) => ({ ...prev, donor_contact: contact.id }))
    setContactSearch("")
    setShowContactDropdown(false)
    if (errors.donor_contact) {
      setErrors((prev) => ({ ...prev, donor_contact: "" }))
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.donor_contact) {
      newErrors.donor_contact = "Contact is required"
    }
    if (!formData.amount || parseFloat(formData.amount) <= 0) {
      newErrors.amount = "Amount must be greater than 0"
    }
    if (!formData.start_date) {
      newErrors.start_date = "Start date is required"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    const amount_cents = Math.round(parseFloat(formData.amount) * 100)

    const payload = {
      donor_contact: formData.donor_contact,
      amount_cents,
      frequency: formData.frequency,
      status: formData.status,
      start_date: formData.start_date,
      end_date: formData.end_date || undefined,
      description: formData.description || undefined,
    }

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: id!, data: payload })
      } else {
        await createMutation.mutateAsync(payload)
      }
      navigate("/pledges")
    } catch {
      // Error is handled by the mutation
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (isEditing && isLoadingRG) {
    return (
      <Section>
        <Container>
          <div className="max-w-2xl mx-auto">
            <div className="h-8 w-48 bg-muted rounded animate-pulse mb-6" />
            <div className="h-96 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-2"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </button>
            <h1 className="text-3xl font-semibold tracking-tight">
              {isEditing ? "Edit Pledge" : "Create Pledge"}
            </h1>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Contact Selection */}
              <Card>
                <CardHeader>
                  <CardTitle>Donor</CardTitle>
                  <CardDescription>Select the donor for this pledge</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label>Contact *</Label>
                    {selectedContact ? (
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <span className="font-medium">{selectedContact.name}</span>
                        {!isEditing && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedContact(null)
                              setFormData((prev) => ({ ...prev, donor_contact: "" }))
                            }}
                          >
                            Change
                          </Button>
                        )}
                      </div>
                    ) : (
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search for a contact..."
                          value={contactSearch}
                          onChange={(e) => {
                            setContactSearch(e.target.value)
                            setShowContactDropdown(true)
                          }}
                          onFocus={() => setShowContactDropdown(true)}
                          className={`pl-9 ${errors.donor_contact ? "border-destructive" : ""}`}
                        />
                        {showContactDropdown && contactResults && contactResults.length > 0 && (
                          <div className="absolute z-10 w-full mt-1 bg-background border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                            {contactResults.map((contact) => (
                              <button
                                key={contact.id}
                                type="button"
                                className="w-full px-4 py-2 text-left hover:bg-muted"
                                onClick={() => handleContactSelect(contact)}
                              >
                                <div className="font-medium">{contact.full_name}</div>
                                {contact.email && (
                                  <div className="text-sm text-muted-foreground">{contact.email}</div>
                                )}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    {errors.donor_contact && (
                      <p className="text-sm text-destructive">{errors.donor_contact}</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Pledge Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Pledge Details</CardTitle>
                  <CardDescription>Amount, frequency, and status of the pledge</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="amount">Amount *</Label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                        <Input
                          id="amount"
                          name="amount"
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.amount}
                          onChange={handleChange}
                          className={`pl-7 ${errors.amount ? "border-destructive" : ""}`}
                          placeholder="0.00"
                        />
                      </div>
                      {errors.amount && (
                        <p className="text-sm text-destructive">{errors.amount}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label>Frequency</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {recurringGiftFrequencyLabels[formData.frequency]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(recurringGiftFrequencyLabels) as RecurringGiftFrequency[]).map((f) => (
                            <DropdownMenuItem
                              key={f}
                              onClick={() => setFormData((prev) => ({ ...prev, frequency: f }))}
                            >
                              {recurringGiftFrequencyLabels[f]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Status</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {recurringGiftStatusLabels[formData.status]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(recurringGiftStatusLabels) as RecurringGiftStatus[]).map((s) => (
                            <DropdownMenuItem
                              key={s}
                              onClick={() => setFormData((prev) => ({ ...prev, status: s }))}
                            >
                              {recurringGiftStatusLabels[s]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="start_date">Start Date *</Label>
                      <Input
                        id="start_date"
                        name="start_date"
                        type="date"
                        value={formData.start_date}
                        onChange={handleChange}
                        className={errors.start_date ? "border-destructive" : ""}
                      />
                      {errors.start_date && (
                        <p className="text-sm text-destructive">{errors.start_date}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="end_date">End Date (optional)</Label>
                      <Input
                        id="end_date"
                        name="end_date"
                        type="date"
                        value={formData.end_date}
                        onChange={handleChange}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                  <CardDescription>Additional information about this pledge</CardDescription>
                </CardHeader>
                <CardContent>
                  <textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows={4}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Add any description about this pledge..."
                  />
                </CardContent>
              </Card>

              {/* Actions */}
              <div className="flex justify-end gap-4">
                <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : isEditing ? "Save Changes" : "Create Pledge"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </Container>
    </Section>
  )
}
