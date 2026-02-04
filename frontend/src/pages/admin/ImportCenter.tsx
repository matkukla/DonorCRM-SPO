import { useState } from "react"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, Loader2 } from "lucide-react"
import { useLatestImports } from "@/hooks/useImports"
import { SPOImportTile } from "@/components/imports/SPOImportTile"
import type { ImportType } from "@/api/imports"

const IMPORT_CONFIGS: Array<{
  type: ImportType
  title: string
  description: string
}> = [
  {
    type: "funds",
    title: "Funds",
    description: "Import fund/account definitions from SPO",
  },
  {
    type: "entities",
    title: "Entities",
    description: "Import contacts from SPO entities",
  },
  {
    type: "transactions",
    title: "Transactions",
    description: "Import donations from SPO transactions",
  },
  {
    type: "pledges",
    title: "Pledges",
    description: "Import pledges/commitments from SPO",
  },
]

/**
 * Import Center - Admin-only page for SPO CSV imports
 *
 * Displays 4 tiles for import types: Funds, Entities, Transactions, Pledges
 * Shows recommended import order and last import status for each type.
 */
export default function ImportCenter() {
  const { data, isLoading, isError } = useLatestImports()
  const [activeImportType, setActiveImportType] = useState<ImportType | null>(null)

  const handleImportClick = (importType: ImportType) => {
    setActiveImportType(importType)
    // Dialog will be added in Plan 12-04
    console.log("Import clicked:", importType)
  }

  const handleDialogClose = () => {
    setActiveImportType(null)
  }

  if (isLoading) {
    return (
      <Section>
        <Container>
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </Container>
      </Section>
    )
  }

  if (isError) {
    return (
      <Section>
        <Container>
          <div className="text-center py-8">
            <p className="text-destructive">Failed to load import status. Please try again.</p>
          </div>
        </Container>
      </Section>
    )
  }

  const dependencyCounts = data?.dependency_counts ?? {
    funds_count: 0,
    entities_with_external_id_count: 0,
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Import Center</h1>
            <p className="text-muted-foreground mt-1">
              Import SPO CSV files for Funds, Entities, Transactions, and Pledges
            </p>
          </div>

          {/* Import Order Guidance */}
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Upload className="h-4 w-4" />
                Recommended Import Order
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                For best results, import files in this order:{" "}
                <span className="font-medium text-foreground">
                  Funds → Entities → Transactions → Pledges
                </span>
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Transactions require valid Fund and Entity references. Pledges require valid Entity references.
              </p>
            </CardContent>
          </Card>

          {/* Import Tiles */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {IMPORT_CONFIGS.map((config) => (
              <SPOImportTile
                key={config.type}
                importType={config.type}
                title={config.title}
                description={config.description}
                latestRun={data?.[config.type] ?? null}
                dependencyCounts={dependencyCounts}
                onImportClick={() => handleImportClick(config.type)}
              />
            ))}
          </div>

          {/* TODO: Import dialog will be added in Plan 12-04 */}
          {activeImportType && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <Card className="w-full max-w-md">
                <CardContent className="pt-6">
                  <p className="text-center">
                    Import dialog for {activeImportType} coming in Plan 12-04...
                  </p>
                  <button
                    onClick={handleDialogClose}
                    className="mt-4 w-full py-2 bg-muted rounded"
                  >
                    Close
                  </button>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </Container>
    </Section>
  )
}
