from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    """Rename existing role values to new names."""
    User = apps.get_model('users', 'User')
    User.objects.filter(role='staff').update(role='missionary')
    User.objects.filter(role='mission_supervisor').update(role='supervisor')


def backwards(apps, schema_editor):
    """Reverse role rename."""
    User = apps.get_model('users', 'User')
    User.objects.filter(role='missionary').update(role='staff')
    User.objects.filter(role='supervisor').update(role='mission_supervisor')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_mission_supervisor_role'),
    ]

    operations = [
        # 1. Data migration FIRST (before AlterField) to avoid constraint violations
        migrations.RunPython(forwards, backwards),

        # 2. Update role field choices and default
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('missionary', 'Missionary'),
                    ('admin', 'Admin'),
                    ('finance', 'Finance'),
                    ('read_only', 'Read Only'),
                    ('supervisor', 'Supervisor'),
                    ('coach', 'Coach'),
                ],
                default='missionary',
                max_length=25,
                verbose_name='role',
                db_index=True,
            ),
        ),

        # 3. Add coach FK on User
        migrations.AddField(
            model_name='user',
            name='coach',
            field=models.ForeignKey(
                blank=True,
                help_text='Coach assigned to this user',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='coached_users',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
