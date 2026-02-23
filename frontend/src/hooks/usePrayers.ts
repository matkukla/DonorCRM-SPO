import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  getPrayers,
  getPrayer,
  createPrayer,
  updatePrayer,
  deletePrayer,
  markPrayed,
  getTodaysFocus,
  getContactPrayers,
} from "@/api/prayers"
import type {
  PrayerIntention,
  PrayerIntentionCreate,
  PrayerIntentionUpdate,
} from "@/api/prayers"
import type { PaginatedResponse } from "@/api/contacts"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function usePrayers(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: ["prayers", params],
    queryFn: () => getPrayers(params),
  })
}

export function usePrayer(id: string | null) {
  return useQuery({
    queryKey: ["prayers", id],
    queryFn: () => getPrayer(id!),
    enabled: !!id,
  })
}

export function useTodaysFocus() {
  return useQuery({
    queryKey: ["prayers", "focus"],
    queryFn: () => getTodaysFocus(),
  })
}

export function useContactPrayers(contactId: string) {
  return useQuery({
    queryKey: ["prayers", "contact", contactId],
    queryFn: () => getContactPrayers(contactId),
    enabled: !!contactId,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreatePrayer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PrayerIntentionCreate) => createPrayer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prayers"] })
      toast.success("Prayer intention created")
    },
    onError: () => {
      toast.error("Failed to create prayer intention")
    },
  })
}

export function useUpdatePrayer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PrayerIntentionUpdate }) =>
      updatePrayer(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prayers"] })
      toast.success("Prayer intention updated")
    },
    onError: () => {
      toast.error("Failed to update prayer intention")
    },
  })
}

export function useDeletePrayer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deletePrayer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prayers"] })
      toast.success("Prayer intention deleted")
    },
    onError: () => {
      toast.error("Failed to delete prayer intention")
    },
  })
}

export function useMarkPrayed() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => markPrayed(id),
    onMutate: async (id) => {
      // Cancel in-flight queries
      await queryClient.cancelQueries({ queryKey: ["prayers"] })

      // Snapshot current cache for rollback
      const previousPrayers = queryClient.getQueriesData<PaginatedResponse<PrayerIntention>>({
        queryKey: ["prayers"],
      })

      // Optimistically update last_prayed_at in all matching caches
      queryClient.setQueriesData<PaginatedResponse<PrayerIntention>>(
        { queryKey: ["prayers"] },
        (old) => {
          if (!old?.results) return old
          return {
            ...old,
            results: old.results.map((p) =>
              p.id === id
                ? { ...p, last_prayed_at: new Date().toISOString() }
                : p,
            ),
          }
        },
      )

      return { previousPrayers }
    },
    onError: (_err, _id, context) => {
      // Rollback on error
      if (context?.previousPrayers) {
        for (const [queryKey, data] of context.previousPrayers) {
          queryClient.setQueryData(queryKey, data)
        }
      }
      toast.error("Failed to mark as prayed")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["prayers"] })
    },
  })
}
