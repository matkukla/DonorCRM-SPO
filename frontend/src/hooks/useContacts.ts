import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query"
import {
  getContacts,
  getContact,
  createContact,
  updateContact,
  deleteContact,
  markContactThanked,
  searchContacts,
  getContactDonations,
  getContactPledges,
  getContactTasks,
  getContactJournals,
  getContactJournalEvents,
  checkDuplicates,
  mergeContacts,
  dismissDuplicate,
} from "@/api/contacts"
import type { ContactCreate, ContactUpdate, MergeRequest, DismissRequest } from "@/api/contacts"

export function useContacts(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: ["contacts", params],
    queryFn: () => getContacts(params),
  })
}

export function useContact(id: string) {
  return useQuery({
    queryKey: ["contacts", id],
    queryFn: () => getContact(id),
    enabled: !!id,
  })
}

export function useCreateContact() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ContactCreate) => createContact(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
    },
  })
}

export function useUpdateContact() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ContactUpdate }) => updateContact(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts", id] })
    },
  })
}

export function useDeleteContact() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteContact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
    },
  })
}

export function useMarkContactThanked() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => markContactThanked(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["contacts", id] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

export function useSearchContacts(query: string) {
  return useQuery({
    queryKey: ["contacts", "search", query],
    queryFn: () => searchContacts(query),
    enabled: query.length >= 2,
  })
}

export function useContactDonations(id: string) {
  return useQuery({
    queryKey: ["contacts", id, "donations"],
    queryFn: () => getContactDonations(id),
    enabled: !!id,
  })
}

export function useContactPledges(id: string) {
  return useQuery({
    queryKey: ["contacts", id, "pledges"],
    queryFn: () => getContactPledges(id),
    enabled: !!id,
  })
}

export function useContactTasks(id: string) {
  return useQuery({
    queryKey: ["contacts", id, "tasks"],
    queryFn: () => getContactTasks(id),
    enabled: !!id,
  })
}

/** Hook for fetching contact's journal memberships */
export function useContactJournals(contactId: string) {
  return useQuery({
    queryKey: ['contacts', contactId, 'journals'],
    queryFn: () => getContactJournals(contactId),
    enabled: !!contactId,
  })
}

/** Hook for fetching contact's journal events with infinite scrolling */
export function useContactJournalEvents(contactId: string) {
  return useInfiniteQuery({
    queryKey: ['contacts', contactId, 'journal-events'],
    queryFn: ({ pageParam = 1 }) => getContactJournalEvents(contactId, pageParam),
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return undefined
      const url = new URL(lastPage.next)
      return parseInt(url.searchParams.get('page') || '1')
    },
    initialPageParam: 1,
    enabled: !!contactId,
  })
}

/** Hook for checking duplicates before creation */
export function useCheckDuplicates() {
  return useMutation({
    mutationFn: (data: { first_name?: string; last_name?: string; email?: string; phone?: string }) =>
      checkDuplicates(data),
  })
}

/** Hook for merging contacts */
export function useMergeContacts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MergeRequest) => mergeContacts(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["duplicates"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

/** Hook for dismissing a duplicate pair */
export function useDismissDuplicate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DismissRequest) => dismissDuplicate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] })
    },
  })
}
