import { Card, CardHeader, CardDescription, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  title: string
  value: string | number
  icon?: LucideIcon
  description?: string
  trend?: {
    value: number
    isPositive: boolean
  }
  isLoading?: boolean
  className?: string
}

export function StatCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  isLoading,
  className,
}: StatCardProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>{title}</CardDescription>
          {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        </div>
        <CardTitle className="text-3xl">
          {isLoading ? (
            <span className="text-muted-foreground">--</span>
          ) : (
            value
          )}
        </CardTitle>
        {(description || trend) && (
          <div className="flex items-center gap-2 text-sm">
            {trend && (
              <span
                className={cn(
                  "font-medium",
                  trend.isPositive ? "text-green-600" : "text-red-600"
                )}
              >
                {trend.isPositive ? "+" : ""}
                {trend.value}%
              </span>
            )}
            {description && (
              <span className="text-muted-foreground">{description}</span>
            )}
          </div>
        )}
      </CardHeader>
    </Card>
  )
}
