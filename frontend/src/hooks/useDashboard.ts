import { useQuery, useMutation } from "@tanstack/react-query"
import { useState, useRef, useCallback } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { getDashboardSummary, getDashboardStats, getGivingSummary, getMonthlyGifts, getUserDashboardLayout, saveDashboardLayout } from "@/api/dashboard"

export const DEFAULT_TILE_ORDER = [
  "giving-summary", "monthly-gifts",
  "thank-you", "recent-donations-stat", "active-pledges", "needs-attention-stat",
  "needs-attention", "support-progress", "recent-donations", "late-donations",
]

const VALID_TILES = new Set(DEFAULT_TILE_ORDER)

function normalizeTileOrder(saved: string[] | undefined): string[] {
  if (!saved || saved.length === 0) return [...DEFAULT_TILE_ORDER]
  const filtered = saved.filter((id) => VALID_TILES.has(id))
  const missing = DEFAULT_TILE_ORDER.filter((id) => !filtered.includes(id))
  return [...filtered, ...missing]
}

export function useDashboardLayout(userId?: string) {
  const { user } = useAuth()
  const isViewingOther = !!userId && userId !== user?.id

  // When viewing another user, fetch their layout from the API
  const { data: otherLayout } = useQuery({
    queryKey: ["dashboard", "layout", userId],
    queryFn: () => getUserDashboardLayout(userId!),
    enabled: isViewingOther,
    staleTime: 2 * 60 * 1000,
  })

  const [tileOrder, setTileOrderState] = useState<string[]>(() => {
    const saved = user?.dashboard_layout?.tile_order
    return normalizeTileOrder(saved)
  })

  // Compute effective tile order: other user's layout when viewing, own when not
  const effectiveTileOrder = isViewingOther
    ? normalizeTileOrder(otherLayout?.tile_order)
    : tileOrder

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const mutation = useMutation({
    mutationFn: saveDashboardLayout,
  })

  const debouncedSave = useCallback((order: string[]) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      mutation.mutate(order)
    }, 1000)
  }, [mutation])

  const setTileOrder = useCallback((newOrder: string[]) => {
    setTileOrderState(newOrder)
    debouncedSave(newOrder)
  }, [debouncedSave])

  const resetToDefault = useCallback(() => {
    setTileOrderState([...DEFAULT_TILE_ORDER])
    // Save immediately on reset (no debounce)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    mutation.mutate([...DEFAULT_TILE_ORDER])
  }, [mutation])

  return {
    tileOrder: effectiveTileOrder,
    setTileOrder,
    resetToDefault,
    isSaving: mutation.isPending,
    isDragEnabled: !isViewingOther,
  }
}

export function useDashboardSummary(userId?: string) {
  return useQuery({
    queryKey: ["dashboard", "summary", userId ?? "me"],
    queryFn: () => getDashboardSummary(userId),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useGivingSummary(year?: number, userId?: string) {
  return useQuery({
    queryKey: ["dashboard", "giving-summary", year, userId ?? "me"],
    queryFn: () => getGivingSummary(year, userId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useMonthlyGifts(months = 12, userId?: string) {
  return useQuery({
    queryKey: ["dashboard", "monthly-gifts", months, userId ?? "me"],
    queryFn: () => getMonthlyGifts(months, userId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
