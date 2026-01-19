import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getGroups,
  getGroup,
  createGroup,
  updateGroup,
  deleteGroup,
  getGroupContacts,
  addContactsToGroup,
  removeContactsFromGroup,
} from "@/api/groups"
import type { GroupCreate, GroupUpdate } from "@/api/groups"

export function useGroups() {
  return useQuery({
    queryKey: ["groups"],
    queryFn: () => getGroups(),
  })
}

export function useGroup(id: string) {
  return useQuery({
    queryKey: ["groups", id],
    queryFn: () => getGroup(id),
    enabled: !!id && id !== "undefined",
  })
}

export function useCreateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: GroupCreate) => createGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
    },
  })
}

export function useUpdateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GroupUpdate }) => updateGroup(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["groups", id] })
    },
  })
}

export function useDeleteGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteGroup(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
    },
  })
}

export function useGroupContacts(groupId: string) {
  return useQuery({
    queryKey: ["groups", groupId, "contacts"],
    queryFn: () => getGroupContacts(groupId),
    enabled: !!groupId && groupId !== "undefined",
  })
}

export function useAddContactsToGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ groupId, contactIds }: { groupId: string; contactIds: string[] }) =>
      addContactsToGroup(groupId, contactIds),
    onSuccess: (_, { groupId }) => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["groups", groupId] })
      queryClient.invalidateQueries({ queryKey: ["groups", groupId, "contacts"] })
    },
  })
}

export function useRemoveContactsFromGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ groupId, contactIds }: { groupId: string; contactIds: string[] }) =>
      removeContactsFromGroup(groupId, contactIds),
    onSuccess: (_, { groupId }) => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["groups", groupId] })
      queryClient.invalidateQueries({ queryKey: ["groups", groupId, "contacts"] })
    },
  })
}
