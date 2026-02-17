import type { FallbackProps } from "react-error-boundary"

export function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            Something went wrong
          </h1>
          <p className="text-muted-foreground">
            An unexpected error occurred. Please try refreshing the page.
          </p>
        </div>
        {import.meta.env.DEV && (
          <pre className="text-left text-sm bg-muted p-4 rounded-lg overflow-auto max-h-40">
            {error instanceof Error ? error.message : String(error)}
          </pre>
        )}
        <button
          onClick={resetErrorBoundary}
          className="inline-flex items-center justify-center rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Refresh Page
        </button>
      </div>
    </div>
  )
}
