import { createContext, useContext, useState, type ReactNode } from "react"

import { SendFeedbackDialog } from "./SendFeedbackDialog"

interface FeedbackDialogContextValue {
  openFeedback: () => void
}

const FeedbackDialogContext = createContext<FeedbackDialogContextValue | null>(
  null,
)

export function FeedbackDialogProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)

  return (
    <FeedbackDialogContext.Provider value={{ openFeedback: () => setOpen(true) }}>
      {children}
      <SendFeedbackDialog open={open} onOpenChange={setOpen} />
    </FeedbackDialogContext.Provider>
  )
}

export function useFeedbackDialog(): FeedbackDialogContextValue {
  const ctx = useContext(FeedbackDialogContext)
  if (!ctx) {
    throw new Error(
      "useFeedbackDialog must be used within a FeedbackDialogProvider",
    )
  }
  return ctx
}
