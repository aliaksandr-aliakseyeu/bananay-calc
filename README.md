# 🍌 Bananay Delivery Calculator

Delivery cost calculator from distribution centers to delivery points.

📚 **[Full project documentation →](PROJECT_OVERVIEW.md)**

## Key Features

- 🗺 **Geospatial search** for delivery points (PostGIS)
- 🧮 **Cost calculator** with real road distances
- 📊 **Regional pricing management**
- 🔍 **Autocomplete and fuzzy search** for delivery points
- 🌐 **RESTful API** with automatic documentation

## Technologies

- **FastAPI** - web framework
- **SQLAlchemy 2.0** - ORM with async support
- **GeoAlchemy2** - extension for PostGIS integration
- **PostgreSQL + PostGIS** - database with geodata
- **Poetry** - dependency management
- **Alembic** - database migrations
- **OpenRouteService API** - real route calculation
- **Yandex Geocoder API** - address geocoding

## Installation

### 1. Install dependencies

```bash
poetry install
```

### 2. Start PostgreSQL with PostGIS

```bash
docker-compose up -d
```

### 3. Create `.env` file

Required variables:

```env
# Database (used by app/core/config.py)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=bananay_calc

# Routing provider: 'openroute' (default), 'yandex', or 'fallback'
ROUTING_PROVIDER=openroute
DISTANCE_FALLBACK_COEFFICIENT=1.4

# API keys (optional)
OPENROUTESERVICE_API_KEY=your_key_here
YANDEX_API_KEY=your_key_here
```

> Note: The repository currently does not include a `.env.example` file — create `.env` manually.

### 4. Apply migrations

```bash
poetry run alembic upgrade head
```

### 5. Import data

**Execution order is important!**

```bash
# 1. Distribution centers (with geocoding)
poetry run python scripts/seed_distribution_centers.py

# 2. Delivery sectors from GeoJSON
poetry run python scripts/import_sectors.py

# 3. Delivery points from Excel
poetry run python scripts/import_delivery_points.py
```

### 6. Start API server

```bash
poetry run uvicorn app.main:app --reload
```

API will be available at: **http://localhost:8000**

- 📖 **Swagger UI:** http://localhost:8000/docs
- 📘 **ReDoc:** http://localhost:8000/redoc
- 📚 **Project documentation:** http://localhost:8000/docs/overview
- ❤️ **Health:** http://localhost:8000/health
- 🗄️ **DB pool status:** http://localhost:8000/health/db-pool

## Project Structure

```
bananay_calc/
├── app/
│   ├── api/v1/        # API endpoints
│   │   └── endpoints/ # Routes by modules
│   ├── core/          # Configuration
│   ├── db/            # Database
│   │   └── models/    # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic (calculator, distances)
│   ├── utils/         # Utilities
│   └── main.py        # FastAPI application
├── scripts/           # Data import scripts
├── alembic/           # Migrations
├── tests/             # Tests
├── PROJECT_OVERVIEW.md  # 📚 Full documentation
└── docker-compose.yml # PostgreSQL + PostGIS
```

## 🚀 API Usage Examples

### Calculate delivery cost

```bash
curl -X POST "http://localhost:8000/api/v1/calculator/by-points" \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": 1,
    "supplier_location": {
      "latitude": 43.585472,
      "longitude": 39.723098
    },
    "product": {
      "length_cm": 30,
      "width_cm": 20,
      "height_cm": 10,
      "weight_kg": 2.5
    },
    "delivery_point_ids": [1, 2, 3]
  }'
```

### Search delivery points

```bash
curl -X POST "http://localhost:8000/api/v1/delivery-points/search" \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": 1,
    "search": "Красная",
    "limit": 10
  }'
```

### Get distribution centers for a region

```bash
curl "http://localhost:8000/api/v1/distribution-centers?region_id=1"
```

### Get settlements for a region

```bash
curl "http://localhost:8000/api/v1/settlements?region_id=1"
```

More details: **http://localhost:8000/docs**

## Development

Activate virtual environment:

```bash
poetry shell
```

Run tests:

```bash
poetry run pytest
```

## Docker quickstart

If you prefer running everything via Docker Compose, see: **[API_QUICKSTART.md](API_QUICKSTART.md)**.

## 📚 Documentation

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - full project documentation
- [API_QUICKSTART.md](API_QUICKSTART.md) - Docker-based quickstart and useful commands
- [CALCULATOR_API.md](CALCULATOR_API.md) - calculator endpoint details

---

_For complete project information see [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)_
