import { Badge } from "@/components/ui/badge"
import type { DuplicateConfidence } from "@/api/contacts"

const confidenceConfig: Record<DuplicateConfidence, { label: string; variant: "destructive" | "warning" | "secondary" }> = {
  high: { label: "High", variant: "destructive" },
  medium: { label: "Medium", variant: "warning" },
  low: { label: "Low", variant: "secondary" },
}

export function ConfidenceBadge({ confidence }: { confidence: DuplicateConfidence }) {
  const config = confidenceConfig[confidence]
  return <Badge variant={config.variant}>{config.label}</Badge>
}
