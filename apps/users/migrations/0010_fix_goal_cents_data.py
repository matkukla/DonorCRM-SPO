"""
Migration 0010: Re-run goal cents conversion that was a no-op in 0008.

Migration 0008's data conversion ran against an empty DB, so users who set
goals afterward had values stored as dollars (e.g. 5000.00 for $5,000/month)
instead of cents (500000). This migration corrects those values and ensures
the column type is BIGINT.

Safe threshold: any value < 10000 must be a dollar amount — no realistic
missionary monthly goal is under $100/month (which would be 10000 cents).
"""
from django.db import migrations


def fix_dollar_values_to_cents(apps, schema_editor):
    User = apps.get_model('users', 'User')
    users_to_fix = []
    for user in User.objects.filter(
        monthly_support_goal_cents__gt=0,
        monthly_support_goal_cents__lt=10000,
    ):
        user.monthly_support_goal_cents = round(float(user.monthly_support_goal_cents) * 100)
        users_to_fix.append(user)
    if users_to_fix:
        User.objects.bulk_update(users_to_fix, ['monthly_support_goal_cents'])


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_remove_redundant_goal_journal_index'),
    ]

    operations = [
        # Step 1: Fix data values (dollar floats → integer cents)
        migrations.RunPython(
            fix_dollar_values_to_cents,
            migrations.RunPython.noop,
        ),
        # Step 2: Guarantee the column type is BIGINT in Postgres.
        # Migration 0008 declared AlterField in Django's migration state, so
        # Django considers the field PositiveBigIntegerField already. But if the
        # DB column is still DECIMAL (0008 ran against an empty DB), a second
        # AlterField is a no-op at the Django state level. RunSQL forces the DDL.
        migrations.RunSQL(
            sql="ALTER TABLE users ALTER COLUMN monthly_support_goal_cents TYPE BIGINT USING round(monthly_support_goal_cents)::BIGINT",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
