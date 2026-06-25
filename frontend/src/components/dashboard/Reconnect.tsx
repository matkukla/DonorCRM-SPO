import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { UserPlus } from "lucide-react"
import type { ReconnectContact } from "@/api/dashboard"

interface ReconnectProps {
  contacts: ReconnectContact[]
  totalCount: number
  isLoading?: boolean
}

function lastTouchLabel(contact: ReconnectContact): string {
  if (contact.days_since_contact === null) return "Never contacted"
  return `${contact.days_since_contact} days ago`
}

export function Reconnect({ contacts, totalCount, isLoading }: ReconnectProps) {
  return (
    <Card>
      <CardHeader className="p-4 pl-7">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <UserPlus className="h-4 w-4 text-primary shrink-0" />
            <div>
              <CardTitle>Reconnect</CardTitle>
              <CardDescription>Donors you haven't talked to recently</CardDescription>
            </div>
          </div>
          {totalCount > 0 && (
            <Link
              to="/contacts?preset=not-contacted-recently"
              className="text-sm text-primary hover:underline shrink-0"
            >
              See all
            </Link>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-4 pl-7 pt-0 pb-4">
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                <div className="h-4 w-20 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : contacts.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            You're in touch with everyone
          </p>
        ) : (
          <div className="space-y-1">
            {contacts.map((contact) => (
              <div
                key={contact.contact_id}
                className="flex items-center justify-between py-2 border-b border-border last:border-0 -mx-2 px-2 rounded"
              >
                <Link
                  to={`/contacts/${contact.contact_id}`}
                  className="text-sm font-medium text-primary hover:underline truncate"
                >
                  {contact.contact_name}
                </Link>
                <span className="text-sm text-muted-foreground shrink-0 ml-2">
                  {lastTouchLabel(contact)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
