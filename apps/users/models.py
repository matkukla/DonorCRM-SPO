"""
Custom User model for DonorCRM.
Uses email as primary identifier with role-based access control.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.users.managers import UserManager


class UserRole(models.TextChoices):
    """
    User roles determine permissions across the system.
    """

    MISSIONARY = "missionary", "Missionary"
    ADMIN = "admin", "Admin"
    SUPERVISOR = "supervisor", "Supervisor"
    COACH = "coach", "Coach"


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom User model using email as the primary identifier.

    Roles:
    - Missionary: Manages their own donors, pledges, and tasks
    - Admin: Full system access, user management, data imports
    - Supervisor: View/manage supervised missionaries' data
    - Coach: View/manage coached users' data (financial data excluded)
    """

    # Remove username, use email instead
    email = models.EmailField("email address", unique=True)

    # Profile information
    first_name = models.CharField("first name", max_length=150)
    last_name = models.CharField("last name", max_length=150)
    phone = models.CharField("phone number", max_length=20, blank=True)

    # Role-based permissions
    role = models.CharField(
        "role", max_length=25, choices=UserRole.choices, default=UserRole.MISSIONARY, db_index=True
    )

    # Supervisor relationships (M2M: a missionary can have multiple supervisors)
    supervisors = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="supervised_users",
        help_text="Supervisors assigned to this missionary",
    )

    # Coach relationships (M2M: a missionary can have multiple coaches)
    coaches = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="coached_users",
        help_text="Coaches assigned to this missionary",
    )

    # Support goal tracking for staff users
    monthly_support_goal_cents = models.PositiveBigIntegerField(
        "monthly support goal (cents)",
        default=0,
        help_text="Monthly support goal in cents (e.g., 350000 = $3,500.00)",
    )
    goal_weeks = models.PositiveIntegerField(
        "goal weeks", default=52, help_text="Number of weeks to accomplish support goal"
    )

    # Dashboard preferences
    dashboard_layout = models.JSONField(
        "dashboard layout",
        default=dict,
        blank=True,
        help_text="User dashboard tile ordering preferences",
    )

    # Django auth fields
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active.",
    )
    date_joined = models.DateTimeField("date joined", default=timezone.now)

    # Activity tracking
    last_login_at = models.DateTimeField("last login", null=True, blank=True)

    # Notification preferences
    email_notifications = models.BooleanField(
        "email notifications",
        default=True,
        help_text="Whether to send email notifications for important events",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        """Auto-clear M2M assignments when role changes away from supervisor/coach."""
        old_role = None
        if self.pk:
            try:
                old_role = User.objects.filter(pk=self.pk).values_list("role", flat=True).first()
            except Exception:
                pass
        super().save(*args, **kwargs)
        if old_role is not None:
            if old_role == UserRole.SUPERVISOR and self.role != UserRole.SUPERVISOR:
                self.supervised_users.clear()
            if old_role == UserRole.COACH and self.role != UserRole.COACH:
                self.coached_users.clear()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class GoalJournalSelection(TimeStampedModel):
    """Journals selected by a user to count toward their support goal."""

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="goal_journal_selections",
        db_index=True,
    )
    journal = models.ForeignKey(
        "journals.Journal",
        on_delete=models.CASCADE,
        related_name="goal_selections",
        db_index=True,
    )

    class Meta:
        db_table = "goal_journal_selections"
        verbose_name = "goal journal selection"
        verbose_name_plural = "goal journal selections"
        unique_together = [["user", "journal"]]

    def __str__(self):
        return f"{self.user.email} \u2192 journal {self.journal_id}"
