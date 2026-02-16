import { useMemo } from "react"
import { subDays, format, parse } from "date-fns"
import HeatMap from "@uiw/react-heat-map"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useAdminActivityHeatmap } from "@/hooks/useInsights"

interface ActivityHeatmapProps {
  dateParams?: {
    date_from?: string
    date_to?: string
  }
}

export function ActivityHeatmap({ dateParams }: ActivityHeatmapProps) {
  const { data, isLoading } = useAdminActivityHeatmap(dateParams)

  // Transform data: replace hyphens with forward slashes for Safari compatibility
  const heatmapData = useMemo(() => {
    if (!data?.activities) return []
    return data.activities.map((d) => ({
      date: d.date.replace(/-/g, '/'),
      count: d.count,
      content: '',
    }))
  }, [data])

  const startDate = useMemo(() => {
    if (dateParams?.date_from) {
      // Parse the date_from parameter
      const parts = dateParams.date_from.split('-')
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]))
    }
    return subDays(new Date(), 365)
  }, [dateParams?.date_from])

  const endDate = useMemo(() => {
    if (dateParams?.date_to) {
      // Parse the date_to parameter
      const parts = dateParams.date_to.split('-')
      return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]))
    }
    return new Date()
  }, [dateParams?.date_to])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Team Activity Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-muted rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  return (
    <TooltipProvider>
      <Card>
        <CardHeader>
          <CardTitle>Team Activity Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <HeatMap
              value={heatmapData}
              startDate={startDate}
              endDate={endDate}
              rectRender={(props, data) => {
                if (!data.date) return <rect {...props} />

                // Parse the Safari-compatible date format (YYYY/MM/DD)
                const dateObj = parse(data.date, 'yyyy/MM/dd', new Date())
                const formattedDate = format(dateObj, 'MMM d, yyyy')

                return (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <rect {...props} />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="font-semibold">{formattedDate}</p>
                      <p className="text-xs">{data.count || 0} {data.count === 1 ? 'activity' : 'activities'}</p>
                    </TooltipContent>
                  </Tooltip>
                )
              }}
              panelColors={{
                0: '#ebedf0',
                2: '#c6e48b',
                4: '#7bc96f',
                10: '#239a3b',
                20: '#196127',
              }}
              rectProps={{
                rx: 2,
              }}
              rectSize={14}
              space={3}
              style={{ color: '#000' }}
            />
          </div>
          <div className="flex items-center justify-end gap-2 mt-4 text-xs text-muted-foreground">
            <span>Less</span>
            <div className="flex gap-1">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#ebedf0' }} />
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#c6e48b' }} />
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#7bc96f' }} />
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#239a3b' }} />
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#196127' }} />
            </div>
            <span>More</span>
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  )
}
