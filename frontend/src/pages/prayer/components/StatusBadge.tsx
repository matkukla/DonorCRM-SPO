import { Badge } from "@/components/ui/badge"
import type { PrayerIntentionStatus } from "@/api/prayers"

const statusStyles: Record<PrayerIntentionStatus, string> = {
  active:
    "bg-green-100 text-green-800 border-green-200 dark:bg-green-950/50 dark:text-green-400 dark:border-green-800",
  answered:
    "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/50 dark:text-blue-400 dark:border-blue-800",
  archived:
    "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800/50 dark:text-gray-400 dark:border-gray-700",
}

const statusLabels: Record<PrayerIntentionStatus, string> = {
  active: "Active",
  answered: "Answered",
  archived: "Archived",
}

export function StatusBadge({ status }: { status: PrayerIntentionStatus }) {
  return (
    <Badge variant="outline" className={statusStyles[status]}>
      {statusLabels[status]}
    </Badge>
  )
}
