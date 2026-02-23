import { useState, useEffect, useCallback } from "react"
import { Heart, ChevronLeft, ChevronRight, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useMarkPrayed } from "@/hooks/usePrayers"
import type { PrayerIntention } from "@/api/prayers"

interface PrayerFocusModeProps {
  open: boolean
  onClose: () => void
  intentions: PrayerIntention[]
}

export function PrayerFocusMode({
  open,
  onClose,
  intentions,
}: PrayerFocusModeProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [prayedIds, setPrayedIds] = useState<Set<string>>(new Set())
  const markPrayedMutation = useMarkPrayed()

  // Reset state when opening
  useEffect(() => {
    if (open) {
      setCurrentIndex(0)
      setPrayedIds(new Set())
    }
  }, [open])

  const isComplete = currentIndex >= intentions.length

  const goToNext = useCallback(() => {
    if (currentIndex < intentions.length) {
      setCurrentIndex((i) => i + 1)
    }
  }, [currentIndex, intentions.length])

  const goToPrevious = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1))
  }, [])

  const handleMarkPrayed = useCallback(() => {
    if (currentIndex >= intentions.length) return
    const intention = intentions[currentIndex]
    markPrayedMutation.mutate(intention.id)
    setPrayedIds((prev) => new Set(prev).add(intention.id))
    // Auto-advance
    setCurrentIndex((i) => i + 1)
  }, [currentIndex, intentions, markPrayedMutation])

  const handleClose = useCallback(() => {
    onClose()
  }, [onClose])

  // Keyboard handler
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowRight":
        case " ":
          e.preventDefault()
          if (!isComplete) goToNext()
          break
        case "ArrowLeft":
          e.preventDefault()
          if (!isComplete) goToPrevious()
          break
        case "p":
        case "Enter":
          e.preventDefault()
          if (isComplete) {
            handleClose()
          } else {
            handleMarkPrayed()
          }
          break
        case "Escape":
          e.preventDefault()
          handleClose()
          break
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open, isComplete, goToNext, goToPrevious, handleMarkPrayed, handleClose])

  if (!open) return null

  // Empty state
  if (intentions.length === 0) {
    return (
      <div className="fixed inset-0 z-50 bg-amber-50 dark:bg-amber-950 flex flex-col items-center justify-center min-h-screen p-8">
        <div className="bg-white dark:bg-card border border-amber-200 dark:border-amber-800 shadow-lg rounded-2xl p-8 md:p-12 max-w-lg w-full text-center">
          <Heart className="h-12 w-12 text-amber-500 mx-auto mb-4" />
          <h2 className="font-serif text-2xl text-amber-900 dark:text-amber-100 mb-2">
            No Intentions for Today
          </h2>
          <p className="text-amber-700 dark:text-amber-300 leading-relaxed mb-6">
            Add some prayer intentions to begin your daily focus.
          </p>
          <Button onClick={handleClose}>Return</Button>
        </div>
      </div>
    )
  }

  // Completion screen
  if (isComplete) {
    return (
      <div className="fixed inset-0 z-50 bg-amber-50 dark:bg-amber-950 flex flex-col items-center justify-center min-h-screen p-8">
        <div className="bg-white dark:bg-card border border-amber-200 dark:border-amber-800 shadow-lg rounded-2xl p-8 md:p-12 text-center max-w-lg w-full">
          <Heart className="h-16 w-16 text-amber-500 mx-auto mb-6" />
          <h2 className="font-serif text-3xl text-amber-900 dark:text-amber-100 mb-3">
            Prayer Complete
          </h2>
          <p className="text-amber-700 dark:text-amber-300 leading-relaxed mb-8 text-lg">
            You prayed for {prayedIds.size} intention
            {prayedIds.size !== 1 ? "s" : ""} today.
          </p>
          <Button onClick={handleClose} size="lg">
            Return
          </Button>
        </div>
      </div>
    )
  }

  const intention = intentions[currentIndex]

  return (
    <div className="fixed inset-0 z-50 bg-amber-50 dark:bg-amber-950 flex flex-col items-center justify-center min-h-screen p-8">
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-4">
        <span className="font-serif text-amber-700 dark:text-amber-400 text-sm">
          Focus Mode
        </span>
        <span className="text-amber-600 dark:text-amber-400 text-sm font-medium">
          {currentIndex + 1} of {intentions.length}
        </span>
        <button
          onClick={handleClose}
          className="flex items-center gap-1.5 text-amber-500 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-200 text-sm transition-colors"
        >
          <X className="h-4 w-4" />
          <span>Escape to exit</span>
        </button>
      </div>

      {/* Main card */}
      <div className="bg-white dark:bg-card border border-amber-200 dark:border-amber-800 shadow-lg rounded-2xl p-8 md:p-12 max-w-2xl w-full">
        <h2 className="text-2xl md:text-3xl font-serif text-amber-900 dark:text-amber-100">
          {intention.title}
        </h2>
        <p className="text-lg text-amber-600 dark:text-amber-400 mt-2">
          {intention.contact_name}
        </p>
        {intention.description && (
          <p className="text-amber-700 dark:text-amber-300 leading-relaxed mt-4">
            {intention.description}
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3 mt-8">
        <Button
          variant="ghost"
          size="icon"
          onClick={goToPrevious}
          disabled={currentIndex === 0}
          className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>

        <Button
          onClick={handleMarkPrayed}
          className="gap-2 bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-700 dark:hover:bg-amber-600"
          size="lg"
        >
          <Heart className="h-4 w-4" />
          Mark as Prayed
        </Button>

        <Button
          variant="ghost"
          onClick={goToNext}
          className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200"
        >
          Skip
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={goToNext}
          disabled={currentIndex >= intentions.length - 1}
          className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>

      {/* Keyboard shortcut hints */}
      <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-6 text-amber-400 dark:text-amber-600 text-sm">
        <span>
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            P
          </kbd>{" "}
          or{" "}
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            Enter
          </kbd>{" "}
          Mark as Prayed
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            &larr;
          </kbd>{" "}
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            &rarr;
          </kbd>{" "}
          Navigate
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            Space
          </kbd>{" "}
          Next
        </span>
        <span>
          <kbd className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900 rounded text-xs">
            Esc
          </kbd>{" "}
          Exit
        </span>
      </div>
    </div>
  )
}
