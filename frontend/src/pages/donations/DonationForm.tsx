import { useState, useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useGift, useCreateGift, useUpdateGift } from "@/hooks/useGifts"
import { useSearchContacts } from "@/hooks/useContacts"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft, Search } from "lucide-react"

interface FormData {
  donor_contact: string
  amount: string  // Dollar string the user types
  gift_date: string
  description: string
}

export default function DonationForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const preselectedContactId = searchParams.get("contact")

  const { data: existingGift, isLoading: isLoadingGift } = useGift(id || null)
  const createMutation = useCreateGift()
  const updateMutation = useUpdateGift()

  const [contactSearch, setContactSearch] = useState("")
  const [selectedContact, setSelectedContact] = useState<{ id: string; name: string } | null>(null)
  const [showContactDropdown, setShowContactDropdown] = useState(false)

  const { data: contactResults } = useSearchContacts(contactSearch)

  const [formData, setFormData] = useState<FormData>({
    donor_contact: preselectedContactId || "",
    amount: "",
    gift_date: new Date().toISOString().split("T")[0],
    description: "",
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existingGift) {
      setFormData({
        donor_contact: existingGift.donor_contact,
        amount: existingGift.amount_dollars,
        gift_date: existingGift.gift_date,
        description: existingGift.description || "",
      })
      setSelectedContact({
        id: existingGift.donor_contact,
        name: existingGift.donor_contact_name,
      })
    }
  }, [existingGift])

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
    if (!formData.gift_date) {
      newErrors.gift_date = "Date is required"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    const amount_cents = Math.round(parseFloat(formData.amount) * 100)
    const submitData = {
      donor_contact: formData.donor_contact,
      amount_cents,
      gift_date: formData.gift_date,
      description: formData.description,
    }

    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: id!, data: submitData })
      } else {
        await createMutation.mutateAsync(submitData)
      }
      navigate("/donations")
    } catch {
      // Error is handled by the mutation
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (isEditing && isLoadingGift) {
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
                            setFormData((prev) => ({ ...prev, donor_contact: "" }))
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
                      <Label htmlFor="gift_date">Date *</Label>
                      <Input
                        id="gift_date"
                        name="gift_date"
                        type="date"
                        value={formData.gift_date}
                        onChange={handleChange}
                        className={errors.gift_date ? "border-destructive" : ""}
                      />
                      {errors.gift_date && (
                        <p className="text-sm text-destructive">{errors.gift_date}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle>Description</CardTitle>
                  <CardDescription>Additional information about this donation</CardDescription>
                </CardHeader>
                <CardContent>
                  <textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows={4}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Add a description for this donation..."
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
