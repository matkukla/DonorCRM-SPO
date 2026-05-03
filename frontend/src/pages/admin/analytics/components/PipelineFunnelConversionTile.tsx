import { AlertTriangleIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { usePipelineFunnelConversion } from "@/hooks/useAdminAnalytics"
import { CHART_COLORS, CHART_WARNING_COLOR } from "@/lib/chart-palette"

interface PipelineFunnelConversionTileProps {
  onStageClick?: (stage: string) => void
}

export function PipelineFunnelConversionTile({ onStageClick }: PipelineFunnelConversionTileProps) {
  const { data, isLoading, error } = usePipelineFunnelConversion()

  if (isLoading) {
    return (
      <Card data-testid="pipeline-funnel-tile" data-state="loading">
        <CardHeader>
          <CardTitle>Pipeline Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card data-testid="pipeline-funnel-tile" data-state="error">
        <CardHeader>
          <CardTitle>Pipeline Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
            <p className="text-destructive text-sm">Failed to load pipeline funnel.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { stages, total_in_pipeline, weakest_transition } = data
  const maxCount = Math.max(...stages.map((s) => s.count_at_or_past), 1)

  return (
    <Card data-testid="pipeline-funnel-tile" data-state="ready">
      <CardHeader>
        <CardTitle>Pipeline Funnel</CardTitle>
        <CardDescription>
          {total_in_pipeline} contacts in pipeline. Stage-to-stage conversion shown between bars.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {total_in_pipeline === 0 ? (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">No pipeline activity yet.</p>
          </div>
        ) : (
          <TooltipProvider>
            <div className="space-y-3">
              {stages.map((stage, idx) => {
                const barWidth = (stage.count_at_or_past / maxCount) * 100
                const color = stage.is_weakest_transition
                  ? CHART_WARNING_COLOR
                  : CHART_COLORS[idx % CHART_COLORS.length]
                const conversion = stage.conversion_from_prior_percentage

                return (
                  <div key={stage.stage} data-testid="pipeline-stage-row">
                    {conversion !== null && (
                      <div className="flex items-center gap-2 pl-2 pb-1">
                        <div className="h-2 w-px bg-border" aria-hidden />
                        {stage.is_weakest_transition ? (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge
                                variant="outline"
                                className="border-amber-500/40 text-amber-600 bg-amber-50 gap-1"
                                data-testid="pipeline-weakest-badge"
                              >
                                <AlertTriangleIcon className="h-3 w-3" aria-hidden />
                                {conversion.toFixed(0)}% conversion
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                              Lowest conversion rate in funnel — coaching opportunity.
                            </TooltipContent>
                          </Tooltip>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {conversion.toFixed(0)}% conversion
                          </span>
                        )}
                      </div>
                    )}
                    <button
                      type="button"
                      className="w-full text-left group"
                      onClick={() => onStageClick?.(stage.stage)}
                      disabled={!onStageClick}
                      aria-label={
                        stage.is_weakest_transition
                          ? `${stage.label}: ${stage.count_at_or_past} contacts. Weakest transition in funnel.`
                          : `${stage.label}: ${stage.count_at_or_past} contacts.`
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">{stage.label}</span>
                        <span className="text-sm tabular-nums text-muted-foreground">
                          {stage.count_at_or_past}
                        </span>
                      </div>
                      <div className="h-6 bg-muted rounded overflow-hidden">
                        <div
                          className="h-full rounded transition-all group-hover:opacity-90"
                          style={{
                            width: `${Math.max(barWidth, 2)}%`,
                            backgroundColor: color,
                          }}
                          role="presentation"
                        />
                      </div>
                    </button>
                  </div>
                )
              })}
            </div>
            {weakest_transition && (
              <p className="text-xs text-muted-foreground mt-4">
                Weakest transition:{" "}
                <span className="font-medium">
                  {weakest_transition.from} → {weakest_transition.to}
                </span>{" "}
                ({weakest_transition.rate.toFixed(0)}% conversion)
              </p>
            )}
          </TooltipProvider>
        )}
      </CardContent>
    </Card>
  )
}
