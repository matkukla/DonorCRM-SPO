# Generated manually for duplicate contact detection and merging feature.

import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0008_allow_blank_first_last_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Install pg_trgm extension for fuzzy name matching
        TrigramExtension(),

        # Add merge tracking fields to Contact
        migrations.AddField(
            model_name="contact",
            name="is_merged",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="merged"
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="merged_into",
            field=models.ForeignKey(
                blank=True,
                help_text="Contact this was merged into",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="merged_contacts",
                to="contacts.contact",
            ),
        ),

        # Add index for owner + is_merged
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["owner", "is_merged"],
                name="contacts_owner_i_ea8938_idx",
            ),
        ),

        # Create DismissedDuplicate model
        migrations.CreateModel(
            name="DismissedDuplicate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "contact_a",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contacts.contact",
                    ),
                ),
                (
                    "contact_b",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contacts.contact",
                    ),
                ),
                (
                    "dismissed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dismissed_duplicates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "dismissed_duplicates",
            },
        ),
        migrations.AddConstraint(
            model_name="dismissedduplicate",
            constraint=models.UniqueConstraint(
                fields=("contact_a", "contact_b"),
                name="unique_dismissed_pair",
            ),
        ),

        # Create ContactMergeLog model
        migrations.CreateModel(
            name="ContactMergeLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "loser_id",
                    models.UUIDField(help_text="ID of the merged-away contact"),
                ),
                (
                    "loser_name",
                    models.CharField(
                        help_text="Name snapshot at merge time", max_length=300
                    ),
                ),
                (
                    "field_overrides",
                    models.JSONField(
                        default=dict,
                        help_text="Field resolution choices",
                    ),
                ),
                (
                    "records_migrated",
                    models.JSONField(
                        default=dict,
                        help_text="Counts of migrated FK records",
                    ),
                ),
                (
                    "survivor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="merge_logs_as_survivor",
                        to="contacts.contact",
                    ),
                ),
                (
                    "merged_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="merge_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "contact_merge_logs",
                "ordering": ["-created_at"],
            },
        ),
    ]
