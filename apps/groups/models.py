"""
Group model for organizing contacts with tags/segments.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Group(TimeStampedModel):
    """
    Tag or segment for organizing contacts.
    Can be organization-wide (owner=None) or private to a user.
    """
    name = models.CharField('name', max_length=100)
    description = models.TextField('description', blank=True)
    color = models.CharField(
        'color',
        max_length=7,
        default='#6366f1',
        help_text='Hex color code for UI display'
    )

    # Ownership - null means organization-wide (shared)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='owned_groups',
        help_text='If set, group is private to this user'
    )

    # System groups can\'t be deleted by users
    is_system = models.BooleanField('system group', default=False)

    class Meta:
        db_table = 'groups'
        verbose_name = 'group'
        verbose_name_plural = 'groups'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'owner'],
                name='unique_group_name_per_owner'
            )
        ]

    def __str__(self):
        return self.name

    @property
    def contact_count(self):
        """Return the number of contacts in this group."""
        return self.contacts.count()

    @property
    def is_shared(self):
        """Return True if this is an organization-wide group."""
        return self.owner is None
