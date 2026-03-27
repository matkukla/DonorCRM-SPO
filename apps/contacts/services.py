"""
Services for duplicate contact detection and merging.

Provides:
- find_duplicates_for_contact: Find potential duplicates for a given contact's data
- scan_duplicates_for_owner: Batch scan for all duplicate pairs across an owner's contacts
- merge_contacts: Atomically merge two contacts (reassign FKs, union groups, soft-delete loser)
"""
from collections import OrderedDict

from django.db import models, transaction
from django.db.models import Q, Value
from django.db.models.functions import Greatest

from apps.contacts.models import Contact, ContactMergeLog, DismissedDuplicate

# Fields that can be overridden during merge (field_overrides={'field': 'right'})
MERGEABLE_FIELDS = frozenset({
    'first_name', 'last_name', 'email', 'phone', 'phone_secondary',
    'organization_name', 'street_address', 'city', 'state', 'postal_code',
    'country', 'status', 'notes',
})

# Confidence tier ordering for sorting
_CONFIDENCE_ORDER = {'high': 0, 'medium': 1, 'low': 2}


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

    first_name = (contact_data.get('first_name') or '').strip()
    last_name = (contact_data.get('last_name') or '').strip()
    email = (contact_data.get('email') or '').strip()
    phone = (contact_data.get('phone') or '').strip()

    # Collect matches keyed by contact ID -> best match info
    matches = OrderedDict()  # contact_id -> {'contact': ..., 'confidence': ..., 'reasons': [...], 'similarity': float}

    def _add_match(contact, confidence, reason, similarity=1.0):
        cid = contact.id
        if cid in matches:
            existing = matches[cid]
            # Keep higher confidence
            if _CONFIDENCE_ORDER[confidence] < _CONFIDENCE_ORDER[existing['confidence']]:
                existing['confidence'] = confidence
                existing['similarity'] = max(existing['similarity'], similarity)
            existing['reasons'].append(reason)
        else:
            matches[cid] = {
                'contact': contact,
                'confidence': confidence,
                'reasons': [reason],
                'similarity': similarity,
            }

    # Exact email match (case-insensitive)
    if email:
        for c in base_qs.filter(email__iexact=email):
            _add_match(c, 'high', 'Exact email match', 1.0)

    # Exact phone match (primary or secondary)
    if phone:
        for c in base_qs.filter(Q(phone=phone) | Q(phone_secondary=phone)):
            _add_match(c, 'high', 'Exact phone match', 1.0)

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
                annotations['first_sim'] = TrigramSimilarity('first_name', first_name)
            else:
                annotations['first_sim'] = Value(0.0, output_field=models.FloatField())

            if last_name:
                annotations['last_sim'] = TrigramSimilarity('last_name', last_name)
            else:
                annotations['last_sim'] = Value(0.0, output_field=models.FloatField())

            name_qs = name_qs.annotate(**annotations).annotate(
                name_similarity=Greatest('first_sim', 'last_sim')
            ).filter(name_similarity__gte=0.4).order_by('-name_similarity')

            for c in name_qs[:20]:
                sim = c.name_similarity
                if sim >= 0.6:
                    _add_match(c, 'medium', f'Name similarity: {sim:.2f}', sim)
                else:
                    _add_match(c, 'low', f'Name similarity: {sim:.2f}', sim)
        except (ImportError, Exception):
            # SQLite or pg_trgm not available -- skip name matching
            pass

    # Sort: confidence tier, then similarity descending
    result = sorted(
        matches.values(),
        key=lambda m: (_CONFIDENCE_ORDER[m['confidence']], -m['similarity'])
    )

    return result[:10]


def scan_duplicates_for_owner(owner_id):
    """
    Batch scan for all duplicate pairs across an owner's contacts.

    Returns deduplicated pairs, excluding dismissed pairs and merged contacts.
    Pairs are ordered by confidence (high > medium > low), then similarity descending.

    Args:
        owner_id: UUID of the contact owner

    Returns:
        List of dicts: [{'contact_a': Contact, 'contact_b': Contact,
                         'confidence': str, 'reasons': list, 'similarity': float}]
    """
    contacts = list(
        Contact.objects.filter(owner_id=owner_id, is_merged=False)
        .order_by('last_name', 'first_name')
    )

    # Load dismissed pairs as canonical set
    raw_dismissed = DismissedDuplicate.objects.filter(
        Q(contact_a__owner_id=owner_id) | Q(contact_b__owner_id=owner_id)
    ).values_list('contact_a_id', 'contact_b_id')

    dismissed_set = set()
    for a, b in raw_dismissed:
        canonical = (min(str(a), str(b)), max(str(a), str(b)))
        dismissed_set.add(canonical)

    pairs = []

    for i, ca in enumerate(contacts):
        for cb in contacts[i + 1:]:
            # Canonical pair for dismissal check
            canonical = (min(str(ca.id), str(cb.id)), max(str(ca.id), str(cb.id)))
            if canonical in dismissed_set:
                continue

            # Check for matches
            reasons = []
            confidence = None
            similarity = 0.0

            # Exact email match
            if ca.email and cb.email and ca.email.lower() == cb.email.lower():
                reasons.append('Exact email match')
                confidence = 'high'
                similarity = 1.0

            # Exact phone match
            phones_a = {p for p in [ca.phone, ca.phone_secondary] if p}
            phones_b = {p for p in [cb.phone, cb.phone_secondary] if p}
            if phones_a & phones_b:
                reasons.append('Exact phone match')
                confidence = 'high'
                similarity = 1.0

            # Fuzzy name match (PostgreSQL only)
            if not reasons:
                try:
                    from django.contrib.postgres.search import TrigramSimilarity

                    # Compare names using trigram similarity
                    name_sim = 0.0
                    if ca.first_name and cb.first_name:
                        first_qs = Contact.objects.filter(pk=cb.pk).annotate(
                            sim=TrigramSimilarity('first_name', ca.first_name)
                        ).values_list('sim', flat=True)
                        first_sim = list(first_qs)
                        if first_sim:
                            name_sim = max(name_sim, first_sim[0] or 0)

                    if ca.last_name and cb.last_name:
                        last_qs = Contact.objects.filter(pk=cb.pk).annotate(
                            sim=TrigramSimilarity('last_name', ca.last_name)
                        ).values_list('sim', flat=True)
                        last_sim = list(last_qs)
                        if last_sim:
                            name_sim = max(name_sim, last_sim[0] or 0)

                    if name_sim >= 0.4:
                        if name_sim >= 0.6:
                            confidence = 'medium'
                        else:
                            confidence = 'low'
                        similarity = name_sim
                        reasons.append(f'Name similarity: {name_sim:.2f}')
                except (ImportError, Exception):
                    # SQLite -- skip name matching
                    pass

            if reasons:
                pairs.append({
                    'contact_a': ca,
                    'contact_b': cb,
                    'confidence': confidence,
                    'reasons': reasons,
                    'similarity': similarity,
                })

    # Sort by confidence tier, then similarity descending
    pairs.sort(key=lambda p: (_CONFIDENCE_ORDER[p['confidence']], -p['similarity']))

    return pairs


@transaction.atomic
def merge_contacts(survivor_id, loser_id, field_overrides, merged_by):
    """
    Atomically merge loser contact into survivor contact.

    Reassigns all FK relationships, union-merges groups, soft-deletes loser,
    recalculates survivor stats, and creates an audit log entry.

    Args:
        survivor_id: UUID of the contact to keep
        loser_id: UUID of the contact to merge away
        field_overrides: dict of {field_name: 'right'} to copy loser's value to survivor
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

    if loser.is_merged:
        raise ValueError('Contact has already been merged')

    # Apply field overrides: copy loser's field value to survivor for 'right' selections
    # Track unique-constrained fields that need clearing on loser to avoid constraint violations
    _unique_fields = {'email'}  # Fields involved in unique constraints with owner
    loser_fields_to_clear = []
    for field_name, choice in (field_overrides or {}).items():
        if choice == 'right' and field_name in MERGEABLE_FIELDS:
            setattr(survivor, field_name, getattr(loser, field_name))
            if field_name in _unique_fields:
                loser_fields_to_clear.append(field_name)

    # Clear unique-constrained fields on loser before saving survivor to avoid
    # UNIQUE constraint violations (e.g., both contacts having the same email+owner)
    if loser_fields_to_clear:
        for field_name in loser_fields_to_clear:
            setattr(loser, field_name, '')
        loser.save(update_fields=loser_fields_to_clear + ['updated_at'])

    # Reassign FK relationships, capturing counts
    gifts_count = Gift.objects.filter(donor_contact=loser).update(donor_contact=survivor)
    recurring_gifts_count = RecurringGift.objects.filter(donor_contact=loser).update(donor_contact=survivor)
    tasks_count = Task.objects.filter(contact=loser).update(contact=survivor)
    prayer_intentions_count = PrayerIntention.objects.filter(contact=loser).update(contact=survivor)
    events_count = Event.objects.filter(contact=loser).update(contact=survivor)
    journal_contacts_count = _merge_journal_contacts(survivor, loser)

    # Union-merge groups
    survivor.groups.add(*loser.groups.all())

    # Soft-delete loser
    loser.is_merged = True
    loser.merged_into = survivor
    loser.save(update_fields=['is_merged', 'merged_into', 'updated_at'])

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
        field_overrides=field_overrides or {},
        records_migrated={
            'gifts': gifts_count,
            'recurring_gifts': recurring_gifts_count,
            'tasks': tasks_count,
            'prayer_intentions': prayer_intentions_count,
            'events': events_count,
            'journal_contacts': journal_contacts_count,
        },
    )

    # Clean up dismissed duplicates involving the loser
    DismissedDuplicate.objects.filter(
        Q(contact_a=loser) | Q(contact_b=loser)
    ).delete()

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
            # Transfer child records to survivor's JournalContact
            JournalStageEvent.objects.filter(journal_contact=loser_jc).update(
                journal_contact=survivor_jc
            )
            Decision.objects.filter(journal_contact=loser_jc).update(
                journal_contact=survivor_jc
            )
            NextStep.objects.filter(journal_contact=loser_jc).update(
                journal_contact=survivor_jc
            )
            loser_jc.delete()
        else:
            # No conflict: just reassign
            loser_jc.contact = survivor
            loser_jc.save(update_fields=['contact'])

        count += 1

    return count
