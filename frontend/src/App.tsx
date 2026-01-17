import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryProvider } from "@/providers/QueryProvider"
import { AuthProvider } from "@/providers/AuthProvider"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { AppLayout } from "@/components/layout/AppLayout"

// Pages
import Login from "@/pages/Login"
import Dashboard from "@/pages/Dashboard"
import Styleguide from "@/pages/Styleguide"
import ContactList from "@/pages/contacts/ContactList"
import ContactDetail from "@/pages/contacts/ContactDetail"
import ContactForm from "@/pages/contacts/ContactForm"
import DonationList from "@/pages/donations/DonationList"
import PledgeList from "@/pages/pledges/PledgeList"
import TaskList from "@/pages/tasks/TaskList"
import GroupList from "@/pages/groups/GroupList"
import Settings from "@/pages/settings/Settings"
import AdminUsers from "@/pages/admin/AdminUsers"

/**
 * Wrap a page with protected route and app layout
 */
function ProtectedPage({ children, requiredRole }: { children: React.ReactNode; requiredRole?: "admin" | "staff" | "viewer" }) {
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
            <Route path="/pledges" element={<ProtectedPage><PledgeList /></ProtectedPage>} />
            <Route path="/tasks" element={<ProtectedPage><TaskList /></ProtectedPage>} />
            <Route path="/groups" element={<ProtectedPage><GroupList /></ProtectedPage>} />
            <Route path="/settings" element={<ProtectedPage><Settings /></ProtectedPage>} />
            <Route path="/admin" element={<ProtectedPage requiredRole="admin"><AdminUsers /></ProtectedPage>} />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryProvider>
  )
}

export default App
