import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryProvider } from "@/providers/QueryProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { AppLayout } from "@/components/layout/AppLayout"
import { Toaster } from "@/components/ui/sonner"

// Pages
import Login from "@/pages/Login"
import Dashboard from "@/pages/Dashboard"
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
import ImportExport from "@/pages/imports/ImportExport"
import JournalDetail from "@/pages/journals/JournalDetail"
import JournalList from "@/pages/journals/JournalList"
import {
  DonationsByMonth,
  DonationsByYear,
  MonthlyCommitments,
  LateDonations,
  FollowUps,
  ReviewQueue,
  Transactions,
} from "@/pages/insights"

/**
 * Wrap a page with protected route and app layout
 */
function ProtectedPage({ children, requiredRole }: { children: React.ReactNode; requiredRole?: "admin" | "staff" | "finance" | "read_only" }) {
  return (
    <ProtectedRoute requiredRole={requiredRole}>
      <AppLayout>{children}</AppLayout>
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
    <QueryProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/styleguide" element={<Styleguide />} />

            {/* Protected routes with app layout */}
            <Route path="/" element={<ProtectedPage><Dashboard /></ProtectedPage>} />
            <Route path="/contacts" element={<ProtectedPage><ContactList /></ProtectedPage>} />
            <Route path="/contacts/new" element={<ProtectedPage><ContactForm /></ProtectedPage>} />
            <Route path="/contacts/:id" element={<ProtectedPage><ContactDetail /></ProtectedPage>} />
            <Route path="/contacts/:id/edit" element={<ProtectedPage><ContactForm /></ProtectedPage>} />
            <Route path="/donations" element={<ProtectedPage><DonationList /></ProtectedPage>} />
            <Route path="/donations/new" element={<ProtectedPage><DonationForm /></ProtectedPage>} />
            <Route path="/donations/:id" element={<ProtectedPage><DonationDetail /></ProtectedPage>} />
            <Route path="/donations/:id/edit" element={<ProtectedPage><DonationForm /></ProtectedPage>} />
            <Route path="/pledges" element={<ProtectedPage><PledgeList /></ProtectedPage>} />
            <Route path="/pledges/new" element={<ProtectedPage><PledgeForm /></ProtectedPage>} />
            <Route path="/pledges/:id" element={<ProtectedPage><PledgeDetail /></ProtectedPage>} />
            <Route path="/pledges/:id/edit" element={<ProtectedPage><PledgeForm /></ProtectedPage>} />
            <Route path="/tasks" element={<ProtectedPage><TaskList /></ProtectedPage>} />
            <Route path="/tasks/new" element={<ProtectedPage><TaskForm /></ProtectedPage>} />
            <Route path="/tasks/:id" element={<ProtectedPage><TaskDetail /></ProtectedPage>} />
            <Route path="/tasks/:id/edit" element={<ProtectedPage><TaskForm /></ProtectedPage>} />
            <Route path="/groups" element={<ProtectedPage><GroupList /></ProtectedPage>} />
            <Route path="/groups/:id" element={<ProtectedPage><GroupDetail /></ProtectedPage>} />
            <Route path="/groups/:id/edit" element={<ProtectedPage><GroupForm /></ProtectedPage>} />
            <Route path="/journals" element={<ProtectedPage><JournalList /></ProtectedPage>} />
            <Route path="/journals/:id" element={<ProtectedPage><JournalDetail /></ProtectedPage>} />

            {/* Insights routes */}
            <Route path="/insights/donations-by-month" element={<ProtectedPage><DonationsByMonth /></ProtectedPage>} />
            <Route path="/insights/donations-by-year" element={<ProtectedPage><DonationsByYear /></ProtectedPage>} />
            <Route path="/insights/monthly-commitments" element={<ProtectedPage><MonthlyCommitments /></ProtectedPage>} />
            <Route path="/insights/late-donations" element={<ProtectedPage><LateDonations /></ProtectedPage>} />
            <Route path="/insights/follow-ups" element={<ProtectedPage><FollowUps /></ProtectedPage>} />
            <Route path="/insights/review-queue" element={<ProtectedPage requiredRole="admin"><ReviewQueue /></ProtectedPage>} />
            <Route path="/insights/transactions" element={<ProtectedPage requiredRole="admin"><Transactions /></ProtectedPage>} />

            <Route path="/settings" element={<ProtectedPage><Settings /></ProtectedPage>} />
            <Route path="/admin" element={<ProtectedPage requiredRole="admin"><AdminUsers /></ProtectedPage>} />
            <Route path="/import-export" element={<ProtectedPage><ImportExport /></ProtectedPage>} />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </AuthProvider>
    </QueryProvider>
  )
}

export default App
