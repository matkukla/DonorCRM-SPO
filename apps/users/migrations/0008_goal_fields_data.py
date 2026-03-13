"""
Migration 0008: Data conversion + AlterField for monthly_support_goal_cents.
- Convert Decimal dollar values to integer cents (multiply by 100)
- AlterField: DecimalField → PositiveBigIntegerField
"""
from django.db import migrations, models


def convert_monthly_goal_to_cents(apps, schema_editor):
    """Multiply old Decimal dollar values by 100 to get integer cents."""
    User = apps.get_model('users', 'User')
    users_to_update = []
    for user in User.objects.all():
        # monthly_support_goal_cents currently holds old Decimal value (e.g., 3500.00)
        old_value = user.monthly_support_goal_cents
        if old_value:
            user.monthly_support_goal_cents = round(float(old_value) * 100)
        else:
            user.monthly_support_goal_cents = 0
        users_to_update.append(user)
    # Bulk update for performance
    User.objects.bulk_update(users_to_update, ['monthly_support_goal_cents'])


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0007_goal_fields_schema'),
    ]

    operations = [
        # Step 1: Convert data BEFORE changing type
        migrations.RunPython(
            convert_monthly_goal_to_cents,
            migrations.RunPython.noop,
        ),
        # Step 2: Now safe to AlterField — all values are already integers
        migrations.AlterField(
            model_name='user',
            name='monthly_support_goal_cents',
            field=models.PositiveBigIntegerField(
                verbose_name='monthly support goal (cents)',
                default=0,
                help_text='Monthly support goal in cents (e.g., 350000 = $3,500.00)',
            ),
        ),
    ]
