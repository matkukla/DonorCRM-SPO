# DonorCRM - Build & Run Guide

This guide covers how to build, test, and run the DonorCRM Django backend.

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ and PostgreSQL 15+ (for local development)

## Quick Start with Docker (Recommended)

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd DonorCRM

# Copy environment template
cp .env.example .env

# Edit .env with your local settings (the defaults should work for development)
```

### 2. Build and Start Services

```bash
# Build and start all services (PostgreSQL, Redis, Django, Celery, Celery Beat)
docker-compose up --build

# Or run in detached mode
docker-compose up -d
```

This will start:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Django web server** on port 8000
- **Celery worker** for background tasks
- **Celery beat** for scheduled tasks

### 3. Run Migrations and Create Superuser

```bash
# Run database migrations
docker-compose exec web python manage.py migrate

# Create a superuser account
docker-compose exec web python manage.py createsuperuser

# You'll be prompted for:
# - Email address: admin@example.com
# - First name: Admin
# - Last name: User
# - Password: (choose a secure password)
```

### 4. Access the Application

- **API Base**: http://localhost:8000/api/v1/
- **Swagger UI**: http://localhost:8000/api/v1/docs/ (interactive API documentation)
- **ReDoc**: http://localhost:8000/api/v1/redoc/ (alternative API docs)
- **OpenAPI Schema**: http://localhost:8000/api/v1/schema/ (JSON/YAML schema for code generation)
- **Admin Panel**: http://localhost:8000/admin/

### 5. Run Tests

```bash
# Run all tests with coverage
docker-compose exec web pytest

# Run tests with verbose output
docker-compose exec web pytest -v

# Run tests for a specific app
docker-compose exec web pytest apps/contacts/tests/

# Run tests and generate HTML coverage report
docker-compose exec web pytest --cov-report=html
```

## Local Development (Without Docker)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements/dev.txt
```

### 2. Setup PostgreSQL Database

```bash
# Using psql
createdb donorcrm
createuser donorcrm -P  # Set password when prompted

# Or using PostgreSQL GUI tools
```

### 3. Setup Environment Variables

```bash
cp .env.example .env

# Edit .env:
DATABASE_URL=postgres://donorcrm:your_password@localhost:5432/donorcrm
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev
```

### 4. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Start Development Server

```bash
# Terminal 1: Django dev server
python manage.py runserver

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat scheduler
celery -A config beat -l info
```

### 6. Run Tests Locally

```bash
pytest
pytest -v --cov=apps
```

## Project Structure

```
DonorCRM/
├── config/                 # Project configuration
│   ├── settings/          # Split settings (base, dev, test, prod)
│   ├── urls.py            # Root URL configuration
│   ├── wsgi.py            # WSGI entry point
│   └── celery.py          # Celery configuration
├── apps/                   # Django applications
│   ├── users/             # Custom user model & authentication
│   ├── contacts/          # Donor/prospect management
│   ├── donations/         # Gift records
│   ├── pledges/           # Recurring commitments
│   ├── tasks/             # Reminders and action items
│   ├── events/            # Audit trail & notifications
│   ├── groups/            # Contact tags/segments
│   ├── dashboard/         # Dashboard aggregations
│   ├── imports/           # CSV import/export
│   └── core/              # Shared utilities
├── docker-compose.yml      # Docker development setup
├── Dockerfile              # Development Docker image
├── Dockerfile.prod         # Production Docker image
├── requirements/           # Python dependencies
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── pyproject.toml          # Tool configuration (pytest, black, isort)
```

## Development Workflow

### Running Linters

```bash
# Format code with Black
docker-compose exec web black apps/ config/

# Sort imports with isort
docker-compose exec web isort apps/ config/

# Run flake8 for style checking
docker-compose exec web flake8 apps/ config/
```

### Creating Migrations

```bash
# After modifying models
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate
```

### Django Shell

```bash
# Interactive Django shell with IPython
docker-compose exec web python manage.py shell_plus
```

### Useful Management Commands

```bash
# Create test data
docker-compose exec web python manage.py shell_plus
>>> from apps.users.tests.factories import UserFactory
>>> from apps.contacts.tests.factories import ContactFactory
>>> user = UserFactory(email='test@example.com')
>>> ContactFactory.create_batch(10, owner=user)

# Check for late pledges manually
docker-compose exec web python manage.py shell
>>> from apps.pledges.tasks import check_late_pledges
>>> check_late_pledges()

# Export contacts
docker-compose exec web python manage.py shell
>>> from apps.imports.services import export_contacts
>>> export_contacts(user, '/tmp/contacts.csv')
```

## API Testing with curl

### 1. Login and Get Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}'

# Save the access token from response
export TOKEN="your_access_token_here"
```

### 2. Get Current User

```bash
curl http://localhost:8000/api/v1/users/me/ \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Create a Contact

```bash
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "status": "prospect"
  }'
```

### 4. List Contacts

```bash
curl http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Add a Donation

```bash
curl -X POST http://localhost:8000/api/v1/donations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contact": "contact_uuid_here",
    "amount": "100.00",
    "date": "2026-01-14",
    "donation_type": "one_time",
    "payment_method": "check"
  }'
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Migration Conflicts

```bash
# Reset migrations (WARNING: destroys data)
docker-compose exec web python manage.py migrate <app> zero
docker-compose exec web python manage.py migrate

# Or start fresh
docker-compose down -v  # Removes volumes
docker-compose up --build
docker-compose exec web python manage.py migrate
```

### Celery Not Processing Tasks

```bash
# Check Celery logs
docker-compose logs celery

# Restart Celery worker
docker-compose restart celery

# Manually trigger a task for testing
docker-compose exec web python manage.py shell
>>> from apps.pledges.tasks import check_late_pledges
>>> result = check_late_pledges.delay()
>>> result.get()  # Wait for result
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
```

## Testing Strategy

### Unit Tests
Focus on individual model methods and business logic.

```bash
# Test a specific model
docker-compose exec web pytest apps/contacts/tests/test_models.py -v
```

### Integration Tests
Test API endpoints with database interactions.

```bash
# Test a specific view
docker-compose exec web pytest apps/contacts/tests/test_views.py -v
```

### Coverage Report

```bash
# Generate coverage report
docker-compose exec web pytest --cov=apps --cov-report=html

# View report (generated in htmlcov/)
open htmlcov/index.html
```

## Deployment

See deployment-specific documentation:
- **Railway**: [railway.toml](railway.toml)
- **Render**: [render.yaml](render.yaml)
- **Production Docker**: Use [Dockerfile.prod](Dockerfile.prod) with gunicorn

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up Sentry for error tracking
- [ ] Enable SSL/HTTPS
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up monitoring (logs, metrics)
- [ ] Review security settings in `config/settings/prod.py`

## Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/
- Celery Documentation: https://docs.celeryq.dev/
- pytest Documentation: https://docs.pytest.org/
