import { Download } from "lucide-react"
import { ExportCard } from "./ExportCard"
import { useExportContacts, useExportDonations } from "@/hooks/useImports"

export function ExportSection() {
  const exportContactsMutation = useExportContacts()
  const exportDonationsMutation = useExportDonations()

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
          scopeDescription="Exports your contacts only."
          onExport={handleExportContacts}
          isExporting={exportContactsMutation.isPending}
        />

        <ExportCard
          title="Export Donations"
          description="Download donations as a CSV file"
          scopeDescription="Exports donations for your contacts only."
          onExport={handleExportDonations}
          isExporting={exportDonationsMutation.isPending}
          showDateFilter
        />
      </div>
    </div>
  )
}
