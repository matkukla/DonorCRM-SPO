import { Download } from "lucide-react"
import { ExportCard } from "./ExportCard"
import { useAuth } from "@/providers/AuthProvider"
import { useExportContacts, useExportDonations } from "@/hooks/useImports"

export function ExportSection() {
  const { user } = useAuth()
  const exportContactsMutation = useExportContacts()
  const exportDonationsMutation = useExportDonations()

  const isAdmin = user?.role === "admin"
  const isFinanceOrAdmin = user?.role === "admin" || user?.role === "finance"

  const getContactsExportScope = () => {
    if (isAdmin) {
      return "Exports all contacts in the system."
    }
    return "Exports your contacts only."
  }

  const getDonationsExportScope = () => {
    if (isFinanceOrAdmin) {
      return "Exports all donations in the system."
    }
    return "Exports donations for your contacts only."
  }

  const handleExportContacts = async () => {
    return exportContactsMutation.mutateAsync()
  }

  const handleExportDonations = async (startDate?: string, endDate?: string) => {
    return exportDonationsMutation.mutateAsync({ startDate, endDate })
  }

  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Download className="h-5 w-5 text-muted-foreground" />
          Export Data
        </h2>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <ExportCard
          title="Export Contacts"
          description="Download all contacts as a CSV file"
          scopeDescription={getContactsExportScope()}
          onExport={handleExportContacts}
          isExporting={exportContactsMutation.isPending}
        />

        <ExportCard
          title="Export Donations"
          description="Download donations as a CSV file"
          scopeDescription={getDonationsExportScope()}
          onExport={handleExportDonations}
          isExporting={exportDonationsMutation.isPending}
          showDateFilter
        />
      </div>
    </div>
  )
}
