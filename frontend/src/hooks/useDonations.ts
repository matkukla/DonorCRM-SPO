import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getDonations,
  getDonation,
  createDonation,
  updateDonation,
  deleteDonation,
  markDonationThanked,
} from "@/api/donations"
import type { DonationFilters, DonationCreate, DonationUpdate } from "@/api/donations"

export function useDonations(filters: DonationFilters = {}) {
  return useQuery({
    queryKey: ["donations", filters],
    queryFn: () => getDonations(filters),
  })
}

export function useDonation(id: string) {
  return useQuery({
    queryKey: ["donations", id],
    queryFn: () => getDonation(id),
    enabled: !!id,
  })
}

export function useCreateDonation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DonationCreate) => createDonation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useUpdateDonation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DonationUpdate }) => updateDonation(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["donations", id] })
    },
  })
}

export function useDeleteDonation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteDonation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useMarkDonationThanked() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => markDonationThanked(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["donations"] })
      queryClient.invalidateQueries({ queryKey: ["donations", id] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}
