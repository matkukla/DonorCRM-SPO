import { useState } from "react"
import { toast } from "sonner"
import { format } from "date-fns"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileSpreadsheet, Loader2, Upload } from "lucide-react"
import { useMPDUpload, useMPDUploadHistory } from "@/hooks/useMPD"
import { MPDResultsDialog } from "./MPDResultsDialog"
import { FileDropZone } from "./FileDropZone"
import type { MPDUploadResult } from "@/api/mpd"

export function MPDImportTile() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadResult, setUploadResult] = useState<MPDUploadResult | null>(null)
  const [showResults, setShowResults] = useState(false)

  const uploadMutation = useMPDUpload()
  const { data: uploadHistory } = useMPDUploadHistory()

  const handleUpload = async () => {
    if (!selectedFile) return

    try {
      const result = await uploadMutation.mutateAsync(selectedFile)
      setUploadResult(result)
      setShowResults(true)
      setSelectedFile(null)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; error?: string } } }
      const message =
        error.response?.data?.detail ||
        error.response?.data?.error ||
        "Upload failed. Please try again."
      toast.error(message)
    }
  }

  const handleResultsClose = () => {
    setShowResults(false)
    setUploadResult(null)
  }

  const recentUploads = uploadHistory?.slice(0, 5) ?? []

  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-muted-foreground" />
            Smartsheet MPD Report
          </CardTitle>
          <CardDescription>
            Upload monthly MPD Dashboard Report (CSV or Excel)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* File drop zone */}
          <FileDropZone
            accept=".csv,.xlsx,.xls"
            onFileSelect={setSelectedFile}
            onClear={() => setSelectedFile(null)}
            selectedFile={selectedFile}
            disabled={uploadMutation.isPending}
          />

          {/* Upload button */}
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload
              </>
            )}
          </Button>

          {/* Recent upload history */}
          {recentUploads.length > 0 && (
            <div className="pt-2 border-t border-border">
              <p className="text-xs font-medium text-muted-foreground mb-2">Recent Uploads</p>
              <div className="space-y-1.5">
                {recentUploads.map((upload) => (
                  <div
                    key={upload.id}
                    className="flex items-center justify-between text-xs text-muted-foreground"
                  >
                    <span className="truncate max-w-[140px]" title={upload.filename}>
                      {format(new Date(upload.created_at), "MMM d, yyyy")}
                    </span>
                    <span>
                      <span className="text-green-600 dark:text-green-400">
                        {upload.matched_count} matched
                      </span>
                      {upload.unmatched_count > 0 && (
                        <span className="text-amber-600 dark:text-amber-400 ml-1.5">
                          {upload.unmatched_count} unmatched
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results dialog */}
      {uploadResult && (
        <MPDResultsDialog
          open={showResults}
          onClose={handleResultsClose}
          result={uploadResult}
        />
      )}
    </>
  )
}
