import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  importContacts,
  importDonations,
  exportContacts,
  exportDonations,
  downloadContactTemplate,
  downloadDonationTemplate,
} from "@/api/imports"

export function useImportContacts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, validateOnly }: { file: File; validateOnly?: boolean }) =>
      importContacts(file, validateOnly),
    onSuccess: (_, { validateOnly }) => {
      // Only invalidate queries if we actually imported (not validation)
      if (!validateOnly) {
        queryClient.invalidateQueries({ queryKey: ["contacts"] })
        queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      }
    },
  })
}

export function useImportDonations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, validateOnly }: { file: File; validateOnly?: boolean }) =>
      importDonations(file, validateOnly),
    onSuccess: (_, { validateOnly }) => {
      // Only invalidate queries if we actually imported (not validation)
      if (!validateOnly) {
        queryClient.invalidateQueries({ queryKey: ["donations"] })
        queryClient.invalidateQueries({ queryKey: ["contacts"] })
        queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      }
    },
  })
}

export function useExportContacts() {
  return useMutation({
    mutationFn: () => exportContacts(),
  })
}

export function useExportDonations() {
  return useMutation({
    mutationFn: ({ startDate, endDate }: { startDate?: string; endDate?: string }) =>
      exportDonations(startDate, endDate),
  })
}

export function useDownloadContactTemplate() {
  return useMutation({
    mutationFn: () => downloadContactTemplate(),
  })
}

export function useDownloadDonationTemplate() {
  return useMutation({
    mutationFn: () => downloadDonationTemplate(),
  })
}
