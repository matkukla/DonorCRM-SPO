import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getBroadcasts,
  getBroadcast,
  createBroadcast,
  updateBroadcast,
  cancelBroadcast,
  getBroadcastCopies,
} from "@/api/broadcasts"
import type { BroadcastCreate, BroadcastUpdate, BroadcastFilters } from "@/api/broadcasts"

export function useBroadcasts(filters: BroadcastFilters = {}) {
  return useQuery({
    queryKey: ["broadcasts", filters],
    queryFn: () => getBroadcasts(filters),
  })
}

export function useBroadcast(id: string) {
  return useQuery({
    queryKey: ["broadcasts", id],
    queryFn: () => getBroadcast(id),
    enabled: !!id,
  })
}

export function useCreateBroadcast() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: BroadcastCreate) => createBroadcast(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useUpdateBroadcast() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: BroadcastUpdate }) => updateBroadcast(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] })
      queryClient.invalidateQueries({ queryKey: ["broadcasts", id] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useCancelBroadcast() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cancelBroadcast(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["broadcasts"] })
      queryClient.invalidateQueries({ queryKey: ["broadcasts", id] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useBroadcastCopies(id: string, page: number = 1) {
  return useQuery({
    queryKey: ["broadcasts", id, "copies", page],
    queryFn: () => getBroadcastCopies(id, page),
    enabled: !!id,
  })
}
