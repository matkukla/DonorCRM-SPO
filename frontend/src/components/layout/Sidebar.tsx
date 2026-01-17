import { NavLink } from "react-router-dom"
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
} from "lucide-react"
import { useAuth } from "@/providers/AuthProvider"

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

const bottomNavItems: NavItem[] = [
  { label: "Import/Export", href: "/import-export", icon: <FileUp className="h-5 w-5" /> },
  { label: "Settings", href: "/settings", icon: <Settings className="h-5 w-5" /> },
  { label: "Admin", href: "/admin", icon: <ShieldCheck className="h-5 w-5" />, requiredRole: "admin" },
]

interface SidebarProps {
  className?: string
  onNavClick?: () => void
}

export function Sidebar({ className, onNavClick }: SidebarProps) {
  const { user } = useAuth()

  const canAccess = (item: NavItem) => {
    if (!item.requiredRole) return true
    if (!user) return false
    const roleHierarchy: Record<string, number> = { admin: 4, finance: 3, staff: 2, read_only: 1 }
    return roleHierarchy[user.role] >= roleHierarchy[item.requiredRole]
  }

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
