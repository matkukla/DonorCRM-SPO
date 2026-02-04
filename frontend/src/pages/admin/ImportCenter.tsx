import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload } from "lucide-react"

/**
 * Import Center - Admin-only page for SPO CSV imports
 *
 * Displays 4 tiles for import types: Funds, Entities, Transactions, Pledges
 * Shows recommended import order and last import status for each type.
 */
export default function ImportCenter() {
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

          {/* Placeholder for tiles - will be added in Plan 12-03 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Funds</CardTitle>
                <CardDescription>Import fund/account definitions</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Tile component coming soon...</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Entities</CardTitle>
                <CardDescription>Import contacts from SPO entities</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Tile component coming soon...</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Transactions</CardTitle>
                <CardDescription>Import donations from SPO transactions</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Tile component coming soon...</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Pledges</CardTitle>
                <CardDescription>Import pledges/commitments</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Tile component coming soon...</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </Container>
    </Section>
  )
}
