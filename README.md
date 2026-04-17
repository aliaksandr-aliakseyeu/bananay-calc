# Bananay Calc

Logistics backend and delivery calculator API for the Bananay ecosystem.

Бэкенд логистической платформы и API-калькулятор доставки для экосистемы Bananay.

## Overview / Обзор

`bananay_calc` is the main FastAPI backend used by the Bananay web applications. It provides delivery cost calculation, geospatial search, operational APIs for multiple product roles, and project documentation endpoints.

`bananay_calc` это основной FastAPI-бэкенд для веб-приложений Bananay. Он обслуживает расчёт стоимости доставки, геопоиск, рабочие API для разных ролей продукта и встроенные endpoints с документацией.

## Stack / Стек

- FastAPI
- SQLAlchemy 2 async
- PostgreSQL + PostGIS
- GeoAlchemy2
- Alembic
- Poetry
- OpenRouteService / Yandex routing integration
- Python 3.11+

## What This Repo Contains / Что есть в репозитории

- Delivery calculator and distance logic
- Delivery point, distribution center and settlement APIs
- Auth and role-oriented API surface for producers, drivers, couriers, hubs and delivery points
- Health and diagnostics endpoints
- Import/seed scripts and Alembic migrations

## Prerequisites / Требования

- Python `3.11+`
- Poetry
- PostgreSQL with PostGIS
- Docker Desktop or a local PostgreSQL/PostGIS installation

## Environment Variables / Переменные окружения

The repository does not currently contain a committed `.env.example`, so create `.env` manually.

В репозитории сейчас нет закоммиченного `.env.example`, поэтому `.env` нужно создать вручную.

```env
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=bananay_calc

# Routing provider: openroute | yandex | fallback
ROUTING_PROVIDER=openroute
DISTANCE_FALLBACK_COEFFICIENT=1.4

# Optional provider keys
OPENROUTESERVICE_API_KEY=
YANDEX_API_KEY=
```

## Local Development / Локальный запуск

### 1. Install dependencies / Установить зависимости

```bash
poetry install
```

### 2. Start PostgreSQL with PostGIS / Запустить PostgreSQL с PostGIS

```bash
docker-compose up -d
```

### 3. Apply migrations / Применить миграции

```bash
poetry run alembic upgrade head
```

### 4. Import base data / Импортировать базовые данные

Run the scripts in this order:

Запускайте скрипты в таком порядке:

```bash
poetry run python scripts/seed_distribution_centers.py
poetry run python scripts/import_sectors.py
poetry run python scripts/import_delivery_points.py
```

### 5. Start the API / Запустить API

```bash
poetry run uvicorn app.main:app --reload
```

Default local URL: `http://localhost:8000`

## Main Endpoints / Основные endpoints

- `/docs` - Swagger UI
- `/redoc` - ReDoc
- `/docs/overview` - project overview page rendered from `PROJECT_OVERVIEW.md`
- `/health` - basic health check
- `/health/db-pool` - DB pool diagnostics
- `/api/*` - main application API

## Main Areas / Основные зоны

- `app/api/v1/` - versioned API routes
- `app/services/` - business logic and integrations
- `app/db/` - database setup and models
- `alembic/` - migrations
- `scripts/` - seed/import utilities
- `tests/` - automated tests

## Testing / Тесты

```bash
poetry run pytest
```

## Docker Notes / Docker и деплой

- `docker-compose.yml` can be used to start PostgreSQL/PostGIS locally.
- The API itself is started with `uvicorn` during development.
- For additional operational notes see [API_QUICKSTART.md](API_QUICKSTART.md).

## Related Documentation / Связанная документация

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- [API_QUICKSTART.md](API_QUICKSTART.md)
- [CALCULATOR_API.md](CALCULATOR_API.md)

## Notes / Примечания

- This backend is broader than just the delivery calculator: it also serves APIs for multiple Bananay role apps.
- Static assets from `public/` are mounted at `/public` when that directory exists.
- The FastAPI app exposes automatic API docs and a project overview page out of the box.
