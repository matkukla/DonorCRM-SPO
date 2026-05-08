"""Registry of model fields encrypted with ``EncryptedTextField``.

Drives ``rotate_pii_encryption --all`` so a single command re-encrypts every
PII column under the current write key. Add a tuple here whenever a field is
migrated to ``EncryptedTextField``.
"""
from __future__ import annotations

from typing import List, Tuple

# (app_label, model_name, field_name)
ENCRYPTED_FIELDS: List[Tuple[str, str, str]] = [
    ("contacts", "Contact", "notes"),
    ("contacts", "Contact", "phone"),
    ("contacts", "Contact", "phone_secondary"),
    ("contacts", "Contact", "street_address"),
    ("contacts", "Contact", "email"),
    ("journals", "JournalStageEvent", "notes"),
    ("prayers", "PrayerIntention", "description"),
    ("gifts", "Gift", "description"),
    ("gifts", "RecurringGift", "description"),
]
