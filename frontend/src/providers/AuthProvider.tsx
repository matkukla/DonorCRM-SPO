import { createContext, useContext, useState, useEffect, useCallback } from "react"
import type { ReactNode } from "react"
import { login as apiLogin, logout as apiLogout, getCurrentUser, hasStoredAuth } from "@/api/auth"
import type { User, LoginCredentials } from "@/api/auth"

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  error: string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check for existing auth on mount
  useEffect(() => {
    const initAuth = async () => {
      if (hasStoredAuth()) {
        try {
          const currentUser = await getCurrentUser()
          setUser(currentUser)
        } catch {
          // Token invalid or expired, clear it
          apiLogout()
        }
      }
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    setError(null)
    setIsLoading(true)
    try {
      const loggedInUser = await apiLogin(credentials)
      setUser(loggedInUser)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed"
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    apiLogout()
    setUser(null)
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    error,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
