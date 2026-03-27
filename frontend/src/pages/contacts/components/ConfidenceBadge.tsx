import { Badge } from "@/components/ui/badge"
import type { DuplicateConfidence } from "@/api/contacts"

const confidenceConfig: Record<DuplicateConfidence, { variant: "destructive" | "warning" | "secondary"; label: string }> = {
  high: { variant: "destructive", label: "High" },
  medium: { variant: "warning", label: "Medium" },
  low: { variant: "secondary", label: "Low" },
}

interface ConfidenceBadgeProps {
  confidence: DuplicateConfidence
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const config = confidenceConfig[confidence]
  return <Badge variant={config.variant}>{config.label}</Badge>
}
