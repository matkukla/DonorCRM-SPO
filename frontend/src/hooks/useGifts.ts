import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getGifts,
  getGift,
  createGift,
  updateGift,
  deleteGift,
  getRecurringGifts,
  getRecurringGift,
  createRecurringGift,
  updateRecurringGift,
  deleteRecurringGift,
} from "@/api/gifts"
import type {
  GiftCreate,
  GiftUpdate,
  RecurringGiftCreate,
  RecurringGiftUpdate,
} from "@/api/gifts"

// ---------------------------------------------------------------------------
// Gift hooks
// ---------------------------------------------------------------------------

export function useGifts(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: ["gifts", params],
    queryFn: () => getGifts(params),
  })
}

export function useGift(id: string | null) {
  return useQuery({
    queryKey: ["gifts", id],
    queryFn: () => getGift(id!),
    enabled: !!id,
  })
}

export function useCreateGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: GiftCreate) => createGift(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gifts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useUpdateGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GiftUpdate }) => updateGift(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["gifts"] })
      queryClient.invalidateQueries({ queryKey: ["gifts", id] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useDeleteGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteGift(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gifts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

// ---------------------------------------------------------------------------
// RecurringGift hooks
// ---------------------------------------------------------------------------

export function useRecurringGifts(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: ["recurring-gifts", params],
    queryFn: () => getRecurringGifts(params),
  })
}

export function useRecurringGift(id: string | null) {
  return useQuery({
    queryKey: ["recurring-gifts", id],
    queryFn: () => getRecurringGift(id!),
    enabled: !!id,
  })
}

export function useCreateRecurringGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: RecurringGiftCreate) => createRecurringGift(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-gifts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useUpdateRecurringGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RecurringGiftUpdate }) => updateRecurringGift(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["recurring-gifts"] })
      queryClient.invalidateQueries({ queryKey: ["recurring-gifts", id] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useDeleteRecurringGift() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteRecurringGift(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-gifts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}
