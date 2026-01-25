import {
  useQuery,
  useMutation,
  useInfiniteQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  getJournals,
  getJournal,
  createJournal,
  updateJournal,
  archiveJournal,
  getJournalMembers,
  getStageEvents,
  createStageEvent,
  createDecision,
  updateDecision,
  deleteDecision,
  getNextSteps,
  createNextStep,
  updateNextStep,
  deleteNextStep,
} from "@/api/journals"
import type {
  JournalFilters,
  JournalCreate,
  JournalUpdate,
  JournalMemberFilters,
  StageEventCreate,
} from "@/api/journals"
import type {
  PipelineStage,
  DecisionCreate,
  DecisionUpdate,
  JournalMember,
} from "@/types/journals"
import { toast } from "sonner"

interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Hook for fetching paginated journal list */
export function useJournals(filters: JournalFilters = {}) {
  return useQuery({
    queryKey: ["journals", filters],
    queryFn: () => getJournals(filters),
  })
}

/** Hook for fetching single journal */
export function useJournal(id: string) {
  return useQuery({
    queryKey: ["journals", id],
    queryFn: () => getJournal(id),
    enabled: !!id,
  })
}

/** Hook for creating a journal */
export function useCreateJournal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: JournalCreate) => createJournal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journals"] })
    },
  })
}

/** Hook for updating a journal */
export function useUpdateJournal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: JournalUpdate }) =>
      updateJournal(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["journals"] })
      queryClient.invalidateQueries({ queryKey: ["journals", id] })
    },
  })
}

/** Hook for archiving a journal */
export function useArchiveJournal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => archiveJournal(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journals"] })
    },
  })
}

/** Hook for fetching journal members with stage event summaries */
export function useJournalMembers(
  journalId: string,
  filters: Omit<JournalMemberFilters, 'journal'> = {}
) {
  return useQuery({
    queryKey: ["journals", journalId, "members", filters],
    queryFn: () => getJournalMembers(journalId, filters),
    enabled: !!journalId,
  })
}

/**
 * Hook for fetching stage events with infinite scroll pagination.
 * Used in EventTimelineDrawer for "Load More" functionality.
 *
 * Per RESEARCH.md: useInfiniteQuery with getNextPageParam for paginated timeline.
 */
export function useStageEventsInfinite(
  journalContactId: string,
  stage?: PipelineStage,
  options: { enabled?: boolean; pageSize?: number } = {}
) {
  const { enabled = true, pageSize = 5 } = options

  return useInfiniteQuery({
    queryKey: ["stage-events", journalContactId, stage],
    queryFn: ({ pageParam = 1 }) =>
      getStageEvents({
        journalContactId,
        stage,
        page: pageParam,
        pageSize,
      }),
    getNextPageParam: (lastPage) => {
      // DRF pagination returns `next` URL if there are more pages
      if (lastPage.next) {
        // Extract page number from URL (e.g., "...?page=2")
        const url = new URL(lastPage.next)
        const nextPage = url.searchParams.get('page')
        return nextPage ? parseInt(nextPage, 10) : undefined
      }
      return undefined
    },
    initialPageParam: 1,
    enabled: enabled && !!journalContactId,
  })
}

/** Hook for creating a stage event */
export function useCreateStageEvent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: StageEventCreate) => createStageEvent(data),
    onSuccess: (_, variables) => {
      // Invalidate both the specific stage query and any all-events query
      queryClient.invalidateQueries({
        queryKey: ["stage-events", variables.journal_contact],
      })
      // Also invalidate journal members to update stage event summaries
      queryClient.invalidateQueries({
        queryKey: ["journals"],
        refetchType: "active",
      })
    },
  })
}

/**
 * Hook for creating a decision with cache update.
 * After creation, invalidates members list to show new decision.
 */
export function useCreateDecision(journalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DecisionCreate) => createDecision(data),
    onSuccess: () => {
      toast.success("Decision created")
      // Invalidate members to refetch with new decision
      queryClient.invalidateQueries({
        queryKey: ["journals", journalId, "members"],
      })
    },
    onError: () => {
      toast.error("Failed to create decision")
    },
  })
}

/**
 * Hook for updating a decision with optimistic updates.
 *
 * Critical pattern from STATE.md:
 * "Optimistic update rollback on error (use React Query mutation onError callbacks)"
 *
 * Flow:
 * 1. onMutate: Cancel queries, snapshot cache, optimistically update
 * 2. onError: Rollback to snapshot
 * 3. onSettled: Invalidate to sync with server
 */
export function useUpdateDecision(journalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DecisionUpdate }) =>
      updateDecision(id, data),

    onMutate: async ({ id, data }) => {
      // 1. Cancel outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({
        queryKey: ["journals", journalId, "members"],
      })

      // 2. Snapshot current cache for rollback
      const previousMembers = queryClient.getQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}]
      )

      // 3. Optimistically update the cache
      if (previousMembers) {
        queryClient.setQueryData<PaginatedResponse<JournalMember>>(
          ["journals", journalId, "members", {}],
          (old) => {
            if (!old) return old
            return {
              ...old,
              results: old.results.map((member) => {
                if (member.decision?.id === id) {
                  return {
                    ...member,
                    decision: { ...member.decision, ...data },
                  }
                }
                return member
              }),
            }
          }
        )
      }

      // 4. Return context with snapshot for rollback
      return { previousMembers }
    },

    onError: (_err, _variables, context) => {
      // Rollback to snapshot on error
      if (context?.previousMembers) {
        queryClient.setQueryData(
          ["journals", journalId, "members", {}],
          context.previousMembers
        )
      }
      toast.error("Failed to update decision")
    },

    onSuccess: () => {
      toast.success("Decision updated")
    },

    onSettled: () => {
      // Always refetch to ensure cache matches server
      queryClient.invalidateQueries({
        queryKey: ["journals", journalId, "members"],
      })
    },
  })
}

/**
 * Hook for deleting a decision with optimistic removal.
 */
export function useDeleteDecision(journalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteDecision(id),

    onMutate: async (id) => {
      await queryClient.cancelQueries({
        queryKey: ["journals", journalId, "members"],
      })

      const previousMembers = queryClient.getQueryData<PaginatedResponse<JournalMember>>(
        ["journals", journalId, "members", {}]
      )

      if (previousMembers) {
        queryClient.setQueryData<PaginatedResponse<JournalMember>>(
          ["journals", journalId, "members", {}],
          (old) => {
            if (!old) return old
            return {
              ...old,
              results: old.results.map((member) => {
                if (member.decision?.id === id) {
                  return { ...member, decision: null }
                }
                return member
              }),
            }
          }
        )
      }

      return { previousMembers }
    },

    onError: (_err, _variables, context) => {
      if (context?.previousMembers) {
        queryClient.setQueryData(
          ["journals", journalId, "members", {}],
          context.previousMembers
        )
      }
      toast.error("Failed to delete decision")
    },

    onSuccess: () => {
      toast.success("Decision deleted")
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["journals", journalId, "members"],
      })
    },
  })
}
