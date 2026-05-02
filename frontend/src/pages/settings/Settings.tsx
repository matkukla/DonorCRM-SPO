import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { Container } from "@/components/layout/Container"
import { Section } from "@/components/layout/Section"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/providers/AuthProvider"
import { apiClient } from "@/api/client"
import { useOrgSettings, useUpdateOrgSettings } from "@/hooks/useAdminAnalytics"
import { User, Lock, CheckCircle, Target, ArrowRight, Building2 } from "lucide-react"

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const isAdmin = user?.role === "admin"

  // Profile form state
  const [firstName, setFirstName] = useState(user?.first_name || "")
  const [lastName, setLastName] = useState(user?.last_name || "")
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false)
  const [profileSuccess, setProfileSuccess] = useState(false)
  const [profileError, setProfileError] = useState("")

  // Org annual goal (admin-only)
  const { data: orgSettings } = useOrgSettings()
  const updateOrgSettings = useUpdateOrgSettings()
  const [annualGoalDollars, setAnnualGoalDollars] = useState("")
  const [annualGoalSaved, setAnnualGoalSaved] = useState(false)
  const [annualGoalError, setAnnualGoalError] = useState("")
  const annualGoalSeededRef = useRef(false)

  // Only seed the input from the server once. After that the user's local
  // state is the source of truth — re-syncing on every orgSettings change
  // would clobber what the user typed if the API response arrives mid-edit.
  useEffect(() => {
    if (orgSettings && !annualGoalSeededRef.current) {
      annualGoalSeededRef.current = true
      setAnnualGoalDollars(
        orgSettings.annual_goal_cents > 0
          ? String(Math.round(orgSettings.annual_goal_cents / 100))
          : "",
      )
    }
  }, [orgSettings])

  const handleSaveAnnualGoal = async (e: React.FormEvent) => {
    e.preventDefault()
    setAnnualGoalError("")
    setAnnualGoalSaved(false)
    const dollars = annualGoalDollars.trim() === "" ? 0 : Number(annualGoalDollars)
    if (!Number.isFinite(dollars) || dollars < 0) {
      setAnnualGoalError("Please enter a valid non-negative dollar amount.")
      return
    }
    try {
      await updateOrgSettings.mutateAsync({ annual_goal_cents: Math.round(dollars * 100) })
      setAnnualGoalSaved(true)
      setTimeout(() => setAnnualGoalSaved(false), 3000)
    } catch {
      setAnnualGoalError("Failed to save. Please try again.")
    }
  }

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

          {/* Fundraising Goal Card - links to dedicated Goal page (GOAL-11) */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-muted-foreground" />
                <CardTitle>Fundraising Goal</CardTitle>
              </div>
              <CardDescription>
                Set your monthly support goal and journal selections on the Goal page.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link to="/goal">
                  Go to Goal page
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Org Annual Goal Card — admin only. Drives the Fiscal Year Pace tile.
              The card chrome (title + description) renders immediately so admins
              see the section header even on slow networks; the form body only
              mounts after orgSettings loads, so the input is seeded with the
              persisted value on first paint and a useEffect race can't clobber
              typed input. */}
          {isAdmin && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-muted-foreground" />
                  <CardTitle>Organization Annual Goal</CardTitle>
                </div>
                <CardDescription>
                  Org-wide annual fundraising goal used by the Admin Analytics
                  Fiscal Year Pace tile. Leave empty to fall back to the sum of
                  each missionary's monthly goal × 12.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {orgSettings ? (
                  <form onSubmit={handleSaveAnnualGoal} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="annualGoal">Annual Goal ($)</Label>
                      <Input
                        id="annualGoal"
                        type="number"
                        min="0"
                        step="1"
                        placeholder="e.g. 500000"
                        value={annualGoalDollars}
                        onChange={(e) => setAnnualGoalDollars(e.target.value)}
                      />
                    </div>

                    {annualGoalError && (
                      <p className="text-sm text-destructive">{annualGoalError}</p>
                    )}

                    {annualGoalSaved && (
                      <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                        <CheckCircle className="h-4 w-4" />
                        Saved
                      </div>
                    )}

                    <Button type="submit" disabled={updateOrgSettings.isPending}>
                      {updateOrgSettings.isPending ? "Saving..." : "Save Annual Goal"}
                    </Button>
                  </form>
                ) : (
                  <div className="h-24 bg-muted rounded animate-pulse" />
                )}
              </CardContent>
            </Card>
          )}

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
                    <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
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
                    <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
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
