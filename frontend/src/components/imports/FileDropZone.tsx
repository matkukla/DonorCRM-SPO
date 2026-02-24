import { useState, useRef } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Upload, FileText, X } from "lucide-react"

interface FileDropZoneProps {
  onFileSelect: (file: File) => void
  accept: string
  maxSizeMB?: number
  disabled?: boolean
  selectedFile: File | null
  onClear: () => void
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(bytes / 1024).toFixed(1)} KB`
}

export function FileDropZone({
  onFileSelect,
  accept,
  maxSizeMB = 10,
  disabled = false,
  selectedFile,
  onClear,
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const maxSizeBytes = maxSizeMB * 1024 * 1024
  const acceptExtensions = accept.split(",").map((ext) => ext.trim().toLowerCase())

  const validateFile = (file: File): boolean => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()
    if (!acceptExtensions.includes(ext)) {
      toast.error(`Invalid file type. Please select a ${accept} file.`)
      return false
    }
    if (file.size > maxSizeBytes) {
      toast.error(`File too large (max ${maxSizeMB} MB)`)
      return false
    }
    return true
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) return

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && validateFile(droppedFile)) {
      onFileSelect(droppedFile)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && validateFile(file)) {
      onFileSelect(file)
    }
    // Reset input so selecting the same file again triggers onChange
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleClear = () => {
    onClear()
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        isDragging
          ? "border-primary bg-primary/5"
          : selectedFile
            ? "border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-950/50"
            : "border-border hover:border-primary/50"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {selectedFile ? (
        <div className="flex items-center justify-center gap-3">
          <FileText className="h-8 w-8 text-green-600 dark:text-green-400" />
          <div className="text-left">
            <p className="font-medium">{selectedFile.name}</p>
            <p className="text-sm text-muted-foreground">
              {formatFileSize(selectedFile.size)}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleClear}
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <>
          <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground mb-2">
            Drag & drop or click to browse
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
            accept={accept}
            className="hidden"
            onChange={handleFileChange}
          />
        </>
      )}
    </div>
  )
}
