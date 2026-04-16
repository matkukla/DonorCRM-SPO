"""
Migration 0011: Re-assign users with removed roles (finance, read_only) to missionary.

The finance and read_only roles were removed from UserRole enum in PR #45.
Django TextChoices is just a CharField — existing rows won't error, but users
with those roles would silently get missionary-level access anyway (only own
data via get_visible_user_ids). This migration makes that explicit.
"""
from django.db import migrations


def reassign_dead_roles(apps, schema_editor):
    User = apps.get_model('users', 'User')
    updated = User.objects.filter(role__in=['finance', 'read_only']).update(role='missionary')
    if updated:
        print(f"  Reassigned {updated} user(s) from finance/read_only to missionary")


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0010_fix_goal_cents_data'),
    ]

    operations = [
        migrations.RunPython(
            reassign_dead_roles,
            migrations.RunPython.noop,
        ),
    ]
