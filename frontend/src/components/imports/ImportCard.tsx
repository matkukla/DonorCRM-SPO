import { useState, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  X,
  Download,
} from "lucide-react"
import type { ImportResult } from "@/api/imports"

interface ImportCardProps {
  title: string
  description: string
  templateColumns: string
  onImport: (file: File, validateOnly: boolean) => Promise<ImportResult>
  onDownloadTemplate: () => Promise<void>
  isImporting: boolean
  isDownloadingTemplate: boolean
}

export function ImportCard({
  title,
  description,
  templateColumns,
  onImport,
  onDownloadTemplate,
  isImporting,
  isDownloadingTemplate,
}: ImportCardProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.name.endsWith(".csv")) {
      setFile(droppedFile)
      setResult(null)
      setError(null)
    } else {
      setError("Please upload a CSV file")
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.name.endsWith(".csv")) {
      setFile(selectedFile)
      setResult(null)
      setError(null)
    } else {
      setError("Please upload a CSV file")
    }
  }

  const handleValidate = async () => {
    if (!file) return
    setError(null)
    try {
      const importResult = await onImport(file, true)
      setResult(importResult)
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { detail?: string } } }
      setError(apiError.response?.data?.detail || "Validation failed. Please check your file format.")
    }
  }

  const handleImport = async () => {
    if (!file) return
    setError(null)
    try {
      const importResult = await onImport(file, false)
      setResult(importResult)
      if (importResult.error_count === 0) {
        setFile(null)
      }
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { detail?: string } } }
      setError(apiError.response?.data?.detail || "Import failed. Please check your file format.")
    }
  }

  const handleClearFile = () => {
    setFile(null)
    setResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Template Download */}
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div>
            <p className="text-sm font-medium">Download Template</p>
            <p className="text-xs text-muted-foreground">
              Columns: {templateColumns}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={onDownloadTemplate}
            disabled={isDownloadingTemplate}
          >
            <Download className="h-4 w-4 mr-2" />
            Template
          </Button>
        </div>

        {/* File Upload */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragging
              ? "border-primary bg-primary/5"
              : file
              ? "border-green-500 bg-green-50"
              : "border-border hover:border-primary/50"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="h-8 w-8 text-green-600" />
              <div className="text-left">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleClearFile}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <>
              <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground mb-2">
                Drag and drop a CSV file here, or
              </p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse Files
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileSelect}
              />
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className={`p-4 rounded-lg ${
            result.error_count === 0 ? "bg-green-50 border border-green-200" : "bg-yellow-50 border border-yellow-200"
          }`}>
            <div className="flex items-center gap-4 mb-2">
              {result.error_count === 0 ? (
                <Badge variant="success" className="gap-1">
                  <CheckCircle className="h-3 w-3" />
                  Success
                </Badge>
              ) : (
                <Badge variant="warning" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Partial Success
                </Badge>
              )}
              <span className="text-sm">
                <span className="font-medium">{result.imported_count}</span> records imported
                {result.error_count > 0 && (
                  <>, <span className="font-medium text-destructive">{result.error_count}</span> errors</>
                )}
              </span>
            </div>
            {result.errors.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-medium mb-2">Errors:</p>
                <ul className="text-sm text-muted-foreground space-y-1 max-h-32 overflow-y-auto">
                  {result.errors.slice(0, 10).map((err, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-destructive">•</span>
                      {err}
                    </li>
                  ))}
                  {result.errors.length > 10 && (
                    <li className="text-muted-foreground italic">
                      ...and {result.errors.length - 10} more errors
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={handleValidate}
            disabled={!file || isImporting}
            className="flex-1"
          >
            Validate
          </Button>
          <Button
            onClick={handleImport}
            disabled={!file || isImporting}
            className="flex-1"
          >
            {isImporting ? "Importing..." : "Import"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
