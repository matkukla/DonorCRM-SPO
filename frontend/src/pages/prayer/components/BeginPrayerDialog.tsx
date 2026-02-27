import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { usePrayers, useTodaysFocus } from "@/hooks/usePrayers"
import type { PrayerIntention } from "@/api/prayers"

interface BeginPrayerDialogProps {
  open: boolean
  onClose: () => void
  onStartPrayer: (intentions: PrayerIntention[]) => void
}

export function BeginPrayerDialog({
  open,
  onClose,
  onStartPrayer,
}: BeginPrayerDialogProps) {
  const { data: activeData, isLoading } = usePrayers({
    status: "active",
    page_size: "200",
  })
  const { data: todaysFocusData } = useTodaysFocus()

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Reset selected IDs when dialog opens, pre-checking today's focus
  useEffect(() => {
    if (open && todaysFocusData) {
      setSelectedIds(new Set(todaysFocusData.map((i) => i.id)))
    } else if (open) {
      setSelectedIds(new Set())
    }
  }, [open, todaysFocusData])

  const activeIntentions = activeData?.results ?? []
  const allSelected =
    activeIntentions.length > 0 &&
    activeIntentions.every((i) => selectedIds.has(i.id))

  const handleToggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(activeIntentions.map((i) => i.id)))
    }
  }

  const handleToggle = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const handleStartPrayer = () => {
    const filtered = activeIntentions.filter((i) => selectedIds.has(i.id))
    onStartPrayer(filtered)
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-amber-900 dark:text-amber-100">
            Choose Prayer Intentions
          </DialogTitle>
          <DialogDescription>
            Select which intentions to include in your prayer session.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-3 py-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-4 py-3 rounded-lg"
              >
                <div className="h-4 w-4 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
                  <div className="h-3 w-1/2 bg-amber-100 dark:bg-amber-900/30 rounded animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : activeIntentions.length === 0 ? (
          <div className="py-6 text-center">
            <p className="text-amber-700/70 dark:text-amber-400/60 text-sm">
              No active intentions to select.
            </p>
          </div>
        ) : (
          <>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleToggleAll}
                className="text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
              >
                {allSelected ? "Deselect All" : "Select All"}
              </button>
            </div>

            <div className="max-h-[50vh] overflow-y-auto -mx-1 px-1">
              {activeIntentions.map((intention) => (
                <label
                  key={intention.id}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-amber-50/50 dark:hover:bg-amber-950/30 cursor-pointer transition-colors"
                >
                  <Checkbox
                    checked={selectedIds.has(intention.id)}
                    onCheckedChange={(checked) =>
                      handleToggle(intention.id, !!checked)
                    }
                    className="border-amber-300 dark:border-amber-700 data-[state=checked]:bg-amber-600 data-[state=checked]:border-amber-600"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-amber-900 dark:text-amber-100 truncate">
                      {intention.title}
                    </p>
                    <p className="text-sm text-amber-700/70 dark:text-amber-400/60">
                      {intention.contact_name}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </>
        )}

        <DialogFooter>
          <div className="flex flex-col items-end gap-1.5 w-full sm:w-auto">
            {selectedIds.size === 0 && activeIntentions.length > 0 && (
              <p className="text-xs text-amber-600/70 dark:text-amber-400/50">
                Select at least one intention
              </p>
            )}
            <Button
              onClick={handleStartPrayer}
              disabled={selectedIds.size === 0}
              className="bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-700 dark:hover:bg-amber-600"
            >
              Start Prayer
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
