import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  importContacts,
  importDonations,
  exportContacts,
  exportDonations,
  downloadContactTemplate,
  downloadDonationTemplate,
  getFunds,
  importRE,
  importGeneric,
  getImportBatches,
  type REImportType,
  type GenericImportType,
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

// Fund list for filter dropdowns

export function useFunds() {
  return useQuery({
    queryKey: ["funds"],
    queryFn: getFunds,
  })
}

// RE Import Hooks

export function useREImport(importType: REImportType) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => importRE(importType, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['importBatches'] })
      // Invalidate related data queries
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['gifts'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-gifts'] })
      queryClient.invalidateQueries({ queryKey: ['prayers'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useImportBatches(importType?: string) {
  return useQuery({
    queryKey: ['importBatches', importType].filter(Boolean),
    queryFn: () => getImportBatches(importType),
    staleTime: 30 * 1000, // 30 seconds
  })
}

// Generic Import Hook

export function useGenericImport(importType: GenericImportType) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, matchBy }: { file: File; matchBy: string }) =>
      importGeneric(importType, file, matchBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['importBatches'] })
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
      queryClient.invalidateQueries({ queryKey: ['gifts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
