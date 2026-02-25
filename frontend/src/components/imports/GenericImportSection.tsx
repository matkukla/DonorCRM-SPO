import { useState } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { FileUp, Users, DollarSign, Loader2, Upload } from "lucide-react"
import { FileDropZone } from "./FileDropZone"
import { ImportResultBanner } from "./ImportResultBanner"
import { useGenericImport } from "@/hooks/useImports"
import type { GenericImportType, REImportResponse } from "@/api/imports"
import type { LucideIcon } from "lucide-react"

interface GenericImportCardProps {
  importType: GenericImportType
  title: string
  description: string
  icon: LucideIcon
}

function GenericImportCard({
  importType,
  title,
  description,
  icon: Icon,
}: GenericImportCardProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [matchBy, setMatchBy] = useState("email")
  const [result, setResult] = useState<REImportResponse | null>(null)

  const mutation = useGenericImport(importType)

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
      const importResult = await mutation.mutateAsync({ file: selectedFile, matchBy })
      setResult(importResult)
      setSelectedFile(null)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      toast.error(
        error.response?.data?.detail || `${title} import failed. Please try again.`,
      )
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Matching strategy selector */}
        <div className="flex items-center gap-3">
          <Label htmlFor={`match-${importType}`} className="shrink-0 text-sm">
            Contact matching
          </Label>
          <Select value={matchBy} onValueChange={setMatchBy}>
            <SelectTrigger id={`match-${importType}`} className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="email">Match by Email</SelectItem>
              <SelectItem value="name">Match by Name</SelectItem>
              <SelectItem value="external_id">Match by External ID</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* File upload zone */}
        <FileDropZone
          onFileSelect={handleFileSelect}
          accept=".csv"
          maxSizeMB={10}
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
      </CardContent>
    </Card>
  )
}

export function GenericImportSection() {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileUp className="h-5 w-5 text-muted-foreground" />
          Generic CSV Import
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Import contacts or donations from any CSV file format.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <GenericImportCard
          importType="contacts"
          title="Contacts"
          description="Import contacts from any CSV format"
          icon={Users}
        />
        <GenericImportCard
          importType="donations"
          title="Donations"
          description="Import donations linked to existing contacts"
          icon={DollarSign}
        />
      </div>
    </div>
  )
}
