import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Upload, AlertTriangle, CheckCircle, XCircle, Clock } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import type { ImportType, LatestImportRun, DependencyCounts } from "@/api/imports"

interface SPOImportTileProps {
  importType: ImportType
  title: string
  description: string
  latestRun: LatestImportRun | null
  dependencyCounts: DependencyCounts
  onImportClick: () => void
  isLoading?: boolean
}

const IMPORT_TYPE_ORDER: Record<ImportType, number> = {
  funds: 1,
  entities: 2,
  transactions: 3,
  pledges: 4,
}

function getStatusBadge(status: string | undefined) {
  if (!status) {
    return (
      <Badge variant="secondary" className="gap-1">
        <Clock className="h-3 w-3" />
        Never imported
      </Badge>
    )
  }

  switch (status) {
    case "completed":
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle className="h-3 w-3" />
          Completed
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      )
    case "importing":
      return (
        <Badge variant="warning" className="gap-1">
          <Clock className="h-3 w-3" />
          In Progress
        </Badge>
      )
    default:
      return (
        <Badge variant="secondary" className="gap-1">
          {status}
        </Badge>
      )
  }
}

function getDependencyWarning(
  importType: ImportType,
  dependencyCounts: DependencyCounts
): { show: boolean; message: string } {
  if (importType === "transactions") {
    const missingDeps: string[] = []
    if (dependencyCounts.funds_count === 0) missingDeps.push("Funds")
    if (dependencyCounts.entities_with_external_id_count === 0) missingDeps.push("Entities")

    if (missingDeps.length > 0) {
      return {
        show: true,
        message: `No ${missingDeps.join(" or ")} imported yet. Transactions require valid entity_id and fund_id references.`,
      }
    }
  }

  if (importType === "pledges") {
    if (dependencyCounts.entities_with_external_id_count === 0) {
      return {
        show: true,
        message: "No Entities imported yet. Pledges require valid entity_id references.",
      }
    }
  }

  return { show: false, message: "" }
}

export function SPOImportTile({
  importType,
  title,
  description,
  latestRun,
  dependencyCounts,
  onImportClick,
  isLoading = false,
}: SPOImportTileProps) {
  const warning = getDependencyWarning(importType, dependencyCounts)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm font-normal">
                {IMPORT_TYPE_ORDER[importType]}.
              </span>
              {title}
            </CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
          {getStatusBadge(latestRun?.status)}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Last import info */}
        {latestRun && (
          <div className="text-sm text-muted-foreground">
            <p>
              Last import:{" "}
              <span className="font-medium text-foreground">
                {formatDistanceToNow(new Date(latestRun.created_at), { addSuffix: true })}
              </span>
            </p>
            <p className="mt-1">
              {latestRun.created_count} created, {latestRun.updated_count} updated
              {latestRun.error_count > 0 && (
                <span className="text-destructive">, {latestRun.error_count} errors</span>
              )}
            </p>
          </div>
        )}

        {/* Dependency warning */}
        {warning.show && (
          <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-yellow-800">{warning.message}</p>
          </div>
        )}

        {/* Import button */}
        <Button onClick={onImportClick} disabled={isLoading} className="w-full">
          <Upload className="h-4 w-4 mr-2" />
          Import {title}
        </Button>
      </CardContent>
    </Card>
  )
}
