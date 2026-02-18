import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  importContacts,
  importDonations,
  exportContacts,
  exportDonations,
  downloadContactTemplate,
  downloadDonationTemplate,
  getLatestImports,
  importFunds,
  importEntities,
  importTransactions,
  importPledges,
  getFunds,
  type ImportType,
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

// SPO Import Center Hooks

/**
 * Fetch latest import runs for all 4 SPO CSV types
 */
export function useLatestImports() {
  return useQuery({
    queryKey: ["latestImports"],
    queryFn: getLatestImports,
    staleTime: 30 * 1000, // 30 seconds - imports don't change frequently
  })
}

/**
 * Mutation hook for SPO CSV imports
 * Handles all 4 import types with automatic query invalidation
 */
export function useSPOImport(importType: ImportType) {
  const queryClient = useQueryClient()

  const importFn = {
    funds: importFunds,
    entities: importEntities,
    transactions: importTransactions,
    pledges: importPledges,
  }[importType]

  return useMutation({
    mutationFn: ({ file, validateOnly }: { file: File; validateOnly: boolean }) =>
      importFn(file, validateOnly),
    onSuccess: () => {
      // Invalidate latest imports to refresh tile status
      queryClient.invalidateQueries({ queryKey: ["latestImports"] })
    },
  })
}
