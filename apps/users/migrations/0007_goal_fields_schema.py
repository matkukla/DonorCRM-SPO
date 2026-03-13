"""
Migration 0007: Schema-only changes for goal fields.
- Rename monthly_goal → monthly_support_goal_cents (keeps Decimal type for now)
- Add goal_weeks field
- Create GoalJournalSelection model
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0006_m2m_supervisors'),
        ('journals', '0003_add_next_step_model'),
    ]

    operations = [
        # Step 1: Rename only — column still holds Decimal data, same type
        migrations.RenameField(
            model_name='user',
            old_name='monthly_goal',
            new_name='monthly_support_goal_cents',
        ),
        # Step 2: Add goal_weeks
        migrations.AddField(
            model_name='user',
            name='goal_weeks',
            field=models.PositiveIntegerField(
                verbose_name='goal weeks',
                default=52,
                help_text='Number of weeks to accomplish support goal',
            ),
        ),
        # Step 3: Create GoalJournalSelection
        migrations.CreateModel(
            name='GoalJournalSelection',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    to='users.User',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='goal_journal_selections',
                    db_index=True,
                )),
                ('journal', models.ForeignKey(
                    to='journals.Journal',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='goal_selections',
                    db_index=True,
                )),
            ],
            options={
                'db_table': 'goal_journal_selections',
                'verbose_name': 'goal journal selection',
                'verbose_name_plural': 'goal journal selections',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'journal')},
            },
        ),
    ]
