# DonorCRM - Quick Start Guide

Get the DonorCRM backend running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Git installed

## 1. Environment Setup (30 seconds)

```bash
# Copy the environment template
cp .env.example .env

# The defaults in .env.example work for development, but you can customize:
# - SECRET_KEY (auto-generated is fine for dev)
# - DATABASE_URL (default works with docker-compose)
# - REDIS_URL (default works with docker-compose)
```

## 2. Start Services (2 minutes)

```bash
# Build and start all Docker services
docker-compose up --build

# This starts:
# - PostgreSQL database
# - Redis cache
# - Django web server on http://localhost:8000
# - Celery worker
# - Celery beat scheduler
```

Wait for the log message: `"Listening at: http://0.0.0.0:8000"`

## 3. Initialize Database (1 minute)

In a new terminal:

```bash
# Run database migrations
docker-compose exec web python manage.py migrate

# Create your admin account
docker-compose exec web python manage.py createsuperuser
# Enter:
#   Email: your@email.com
#   First name: Your
#   Last name: Name
#   Password: ********
```

## 4. Verify Installation (1 minute)

```bash
# Run the test suite
docker-compose exec web pytest

# You should see:
# ✓ All tests passing
# ✓ 80%+ coverage
```

## 5. Test the API (30 seconds)

### Get a JWT Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"your_password"}'

# Save the access token from the response
export TOKEN="your_access_token_here"
```

### Get Your Profile

```bash
curl http://localhost:8000/api/v1/users/me/ \
  -H "Authorization: Bearer $TOKEN"
```

### Create a Contact

```bash
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Donor",
    "email": "john@example.com",
    "status": "prospect"
  }'
```

## You're Ready! 🎉

### What's Available

- **API**: http://localhost:8000/api/v1/
- **Swagger UI**: http://localhost:8000/api/v1/docs/ (interactive API documentation)
- **ReDoc**: http://localhost:8000/api/v1/redoc/ (alternative API documentation)
- **OpenAPI Schema**: http://localhost:8000/api/v1/schema/ (JSON schema)
- **Admin Panel**: http://localhost:8000/admin/ (login with superuser credentials)
- **PostgreSQL**: localhost:5432 (user: donorcrm, password: donorcrm_dev_password, db: donorcrm)
- **Redis**: localhost:6379

### Next Steps

1. **Explore the API**: See [BUILD.md](BUILD.md) for all endpoints
2. **Run more tests**: `docker-compose exec web pytest -v`
3. **Check logs**: `docker-compose logs -f web`
4. **Access Django shell**: `docker-compose exec web python manage.py shell_plus`

### Common Commands

```bash
# Stop services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# View logs
docker-compose logs -f

# Run specific tests
docker-compose exec web pytest apps/contacts/tests/ -v

# Django shell
docker-compose exec web python manage.py shell_plus

# Create migrations
docker-compose exec web python manage.py makemigrations

# Check for issues
docker-compose exec web python manage.py check
```

### Troubleshooting

**Port 8000 already in use?**
```bash
# Change the port in docker-compose.yml
# Find: "8000:8000"
# Change to: "8080:8000"
```

**Database connection errors?**
```bash
# Restart the database
docker-compose restart db

# Or start fresh
docker-compose down -v
docker-compose up --build
```

**Tests failing?**
```bash
# Make sure migrations are current
docker-compose exec web python manage.py migrate

# Check for any errors
docker-compose exec web python manage.py check
```

## Full Documentation

- **BUILD.md** - Complete build and development guide
- **IMPLEMENTATION_SUMMARY.md** - Technical architecture and API reference
- **README.md** - Project overview and philosophy
- **Plan file** - Implementation plan in `.claude/plans/`

## Deployment

When ready to deploy:

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Render
```bash
# Push to GitHub
git push origin main

# In Render dashboard:
# 1. New Blueprint
# 2. Connect repository
# 3. Deploy from render.yaml
```

See [BUILD.md](BUILD.md#deployment) for detailed deployment instructions.
