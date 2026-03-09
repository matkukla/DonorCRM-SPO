from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(supervisor__isnull=False):
        user.supervisors.add(user.supervisor_id)
    for user in User.objects.filter(coach__isnull=False):
        user.coaches.add(user.coach_id)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_roles_redesign'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='supervisors',
            field=models.ManyToManyField(
                blank=True,
                help_text='Supervisors assigned to this missionary',
                related_name='supervised_users',
                symmetrical=False,
                to='users.user',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='coaches',
            field=models.ManyToManyField(
                blank=True,
                help_text='Coaches assigned to this missionary',
                related_name='coached_users',
                symmetrical=False,
                to='users.user',
            ),
        ),
        migrations.RunPython(copy_fk_to_m2m, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='user',
            name='supervisor',
        ),
        migrations.RemoveField(
            model_name='user',
            name='coach',
        ),
    ]
