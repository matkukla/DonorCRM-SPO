import { useState, useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { usePledge, useCreatePledge, useUpdatePledge } from "@/hooks/usePledges"
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
import type { PledgeFrequency, PledgeCreate } from "@/api/pledges"
import { pledgeFrequencyLabels } from "@/api/pledges"

export default function PledgeForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const preselectedContactId = searchParams.get("contact")

  const { data: existingPledge, isLoading: isLoadingPledge } = usePledge(id || "")
  const createMutation = useCreatePledge()
  const updateMutation = useUpdatePledge()

  const [contactSearch, setContactSearch] = useState("")
  const [selectedContact, setSelectedContact] = useState<{ id: string; name: string } | null>(null)
  const [showContactDropdown, setShowContactDropdown] = useState(false)

  const { data: contactResults } = useSearchContacts(contactSearch)

  const [formData, setFormData] = useState<PledgeCreate>({
    contact: preselectedContactId || "",
    amount: "",
    frequency: "monthly",
    start_date: new Date().toISOString().split("T")[0],
    notes: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingPledge) {
      setFormData({
        contact: existingPledge.contact,
        amount: existingPledge.amount,
        frequency: existingPledge.frequency,
        start_date: existingPledge.start_date,
        end_date: existingPledge.end_date || undefined,
        notes: existingPledge.notes || "",
      })
      setSelectedContact({
        id: existingPledge.contact,
        name: existingPledge.contact_name,
      })
    }
  }, [existingPledge])

  useEffect(() => {
    if (preselectedContactId && contactResults) {
      const contact = contactResults.find((c) => c.id === preselectedContactId)
      if (contact) {
        setSelectedContact({ id: contact.id, name: contact.full_name })
        setFormData((prev) => ({ ...prev, contact: contact.id }))
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
    setFormData((prev) => ({ ...prev, contact: contact.id }))
    setContactSearch("")
    setShowContactDropdown(false)
    if (errors.contact) {
      setErrors((prev) => ({ ...prev, contact: "" }))
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.contact) {
      newErrors.contact = "Contact is required"
    }
    if (!formData.amount || parseFloat(String(formData.amount)) <= 0) {
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

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: id!, data: formData })
        navigate(`/pledges/${id}`)
      } else {
        const newPledge = await createMutation.mutateAsync(formData)
        navigate(`/pledges/${newPledge.id}`)
      }
    } catch {
      // Error is handled by the mutation
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  // Calculate monthly equivalent preview
  const getMonthlyEquivalent = () => {
    const amount = parseFloat(String(formData.amount)) || 0
    const multipliers: Record<PledgeFrequency, number> = {
      monthly: 1,
      quarterly: 1 / 3,
      semi_annual: 1 / 6,
      annual: 1 / 12,
    }
    return amount * (multipliers[formData.frequency || "monthly"] || 1)
  }

  if (isEditing && isLoadingPledge) {
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
                              setFormData((prev) => ({ ...prev, contact: "" }))
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
                          className={`pl-9 ${errors.contact ? "border-destructive" : ""}`}
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
                    {errors.contact && (
                      <p className="text-sm text-destructive">{errors.contact}</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Pledge Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Pledge Details</CardTitle>
                  <CardDescription>Amount and frequency of the pledge</CardDescription>
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
                            {pledgeFrequencyLabels[formData.frequency || "monthly"]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(pledgeFrequencyLabels) as PledgeFrequency[]).map((f) => (
                            <DropdownMenuItem
                              key={f}
                              onClick={() => setFormData((prev) => ({ ...prev, frequency: f }))}
                            >
                              {pledgeFrequencyLabels[f]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  {/* Monthly equivalent preview */}
                  {formData.amount && parseFloat(String(formData.amount)) > 0 && (
                    <div className="p-3 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        Monthly equivalent:{" "}
                        <span className="font-medium text-foreground">
                          ${getMonthlyEquivalent().toFixed(2)}/month
                        </span>
                      </p>
                    </div>
                  )}

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
                        value={formData.end_date || ""}
                        onChange={handleChange}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Notes */}
              <Card>
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                  <CardDescription>Additional information about this pledge</CardDescription>
                </CardHeader>
                <CardContent>
                  <textarea
                    id="notes"
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    rows={4}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Add any notes about this pledge..."
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
