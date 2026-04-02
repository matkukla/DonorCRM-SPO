import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { CheckCircle, AlertTriangle, Info, X, ChevronDown, ChevronUp, RefreshCw } from "lucide-react"
import type { REImportResponse } from "@/api/imports"

interface ImportResultBannerProps {
  result: REImportResponse
  onDismiss?: () => void
  onReimport?: () => void
  isReimporting?: boolean
}

function SkipDetailsCollapsible({ result }: { result: REImportResponse }) {
  const [open, setOpen] = useState(false)
  const skippedDetails = result.summary?.skipped_details ?? []

  if (skippedDetails.length === 0) return null

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-3">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
          {open ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
          {open ? "Hide" : "Show"} skip details ({skippedDetails.length})
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 max-h-60 overflow-y-auto space-y-1 text-sm">
          {skippedDetails.map((detail, index) => (
            <div
              key={index}
              className="flex items-start gap-2 text-muted-foreground"
            >
              <span className="shrink-0">Row {detail.row}:</span>
              <span>
                {detail.contact_name}
                {detail.constituent_id && ` (ID: ${detail.constituent_id})`}
                {" \u2014 "}matched by {detail.match_type}, all fields already populated
              </span>
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function ImportResultBanner({ result, onDismiss, onReimport, isReimporting }: ImportResultBannerProps) {
  const [errorsOpen, setErrorsOpen] = useState(false)

  // Duplicate state
  if (result.is_duplicate) {
    return (
      <div className="relative p-4 rounded-lg bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800">
        {onDismiss && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-2 right-2 h-6 w-6"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
        <div className="flex items-center gap-2">
          <Badge variant="info" className="gap-1">
            <Info className="h-3 w-3" />
            Already Processed
          </Badge>
        </div>
        <p className="text-sm mt-2 text-blue-800 dark:text-blue-200">
          This file has been imported before. No changes were made.
        </p>
        {onReimport && (
          <Button
            variant="outline"
            size="sm"
            className="mt-3 gap-1"
            onClick={onReimport}
            disabled={isReimporting}
          >
            {isReimporting ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
            Reimport &amp; Update
          </Button>
        )}
      </div>
    )
  }

  // Success state (no errors)
  if (result.error_count === 0) {
    return (
      <div className="relative p-4 rounded-lg bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-800">
        {onDismiss && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-2 right-2 h-6 w-6"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
        <div className="flex items-center gap-2">
          <Badge variant="success" className="gap-1">
            <CheckCircle className="h-3 w-3" />
            Success
          </Badge>
        </div>
        <div className="mt-2 flex gap-4 text-sm">
          <span>
            <span className="font-medium">{result.created_count}</span> created
          </span>
          <span>
            <span className="font-medium">{result.updated_count}</span> updated
          </span>
          {result.skipped_count > 0 && (
            <span>
              <span className="font-medium">{result.skipped_count}</span> skipped
            </span>
          )}
        </div>
        <SkipDetailsCollapsible result={result} />
      </div>
    )
  }

  // Partial success state (has errors)
  const errors = result.summary?.errors ?? []

  return (
    <div className="relative p-4 rounded-lg bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800">
      {onDismiss && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2 h-6 w-6"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          <X className="h-3 w-3" />
        </Button>
      )}
      <div className="flex items-center gap-2">
        <Badge variant="warning" className="gap-1">
          <AlertTriangle className="h-3 w-3" />
          Partial Success
        </Badge>
      </div>
      <div className="mt-2 flex gap-4 text-sm">
        <span>
          <span className="font-medium">{result.created_count}</span> created
        </span>
        <span>
          <span className="font-medium">{result.updated_count}</span> updated
        </span>
        {result.skipped_count > 0 && (
          <span>
            <span className="font-medium">{result.skipped_count}</span> skipped
          </span>
        )}
        <span className="text-destructive">
          <span className="font-medium">{result.error_count}</span> errors
        </span>
      </div>

      {errors.length > 0 && (
        <Collapsible open={errorsOpen} onOpenChange={setErrorsOpen} className="mt-3">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
              {errorsOpen ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
              {errorsOpen ? "Hide" : "Show"} error details ({errors.length})
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 max-h-60 overflow-y-auto space-y-1 text-sm">
              {errors.map((err, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 text-muted-foreground"
                >
                  <span className="text-destructive shrink-0">Row {err.row}:</span>
                  <span>{err.error}</span>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}

      <SkipDetailsCollapsible result={result} />
    </div>
  )
}
