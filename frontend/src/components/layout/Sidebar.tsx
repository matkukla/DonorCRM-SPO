import * as React from "react"
import { NavLink, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Users,
  DollarSign,
  FileText,
  CheckSquare,
  UsersRound,
  Settings,
  ShieldCheck,
  FileUp,
  BarChart3,
  ChevronDown,
  BookOpen,
  Calendar,
  CalendarDays,
  TrendingUp,
  AlertCircle,
  ListTodo,
  ClipboardCheck,
  Receipt,
} from "lucide-react"
import { useAuth } from "@/providers/AuthProvider"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  requiredRole?: "admin" | "staff" | "finance" | "read_only"
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: <LayoutDashboard className="h-5 w-5" /> },
  { label: "Contacts", href: "/contacts", icon: <Users className="h-5 w-5" /> },
  { label: "Donations", href: "/donations", icon: <DollarSign className="h-5 w-5" /> },
  { label: "Pledges", href: "/pledges", icon: <FileText className="h-5 w-5" /> },
  { label: "Tasks", href: "/tasks", icon: <CheckSquare className="h-5 w-5" /> },
  { label: "Groups", href: "/groups", icon: <UsersRound className="h-5 w-5" /> },
]

const insightsItems: NavItem[] = [
  { label: "Journals", href: "/journals", icon: <BookOpen className="h-4 w-4" /> },
  { label: "Donations by Month", href: "/insights/donations-by-month", icon: <Calendar className="h-4 w-4" /> },
  { label: "Donations by Year", href: "/insights/donations-by-year", icon: <CalendarDays className="h-4 w-4" /> },
  { label: "Monthly Commitments", href: "/insights/monthly-commitments", icon: <TrendingUp className="h-4 w-4" /> },
  { label: "Late Donations", href: "/insights/late-donations", icon: <AlertCircle className="h-4 w-4" /> },
  { label: "Follow-ups", href: "/insights/follow-ups", icon: <ListTodo className="h-4 w-4" /> },
  { label: "Review Queue", href: "/insights/review-queue", icon: <ClipboardCheck className="h-4 w-4" />, requiredRole: "admin" },
  { label: "Transactions", href: "/insights/transactions", icon: <Receipt className="h-4 w-4" />, requiredRole: "admin" },
]

const bottomNavItems: NavItem[] = [
  { label: "Import/Export", href: "/import-export", icon: <FileUp className="h-5 w-5" /> },
  { label: "Settings", href: "/settings", icon: <Settings className="h-5 w-5" /> },
  { label: "Admin", href: "/admin", icon: <ShieldCheck className="h-5 w-5" />, requiredRole: "admin" },
]

interface SidebarProps {
  className?: string
  onNavClick?: () => void
}

const INSIGHTS_OPEN_KEY = "insights-nav-open"

export function Sidebar({ className, onNavClick }: SidebarProps) {
  const { user } = useAuth()
  const location = useLocation()

  // Check if any insights route is active
  const isInsightsActive = location.pathname.startsWith("/insights") || location.pathname === "/journals"

  // Persist open state in localStorage
  const [isInsightsOpen, setIsInsightsOpen] = React.useState(() => {
    const stored = localStorage.getItem(INSIGHTS_OPEN_KEY)
    return stored !== null ? stored === "true" : isInsightsActive
  })

  // Update localStorage when state changes
  React.useEffect(() => {
    localStorage.setItem(INSIGHTS_OPEN_KEY, String(isInsightsOpen))
  }, [isInsightsOpen])

  // Auto-expand when navigating to insights route
  React.useEffect(() => {
    if (isInsightsActive && !isInsightsOpen) {
      setIsInsightsOpen(true)
    }
  }, [isInsightsActive, isInsightsOpen])

  const canAccess = (item: NavItem) => {
    if (!item.requiredRole) return true
    if (!user) return false
    const roleHierarchy: Record<string, number> = { admin: 4, finance: 3, staff: 2, read_only: 1 }
    return roleHierarchy[user.role] >= roleHierarchy[item.requiredRole]
  }

  const filteredInsightsItems = insightsItems.filter(canAccess)

  return (
    <aside className={cn("flex flex-col h-full bg-white border-r border-border", className)}>
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-border">
        <span className="text-xl font-semibold text-primary">DonorCRM</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-3">
          {navItems.map((item) => (
            <li key={item.href}>
              <NavLink
                to={item.href}
                onClick={onNavClick}
                end={item.href === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            </li>
          ))}

          {/* Insights Dropdown */}
          <li>
            <Collapsible open={isInsightsOpen} onOpenChange={setIsInsightsOpen}>
              <CollapsibleTrigger
                className={cn(
                  "flex items-center justify-between w-full gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isInsightsActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <span className="flex items-center gap-3">
                  <BarChart3 className="h-5 w-5" />
                  Insights
                </span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 transition-transform duration-200",
                    isInsightsOpen && "rotate-180"
                  )}
                />
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-1 ml-4 space-y-1">
                {filteredInsightsItems.map((item) => (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    onClick={onNavClick}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                        isActive
                          ? "bg-primary/10 text-primary font-medium"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )
                    }
                  >
                    {item.icon}
                    {item.label}
                  </NavLink>
                ))}
              </CollapsibleContent>
            </Collapsible>
          </li>
        </ul>
      </nav>

      {/* Bottom Navigation */}
      <div className="border-t border-border py-4">
        <ul className="space-y-1 px-3">
          {bottomNavItems.filter(canAccess).map((item) => (
            <li key={item.href}>
              <NavLink
                to={item.href}
                onClick={onNavClick}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}
