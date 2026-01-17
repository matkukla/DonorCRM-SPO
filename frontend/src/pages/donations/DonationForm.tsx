import { useState, useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useDonation, useCreateDonation, useUpdateDonation } from "@/hooks/useDonations"
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
import type { DonationType, PaymentMethod, DonationCreate } from "@/api/donations"
import { donationTypeLabels, paymentMethodLabels } from "@/api/donations"

export default function DonationForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const preselectedContactId = searchParams.get("contact")

  const { data: existingDonation, isLoading: isLoadingDonation } = useDonation(id || "")
  const createMutation = useCreateDonation()
  const updateMutation = useUpdateDonation()

  const [contactSearch, setContactSearch] = useState("")
  const [selectedContact, setSelectedContact] = useState<{ id: string; name: string } | null>(null)
  const [showContactDropdown, setShowContactDropdown] = useState(false)

  const { data: contactResults } = useSearchContacts(contactSearch)

  const [formData, setFormData] = useState<DonationCreate>({
    contact: preselectedContactId || "",
    amount: "",
    date: new Date().toISOString().split("T")[0],
    donation_type: "one_time",
    payment_method: "check",
    notes: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingDonation) {
      setFormData({
        contact: existingDonation.contact,
        amount: existingDonation.amount,
        date: existingDonation.date,
        donation_type: existingDonation.donation_type,
        payment_method: existingDonation.payment_method,
        notes: existingDonation.notes || "",
      })
      setSelectedContact({
        id: existingDonation.contact,
        name: existingDonation.contact_name,
      })
    }
  }, [existingDonation])

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
    if (!formData.date) {
      newErrors.date = "Date is required"
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
        navigate(`/donations/${id}`)
      } else {
        const newDonation = await createMutation.mutateAsync(formData)
        navigate(`/donations/${newDonation.id}`)
      }
    } catch {
      // Error is handled by the mutation
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (isEditing && isLoadingDonation) {
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
              {isEditing ? "Edit Donation" : "Record Donation"}
            </h1>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {/* Contact Selection */}
              <Card>
                <CardHeader>
                  <CardTitle>Donor</CardTitle>
                  <CardDescription>Select the donor for this donation</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label>Contact *</Label>
                    {selectedContact ? (
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <span className="font-medium">{selectedContact.name}</span>
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

              {/* Donation Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Donation Details</CardTitle>
                  <CardDescription>Amount and date of the donation</CardDescription>
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
                      <Label htmlFor="date">Date *</Label>
                      <Input
                        id="date"
                        name="date"
                        type="date"
                        value={formData.date}
                        onChange={handleChange}
                        className={errors.date ? "border-destructive" : ""}
                      />
                      {errors.date && (
                        <p className="text-sm text-destructive">{errors.date}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Donation Type</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {donationTypeLabels[formData.donation_type || "one_time"]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(donationTypeLabels) as DonationType[]).map((t) => (
                            <DropdownMenuItem
                              key={t}
                              onClick={() => setFormData((prev) => ({ ...prev, donation_type: t }))}
                            >
                              {donationTypeLabels[t]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <div className="space-y-2">
                      <Label>Payment Method</Label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="secondary" className="w-full justify-between">
                            {paymentMethodLabels[formData.payment_method || "check"]}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-full">
                          {(Object.keys(paymentMethodLabels) as PaymentMethod[]).map((p) => (
                            <DropdownMenuItem
                              key={p}
                              onClick={() => setFormData((prev) => ({ ...prev, payment_method: p }))}
                            >
                              {paymentMethodLabels[p]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Notes */}
              <Card>
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                  <CardDescription>Additional information about this donation</CardDescription>
                </CardHeader>
                <CardContent>
                  <textarea
                    id="notes"
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    rows={4}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Add any notes about this donation..."
                  />
                </CardContent>
              </Card>

              {/* Actions */}
              <div className="flex justify-end gap-4">
                <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Saving..." : isEditing ? "Save Changes" : "Record Donation"}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </Container>
    </Section>
  )
}
