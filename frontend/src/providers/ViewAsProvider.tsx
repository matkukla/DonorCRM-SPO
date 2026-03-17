import { createContext, useContext, useState, useCallback } from "react"
import type { ReactNode } from "react"
import { queryClient } from "@/providers/QueryProvider"

export const VIEW_AS_USER_ID_KEY = "donorcrm_view_as_user_id"
export const VIEW_AS_USER_NAME_KEY = "donorcrm_view_as_user_name"

interface ViewAsContextType {
  viewAsUserId: string | null
  viewAsUserName: string | null
  setViewAsUser: (id: string, name: string) => void
  exitViewAs: () => void
  isViewingAs: boolean
}

const ViewAsContext = createContext<ViewAsContextType | undefined>(undefined)

interface ViewAsProviderProps {
  children: ReactNode
}

export function ViewAsProvider({ children }: ViewAsProviderProps) {
  const [viewAsUserId, setViewAsUserId] = useState<string | null>(
    () => sessionStorage.getItem(VIEW_AS_USER_ID_KEY)
  )
  const [viewAsUserName, setViewAsUserName] = useState<string | null>(
    () => sessionStorage.getItem(VIEW_AS_USER_NAME_KEY)
  )

  const setViewAsUser = useCallback((id: string, name: string) => {
    sessionStorage.setItem(VIEW_AS_USER_ID_KEY, id)
    sessionStorage.setItem(VIEW_AS_USER_NAME_KEY, name)
    setViewAsUserId(id)
    setViewAsUserName(name)
    queryClient.clear()
  }, [])

  const exitViewAs = useCallback(() => {
    sessionStorage.removeItem(VIEW_AS_USER_ID_KEY)
    sessionStorage.removeItem(VIEW_AS_USER_NAME_KEY)
    setViewAsUserId(null)
    setViewAsUserName(null)
    queryClient.clear()
  }, [])

  const value: ViewAsContextType = {
    viewAsUserId,
    viewAsUserName,
    setViewAsUser,
    exitViewAs,
    isViewingAs: viewAsUserId !== null,
  }

  return <ViewAsContext.Provider value={value}>{children}</ViewAsContext.Provider>
}

export function useViewAs(): ViewAsContextType {
  const context = useContext(ViewAsContext)
  if (context === undefined) {
    throw new Error("useViewAs must be used within a ViewAsProvider")
  }
  return context
}
