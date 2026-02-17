import { useState } from "react"
import { Download, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { apiClient } from "@/api/client"

interface ExportCSVButtonProps {
  /** Export endpoint URL, e.g. "/contacts/export/csv/" */
  exportUrl: string
  /** Current filter params to forward to the export endpoint */
  queryParams: Record<string, string>
  /** Override filename (optional; server Content-Disposition takes priority) */
  filename?: string
  disabled?: boolean
}

/**
 * Button that triggers a CSV download from the given export endpoint,
 * forwarding the current filter params. Shows a loading spinner during download.
 */
export function ExportCSVButton({
  exportUrl,
  queryParams,
  filename = "export.csv",
  disabled,
}: ExportCSVButtonProps) {
  const [loading, setLoading] = useState(false)

  const handleExport = async () => {
    setLoading(true)
    try {
      const response = await apiClient.get(exportUrl, {
        params: queryParams,
        responseType: "blob",
      })

      // Extract filename from Content-Disposition header if available
      const disposition = response.headers["content-disposition"]
      let resolvedFilename = filename
      if (disposition) {
        const match = disposition.match(/filename="?([^";\n]+)"?/)
        if (match?.[1]) {
          resolvedFilename = match[1]
        }
      }

      // Trigger browser download (matches existing pattern in api/imports.ts)
      const url = window.URL.createObjectURL(
        new Blob([response.data], { type: "text/csv" })
      )
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", resolvedFilename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      toast.error("Failed to export CSV")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={handleExport}
      disabled={disabled || loading}
    >
      {loading ? (
        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
      ) : (
        <Download className="mr-1 h-4 w-4" />
      )}
      Export CSV
    </Button>
  )
}
