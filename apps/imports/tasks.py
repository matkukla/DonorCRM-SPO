"""
Celery tasks for asynchronous CSV imports.
"""
import logging
import uuid

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache key prefix for import progress
IMPORT_PROGRESS_PREFIX = 'import_progress_'
IMPORT_PROGRESS_TTL = 3600  # 1 hour


def get_import_progress(import_id: str) -> dict:
    """Get progress for an import task."""
    return cache.get(f'{IMPORT_PROGRESS_PREFIX}{import_id}', {
        'status': 'unknown',
        'progress': 0,
        'total': 0,
        'imported': 0,
        'errors': []
    })


def set_import_progress(import_id: str, data: dict):
    """Update progress for an import task."""
    cache.set(f'{IMPORT_PROGRESS_PREFIX}{import_id}', data, IMPORT_PROGRESS_TTL)


@shared_task(bind=True)
def import_contacts_async(self, file_content: str, user_id: int, import_id: str = None):
    """
    Asynchronously import contacts from CSV content.

    Args:
        file_content: CSV file content as string
        user_id: ID of the user performing the import
        import_id: Optional import ID for progress tracking
    """
    from apps.contacts.models import Contact
    from apps.imports.services import parse_contacts_csv
    from apps.users.models import User

    if not import_id:
        import_id = uuid.uuid4().hex[:12]

    logger.info(f'Starting async contact import {import_id} for user {user_id}')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'Import {import_id} failed: User {user_id} not found')
        set_import_progress(import_id, {
            'status': 'failed',
            'error': 'User not found'
        })
        return {'status': 'failed', 'error': 'User not found'}

    # Parse CSV
    set_import_progress(import_id, {
        'status': 'parsing',
        'progress': 0,
        'total': 0,
        'imported': 0,
        'errors': []
    })

    valid_records, errors = parse_contacts_csv(file_content, user)
    total = len(valid_records)

    logger.info(f'Import {import_id}: {total} valid records, {len(errors)} errors')

    if not valid_records:
        set_import_progress(import_id, {
            'status': 'completed',
            'progress': 100,
            'total': 0,
            'imported': 0,
            'errors': errors[:50]  # Limit stored errors
        })
        return {
            'status': 'completed',
            'imported': 0,
            'errors': errors
        }

    # Import in batches
    batch_size = 100
    imported = 0
    contacts_to_create = []

    for i, record in enumerate(valid_records):
        contacts_to_create.append(Contact(owner=user, **record))

        # Create batch when full or at end
        if len(contacts_to_create) >= batch_size or i == total - 1:
            Contact.objects.bulk_create(contacts_to_create)
            imported += len(contacts_to_create)
            contacts_to_create = []

            # Update progress
            progress = int((i + 1) / total * 100)
            set_import_progress(import_id, {
                'status': 'importing',
                'progress': progress,
                'total': total,
                'imported': imported,
                'errors': errors[:50]
            })

            logger.debug(f'Import {import_id}: {imported}/{total} contacts created')

    # Final progress update
    set_import_progress(import_id, {
        'status': 'completed',
        'progress': 100,
        'total': total,
        'imported': imported,
        'errors': errors[:50]
    })

    logger.info(f'Import {import_id} completed: {imported} contacts imported')

    return {
        'status': 'completed',
        'import_id': import_id,
        'imported': imported,
        'error_count': len(errors),
        'errors': errors[:50]
    }


@shared_task(bind=True)
def import_donations_async(self, file_content: str, user_id: int, import_id: str = None):
    """
    Asynchronously import donations from CSV content.

    Args:
        file_content: CSV file content as string
        user_id: ID of the user performing the import
        import_id: Optional import ID for progress tracking
    """
    from django.utils import timezone

    from apps.donations.models import Donation
    from apps.imports.services import parse_donations_csv
    from apps.users.models import User

    if not import_id:
        import_id = uuid.uuid4().hex[:12]

    logger.info(f'Starting async donation import {import_id} for user {user_id}')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'Import {import_id} failed: User {user_id} not found')
        set_import_progress(import_id, {
            'status': 'failed',
            'error': 'User not found'
        })
        return {'status': 'failed', 'error': 'User not found'}

    # Parse CSV
    set_import_progress(import_id, {
        'status': 'parsing',
        'progress': 0,
        'total': 0,
        'imported': 0,
        'errors': []
    })

    valid_records, errors = parse_donations_csv(file_content, user)
    total = len(valid_records)

    logger.info(f'Import {import_id}: {total} valid records, {len(errors)} errors')

    if not valid_records:
        set_import_progress(import_id, {
            'status': 'completed',
            'progress': 100,
            'total': 0,
            'imported': 0,
            'errors': errors[:50]
        })
        return {
            'status': 'completed',
            'imported': 0,
            'errors': errors
        }

    # Import in batches
    batch_size = 100
    imported = 0
    batch_id = f'import-{import_id}'
    now = timezone.now()
    donations_to_create = []

    for i, record in enumerate(valid_records):
        record['import_batch'] = batch_id
        record['imported_at'] = now
        donations_to_create.append(Donation(**record))

        # Create batch when full or at end
        if len(donations_to_create) >= batch_size or i == total - 1:
            Donation.objects.bulk_create(donations_to_create)
            imported += len(donations_to_create)
            donations_to_create = []

            # Update progress
            progress = int((i + 1) / total * 100)
            set_import_progress(import_id, {
                'status': 'importing',
                'progress': progress,
                'total': total,
                'imported': imported,
                'errors': errors[:50]
            })

            logger.debug(f'Import {import_id}: {imported}/{total} donations created')

    # Final progress update
    set_import_progress(import_id, {
        'status': 'completed',
        'progress': 100,
        'total': total,
        'imported': imported,
        'errors': errors[:50]
    })

    logger.info(f'Import {import_id} completed: {imported} donations imported')

    return {
        'status': 'completed',
        'import_id': import_id,
        'imported': imported,
        'error_count': len(errors),
        'errors': errors[:50]
    }
