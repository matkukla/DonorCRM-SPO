import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical } from "lucide-react"
import { cn } from "@/lib/utils"

interface SortableDashboardTileProps {
  id: string
  children: React.ReactNode
  className?: string
}

export function SortableDashboardTile({ id, children, className }: SortableDashboardTileProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  return (
    <div
      ref={setNodeRef}
      data-tile-id={id}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={cn(
        "group relative",
        isDragging && "opacity-40 border-2 border-dashed border-border rounded-lg",
        className
      )}
    >
      <button
        className="absolute top-5 left-2 z-10 p-0.5 rounded cursor-grab active:cursor-grabbing text-muted-foreground/0 group-hover:text-muted-foreground hover:text-foreground transition-colors duration-150"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      {children}
    </div>
  )
}
