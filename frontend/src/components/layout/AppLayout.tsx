import type { ReactNode } from "react"
import { Sidebar } from "./Sidebar"
import { Header } from "./Header"
import { ViewAsBanner } from "./ViewAsBanner"
import { FeedbackDialogProvider } from "@/components/feedback/FeedbackDialogContext"

interface AppLayoutProps {
  children: ReactNode
}

/**
 * Main application layout with sidebar and header
 */
export function AppLayout({ children }: AppLayoutProps) {
  return (
    <FeedbackDialogProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Sidebar - hidden on mobile */}
        <div className="hidden lg:flex lg:w-64 lg:flex-col">
          <Sidebar />
        </div>

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <ViewAsBanner />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
    </FeedbackDialogProvider>
  )
}
