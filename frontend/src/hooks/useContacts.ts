import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
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
} from "@/api/contacts"
import type { ContactFilters, ContactCreate, ContactUpdate } from "@/api/contacts"

export function useContacts(filters: ContactFilters = {}) {
  return useQuery({
    queryKey: ["contacts", filters],
    queryFn: () => getContacts(filters),
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
