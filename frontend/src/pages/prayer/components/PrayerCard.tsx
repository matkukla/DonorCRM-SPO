import { Heart, Pencil } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "./StatusBadge"
import { formatLocalDate } from "@/lib/utils"
import type { PrayerIntention } from "@/api/prayers"

interface PrayerCardProps {
  intention: PrayerIntention
  onPrayed: (id: string) => void
  onEdit: (intention: PrayerIntention) => void
}

export function PrayerCard({ intention, onPrayed, onEdit }: PrayerCardProps) {
  return (
    <div className="bg-white dark:bg-card border border-amber-100 dark:border-amber-800 shadow-sm rounded-xl p-5">
      {/* Top row: title + status */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <h3 className="font-serif text-amber-900 dark:text-amber-100 text-lg leading-snug">
          {intention.title}
        </h3>
        <StatusBadge status={intention.status} />
      </div>

      {/* Created date */}
      <p className="text-sm text-amber-500 dark:text-amber-400">
        {formatLocalDate(intention.created_at)}
      </p>

      {/* Description */}
      {intention.description && (
        <p className="text-amber-700 dark:text-amber-300 text-sm leading-relaxed mt-2 line-clamp-3">
          {intention.description}
        </p>
      )}

      {/* Last prayed info */}
      {intention.last_prayed_at && (
        <p className="text-xs text-amber-500/80 dark:text-amber-400/60 mt-2">
          Last prayed:{" "}
          {formatDistanceToNow(new Date(intention.last_prayed_at), {
            addSuffix: true,
          })}
        </p>
      )}

      {/* Bottom row: prayed + edit */}
      <div className="flex items-center gap-2 mt-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPrayed(intention.id)}
          className="gap-1.5 border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/30"
        >
          <Heart className="h-3.5 w-3.5" />
          Prayed
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onEdit(intention)}
          className="gap-1.5 text-amber-600 dark:text-amber-400"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </Button>
      </div>
    </div>
  )
}
