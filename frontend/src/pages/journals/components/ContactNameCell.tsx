import * as React from "react"

export interface ContactNameCellProps {
  /** Contact display name */
  name: string
  /** Contact email (optional) */
  email: string | null
  /** Contact status (for potential future badge) */
  status: string
}

/**
 * Contact name cell for the sticky first column.
 * Memoized to prevent re-renders when other cells change.
 */
export const ContactNameCell = React.memo<ContactNameCellProps>(
  ({ name, email }) => {
    return (
      <div className="flex flex-col min-w-[180px]">
        <span className="font-medium text-sm truncate">{name}</span>
        {email && (
          <span className="text-xs text-muted-foreground truncate">{email}</span>
        )}
      </div>
    )
  }
)

ContactNameCell.displayName = "ContactNameCell"
