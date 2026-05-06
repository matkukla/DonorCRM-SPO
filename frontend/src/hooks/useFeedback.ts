import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import {
  createFeedbackEntry,
  deleteFeedbackEntry,
  getFeedbackEntries,
  getFeedbackEntry,
  updateFeedbackEntry,
} from "@/api/feedback"
import type {
  FeedbackEntryCreate,
  FeedbackEntryUpdate,
} from "@/api/feedback"

const FEEDBACK_KEY = ["feedback"] as const

export function useFeedbackEntries(params: Record<string, string> = {}) {
  return useQuery({
    queryKey: [...FEEDBACK_KEY, params],
    queryFn: () => getFeedbackEntries(params),
  })
}

export function useFeedbackEntry(id: string | null) {
  return useQuery({
    queryKey: [...FEEDBACK_KEY, id],
    queryFn: () => getFeedbackEntry(id!),
    enabled: !!id,
  })
}

export function useCreateFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: FeedbackEntryCreate) => createFeedbackEntry(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FEEDBACK_KEY })
      toast.success("Thanks! Your feedback has been sent.")
    },
    onError: () => {
      toast.error("Failed to send feedback. Please try again.")
    },
  })
}

export function useUpdateFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: FeedbackEntryUpdate }) =>
      updateFeedbackEntry(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FEEDBACK_KEY })
      toast.success("Feedback updated")
    },
    onError: () => {
      toast.error("Failed to update feedback")
    },
  })
}

export function useDeleteFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteFeedbackEntry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FEEDBACK_KEY })
      toast.success("Feedback deleted")
    },
    onError: () => {
      toast.error("Failed to delete feedback")
    },
  })
}
