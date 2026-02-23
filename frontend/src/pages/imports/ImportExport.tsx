import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "@/providers/AuthProvider"
import { REImportSection } from "@/components/imports/REImportSection"
import { SmartsheetSection } from "@/components/imports/SmartsheetSection"
import { GenericImportSection } from "@/components/imports/GenericImportSection"
import { ExportSection } from "@/components/imports/ExportSection"
import { ImportHistorySection } from "@/components/imports/ImportHistorySection"

export default function ImportExport() {
  const { user } = useAuth()

  const isAdmin = user?.role === "admin"

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Import & Export</h1>
            <p className="text-muted-foreground mt-1">
              Import data from Raiser's Edge, Smartsheet, or CSV files, and export your data
            </p>
          </div>

          <div className="space-y-10">
            {/* RE Imports - Admin only */}
            {isAdmin && <REImportSection />}

            {/* Smartsheet - Admin only */}
            {isAdmin && <SmartsheetSection />}

            {/* Generic CSV Import - visible to all (placeholder) */}
            <GenericImportSection />

            <Separator />

            {/* Exports - all authenticated users */}
            <ExportSection />

            <Separator />

            {/* Import History - all authenticated users */}
            <ImportHistorySection />
          </div>
        </div>
      </Container>
    </Section>
  )
}
