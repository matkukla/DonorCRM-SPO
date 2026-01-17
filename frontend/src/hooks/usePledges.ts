import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getPledges,
  getPledge,
  createPledge,
  updatePledge,
  deletePledge,
  pausePledge,
  resumePledge,
  cancelPledge,
} from "@/api/pledges"
import type { PledgeFilters, PledgeCreate, PledgeUpdate } from "@/api/pledges"

export function usePledges(filters: PledgeFilters = {}) {
  return useQuery({
    queryKey: ["pledges", filters],
    queryFn: () => getPledges(filters),
  })
}

export function usePledge(id: string) {
  return useQuery({
    queryKey: ["pledges", id],
    queryFn: () => getPledge(id),
    enabled: !!id,
  })
}

export function useCreatePledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: PledgeCreate) => createPledge(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useUpdatePledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PledgeUpdate }) => updatePledge(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["pledges", id] })
    },
  })
}

export function useDeletePledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deletePledge(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function usePausePledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => pausePledge(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["pledges", id] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useResumePledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => resumePledge(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["pledges", id] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useCancelPledge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => cancelPledge(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["pledges"] })
      queryClient.invalidateQueries({ queryKey: ["pledges", id] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}
