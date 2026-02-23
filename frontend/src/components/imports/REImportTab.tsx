import { useState } from "react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, Upload } from "lucide-react"
import { FileDropZone } from "./FileDropZone"
import { ImportResultBanner } from "./ImportResultBanner"
import { CSVHeaderReference } from "./CSVHeaderReference"
import { useREImport } from "@/hooks/useImports"
import type { REImportType, REImportResponse } from "@/api/imports"

interface REImportTabProps {
  importType: REImportType
  stepNumber: number
  totalSteps: number
  title: string
  description: string
}

export function REImportTab({
  importType,
  stepNumber,
  totalSteps,
  title,
  description,
}: REImportTabProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<REImportResponse | null>(null)

  const mutation = useREImport(importType)

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    setResult(null)
  }

  const handleClear = () => {
    setSelectedFile(null)
    setResult(null)
  }

  const handleImport = async () => {
    if (!selectedFile) return

    try {
      const importResult = await mutation.mutateAsync(selectedFile)
      setResult(importResult)
      setSelectedFile(null)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      toast.error(error.response?.data?.detail || `${title} import failed. Please try again.`)
    }
  }

  return (
    <div className="space-y-4">
      {/* Step indicator and description */}
      <div>
        <Badge variant="secondary" className="mb-2">
          Step {stepNumber} of {totalSteps}
        </Badge>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>

      {/* File upload zone */}
      <FileDropZone
        onFileSelect={handleFileSelect}
        accept=".csv"
        selectedFile={selectedFile}
        onClear={handleClear}
        disabled={mutation.isPending}
      />

      {/* Import button */}
      <Button
        onClick={handleImport}
        disabled={!selectedFile || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Importing...
          </>
        ) : (
          <>
            <Upload className="h-4 w-4 mr-2" />
            Import {title}
          </>
        )}
      </Button>

      {/* Result banner */}
      {result && (
        <ImportResultBanner
          result={result}
          onDismiss={() => setResult(null)}
        />
      )}

      {/* CSV header reference */}
      <CSVHeaderReference importType={importType} />
    </div>
  )
}
