import { useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAdminUserPerformance } from "@/hooks/useInsights"
import type { UserPerformanceItem } from "@/api/insights"

interface UserComparisonProps {
  users?: UserPerformanceItem[]
  isUsersLoading?: boolean
}

export function UserComparison({ users, isUsersLoading }: UserComparisonProps = {}) {
  const [user1Id, setUser1Id] = useState<string>("")
  const [user2Id, setUser2Id] = useState<string>("")

  // Only fetch if parent didn't pass `users`. Preserves standalone reusability.
  const shouldFetchUsers = users === undefined
  const { data: fetchedData, isLoading: fetchedLoading } = useAdminUserPerformance({
    enabled: shouldFetchUsers,
  })

  const data = shouldFetchUsers ? fetchedData : { users: users ?? [] }
  const isLoading = shouldFetchUsers ? fetchedLoading : (isUsersLoading ?? false)

  const user1 = useMemo(() => {
    if (!user1Id || !data?.users) return null
    return data.users.find((u) => u.id === user1Id)
  }, [user1Id, data])

  const user2 = useMemo(() => {
    if (!user2Id || !data?.users) return null
    return data.users.find((u) => u.id === user2Id)
  }, [user2Id, data])

  const metrics = useMemo(() => {
    if (!user1 || !user2) return []

    return [
      {
        label: 'Total Contacts',
        user1Value: user1.total_contacts,
        user2Value: user2.total_contacts,
      },
      {
        label: 'Active Journals',
        user1Value: user1.active_journals,
        user2Value: user2.active_journals,
      },
      {
        label: 'Decisions Logged',
        user1Value: user1.decisions_logged,
        user2Value: user2.decisions_logged,
      },
      {
        label: 'Conversion Rate',
        user1Value: user1.conversion_rate,
        user2Value: user2.conversion_rate,
        suffix: '%',
        formatValue: (val: number) => val.toFixed(1),
      },
      {
        label: 'Total Donations',
        user1Value: user1.total_donations,
        user2Value: user2.total_donations,
        isCurrency: true,
      },
    ]
  }, [user1, user2])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Compare Missionaries</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 bg-muted rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compare Missionaries</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* User Selection */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Missionary 1
              </label>
              <Select value={user1Id} onValueChange={setUser1Id}>
                <SelectTrigger>
                  <SelectValue placeholder="Select user" />
                </SelectTrigger>
                <SelectContent>
                  {data?.users.map((user) => (
                    <SelectItem key={user.id} value={user.id} disabled={user.id === user2Id}>
                      {user.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Missionary 2
              </label>
              <Select value={user2Id} onValueChange={setUser2Id}>
                <SelectTrigger>
                  <SelectValue placeholder="Select user" />
                </SelectTrigger>
                <SelectContent>
                  {data?.users.map((user) => (
                    <SelectItem key={user.id} value={user.id} disabled={user.id === user1Id}>
                      {user.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Comparison Grid */}
          {user1 && user2 ? (
            <div className="space-y-3 mt-4">
              {metrics.map((metric) => {
                const user1Higher = metric.user1Value > metric.user2Value
                const user2Higher = metric.user2Value > metric.user1Value

                const formatValue = (val: number) => {
                  if (metric.formatValue) return metric.formatValue(val)
                  if (metric.isCurrency) {
                    return val.toLocaleString('en-US', {
                      style: 'currency',
                      currency: 'USD',
                    })
                  }
                  return val.toLocaleString()
                }

                return (
                  <div key={metric.label} className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">{metric.label}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div
                        className={`text-lg font-semibold ${
                          user1Higher ? 'text-green-600 dark:text-green-400' : ''
                        }`}
                      >
                        {formatValue(metric.user1Value)}
                        {metric.suffix || ''}
                      </div>
                      <div
                        className={`text-lg font-semibold ${
                          user2Higher ? 'text-green-600 dark:text-green-400' : ''
                        }`}
                      >
                        {formatValue(metric.user2Value)}
                        {metric.suffix || ''}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Select two missionaries to compare
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
