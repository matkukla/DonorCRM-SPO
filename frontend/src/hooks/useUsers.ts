import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getUsers,
  getUser,
  createUser,
  updateUser,
  deactivateUser,
  getAssignments,
  updateAssignments,
} from "@/api/users"
import type { UserCreate, UserUpdate, AssignmentUpdate } from "@/api/users"

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: () => getUsers(),
  })
}

export function useUser(id: string) {
  return useQuery({
    queryKey: ["users", id],
    queryFn: () => getUser(id),
    enabled: !!id,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UserCreate) => createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserUpdate }) => updateUser(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      queryClient.invalidateQueries({ queryKey: ["users", id] })
      queryClient.invalidateQueries({ queryKey: ["assignments"] })
    },
  })
}

export function useDeactivateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deactivateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })
}

export function useAssignments() {
  return useQuery({
    queryKey: ['assignments'],
    queryFn: getAssignments,
  })
}

export function useUpdateAssignments() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (assignments: AssignmentUpdate[]) => updateAssignments(assignments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] })
    },
  })
}
