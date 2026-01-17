import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Download, FileDown, CheckCircle } from "lucide-react"

interface ExportCardProps {
  title: string
  description: string
  scopeDescription: string
  onExport: (startDate?: string, endDate?: string) => Promise<void>
  isExporting: boolean
  showDateFilter?: boolean
}

export function ExportCard({
  title,
  description,
  scopeDescription,
  onExport,
  isExporting,
  showDateFilter = false,
}: ExportCardProps) {
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleExport = async () => {
    setError(null)
    setSuccess(false)
    try {
      await onExport(startDate || undefined, endDate || undefined)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { detail?: string } } }
      setError(apiError.response?.data?.detail || "Export failed. Please try again.")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileDown className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scope Info */}
        <div className="p-3 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground">{scopeDescription}</p>
        </div>

        {/* Date Filter (for donations) */}
        {showDateFilter && (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date (optional)</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">End Date (optional)</Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm">Export downloaded successfully</span>
          </div>
        )}

        {/* Export Button */}
        <Button onClick={handleExport} disabled={isExporting} className="w-full">
          <Download className="h-4 w-4 mr-2" />
          {isExporting ? "Exporting..." : "Export to CSV"}
        </Button>
      </CardContent>
    </Card>
  )
}
