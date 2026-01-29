import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useJournals } from "@/hooks/useJournals"
import { BookOpen, ChevronRight } from "lucide-react"

export default function JournalList() {
  const { data, isLoading, error } = useJournals()

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Journals</h1>
            <p className="text-muted-foreground mt-1">
              Your fundraising pipeline journals
            </p>
          </div>

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
                        Created {new Date(journal.created_at).toLocaleDateString()}
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
      </Container>
    </Section>
  )
}
