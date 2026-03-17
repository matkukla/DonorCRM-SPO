import { Eye, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useViewAs } from "@/providers/ViewAsProvider"

export function ViewAsBanner() {
  const { isViewingAs, viewAsUserName, exitViewAs } = useViewAs()

  if (!isViewingAs) return null

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2 bg-amber-50 border-b border-amber-200 text-amber-800 text-sm dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
      <div className="flex items-center gap-2">
        <Eye className="h-4 w-4 shrink-0" />
        <span>
          Viewing <strong>{viewAsUserName}</strong> · Read Only
        </span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={exitViewAs}
        className="text-amber-800 hover:text-amber-900 hover:bg-amber-100 dark:text-amber-300 dark:hover:text-amber-200 dark:hover:bg-amber-900/30 h-7 px-2"
      >
        <X className="h-3.5 w-3.5 mr-1" />
        Exit
      </Button>
    </div>
  )
}
