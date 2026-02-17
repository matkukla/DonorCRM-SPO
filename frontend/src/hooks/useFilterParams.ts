import { useQueryStates, parseAsString, parseAsBoolean, parseAsInteger } from "nuqs"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FilterParsers = Record<string, any>

/**
 * Shared hook for type-safe URL filter state management.
 * Wraps nuqs useQueryStates with convenience methods for
 * clearing filters, listing active filters, and building API query params.
 */
export function useFilterParams<T extends FilterParsers>(parsers: T) {
  const [filters, setFilters] = useQueryStates(parsers, {
    shallow: false, // trigger React re-render for React Query refetch
  })

  // Clear all filters (reset to null), keeping page at 1
  const clearAll = () => {
    const cleared = Object.fromEntries(
      Object.keys(parsers).map((key) => [key, key === "page" ? 1 : null])
    ) as Parameters<typeof setFilters>[0]
    setFilters(cleared)
  }

  // Get list of active filters (non-null, excluding 'page' and 'search')
  const activeFilters = Object.entries(filters).filter(
    ([key, value]) => value !== null && key !== "page" && key !== "search"
  ) as [string, string | boolean | number][]

  const activeFilterCount = activeFilters.length

  // Build query params object for API calls (filter out nulls)
  const toQueryParams = (): Record<string, string> => {
    const params: Record<string, string> = {}
    for (const [key, value] of Object.entries(filters)) {
      if (value !== null && value !== undefined) {
        params[key] = String(value)
      }
    }
    return params
  }

  return {
    filters,
    setFilters,
    clearAll,
    activeFilters,
    activeFilterCount,
    toQueryParams,
  }
}

// ---------------------------------------------------------------------------
// Per-page parser definitions
// Field names MUST match backend FilterSet field names exactly.
// ---------------------------------------------------------------------------

export const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  needs_thank_you: parseAsBoolean,
  last_gift_after: parseAsString,
  last_gift_before: parseAsString,
  group: parseAsString,
  ordering: parseAsString,
}

export const donationFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  donation_type: parseAsString,
  payment_method: parseAsString,
  thanked: parseAsBoolean,
  date_after: parseAsString,
  date_before: parseAsString,
  ordering: parseAsString,
}

export const pledgeFilterParsers = {
  page: parseAsInteger.withDefault(1),
  status: parseAsString,
  frequency: parseAsString,
  is_late: parseAsBoolean,
  start_date_after: parseAsString,
  start_date_before: parseAsString,
  ordering: parseAsString,
}

export const taskFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  task_type: parseAsString,
  priority: parseAsString,
  due_date_after: parseAsString,
  due_date_before: parseAsString,
  ordering: parseAsString,
}

// Transactions page uses offset-based pagination (insights service)
export const transactionFilterParsers = {
  offset: parseAsInteger.withDefault(0),
  date_from: parseAsString,
  date_to: parseAsString,
}
