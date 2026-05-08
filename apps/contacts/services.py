"""
Services for duplicate contact detection and merging.

Provides:
- find_duplicates_for_contact: Find potential duplicates for a given contact's data
- merge_contacts: Atomically merge two contacts (reassign FKs, union groups, soft-delete loser)
"""
from collections import OrderedDict

from django.db import OperationalError, models, transaction
from django.db.models import Q, Value
from django.db.models.functions import Greatest

from apps.contacts.models import Contact, ContactMergeLog, DismissedDuplicate

# Fields eligible for auto-fill during merge (survivor blank → copy loser's value)
# Note: 'status' deliberately excluded — survivor keeps their status
_FILLABLE_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "phone",
    "phone_secondary",
    "organization_name",
    "street_address",
    "city",
    "state",
    "postal_code",
    "country",
    "notes",
    "external_id",
    "external_constituent_id",
]

# Confidence tier ordering for sorting
_CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def find_duplicates_for_contact(contact_data, owner_id, exclude_id=None):
    """
    Find potential duplicate contacts for the given contact data.

    Args:
        contact_data: dict with keys first_name, last_name, email, phone
        owner_id: UUID of the contact owner (scoping)
        exclude_id: optional UUID to exclude (e.g., the contact being edited)

    Returns:
        List of dicts: [{'contact': Contact, 'confidence': str, 'reasons': list, 'similarity': float}]
        Sorted by confidence (high > medium > low), then similarity descending.
        Limited to 10 results.
    """
    base_qs = Contact.objects.filter(owner_id=owner_id, is_merged=False)
    if exclude_id:
        base_qs = base_qs.exclude(pk=exclude_id)

    first_name = (contact_data.get("first_name") or "").strip()
    last_name = (contact_data.get("last_name") or "").strip()
    email = (contact_data.get("email") or "").strip()
    phone = (contact_data.get("phone") or "").strip()

    # Collect matches keyed by contact ID -> best match info
    matches = (
        OrderedDict()
    )  # contact_id -> {'contact': ..., 'confidence': ..., 'reasons': [...], 'similarity': float}

    def _add_match(contact, confidence, reason, similarity=1.0):
        cid = contact.id
        if cid in matches:
            existing = matches[cid]
            # Keep higher confidence
            if _CONFIDENCE_ORDER[confidence] < _CONFIDENCE_ORDER[existing["confidence"]]:
                existing["confidence"] = confidence
                existing["similarity"] = max(existing["similarity"], similarity)
            existing["reasons"].append(reason)
        else:
            matches[cid] = {
                "contact": contact,
                "confidence": confidence,
                "reasons": [reason],
                "similarity": similarity,
            }

    # Exact email match (case-insensitive). email is encrypted at rest;
    # equality lookups go through the email_hash blind index.
    if email:
        from apps.core.blind_index import lookup_hashes

        candidates = lookup_hashes(email)
        if candidates:
            for c in base_qs.filter(email_hash__in=candidates):
                _add_match(c, "high", "Exact email match", 1.0)

    # Exact phone match (primary or secondary). Both columns are encrypted
    # at rest; equality lookups go via the digit-normalized blind index.
    if phone:
        from apps.core.blind_index import lookup_hashes, normalize_phone

        phone_hashes = lookup_hashes(normalize_phone(phone))
        if phone_hashes:
            for c in base_qs.filter(
                Q(phone_hash__in=phone_hashes) | Q(phone_secondary_hash__in=phone_hashes)
            ):
                _add_match(c, "high", "Exact phone match", 1.0)

    # Fuzzy name match via TrigramSimilarity (PostgreSQL only)
    if first_name or last_name:
        try:
            from django.contrib.postgres.search import TrigramSimilarity

            name_qs = base_qs
            # Exclude contacts already found via exact match
            if matches:
                name_qs = name_qs.exclude(pk__in=matches.keys())

            annotations = {}
            if first_name:
                annotations["first_sim"] = TrigramSimilarity("first_name", first_name)
            else:
                annotations["first_sim"] = Value(0.0, output_field=models.FloatField())

            if last_name:
                annotations["last_sim"] = TrigramSimilarity("last_name", last_name)
            else:
                annotations["last_sim"] = Value(0.0, output_field=models.FloatField())

            name_qs = (
                name_qs.annotate(**annotations)
                .annotate(name_similarity=Greatest("first_sim", "last_sim"))
                .filter(name_similarity__gte=0.4)
                .order_by("-name_similarity")
            )

            for c in name_qs[:20]:
                sim = c.name_similarity
                if sim >= 0.6:
                    _add_match(c, "medium", f"Name similarity: {sim:.2f}", sim)
                else:
                    _add_match(c, "low", f"Name similarity: {sim:.2f}", sim)
        except ImportError:
            # django.contrib.postgres not available (e.g., SQLite test env)
            pass
        except OperationalError:
            import logging

            logging.getLogger(__name__).warning("Trigram name matching failed", exc_info=True)

    # Sort: confidence tier, then similarity descending
    result = sorted(
        matches.values(), key=lambda m: (_CONFIDENCE_ORDER[m["confidence"]], -m["similarity"])
    )

    return result[:10]


@transaction.atomic
def merge_contacts(survivor_id, loser_id, merged_by):
    """
    Atomically merge loser contact into survivor contact.

    Auto-fills the survivor's blank fields with the loser's values, reassigns
    all FK relationships, union-merges groups, soft-deletes loser, recalculates
    survivor stats, and creates an audit log entry.

    Args:
        survivor_id: UUID of the contact to keep
        loser_id: UUID of the contact to merge away
        merged_by: User instance performing the merge

    Returns:
        The survivor Contact instance

    Raises:
        ValueError: If loser has already been merged
        Contact.DoesNotExist: If either contact is not found
    """
    from apps.events.models import Event
    from apps.gifts.models import Gift, RecurringGift
    from apps.prayers.models import PrayerIntention
    from apps.tasks.models import Task

    survivor = Contact.objects.select_for_update().get(pk=survivor_id)
    loser = Contact.objects.select_for_update().get(pk=loser_id)

    if survivor_id == loser_id:
        raise ValueError("Cannot merge a contact with itself")
    if loser.is_merged:
        raise ValueError("Contact has already been merged")
    if survivor.is_merged:
        raise ValueError("Survivor contact has already been merged")

    # Auto-fill blanks: copy loser's non-empty values into survivor's empty fields
    _unique_fields = {
        "email",
        "external_id",
        "external_constituent_id",
    }  # Fields involved in unique constraints
    fields_auto_filled = {}

    for field_name in _FILLABLE_FIELDS:
        survivor_val = getattr(survivor, field_name, "") or ""
        loser_val = getattr(loser, field_name, "") or ""
        if not str(survivor_val).strip() and str(loser_val).strip():
            setattr(survivor, field_name, loser_val)
            fields_auto_filled[field_name] = str(loser_val)

    # Clear unique-constrained fields AND phone fields on loser before saving
    # survivor. This prevents UNIQUE constraint violations during merge AND
    # ensures the soft-deleted loser row doesn't cause stale matches in import
    # lookups (which match on email, external_id, external_constituent_id, and phone).
    _fields_to_clear_on_loser = _unique_fields | {"phone", "phone_secondary"}
    all_fields_to_clear = [f for f in _fields_to_clear_on_loser if getattr(loser, f, "")]
    if all_fields_to_clear:
        for field_name in all_fields_to_clear:
            setattr(loser, field_name, "")
        loser.save(update_fields=all_fields_to_clear + ["updated_at"])

    # Reassign FK relationships, capturing counts
    gifts_count = Gift.objects.filter(donor_contact=loser).update(donor_contact=survivor)
    recurring_gifts_count = RecurringGift.objects.filter(donor_contact=loser).update(
        donor_contact=survivor
    )
    tasks_count = Task.objects.filter(contact=loser).update(contact=survivor)
    prayer_intentions_count = PrayerIntention.objects.filter(contact=loser).update(contact=survivor)
    events_count = Event.objects.filter(contact=loser).update(contact=survivor)
    journal_contacts_count = _merge_journal_contacts(survivor, loser)

    # Union-merge groups
    survivor.groups.add(*loser.groups.all())

    # Soft-delete loser
    loser.is_merged = True
    loser.merged_into = survivor
    loser.save(update_fields=["is_merged", "merged_into", "updated_at"])

    # Save survivor (field overrides may have changed fields)
    survivor.save()

    # Recalculate survivor's giving stats
    survivor.update_giving_stats()

    # Create audit log
    ContactMergeLog.objects.create(
        survivor=survivor,
        loser_id=loser.id,
        loser_name=loser.full_name,
        merged_by=merged_by,
        field_overrides=fields_auto_filled,
        records_migrated={
            "gifts": gifts_count,
            "recurring_gifts": recurring_gifts_count,
            "tasks": tasks_count,
            "prayer_intentions": prayer_intentions_count,
            "events": events_count,
            "journal_contacts": journal_contacts_count,
        },
    )

    # Clean up dismissed duplicates involving the loser
    DismissedDuplicate.objects.filter(Q(contact_a=loser) | Q(contact_b=loser)).delete()

    return survivor


def _merge_journal_contacts(survivor, loser):
    """
    Handle JournalContact merge with unique_together conflict resolution.

    If both contacts are in the same journal, transfer stage events, decisions,
    and next steps from the loser's JournalContact to the survivor's, then delete
    the loser's JournalContact. Otherwise, just reassign the loser's JournalContact
    to point to the survivor.

    Returns:
        Count of JournalContacts processed.
    """
    from apps.journals.models import Decision, JournalContact, JournalStageEvent, NextStep

    count = 0
    for loser_jc in JournalContact.objects.filter(contact=loser):
        survivor_jc = JournalContact.objects.filter(
            journal=loser_jc.journal, contact=survivor
        ).first()

        if survivor_jc:
            # Conflict: both contacts are in the same journal
            # Transfer stage events (no unique constraint issues)
            JournalStageEvent.objects.filter(journal_contact=loser_jc).update(
                journal_contact=survivor_jc
            )
            # Handle Decisions: unique per journal_contact
            survivor_has_decision = Decision.objects.filter(journal_contact=survivor_jc).exists()
            if survivor_has_decision:
                Decision.objects.filter(journal_contact=loser_jc).delete()
            else:
                Decision.objects.filter(journal_contact=loser_jc).update(
                    journal_contact=survivor_jc
                )
            # NextSteps can be transferred (no unique constraint on journal_contact)
            NextStep.objects.filter(journal_contact=loser_jc).update(journal_contact=survivor_jc)
            loser_jc.delete()
        else:
            # No conflict: just reassign
            loser_jc.contact = survivor
            loser_jc.save(update_fields=["contact"])

        count += 1

    return count
