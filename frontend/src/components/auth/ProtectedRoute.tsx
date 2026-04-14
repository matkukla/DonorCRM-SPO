import { useEffect, useRef } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { toast } from "sonner"
import type { ReactNode } from "react"

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: "admin" | "missionary" | "supervisor" | "coach"
}

/**
 * Wrapper component that redirects to login if user is not authenticated.
 * Optionally checks for required role.
 */
export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()
  const toastShown = useRef(false)

  useEffect(() => {
    if (requiredRole && user) {
      const roleHierarchy: Record<string, number> = { admin: 4, supervisor: 3, coach: 2, missionary: 1 }
      const userLevel = roleHierarchy[user.role]
      const requiredLevel = roleHierarchy[requiredRole]
      if (userLevel < requiredLevel && !toastShown.current) {
        toastShown.current = true
        toast.info("You don't have access to that page")
      }
    }
  }, [requiredRole, user])

  // Show nothing while checking auth status
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Redirect to home if insufficient role
  if (requiredRole && user) {
    const roleHierarchy: Record<string, number> = { admin: 4, supervisor: 3, coach: 2, missionary: 1 }
    const userLevel = roleHierarchy[user.role]
    const requiredLevel = roleHierarchy[requiredRole]

    if (userLevel < requiredLevel) {
      return <Navigate to="/" replace />
    }
  }

  return <>{children}</>
}
