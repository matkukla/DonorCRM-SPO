import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ImportCard } from "@/components/imports/ImportCard"
import { ExportCard } from "@/components/imports/ExportCard"
import { useAuth } from "@/providers/AuthProvider"
import {
  useImportContacts,
  useImportDonations,
  useExportContacts,
  useExportDonations,
  useDownloadContactTemplate,
  useDownloadDonationTemplate,
} from "@/hooks/useImports"
import { Upload, Download } from "lucide-react"

export default function ImportExport() {
  const { user } = useAuth()

  const importContactsMutation = useImportContacts()
  const importDonationsMutation = useImportDonations()
  const exportContactsMutation = useExportContacts()
  const exportDonationsMutation = useExportDonations()
  const downloadContactTemplateMutation = useDownloadContactTemplate()
  const downloadDonationTemplateMutation = useDownloadDonationTemplate()

  const isAdmin = user?.role === "admin"
  const isFinanceOrAdmin = user?.role === "admin" || user?.role === "finance"

  const handleImportContacts = async (file: File, validateOnly: boolean) => {
    return importContactsMutation.mutateAsync({ file, validateOnly })
  }

  const handleImportDonations = async (file: File, validateOnly: boolean) => {
    return importDonationsMutation.mutateAsync({ file, validateOnly })
  }

  const handleExportContacts = async () => {
    return exportContactsMutation.mutateAsync()
  }

  const handleExportDonations = async (startDate?: string, endDate?: string) => {
    return exportDonationsMutation.mutateAsync({ startDate, endDate })
  }

  const handleDownloadContactTemplate = async () => {
    return downloadContactTemplateMutation.mutateAsync()
  }

  const handleDownloadDonationTemplate = async () => {
    return downloadDonationTemplateMutation.mutateAsync()
  }

  const getContactsExportScope = () => {
    if (isAdmin) {
      return "Exports all contacts in the system."
    }
    return "Exports your contacts only."
  }

  const getDonationsExportScope = () => {
    if (isAdmin || user?.role === "finance") {
      return "Exports all donations in the system."
    }
    return "Exports donations for your contacts only."
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Import & Export</h1>
            <p className="text-muted-foreground mt-1">
              Bulk import contacts and donations from CSV files, or export data
            </p>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="import" className="space-y-6">
            <TabsList>
              <TabsTrigger value="import" className="gap-2">
                <Upload className="h-4 w-4" />
                Import
              </TabsTrigger>
              <TabsTrigger value="export" className="gap-2">
                <Download className="h-4 w-4" />
                Export
              </TabsTrigger>
            </TabsList>

            {/* Import Tab */}
            <TabsContent value="import" className="space-y-6">
              {!isAdmin && !isFinanceOrAdmin && (
                <div className="p-4 bg-muted rounded-lg text-center">
                  <p className="text-muted-foreground">
                    You don't have permission to import data. Contact an administrator if you need to import contacts or donations.
                  </p>
                </div>
              )}

              <div className="grid gap-6 md:grid-cols-2">
                {/* Contact Import - Admin only */}
                {isAdmin && (
                  <ImportCard
                    title="Import Contacts"
                    description="Upload a CSV file to bulk import contacts"
                    templateColumns="first_name*, last_name*, email, phone, street_address, city, state, postal_code, country, notes"
                    onImport={handleImportContacts}
                    onDownloadTemplate={handleDownloadContactTemplate}
                    isImporting={importContactsMutation.isPending}
                    isDownloadingTemplate={downloadContactTemplateMutation.isPending}
                  />
                )}

                {/* Donation Import - Finance/Admin */}
                {isFinanceOrAdmin && (
                  <ImportCard
                    title="Import Donations"
                    description="Upload a CSV file to bulk import donations"
                    templateColumns="contact_email OR (contact_first_name + contact_last_name)*, amount*, date*, donation_type, payment_method, external_id, notes"
                    onImport={handleImportDonations}
                    onDownloadTemplate={handleDownloadDonationTemplate}
                    isImporting={importDonationsMutation.isPending}
                    isDownloadingTemplate={downloadDonationTemplateMutation.isPending}
                  />
                )}
              </div>
            </TabsContent>

            {/* Export Tab */}
            <TabsContent value="export" className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Contact Export - All authenticated users */}
                <ExportCard
                  title="Export Contacts"
                  description="Download all contacts as a CSV file"
                  scopeDescription={getContactsExportScope()}
                  onExport={handleExportContacts}
                  isExporting={exportContactsMutation.isPending}
                />

                {/* Donation Export - All authenticated users */}
                <ExportCard
                  title="Export Donations"
                  description="Download donations as a CSV file"
                  scopeDescription={getDonationsExportScope()}
                  onExport={handleExportDonations}
                  isExporting={exportDonationsMutation.isPending}
                  showDateFilter
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </Container>
    </Section>
  )
}
