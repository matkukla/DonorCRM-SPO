import { FileSpreadsheet } from "lucide-react"
import { MPDImportTile } from "./MPDImportTile"

export function SmartsheetSection() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5 text-muted-foreground" />
          Smartsheet Import
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Upload monthly MPD Dashboard Report
        </p>
      </div>

      <div className="max-w-lg">
        <MPDImportTile />
      </div>
    </div>
  )
}
