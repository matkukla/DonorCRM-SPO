import React, { Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { NuqsAdapter } from "nuqs/adapters/react-router/v6"
import { ErrorBoundary } from "react-error-boundary"
import { Loader2 } from "lucide-react"
import { QueryProvider } from "@/providers/QueryProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ThemeProvider } from "@/providers/ThemeProvider"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { AppLayout } from "@/components/layout/AppLayout"
import { ErrorFallback } from "@/components/ErrorFallback"
import { Toaster } from "@/components/ui/sonner"

// Eagerly loaded pages (lightweight, frequently visited)
import Login from "@/pages/Login"
import Styleguide from "@/pages/Styleguide"
import ContactList from "@/pages/contacts/ContactList"
import ContactDetail from "@/pages/contacts/ContactDetail"
import ContactForm from "@/pages/contacts/ContactForm"
import DonationList from "@/pages/donations/DonationList"
import DonationDetail from "@/pages/donations/DonationDetail"
import DonationForm from "@/pages/donations/DonationForm"
import PledgeList from "@/pages/pledges/PledgeList"
import PledgeDetail from "@/pages/pledges/PledgeDetail"
import PledgeForm from "@/pages/pledges/PledgeForm"
import TaskList from "@/pages/tasks/TaskList"
import TaskDetail from "@/pages/tasks/TaskDetail"
import TaskForm from "@/pages/tasks/TaskForm"
import GroupList from "@/pages/groups/GroupList"
import GroupDetail from "@/pages/groups/GroupDetail"
import GroupForm from "@/pages/groups/GroupForm"
import Settings from "@/pages/settings/Settings"
import AdminUsers from "@/pages/admin/AdminUsers"
import JournalList from "@/pages/journals/JournalList"

// Lazy-loaded pages (heavy: recharts, dnd-kit, complex sub-components)
const Dashboard = React.lazy(() => import("@/pages/Dashboard"))
const JournalDetail = React.lazy(() => import("@/pages/journals/JournalDetail"))
const ImportExport = React.lazy(() => import("@/pages/imports/ImportExport"))
const AdminAnalyticsDashboard = React.lazy(() => import("@/pages/admin/analytics/AdminAnalyticsDashboard"))
const PrayerList = React.lazy(() => import("@/pages/prayer/PrayerList"))
const AdminAssignments = React.lazy(() => import("@/pages/admin/AdminAssignments"))
const TeamPage = React.lazy(() => import("@/pages/team/TeamPage"))
const MissionaryProfilePage = React.lazy(() => import("@/pages/team/MissionaryProfilePage"))

// Lazy-loaded admin analytics sub-pages (recharts, data tables)
const StalledContacts = React.lazy(() => import("@/pages/admin/analytics/StalledContacts"))
const UserDetail = React.lazy(() => import("@/pages/admin/analytics/UserDetail"))

// Lazy-loaded insights pages (recharts charts) -- individual imports for proper code splitting
const DonationsByMonthYear = React.lazy(() => import("@/pages/insights/DonationsByMonthYear"))
const MonthlyCommitments = React.lazy(() => import("@/pages/insights/MonthlyCommitments"))
const LateDonations = React.lazy(() => import("@/pages/insights/LateDonations"))
const FollowUps = React.lazy(() => import("@/pages/insights/FollowUps"))
const Transactions = React.lazy(() => import("@/pages/insights/Transactions"))

/**
 * Loading fallback shown inside the app layout while lazy chunks load.
 */
function PageLoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )
}

/**
 * Wrap a page with protected route and app layout.
 * Suspense boundary is inside the layout so sidebar stays visible during chunk loading.
 */
function ProtectedPage({ children, requiredRole }: { children: React.ReactNode; requiredRole?: "admin" | "missionary" | "finance" | "read_only" | "supervisor" | "coach" }) {
  return (
    <ProtectedRoute requiredRole={requiredRole}>
      <AppLayout>
        <Suspense fallback={<PageLoadingFallback />}>
          {children}
        </Suspense>
      </AppLayout>
    </ProtectedRoute>
  )
}

/**
 * DonorCRM Frontend
 *
 * Routing structure with authentication
 */
function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary FallbackComponent={ErrorFallback} onReset={() => window.location.reload()}>
        <QueryProvider>
          <AuthProvider>
            <BrowserRouter>
              <NuqsAdapter>
              <Routes>
                {/* Public routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/styleguide" element={<Styleguide />} />

                {/* Protected routes with app layout */}
                <Route path="/" element={<ProtectedPage><Dashboard /></ProtectedPage>} />
                <Route path="/contacts" element={<ProtectedPage><ContactList /></ProtectedPage>} />
                <Route path="/contacts/new" element={<ProtectedPage requiredRole="missionary"><ContactForm /></ProtectedPage>} />
                <Route path="/contacts/:id" element={<ProtectedPage><ContactDetail /></ProtectedPage>} />
                <Route path="/contacts/:id/edit" element={<ProtectedPage requiredRole="missionary"><ContactForm /></ProtectedPage>} />
                <Route path="/donations" element={<ProtectedPage><DonationList /></ProtectedPage>} />
                <Route path="/donations/new" element={<ProtectedPage requiredRole="missionary"><DonationForm /></ProtectedPage>} />
                <Route path="/donations/:id" element={<ProtectedPage><DonationDetail /></ProtectedPage>} />
                <Route path="/donations/:id/edit" element={<ProtectedPage requiredRole="missionary"><DonationForm /></ProtectedPage>} />
                <Route path="/pledges" element={<ProtectedPage><PledgeList /></ProtectedPage>} />
                <Route path="/pledges/new" element={<ProtectedPage requiredRole="missionary"><PledgeForm /></ProtectedPage>} />
                <Route path="/pledges/:id" element={<ProtectedPage><PledgeDetail /></ProtectedPage>} />
                <Route path="/pledges/:id/edit" element={<ProtectedPage requiredRole="missionary"><PledgeForm /></ProtectedPage>} />
                <Route path="/tasks" element={<ProtectedPage><TaskList /></ProtectedPage>} />
                <Route path="/tasks/new" element={<ProtectedPage requiredRole="missionary"><TaskForm /></ProtectedPage>} />
                <Route path="/tasks/:id" element={<ProtectedPage><TaskDetail /></ProtectedPage>} />
                <Route path="/tasks/:id/edit" element={<ProtectedPage requiredRole="missionary"><TaskForm /></ProtectedPage>} />
                <Route path="/groups" element={<ProtectedPage><GroupList /></ProtectedPage>} />
                <Route path="/groups/:id" element={<ProtectedPage><GroupDetail /></ProtectedPage>} />
                <Route path="/groups/:id/edit" element={<ProtectedPage requiredRole="missionary"><GroupForm /></ProtectedPage>} />
                <Route path="/journals" element={<ProtectedPage><JournalList /></ProtectedPage>} />
                <Route path="/journals/:id" element={<ProtectedPage><JournalDetail /></ProtectedPage>} />
                <Route path="/prayer" element={<ProtectedPage><PrayerList /></ProtectedPage>} />

                {/* Insights routes */}
                <Route path="/insights/donations-by-month-year" element={<ProtectedPage><DonationsByMonthYear /></ProtectedPage>} />
                <Route path="/insights/monthly-commitments" element={<ProtectedPage><MonthlyCommitments /></ProtectedPage>} />
                <Route path="/insights/late-donations" element={<ProtectedPage><LateDonations /></ProtectedPage>} />
                <Route path="/insights/follow-ups" element={<ProtectedPage><FollowUps /></ProtectedPage>} />
                <Route path="/insights/review-queue" element={<Navigate to="/admin/analytics/dashboard" replace />} />
                <Route path="/insights/transactions" element={<ProtectedPage requiredRole="admin"><Transactions /></ProtectedPage>} />

                <Route path="/settings" element={<ProtectedPage><Settings /></ProtectedPage>} />
                <Route path="/admin" element={<ProtectedPage requiredRole="admin"><AdminUsers /></ProtectedPage>} />
                <Route path="/admin/assignments" element={<ProtectedPage requiredRole="admin"><AdminAssignments /></ProtectedPage>} />
                <Route path="/admin/analytics" element={<Navigate to="/admin/analytics/dashboard" replace />} />
                <Route path="/admin/analytics/dashboard" element={<ProtectedPage requiredRole="admin"><AdminAnalyticsDashboard /></ProtectedPage>} />
                <Route path="/admin/analytics/stalled" element={<ProtectedPage requiredRole="admin"><StalledContacts /></ProtectedPage>} />
                <Route path="/admin/analytics/users/:id" element={<ProtectedPage requiredRole="admin"><UserDetail /></ProtectedPage>} />
                <Route path="/team" element={<ProtectedPage requiredRole="missionary"><TeamPage /></ProtectedPage>} />
                <Route path="/team/:userId" element={<ProtectedPage requiredRole="missionary"><MissionaryProfilePage /></ProtectedPage>} />
                <Route path="/import-export" element={<ProtectedPage requiredRole="missionary"><ImportExport /></ProtectedPage>} />

                {/* Catch-all redirect */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
              </NuqsAdapter>
            </BrowserRouter>
            <Toaster position="bottom-right" />
          </AuthProvider>
        </QueryProvider>
      </ErrorBoundary>
    </ThemeProvider>
  )
}

export default App
