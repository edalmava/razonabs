# AGENTS.md - Test de Razonamiento Abstracto

## Project Overview
Django-based assessment system for abstract reasoning tests. Students take timed tests with visual questions; teachers manage the question bank.

## Tech Stack
- **Framework:** Django 6.0.5
- **Python:** 3.13
- **DB:** PostgreSQL (default), SQLite (local dev fallback)
- **Images:** Pillow

## Commands
```powershell
# Activate venv
.\virtual\Scripts\Activate.ps1

# Run dev server
python manage.py runserver

# DB migration
python manage.py makemigrations test_razonamiento
python manage.py migrate
```

## Key Files
- `test_razonamiento/`: Main app (models, views, admin)
- `testrazonabs/`: Project settings
- `GEMINI.md`: Detailed project documentation
- `db.sqlite3`: Local SQLite DB (exists)

## Configuration Notes
- `DEBUG = True` in `settings.py`
- `ALLOWED_HOSTS = []` (requires update for deployment)
- Database defaults to PostgreSQL on localhost:5433. Switch to SQLite for local dev if Postgres is unavailable:
  ```python
  DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
  ```

## Important Constraints
- All models inherit from `TimeStampedModel`
- Questions must have exactly 6 answer options (enforced by model validation)
- Images stored in `media/questions/{id}/`
- `AUTH_USER_MODEL` points to `CustomUser` in `test_razonamiento`
- Test model has `max_attempts` field (default: 1) - controls how many times a student can take the test

## Template Constraints
- **CRITICAL:** Django templates do NOT allow variables starting with underscores (`_`). Use dictionary context or computed properties instead of attaching `_attr` to model instances.

## Model Methods (Test)
- `get_user_attempts_count(user)`: Returns finished attempts for a user
- `has_active_attempt(user)`: Returns True if user has an in-progress attempt
- `can_start_new(user)`: Returns True if user can start a new attempt

## Teacher Features
- Student CRUD: `/teacher/students/`, `add/`, `<pk>/edit/`, `<pk>/delete/`
- Question management: `/teacher/questions/`
- Test creation with `max_attempts`, `num_questions`, `seconds_per_question`