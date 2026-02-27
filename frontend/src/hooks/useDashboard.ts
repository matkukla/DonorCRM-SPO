import { useQuery, useMutation } from "@tanstack/react-query"
import { useState, useRef, useCallback } from "react"
import { useAuth } from "@/providers/AuthProvider"
import { getDashboardSummary, getDashboardStats, getGivingSummary, getMonthlyGifts, saveDashboardLayout } from "@/api/dashboard"

export const DEFAULT_TILE_ORDER = [
  "giving-summary", "monthly-gifts",
  "thank-you", "recent-donations-stat", "active-pledges", "needs-attention-stat",
  "needs-attention", "support-progress", "recent-donations", "late-donations",
]

const VALID_TILES = new Set(DEFAULT_TILE_ORDER)

export function useDashboardLayout() {
  const { user } = useAuth()

  const [tileOrder, setTileOrderState] = useState<string[]>(() => {
    const saved = user?.dashboard_layout?.tile_order
    if (!saved || saved.length === 0) return [...DEFAULT_TILE_ORDER]

    // Filter out stale tile IDs, append any missing tiles
    const filtered = saved.filter((id) => VALID_TILES.has(id))
    const missing = DEFAULT_TILE_ORDER.filter((id) => !filtered.includes(id))
    return [...filtered, ...missing]
  })

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

  return { tileOrder, setTileOrder, resetToDefault, isSaving: mutation.isPending }
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
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

export function useGivingSummary(year?: number) {
  return useQuery({
    queryKey: ["dashboard", "giving-summary", year],
    queryFn: () => getGivingSummary(year),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useMonthlyGifts(months = 12) {
  return useQuery({
    queryKey: ["dashboard", "monthly-gifts", months],
    queryFn: () => getMonthlyGifts(months),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
