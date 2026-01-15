"""
Factories for Contact model tests.
"""
import factory
from faker import Faker

from apps.contacts.models import Contact, ContactStatus
from apps.users.tests.factories import UserFactory

fake = Faker()


class ContactFactory(factory.django.DjangoModelFactory):
    """Factory for creating Contact instances."""

    class Meta:
        model = Contact

    owner = factory.SubFactory(UserFactory)
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    email = factory.LazyFunction(fake.email)
    phone = factory.LazyFunction(lambda: fake.numerify('###-###-####'))
    street_address = factory.LazyFunction(fake.street_address)
    city = factory.LazyFunction(fake.city)
    state = factory.LazyFunction(fake.state_abbr)
    postal_code = factory.LazyFunction(fake.zipcode)
    country = 'USA'
    status = ContactStatus.PROSPECT
    notes = ''


class DonorContactFactory(ContactFactory):
    """Factory for creating donor contacts with giving history."""
    status = ContactStatus.DONOR


class LapsedContactFactory(ContactFactory):
    """Factory for creating lapsed donor contacts."""
    status = ContactStatus.LAPSED
