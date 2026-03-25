"""
Factories for Task model tests.
"""
from datetime import timedelta

import factory
from django.utils import timezone
from faker import Faker

from apps.contacts.tests.factories import ContactFactory
from apps.tasks.models import BroadcastTask, Task, TaskPriority, TaskStatus, TaskType
from apps.users.tests.factories import UserFactory

fake = Faker()


class TaskFactory(factory.django.DjangoModelFactory):
    """Factory for creating Task instances."""

    class Meta:
        model = Task

    owner = factory.SubFactory(UserFactory)
    contact = factory.SubFactory(ContactFactory)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    description = ''
    task_type = TaskType.OTHER
    priority = TaskPriority.MEDIUM
    status = TaskStatus.PENDING
    due_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=7))


class CallTaskFactory(TaskFactory):
    """Factory for phone call tasks."""
    task_type = TaskType.CALL
    title = factory.LazyFunction(lambda: f'Call {fake.name()}')


class ThankYouTaskFactory(TaskFactory):
    """Factory for thank you tasks."""
    task_type = TaskType.THANK_YOU
    priority = TaskPriority.HIGH


class OverdueTaskFactory(TaskFactory):
    """Factory for overdue tasks."""
    due_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=5))


class CompletedTaskFactory(TaskFactory):
    """Factory for completed tasks."""
    status = TaskStatus.COMPLETED
    completed_at = factory.LazyFunction(timezone.now)


class BroadcastTaskFactory(factory.django.DjangoModelFactory):
    """Factory for creating BroadcastTask instances."""

    class Meta:
        model = BroadcastTask

    sender = factory.SubFactory(UserFactory)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    description = ''
    task_type = TaskType.OTHER
    priority = TaskPriority.MEDIUM
    due_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=7))
    target_type = 'all_missionaries'
    recipient_ids = factory.LazyFunction(list)
    recipient_count = 0
