import { useState } from "react"
import { useUsers, useCreateUser, useUpdateUser, useDeactivateUser } from "@/hooks/useUsers"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, MoreHorizontal, UserX, Edit, ChevronDown } from "lucide-react"
import type { User, UserRole } from "@/api/users"
import { userRoleLabels } from "@/api/users"

const roleVariants: Record<UserRole, "default" | "secondary" | "success" | "warning" | "info" | "destructive"> = {
  admin: "destructive",
  staff: "default",
  viewer: "secondary",
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never"
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default function AdminUsers() {
  const { data: users, isLoading } = useUsers()
  const createMutation = useCreateUser()
  const updateMutation = useUpdateUser()
  const deactivateMutation = useDeactivateUser()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)

  // Create form state
  const [newEmail, setNewEmail] = useState("")
  const [newFirstName, setNewFirstName] = useState("")
  const [newLastName, setNewLastName] = useState("")
  const [newRole, setNewRole] = useState<UserRole>("staff")
  const [newPassword, setNewPassword] = useState("")
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("")
  const [createError, setCreateError] = useState("")

  // Edit form state
  const [editFirstName, setEditFirstName] = useState("")
  const [editLastName, setEditLastName] = useState("")
  const [editRole, setEditRole] = useState<UserRole>("staff")
  const [editError, setEditError] = useState("")

  const resetCreateForm = () => {
    setNewEmail("")
    setNewFirstName("")
    setNewLastName("")
    setNewRole("staff")
    setNewPassword("")
    setNewPasswordConfirm("")
    setCreateError("")
  }

  const handleCreate = async () => {
    setCreateError("")

    if (!newEmail || !newFirstName || !newLastName || !newPassword) {
      setCreateError("Please fill in all required fields.")
      return
    }

    if (newPassword !== newPasswordConfirm) {
      setCreateError("Passwords do not match.")
      return
    }

    if (newPassword.length < 8) {
      setCreateError("Password must be at least 8 characters.")
      return
    }

    try {
      await createMutation.mutateAsync({
        email: newEmail,
        first_name: newFirstName,
        last_name: newLastName,
        role: newRole,
        password: newPassword,
        password_confirm: newPasswordConfirm,
      })
      setIsCreateOpen(false)
      resetCreateForm()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { email?: string[]; password?: string[] } } }
      const emailError = error.response?.data?.email?.[0]
      const passwordError = error.response?.data?.password?.[0]
      setCreateError(emailError || passwordError || "Failed to create user.")
    }
  }

  const openEditDialog = (user: User) => {
    setEditingUser(user)
    setEditFirstName(user.first_name)
    setEditLastName(user.last_name)
    setEditRole(user.role)
    setEditError("")
  }

  const handleUpdate = async () => {
    if (!editingUser) return
    setEditError("")

    try {
      await updateMutation.mutateAsync({
        id: editingUser.id,
        data: {
          first_name: editFirstName,
          last_name: editLastName,
          role: editRole,
        },
      })
      setEditingUser(null)
    } catch {
      setEditError("Failed to update user.")
    }
  }

  const handleDeactivate = (user: User) => {
    if (window.confirm(`Are you sure you want to deactivate ${user.full_name}? They will no longer be able to log in.`)) {
      deactivateMutation.mutate(user.id)
    }
  }

  const handleReactivate = (user: User) => {
    updateMutation.mutate({
      id: user.id,
      data: { is_active: true },
    })
  }

  if (isLoading) {
    return (
      <Section>
        <Container>
          <div className="space-y-6">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </Container>
      </Section>
    )
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">User Management</h1>
              <p className="text-muted-foreground mt-1">
                Manage system users and their roles
              </p>
            </div>
            <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => resetCreateForm()}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add User
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New User</DialogTitle>
                  <DialogDescription>
                    Create a new user account
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder="user@example.com"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="firstName">First Name *</Label>
                      <Input
                        id="firstName"
                        value={newFirstName}
                        onChange={(e) => setNewFirstName(e.target.value)}
                        placeholder="First name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lastName">Last Name *</Label>
                      <Input
                        id="lastName"
                        value={newLastName}
                        onChange={(e) => setNewLastName(e.target.value)}
                        placeholder="Last name"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="secondary" className="w-full justify-between">
                          {userRoleLabels[newRole]}
                          <ChevronDown className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent className="w-full">
                        {(Object.keys(userRoleLabels) as UserRole[]).map((r) => (
                          <DropdownMenuItem key={r} onClick={() => setNewRole(r)}>
                            {userRoleLabels[r]}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="passwordConfirm">Confirm Password *</Label>
                    <Input
                      id="passwordConfirm"
                      type="password"
                      value={newPasswordConfirm}
                      onChange={(e) => setNewPasswordConfirm(e.target.value)}
                      placeholder="Confirm password"
                    />
                  </div>
                  {createError && (
                    <p className="text-sm text-destructive">{createError}</p>
                  )}
                </div>
                <DialogFooter>
                  <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreate} disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Creating..." : "Create User"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {/* Users Table */}
          <Card>
            <CardHeader>
              <CardTitle>All Users</CardTitle>
            </CardHeader>
            <CardContent>
              {users && users.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead className="w-12"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.full_name}</TableCell>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>
                          <Badge variant={roleVariants[user.role]}>
                            {userRoleLabels[user.role]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {user.is_active ? (
                            <Badge variant="success">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(user.last_login_at)}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openEditDialog(user)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              {user.is_active ? (
                                <DropdownMenuItem
                                  onClick={() => handleDeactivate(user)}
                                  className="text-destructive"
                                >
                                  <UserX className="h-4 w-4 mr-2" />
                                  Deactivate
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem onClick={() => handleReactivate(user)}>
                                  Reactivate
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-muted-foreground text-center py-8">No users found</p>
              )}
            </CardContent>
          </Card>

          {/* Edit Dialog */}
          <Dialog open={!!editingUser} onOpenChange={(open) => !open && setEditingUser(null)}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Edit User</DialogTitle>
                <DialogDescription>
                  Update user information
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={editingUser?.email || ""} disabled className="bg-muted" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="editFirstName">First Name</Label>
                    <Input
                      id="editFirstName"
                      value={editFirstName}
                      onChange={(e) => setEditFirstName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="editLastName">Last Name</Label>
                    <Input
                      id="editLastName"
                      value={editLastName}
                      onChange={(e) => setEditLastName(e.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Role</Label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="secondary" className="w-full justify-between">
                        {userRoleLabels[editRole]}
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full">
                      {(Object.keys(userRoleLabels) as UserRole[]).map((r) => (
                        <DropdownMenuItem key={r} onClick={() => setEditRole(r)}>
                          {userRoleLabels[r]}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                {editError && (
                  <p className="text-sm text-destructive">{editError}</p>
                )}
              </div>
              <DialogFooter>
                <Button variant="secondary" onClick={() => setEditingUser(null)}>
                  Cancel
                </Button>
                <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </Container>
    </Section>
  )
}
