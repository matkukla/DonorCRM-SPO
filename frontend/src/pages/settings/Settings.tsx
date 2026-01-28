import { useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/providers/AuthProvider"
import { apiClient } from "@/api/client"
import { User, Lock, CheckCircle, Target } from "lucide-react"

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const queryClient = useQueryClient()

  // Profile form state
  const [firstName, setFirstName] = useState(user?.first_name || "")
  const [lastName, setLastName] = useState(user?.last_name || "")
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false)
  const [profileSuccess, setProfileSuccess] = useState(false)
  const [profileError, setProfileError] = useState("")

  // Goal form state
  const [monthlyGoal, setMonthlyGoal] = useState(user?.monthly_goal || "")
  const [isUpdatingGoal, setIsUpdatingGoal] = useState(false)
  const [goalSuccess, setGoalSuccess] = useState(false)
  const [goalError, setGoalError] = useState("")

  // Password form state
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  const [passwordError, setPasswordError] = useState("")

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsUpdatingProfile(true)
    setProfileSuccess(false)
    setProfileError("")

    try {
      await apiClient.patch("/users/me/", {
        first_name: firstName,
        last_name: lastName,
      })
      await refreshUser()
      setProfileSuccess(true)
      setTimeout(() => setProfileSuccess(false), 3000)
    } catch (err) {
      setProfileError("Failed to update profile. Please try again.")
    } finally {
      setIsUpdatingProfile(false)
    }
  }

  const handleUpdateGoal = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsUpdatingGoal(true)
    setGoalSuccess(false)
    setGoalError("")

    const goalValue = parseFloat(monthlyGoal as string)
    if (monthlyGoal && (isNaN(goalValue) || goalValue < 0)) {
      setGoalError("Please enter a valid dollar amount.")
      setIsUpdatingGoal(false)
      return
    }

    try {
      await apiClient.patch("/users/me/", {
        monthly_goal: monthlyGoal || "0",
      })
      await refreshUser()
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      setGoalSuccess(true)
      setTimeout(() => setGoalSuccess(false), 3000)
    } catch (err) {
      setGoalError("Failed to update goal. Please try again.")
    } finally {
      setIsUpdatingGoal(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError("")
    setPasswordSuccess(false)

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.")
      return
    }

    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters.")
      return
    }

    setIsUpdatingPassword(true)

    try {
      await apiClient.post("/auth/password/change/", {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setPasswordSuccess(true)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setTimeout(() => setPasswordSuccess(false), 3000)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setPasswordError(error.response?.data?.detail || "Failed to change password. Please check your current password.")
    } finally {
      setIsUpdatingPassword(false)
    }
  }

  return (
    <Section>
      <Container>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
            <p className="text-muted-foreground mt-1">
              Manage your account and preferences
            </p>
          </div>

          {/* Fundraising Goal Card - full width */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Fundraising Goal</CardTitle>
              </div>
              <CardDescription>
                Set your monthly support goal. This is used to track progress on your dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpdateGoal} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="monthlyGoal">Monthly Goal ($)</Label>
                    <Input
                      id="monthlyGoal"
                      type="number"
                      min="0"
                      step="0.01"
                      value={monthlyGoal ?? ""}
                      onChange={(e) => setMonthlyGoal(e.target.value)}
                      placeholder="e.g. 5000"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Annual Goal</Label>
                    <Input
                      value={
                        monthlyGoal && !isNaN(parseFloat(monthlyGoal as string))
                          ? `$${(parseFloat(monthlyGoal as string) * 12).toLocaleString()}`
                          : "—"
                      }
                      disabled
                      className="bg-muted"
                    />
                    <p className="text-xs text-muted-foreground">
                      Calculated from monthly goal
                    </p>
                  </div>
                </div>

                {goalError && (
                  <p className="text-sm text-destructive">{goalError}</p>
                )}

                {goalSuccess && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <CheckCircle className="h-4 w-4" />
                    Goal updated successfully
                  </div>
                )}

                <Button type="submit" disabled={isUpdatingGoal}>
                  {isUpdatingGoal ? "Saving..." : "Save Goal"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Profile Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-muted-foreground" />
                  <CardTitle>Profile</CardTitle>
                </div>
                <CardDescription>Update your personal information</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdateProfile} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      value={user?.email || ""}
                      disabled
                      className="bg-muted"
                    />
                    <p className="text-xs text-muted-foreground">
                      Email cannot be changed
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="firstName">First Name</Label>
                      <Input
                        id="firstName"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        placeholder="First name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lastName">Last Name</Label>
                      <Input
                        id="lastName"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        placeholder="Last name"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Input
                      value={user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : ""}
                      disabled
                      className="bg-muted"
                    />
                    <p className="text-xs text-muted-foreground">
                      Role can only be changed by an administrator
                    </p>
                  </div>

                  {profileError && (
                    <p className="text-sm text-destructive">{profileError}</p>
                  )}

                  {profileSuccess && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      Profile updated successfully
                    </div>
                  )}

                  <Button type="submit" disabled={isUpdatingProfile}>
                    {isUpdatingProfile ? "Saving..." : "Save Changes"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Password Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Lock className="h-5 w-5 text-muted-foreground" />
                  <CardTitle>Change Password</CardTitle>
                </div>
                <CardDescription>Update your password</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="currentPassword">Current Password</Label>
                    <Input
                      id="currentPassword"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Enter current password"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="newPassword">New Password</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm New Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                    />
                  </div>

                  {passwordError && (
                    <p className="text-sm text-destructive">{passwordError}</p>
                  )}

                  {passwordSuccess && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      Password changed successfully
                    </div>
                  )}

                  <Button
                    type="submit"
                    disabled={isUpdatingPassword || !currentPassword || !newPassword || !confirmPassword}
                  >
                    {isUpdatingPassword ? "Changing..." : "Change Password"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </Container>
    </Section>
  )
}
