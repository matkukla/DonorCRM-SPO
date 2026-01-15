"""
Management command to generate sample data for testing.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from apps.contacts.models import Contact, ContactStatus
from apps.donations.models import Donation, DonationType, PaymentMethod
from apps.events.models import Event, EventSeverity, EventType
from apps.groups.models import Group
from apps.pledges.models import Pledge, PledgeFrequency, PledgeStatus
from apps.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from apps.users.models import User, UserRole

fake = Faker()


class Command(BaseCommand):
    help = 'Generate sample data for testing the API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contacts',
            type=int,
            default=25,
            help='Number of contacts to create (default: 25)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new data'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self._clear_data()

        self.stdout.write('Generating sample data...')

        # Create users
        users = self._create_users()
        fundraiser = users['fundraiser']

        # Create groups
        groups = self._create_groups(fundraiser)

        # Create contacts
        contacts = self._create_contacts(fundraiser, options['contacts'], groups)

        # Create donations and pledges
        self._create_donations_and_pledges(contacts)

        # Create tasks
        self._create_tasks(fundraiser, contacts)

        self.stdout.write(self.style.SUCCESS('Sample data generated successfully!'))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write(f'  Fundraiser: fundraiser@example.com / testpass123')
        self.stdout.write(f'  Admin: admin@example.com / testpass123')
        self.stdout.write(f'  Finance: finance@example.com / testpass123')
        self.stdout.write('')
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - 3 users (fundraiser, admin, finance)')
        self.stdout.write(f'  - {len(groups)} groups')
        self.stdout.write(f'  - {len(contacts)} contacts')
        self.stdout.write(f'  - {Donation.objects.count()} donations')
        self.stdout.write(f'  - {Pledge.objects.count()} pledges')
        self.stdout.write(f'  - {Task.objects.count()} tasks')
        self.stdout.write(f'  - {Event.objects.count()} events')

    def _clear_data(self):
        """Clear all existing data."""
        Event.objects.all().delete()
        Task.objects.all().delete()
        Donation.objects.all().delete()
        Pledge.objects.all().delete()
        Contact.objects.all().delete()
        Group.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_users(self):
        """Create sample users."""
        users = {}

        # Fundraiser user
        fundraiser, _ = User.objects.get_or_create(
            email='fundraiser@example.com',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Smith',
                'role': UserRole.FUNDRAISER,
                'monthly_goal': Decimal('5000.00'),
                'is_active': True,
            }
        )
        fundraiser.set_password('testpass123')
        fundraiser.save()
        users['fundraiser'] = fundraiser

        # Admin user
        admin, _ = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_active': True,
            }
        )
        admin.set_password('testpass123')
        admin.save()
        users['admin'] = admin

        # Finance user
        finance, _ = User.objects.get_or_create(
            email='finance@example.com',
            defaults={
                'first_name': 'Finance',
                'last_name': 'Manager',
                'role': UserRole.FINANCE,
                'is_active': True,
            }
        )
        finance.set_password('testpass123')
        finance.save()
        users['finance'] = finance

        self.stdout.write(f'  Created/updated 3 users')
        return users

    def _create_groups(self, owner):
        """Create sample groups."""
        group_data = [
            {'name': 'Monthly Supporters', 'color': '#22c55e', 'description': 'Active monthly donors'},
            {'name': 'Church Partners', 'color': '#3b82f6', 'description': 'Church congregations'},
            {'name': 'Family & Friends', 'color': '#f97316', 'description': 'Personal connections'},
            {'name': 'Major Donors', 'color': '#a855f7', 'description': 'Donors giving $500+'},
            {'name': 'Prayer Partners', 'color': '#06b6d4', 'description': 'Committed to praying'},
            {'name': 'Prospects', 'color': '#6366f1', 'description': 'Potential new supporters'},
        ]

        groups = []
        for data in group_data:
            group, _ = Group.objects.get_or_create(
                name=data['name'],
                owner=owner,
                defaults={
                    'color': data['color'],
                    'description': data['description'],
                }
            )
            groups.append(group)

        self.stdout.write(f'  Created {len(groups)} groups')
        return groups

    def _create_contacts(self, owner, count, groups):
        """Create sample contacts with various statuses."""
        contacts = []
        statuses = [
            (ContactStatus.DONOR, 0.4),
            (ContactStatus.PROSPECT, 0.3),
            (ContactStatus.ASKED, 0.15),
            (ContactStatus.LAPSED, 0.1),
            (ContactStatus.DECLINED, 0.05),
        ]

        for i in range(count):
            # Choose status based on distribution
            status = random.choices(
                [s[0] for s in statuses],
                weights=[s[1] for s in statuses]
            )[0]

            contact = Contact.objects.create(
                owner=owner,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email() if random.random() > 0.1 else '',
                phone=fake.numerify('###-###-####'),
                street_address=fake.street_address(),
                city=fake.city(),
                state=fake.state_abbr(),
                postal_code=fake.zipcode(),
                country='USA',
                status=status,
                notes=fake.paragraph() if random.random() > 0.6 else '',
            )

            # Assign to random groups
            if random.random() > 0.3:
                num_groups = random.randint(1, 3)
                selected_groups = random.sample(groups, min(num_groups, len(groups)))
                contact.groups.set(selected_groups)

            contacts.append(contact)

        self.stdout.write(f'  Created {len(contacts)} contacts')
        return contacts

    def _create_donations_and_pledges(self, contacts):
        """Create donations and pledges for donor contacts."""
        today = timezone.now().date()
        donation_count = 0
        pledge_count = 0

        for contact in contacts:
            if contact.status not in [ContactStatus.DONOR, ContactStatus.LAPSED]:
                continue

            # Create historical donations (1-8 per donor)
            num_donations = random.randint(1, 8)
            for j in range(num_donations):
                days_ago = random.randint(1, 365)
                donation_date = today - timedelta(days=days_ago)
                amount = Decimal(random.choice([25, 50, 75, 100, 150, 200, 250, 500, 1000]))

                Donation.objects.create(
                    contact=contact,
                    amount=amount,
                    date=donation_date,
                    donation_type=random.choice([
                        DonationType.ONE_TIME,
                        DonationType.RECURRING,
                        DonationType.SPECIAL,
                    ]),
                    payment_method=random.choice([
                        PaymentMethod.CHECK,
                        PaymentMethod.CREDIT_CARD,
                        PaymentMethod.BANK_TRANSFER,
                    ]),
                    thanked=random.random() > 0.3,
                )
                donation_count += 1

            # Update contact stats after creating donations
            contact.update_giving_stats()

            # Create pledge for some donors (40% chance)
            if random.random() > 0.6:
                frequency = random.choice([
                    PledgeFrequency.MONTHLY,
                    PledgeFrequency.QUARTERLY,
                    PledgeFrequency.ANNUAL,
                ])
                amount = Decimal(random.choice([50, 100, 150, 200, 250]))
                start_date = today - timedelta(days=random.randint(30, 180))

                pledge = Pledge.objects.create(
                    contact=contact,
                    amount=amount,
                    frequency=frequency,
                    status=PledgeStatus.ACTIVE,
                    start_date=start_date,
                )
                pledge_count += 1

                # Check late status for some pledges
                if random.random() > 0.7:
                    pledge.check_late_status()
                    pledge.save()

        self.stdout.write(f'  Created {donation_count} donations')
        self.stdout.write(f'  Created {pledge_count} pledges')

    def _create_tasks(self, owner, contacts):
        """Create sample tasks."""
        today = timezone.now().date()
        task_count = 0

        task_templates = [
            ('Call to thank for donation', TaskType.THANK_YOU, TaskPriority.HIGH),
            ('Follow up on support request', TaskType.FOLLOW_UP, TaskPriority.MEDIUM),
            ('Send monthly newsletter', TaskType.EMAIL, TaskPriority.LOW),
            ('Schedule visit', TaskType.MEETING, TaskPriority.MEDIUM),
            ('Check on prayer request', TaskType.CALL, TaskPriority.MEDIUM),
            ('Send birthday card', TaskType.OTHER, TaskPriority.LOW),
        ]

        # Create some tasks with contacts
        for contact in random.sample(contacts, min(10, len(contacts))):
            template = random.choice(task_templates)
            due_offset = random.randint(-7, 14)  # Some overdue, some upcoming

            Task.objects.create(
                owner=owner,
                contact=contact,
                title=f'{template[0]} - {contact.full_name}',
                task_type=template[1],
                priority=template[2],
                status=TaskStatus.PENDING if due_offset >= 0 else random.choice([
                    TaskStatus.PENDING, TaskStatus.IN_PROGRESS
                ]),
                due_date=today + timedelta(days=due_offset),
                description=fake.sentence() if random.random() > 0.5 else '',
            )
            task_count += 1

        # Create some general tasks without contacts
        for _ in range(5):
            template = random.choice(task_templates)
            due_offset = random.randint(0, 21)

            Task.objects.create(
                owner=owner,
                title=template[0],
                task_type=template[1],
                priority=template[2],
                status=TaskStatus.PENDING,
                due_date=today + timedelta(days=due_offset),
                description=fake.sentence() if random.random() > 0.5 else '',
            )
            task_count += 1

        self.stdout.write(f'  Created {task_count} tasks')
