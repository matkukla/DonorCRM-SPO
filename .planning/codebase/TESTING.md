# Testing Patterns

**Analysis Date:** 2026-01-24

## Test Framework

**Runner:**
- pytest (configured in `pyproject.toml`)
- Config file: `pyproject.toml`

**Assertion Library:**
- pytest's built-in assertions (standard `assert` statements)
- REST framework's status codes: `from rest_framework import status`

**Run Commands:**
```bash
pytest                                    # Run all tests
pytest -m "not slow"                      # Skip slow tests
pytest --cov=apps --cov-report=html       # Coverage with HTML report
pytest apps/contacts/tests/                # Run specific app tests
pytest -v                                 # Verbose output
```

**Coverage Requirements:**
- Minimum coverage: 80% (enforced by `--cov-fail-under=80`)
- Coverage report locations: terminal and HTML (`htmlcov/`)
- Source: `apps/` directory only
- Omit: migrations, tests, `__init__.py`, admin.py

## Test File Organization

**Location:**
- Co-located with source code in `tests/` subdirectory of each app
- Pattern: `apps/{app_name}/tests/`

**Naming:**
- Test modules: `test_*.py` or `*_test.py` (pytest discovers both)
- Test classes: `TestClassName` (CamelCase starting with "Test")
- Test methods: `test_description_of_what_is_tested`

**Structure:**
```
apps/contacts/tests/
├── __init__.py
├── factories.py          # Factory definitions (reused across tests)
├── test_integration.py   # Integration/workflow tests
├── test_models.py        # Model unit tests
└── test_views.py         # API view tests
```

**Marker Registration:**
From `pyproject.toml`:
```python
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

## Test Structure

**Django Database Tests:**
All tests use `@pytest.mark.django_db` decorator to enable database access:

```python
@pytest.mark.django_db
class TestDonorWorkflow:
    """Test the complete workflow from prospect to donor."""

    def test_complete_donor_journey(self, authenticated_client):
        client, user = authenticated_client
        # ... test code
```

**Suite Organization Pattern:**
Classes group related tests by concern:
- `TestPledgeModel` - model methods and properties
- `TestPledgeStateTransitions` - state change validations
- `TestPermissionBoundaries` - permission enforcement
- `TestDonorWorkflow` - end-to-end workflows

## Test Structure Examples

**Model Test Pattern:**
From `apps/pledges/tests/test_models.py`:
```python
@pytest.mark.django_db
class TestPledgeModel:
    """Tests for Pledge model methods and properties."""

    def test_pledge_str(self):
        """Test pledge string representation."""
        pledge = PledgeFactory(amount=Decimal('100.00'), frequency=PledgeFrequency.MONTHLY)
        assert '$100.00' in str(pledge)
        assert 'Monthly' in str(pledge)
```

**View Test Pattern:**
From `apps/dashboard/tests/test_views.py`:
```python
@pytest.mark.django_db
class TestDashboardView:
    """Tests for main dashboard endpoint."""

    def test_get_dashboard(self):
        """Test getting full dashboard data."""
        user = UserFactory(role='staff')
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/')

        assert response.status_code == status.HTTP_200_OK
        assert 'what_changed' in response.data
```

**Integration Test Pattern:**
From `apps/contacts/tests/test_integration.py`:
```python
@pytest.mark.django_db
class TestDonorWorkflow:
    """Test the complete workflow from prospect to donor."""

    def test_complete_donor_journey(self, authenticated_client):
        """
        Test complete journey:
        1. Create prospect
        2. Add first donation (becomes donor)
        3. Stats update automatically
        4. Thank-you tracking
        """
        client, user = authenticated_client

        # Step 1: Create a prospect
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
        })
        assert response.status_code == status.HTTP_201_CREATED
        contact_id = response.data['id']

        # Step 2: Verify behavior
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_200_OK
```

**Patterns:**
- **Setup:** Create test data using factories, authenticate client
- **Action:** Make API calls or invoke methods
- **Assertion:** Verify response status, data content, state changes
- **Cleanup:** Django test database automatically rolls back

## Mocking

**Framework:** factory_boy for test data generation

**Test Data Factories:**
Located in `apps/{app}/tests/factories.py`:

From `apps/contacts/tests/factories.py`:
```python
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
```

**Specialized Factories:**
```python
class DonorContactFactory(ContactFactory):
    """Factory for creating donor contacts with giving history."""
    status = ContactStatus.DONOR

class LapsedContactFactory(ContactFactory):
    """Factory for creating lapsed donor contacts."""
    status = ContactStatus.LAPSED
```

**Factory Usage:**
```python
# Single instance
contact = ContactFactory()
contact_with_args = ContactFactory(first_name='Jane', status=ContactStatus.DONOR)

# Batch creation
contacts = ContactFactory.create_batch(5)

# With subfactory
pledge = PledgeFactory(contact=contact, amount=Decimal('100.00'))
```

**What to Mock:**
- External API calls (not present in sample code)
- Complex dependencies - use factory defaults instead
- Database queries - use factories to create real test data

**What NOT to Mock:**
- Database models - use real instances via factories
- Django ORM queries - test against real database
- API responses - assert on actual response data
- Business logic in models/services - test the actual implementation

## Fixtures and Factories

**Test Data:**
From `conftest.py` (fixtures):
```python
@pytest.fixture
def authenticated_client(user_factory):
    """Return an API client authenticated as a staff user."""
    client = APIClient()
    user = user_factory(role='staff')
    client.force_authenticate(user=user)
    return client, user

@pytest.fixture
def admin_client(user_factory):
    """Return an API client authenticated as an admin."""
    client = APIClient()
    user = user_factory(role='admin')
    client.force_authenticate(user=user)
    return client, user
```

**Fixture Location:**
- Global fixtures: `/home/matkukla/projects/DonorCRM/conftest.py`
- App-level fixtures: In app's `tests/` directory (if needed)

**Available Fixtures in Tests:**
- `api_client` - unauthenticated REST client
- `authenticated_client` - returns (client, staff_user) tuple
- `admin_client` - returns (client, admin_user) tuple
- `finance_client` - returns (client, finance_user) tuple
- `user_factory` - UserFactory for custom user creation

**Factory Imports:**
```python
from apps.contacts.tests.factories import ContactFactory, DonorContactFactory
from apps.users.tests.factories import UserFactory
from apps.pledges.tests.factories import PledgeFactory, AnnualPledgeFactory
from apps.donations.tests.factories import DonationFactory
```

## Coverage

**Requirements:** 80% coverage of `apps/` directory

**View Coverage:**
```bash
pytest --cov=apps --cov-report=html --cov-report=term-missing
# HTML report: htmlcov/index.html
# Terminal: shows uncovered lines
```

**Excluded from Coverage:**
- `*/migrations/*` - auto-generated
- `*/tests/*` - test code itself
- `*/__init__.py` - empty files
- `*/admin.py` - Django admin registration

## Test Types

**Unit Tests:**
- Scope: Individual model methods and properties
- Approach: Create specific test data via factories, invoke method, assert result
- Example: `test_monthly_equivalent_quarterly()` in `apps/pledges/tests/test_models.py`
- No HTTP requests or API calls

**Integration Tests:**
- Scope: Multi-step workflows involving multiple models
- Approach: Create fixture data, make sequential API calls, verify state changes
- Example: `test_complete_donor_journey()` in `apps/contacts/tests/test_integration.py`
- Tests actual API endpoints with full request/response cycle
- Verify cross-model updates (e.g., donation updates contact.total_given)

**E2E Tests:**
- Framework: Not currently used
- Frontend testing via React component testing not found in codebase
- Integration tests serve as e2e validation for API workflows

## Common Patterns

**Async Testing:**
Tests are synchronous. No async patterns found in test code.

**Error Testing:**
From `apps/contacts/tests/test_integration.py`:
```python
def test_permission_boundaries(self):
    """Test that permission boundaries are enforced."""
    client, user1 = authenticated_client

    # User 1 creates a contact
    response = client.post('/api/v1/contacts/', {...})
    contact_id = response.data['id']

    # Create another user
    user2 = user_factory(role='staff')
    client.force_authenticate(user=user2)

    # User 2 tries to access User 1's contact
    response = client.get(f'/api/v1/contacts/{contact_id}/')
    assert response.status_code == status.HTTP_404_NOT_FOUND
```

**Database State Verification:**
```python
def test_fulfillment_percentage_partial(self):
    """Test fulfillment percentage with partial fulfillment."""
    pledge = PledgeFactory(
        total_expected=Decimal('100.00'),
        total_received=Decimal('50.00')
    )
    assert pledge.fulfillment_percentage == 50.0
```

**Date Calculations:**
```python
def test_calculate_next_expected_date_monthly(self):
    """Test next expected date calculation for monthly pledge."""
    start = timezone.now().date()
    pledge = PledgeFactory(start_date=start, frequency=PledgeFrequency.MONTHLY)

    next_date = pledge.calculate_next_expected_date()

    assert next_date is not None
    assert (next_date - start).days >= 28
    assert (next_date - start).days <= 31
```

**Decimal/Money Comparisons:**
```python
def test_fulfillment_percentage_zero(self):
    """Test fulfillment percentage with zero expected."""
    pledge = PledgeFactory(total_expected=Decimal('0'), total_received=Decimal('0'))
    assert pledge.fulfillment_percentage == 0

def test_support_progress(self):
    """Test support progress calculation."""
    user = UserFactory(role='staff', monthly_goal=Decimal('3000.00'))
    result = get_support_progress(user)
    assert result['monthly_goal'] == 3000.0
```

## Test Execution

**Running Specific Tests:**
```bash
# Single test file
pytest apps/contacts/tests/test_integration.py

# Single test class
pytest apps/contacts/tests/test_integration.py::TestDonorWorkflow

# Single test method
pytest apps/contacts/tests/test_integration.py::TestDonorWorkflow::test_complete_donor_journey

# Tests matching pattern
pytest -k "test_permission" apps/contacts/tests/

# Marked tests
pytest -m "integration"
pytest -m "not slow"
```

**Debugging:**
```bash
pytest --pdb               # Drop into debugger on failure
pytest -s                  # Show print statements
pytest -vv                 # Very verbose with all assertions
```

---

*Testing analysis: 2026-01-24*
