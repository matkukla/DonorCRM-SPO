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
    STAFF = 'staff', 'Staff'
    ADMIN = 'admin', 'Admin'
    FINANCE = 'finance', 'Finance'
    READ_ONLY = 'read_only', 'Read Only'


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom User model using email as the primary identifier.

    Roles:
    - Staff: Manages their own donors, pledges, and tasks
    - Admin: Full system access, user management, data imports
    - Finance: Import donations, view giving across organization
    - Read-Only: View-only access for coaches/supervisors
    """
    # Remove username, use email instead
    email = models.EmailField('email address', unique=True)

    # Profile information
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    phone = models.CharField('phone number', max_length=20, blank=True)

    # Role-based permissions
    role = models.CharField(
        'role',
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STAFF,
        db_index=True
    )

    # Support goal tracking for staff users
    monthly_goal = models.DecimalField(
        'monthly support goal',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Monthly support goal amount in dollars'
    )

    # Django auth fields
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Designates whether the user can log into the admin site.'
    )
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Designates whether this user should be treated as active.'
    )
    date_joined = models.DateTimeField('date joined', default=timezone.now)

    # Activity tracking
    last_login_at = models.DateTimeField('last login', null=True, blank=True)

    # Notification preferences
    email_notifications = models.BooleanField(
        'email notifications',
        default=True,
        help_text='Whether to send email notifications for important events'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'

    @property
    def full_name(self):
        """Return the user's full name."""
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def is_finance(self):
        """Check if user has finance role."""
        return self.role == UserRole.FINANCE

    @property
    def is_staff_role(self):
        """Check if user has staff role."""
        return self.role == UserRole.STAFF

    @property
    def is_read_only(self):
        """Check if user has read-only role."""
        return self.role == UserRole.READ_ONLY

    def can_manage_contact(self, contact):
        """Check if user can manage a given contact."""
        if self.is_admin:
            return True
        return contact.owner == self

    def can_view_contact(self, contact):
        """Check if user can view a given contact."""
        if self.role in [UserRole.ADMIN, UserRole.FINANCE, UserRole.READ_ONLY]:
            return True
        return contact.owner == self
