"""Re-encrypt PII columns under the current ``PII_ENCRYPTION_KEYS`` write key.

Used for two operations:

  1. **Algorithm upgrade**: rows written under legacy Fernet are re-encrypted
     to AES-256-GCM v1 (the current scheme).
  2. **Key rotation**: after prepending a new aes256 key, sweep the table to
     re-encrypt every row under the new key, then the legacy key can be
     retired from ``PII_ENCRYPTION_KEYS``.

The command is **idempotent** (re-running cannot corrupt data — every read
returns plaintext, every write re-encrypts under the current key) and
**resumable** (``--resume-from-id`` skips ahead).

Usage
-----

  python manage.py rotate_pii_encryption --all
  python manage.py rotate_pii_encryption --app contacts --model Contact --field notes
  python manage.py rotate_pii_encryption --all --dry-run
  python manage.py rotate_pii_encryption --all --batch-size 1000
  python manage.py rotate_pii_encryption --all --resume-from-id <uuid>
"""

from __future__ import annotations

from typing import Iterable, Tuple

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from apps.core.audit import audit_event
from apps.core.encryption_registry import ENCRYPTED_FIELDS

DEFAULT_BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Re-encrypt PII columns under the current PII_ENCRYPTION_KEYS write key."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true", help="Sweep every field in ENCRYPTED_FIELDS."
        )
        parser.add_argument("--app", help="App label, e.g. 'contacts'.")
        parser.add_argument("--model", help="Model name, e.g. 'Contact'.")
        parser.add_argument("--field", help="Field name, e.g. 'notes'.")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f"Rows per bulk_update batch (default {DEFAULT_BATCH_SIZE}).",
        )
        parser.add_argument(
            "--resume-from-id",
            help="Skip rows with id <= this value. Use to resume after interruption.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count rows that would be touched; do not write.",
        )

    def handle(self, *args, **opts):
        targets = list(self._select_targets(opts))
        if not targets:
            raise CommandError(
                "Nothing to do. Pass --all or --app/--model/--field. "
                "Registered fields: " + ", ".join(f"{a}.{m}.{f}" for a, m, f in ENCRYPTED_FIELDS)
            )

        for app_label, model_name, field_name in targets:
            self._sweep(
                app_label=app_label,
                model_name=model_name,
                field_name=field_name,
                batch_size=opts["batch_size"],
                resume_from_id=opts.get("resume_from_id"),
                dry_run=opts["dry_run"],
            )

    def _select_targets(self, opts) -> Iterable[Tuple[str, str, str]]:
        if opts["all"]:
            return list(ENCRYPTED_FIELDS)
        app, model, field = opts.get("app"), opts.get("model"), opts.get("field")
        if not (app and model and field):
            return []
        return [(app, model, field)]

    def _sweep(
        self,
        *,
        app_label: str,
        model_name: str,
        field_name: str,
        batch_size: int,
        resume_from_id: str | None,
        dry_run: bool,
    ) -> None:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError as exc:
            raise CommandError(f"Unknown model {app_label}.{model_name}: {exc}") from exc

        if not any(f.name == field_name for f in model._meta.get_fields()):
            raise CommandError(f"{app_label}.{model_name} has no field '{field_name}'.")

        target = f"{app_label}.{model_name}.{field_name}"
        self.stdout.write(f"=== {target} ===")

        qs = (
            model.objects.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .only("id", field_name)
            .order_by("id")
        )
        if resume_from_id:
            qs = qs.filter(id__gt=resume_from_id)

        total_seen = 0
        total_written = 0
        batch_first_id = None
        batch_last_id = None
        batch = []

        for instance in qs.iterator(chunk_size=batch_size):
            total_seen += 1
            # Reading instance.<field> returned plaintext (the field's
            # from_db_value handles v1, legacy Fernet, and pre-migration
            # plaintext). Saving via bulk_update re-encrypts under the
            # current write key.
            batch.append(instance)
            if batch_first_id is None:
                batch_first_id = instance.id
            batch_last_id = instance.id

            if len(batch) >= batch_size:
                self._flush(
                    model, batch, field_name, dry_run, target, batch_first_id, batch_last_id
                )
                total_written += len(batch)
                batch = []
                batch_first_id = None

        if batch:
            self._flush(model, batch, field_name, dry_run, target, batch_first_id, batch_last_id)
            total_written += len(batch)

        verb = "would re-encrypt" if dry_run else "re-encrypted"
        self.stdout.write(f"  seen={total_seen} {verb}={total_written}")
        audit_event(
            "crypto.reencrypt.complete",
            target=target,
            seen=total_seen,
            written=total_written,
            dry_run=dry_run,
        )

    @staticmethod
    def _flush(model, batch, field_name, dry_run, target, first_id, last_id):
        if not dry_run:
            model.objects.bulk_update(batch, [field_name])
        audit_event(
            "crypto.reencrypt.batch",
            target=target,
            count=len(batch),
            first_id=first_id,
            last_id=last_id,
            dry_run=dry_run,
        )
