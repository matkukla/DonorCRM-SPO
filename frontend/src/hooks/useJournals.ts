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
} from "@/api/journals"
import type {
  JournalFilters,
  JournalCreate,
  JournalUpdate,
  JournalMemberFilters,
  StageEventCreate,
} from "@/api/journals"
import type { PipelineStage } from "@/types/journals"

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
