import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useJournals } from "@/hooks/useJournals"
import { useFilterParams, journalFilterParsers } from "@/hooks/useFilterParams"
import { journalPresets } from "@/lib/filter-presets"
import { FilterBar } from "@/components/shared/FilterBar"
import { BookOpen, ChevronRight, Plus, Search, Filter } from "lucide-react"
import { CreateJournalDialog } from "./components"
import { formatLocalDate } from "@/lib/utils"

export default function JournalList() {
  const { filters, setFilters, clearAll, activeFilters, toQueryParams } =
    useFilterParams(journalFilterParsers)

  const [searchInput, setSearchInput] = useState(filters.search || "")

  // Sync search input when URL changes externally (e.g., browser back/forward)
  useEffect(() => {
    setSearchInput(filters.search || "")
  }, [filters.search])

  const queryParams = { ...toQueryParams(), page_size: "50" }
  const { data, isLoading, error } = useJournals(queryParams)

  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ search: searchInput || null, page: 1 })
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Journals</h1>
              <p className="text-muted-foreground mt-1">
                Your fundraising pipeline journals
              </p>
            </div>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Journal
            </Button>
          </div>

          {/* Filters */}
          <FilterBar
            activeFilters={activeFilters}
            onClearAll={clearAll}
            onRemoveFilter={(key) => setFilters({ [key]: null, page: 1 })}
            filterLabels={{
              is_archived: "Archived",
              deadline_after: "Deadline From",
              deadline_before: "Deadline To",
            }}
            presets={journalPresets}
            onApplyPreset={(preset) => setFilters({ ...preset.getParams(), page: 1 })}
            exportUrl="/journals/export/csv/"
            exportParams={toQueryParams()}
          >
            {/* Search input */}
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-[200px]">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by journal name..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            {/* Archived toggle */}
            <Button
              variant={filters.is_archived ? "default" : "secondary"}
              size="sm"
              onClick={() => setFilters({
                is_archived: filters.is_archived ? null : true,
                page: 1,
              })}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              {filters.is_archived ? "Showing Archived" : "Show Archived"}
            </Button>

            {/* Deadline date range */}
            <div className="flex items-center gap-2">
              <Input
                type="date"
                value={filters.deadline_after || ""}
                onChange={(e) => setFilters({ deadline_after: e.target.value || null, page: 1 })}
                className="w-[150px]"
                aria-label="Deadline from"
              />
              <span className="text-muted-foreground text-sm">to</span>
              <Input
                type="date"
                value={filters.deadline_before || ""}
                onChange={(e) => setFilters({ deadline_before: e.target.value || null, page: 1 })}
                className="w-[150px]"
                aria-label="Deadline to"
              />
            </div>
          </FilterBar>

          {error && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive">
              Failed to load journals. Please try again.
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              Loading...
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data?.results.map((journal) => (
                <Card key={journal.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <BookOpen className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-lg">{journal.name}</CardTitle>
                        {journal.description && (
                          <CardDescription className="line-clamp-2">
                            {journal.description}
                          </CardDescription>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        Created {formatLocalDate(journal.created_at)}
                      </span>
                      <Link to={`/journals/${journal.id}`}>
                        <Button variant="ghost" size="sm">
                          View
                          <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {data?.results.length === 0 && (
                <div className="col-span-full text-center py-12 text-muted-foreground">
                  <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No journals yet.</p>
                  <p className="text-sm mt-1">
                    Create your first journal to start tracking your fundraising pipeline.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Create Journal Dialog */}
        <CreateJournalDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
      </Container>
    </Section>
  )
}
