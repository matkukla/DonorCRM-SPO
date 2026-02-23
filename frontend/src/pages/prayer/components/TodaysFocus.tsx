import { useTodaysFocus } from "@/hooks/usePrayers"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Heart, Sparkles } from "lucide-react"
import { StatusBadge } from "./StatusBadge"

interface TodaysFocusProps {
  onStartFocusMode: () => void
}

export function TodaysFocus({ onStartFocusMode }: TodaysFocusProps) {
  const { data: intentions, isLoading } = useTodaysFocus()

  return (
    <div className="bg-amber-50/30 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Heart className="h-5 w-5 text-amber-700 dark:text-amber-400" />
          <h2 className="font-serif text-xl text-amber-900 dark:text-amber-100">
            Today's Focus
          </h2>
        </div>
        {intentions && intentions.length > 0 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onStartFocusMode}
            className="gap-1.5"
          >
            <Sparkles className="h-4 w-4" />
            Enter Focus Mode
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card
              key={i}
              className="bg-amber-50/50 dark:bg-amber-950/10 border-amber-100 dark:border-amber-800 p-4"
            >
              <div className="space-y-3">
                <div className="h-5 w-3/4 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
                <div className="h-4 w-1/2 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
                <div className="h-5 w-16 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
              </div>
            </Card>
          ))}
        </div>
      ) : !intentions || intentions.length === 0 ? (
        <p className="text-amber-700/70 dark:text-amber-400/60 text-sm leading-relaxed">
          No active prayer intentions yet. Add your first prayer intention to
          begin your daily focus.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {intentions.map((intention) => (
            <Card
              key={intention.id}
              className="bg-white dark:bg-card border-amber-100 dark:border-amber-800 shadow-sm p-4"
            >
              <h3 className="font-serif text-base text-amber-900 dark:text-amber-100 font-medium mb-1 line-clamp-2">
                {intention.title}
              </h3>
              <p className="text-sm text-amber-700/80 dark:text-amber-400/70 mb-2">
                {intention.contact_name}
              </p>
              <StatusBadge status={intention.status} />
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
