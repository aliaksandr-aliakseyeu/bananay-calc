# 🍌 Bananay Delivery Calculator - Project Overview

## 📋 Contents

- [Technologies](#technologies)
- [Database and Models](#database-and-models)
- [Data Import Scripts](#import-scripts)
- [API Endpoints](#api-endpoints)
- [Working with Geodata](#geodata)
- [Architecture and Project Structure](#architecture) _(in development)_

---

## 🛠 Technologies {#technologies}

### Backend Framework
- **[FastAPI](https://fastapi.tiangolo.com/)** `0.115.0` - modern, high-performance web framework for building APIs
  - Automatic OpenAPI (Swagger) documentation generation
  - Automatic request and response validation
  - Built-in async/await support
  - High performance (comparable to NodeJS and Go)

- **[Uvicorn](https://www.uvicorn.org/)** `0.32.0` - ASGI server for running FastAPI applications
  - HTTP/1.1 and WebSockets support
  - Asynchronous request handling

### Database
- **[PostgreSQL](https://www.postgresql.org/)** `16` - powerful relational database
- **[PostGIS](https://postgis.net/)** `3.4` - extension for working with geospatial data
  - Storage of coordinates (points, polygons)
  - Spatial indexes for fast search
  - Geometric operations (distance, point-in-polygon checks)
  - Uses `postgis/postgis:16-3.4` image

### ORM and Database Operations
- **[SQLAlchemy](https://www.sqlalchemy.org/)** `2.0.44` - ORM with async/await support
  - Async mode through AsyncSession
  - Declarative model definition style
  - Powerful query builder

- **[GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)** `0.18.0` - SQLAlchemy extension for PostGIS
  - Integration of PostGIS types into SQLAlchemy models
  - Geometric operations at ORM level

- **[Asyncpg](https://github.com/MagicStack/asyncpg)** `0.30.0` - asynchronous PostgreSQL driver
  - Fastest driver for Python
  - Native async/await support

- **[Psycopg2-binary](https://www.psycopg.org/)** `2.9.11` - synchronous PostgreSQL driver
  - Used by Alembic for migrations

### Database Migrations
- **[Alembic](https://alembic.sqlalchemy.org/)** `1.17.1` - database migration tool
  - Auto-generation of migrations based on model changes
  - Version history of database schema
  - Rollback capabilities

### Data Validation
- **[Pydantic](https://docs.pydantic.dev/)** `2.x` - data and settings validation
  - Automatic input/output data validation
  - JSON serialization/deserialization
  - Type hints and IDE autocomplete

- **[Pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** `2.12.0` - configuration management
  - Loading settings from .env files
  - Environment variable validation

### Geodata and External API Integration
- **[Shapely](https://shapely.readthedocs.io/)** `2.1.2` - library for working with geometric objects
  - Coordinate transformations
  - Geometric operations

- **[HTTPX](https://www.python-httpx.org/)** `0.27.0` - async HTTP client
  - Used for requests to external routing APIs
  - Timeout and retry support

- **[OpenRouteService API](https://openrouteservice.org/)** - real route calculation between points
  - Free tier: 2000 requests/day
  - Used in calculator to compute distance from supplier to distribution center
  - Alternative to Google Maps Directions API

- **[Yandex Geocoder API](https://yandex.ru/dev/geocode/)** - geocoding (address → coordinates)
  - Free tier: up to 1000 requests/day
  - Used in `seed_distribution_centers.py` script to get distribution center coordinates from addresses
  - Accurate coordinates for addresses in Russia

- **[Yandex Router API](https://yandex.ru/dev/routing/)** - route calculation (optional)
  - Paid service
  - Alternative to OpenRouteService for distance calculation
  - More accurate data for roads in Russia

### Data Processing
- **[OpenPyXL](https://openpyxl.readthedocs.io/)** `3.1.5` - reading/writing Excel files
  - Import delivery points from Excel
  - Parsing addresses and coordinates

- **[tqdm](https://github.com/tqdm/tqdm)** `4.67.1` - progress bar for import scripts
  - Visualization of data loading progress

### Development Tools
- **[Poetry](https://python-poetry.org/)** `2.0+` - dependency and virtual environment management
  - Project dependency isolation
  - Lock file for environment reproducibility

- **[Python-dotenv](https://github.com/theskumar/python-dotenv)** `1.2.1` - .env file loading

### Testing
- **[pytest](https://docs.pytest.org/)** `8.0.0` - testing framework
- **[pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)** `0.24.0` - async test support
- **[pytest-cov](https://pytest-cov.readthedocs.io/)** `6.0.0` - code coverage

### Containerization
- **[Docker](https://www.docker.com/)** - application containerization
- **[Docker Compose](https://docs.docker.com/compose/)** - container orchestration
  - PostgreSQL with PostGIS
  - API application
  - Isolated network

### Additional Tools
- **[geojson.io](https://geojson.io/)** - web tool for creating and editing GeoJSON
  - Used to create delivery sector polygons
  - Visual drawing of areas on map
  - Export to GeoJSON format
  - **Sectors file:** [`сектора.json`](./сектора.json) - contains all delivery sector polygons for Krasnodar Region

### Requirements
- **Python** `>=3.11, <4.0`
- **PostgreSQL** `16+` with **PostGIS** `3.4+` extension

---

## 🗂 Technology Versions

| Technology | Version | Purpose |
|-----------|--------|------------|
| Python | 3.11+ | Programming language |
| FastAPI | 0.115.0 | Web framework |
| SQLAlchemy | 2.0.44 | ORM |
| GeoAlchemy2 | 0.18.0 | PostGIS integration |
| PostgreSQL | 16 | Database |
| PostGIS | 3.4 | Geospatial extension |
| Alembic | 1.17.1 | Database migrations |
| Pydantic | 2.x | Data validation |
| Uvicorn | 0.32.0 | ASGI server |
| Docker | latest | Containerization |

---

## 🗄 Database and Models {#database-and-models}

### Database Structure Overview

The project uses **PostgreSQL 16** with **PostGIS 3.4** extension for working with geospatial data. The database is designed to store information about regions, delivery points, sectors, distribution centers, and pricing for delivery cost calculation.

### Database Schema

#### 🌍 Geographic Hierarchy

```
countries (Countries)
    ↓
regions (Regions/federal subjects)
    ↓
settlements (Settlements)
    ↓
districts (Settlement districts) [optional]
    ↓
delivery_points (Delivery points)
```

#### 📊 Main Tables

##### 1️⃣ **countries** - Countries
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| name | VARCHAR(100) | Country name (unique) |
| code | VARCHAR(2) | ISO country code (unique) |

**Relationships:**
- `1 → Many` regions

---

##### 2️⃣ **regions** - Regions (federal subjects)
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| country_id | INTEGER | FK → countries.id |
| name | VARCHAR(200) | Region name |
| type | ENUM | Region type (krai, oblast, republic, etc.) |

**Relationships:**
- `Many → 1` countries
- `1 → Many` settlements
- `1 → Many` sectors
- `1 → Many` distribution_centers
- `1 → 1` region_pricing (optional)

**Enum RegionType:**
- край (krai)
- область (oblast)
- республика (republic)
- автономная область (autonomous oblast)
- автономный округ (autonomous okrug)
- город федерального значения (federal city)

---

##### 3️⃣ **region_pricing** - Regional pricing and calculation parameters
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| region_id | INTEGER | FK → regions.id (UNIQUE) |
| **Driver rates** |
| driver_hourly_rate | NUMERIC(10,2) | Driver hourly cost, RUB |
| planned_work_hours | NUMERIC(10,2) | Planned work hours |
| **Transport parameters** |
| fuel_price_per_liter | NUMERIC(10,2) | Fuel cost, RUB/L |
| fuel_consumption_per_100km | NUMERIC(10,2) | Fuel consumption, L/100km |
| depreciation_coefficient | NUMERIC(10,4) | Vehicle depreciation coefficient |
| **Distribution center rates** |
| warehouse_processing_per_kg | NUMERIC(10,2) | Processing cost per kg at DC, RUB |
| service_fee_per_kg | NUMERIC(10,2) | Service fee per kg (company revenue), RUB |
| delivery_point_cost | NUMERIC(10,2) | Cost per delivery point, RUB |
| standard_trip_weight | NUMERIC(10,2) | Standard trip cargo weight, kg |
| **Standard box** |
| standard_box_length | INTEGER | Length, cm |
| standard_box_width | INTEGER | Width, cm |
| standard_box_height | INTEGER | Height, cm |
| standard_box_max_weight | NUMERIC(10,2) | Maximum weight, kg |
| **Discount parameters** |
| min_points_for_discount | INTEGER | Minimum points before discount applies |
| discount_step_points | INTEGER | Delivery point increment step |
| initial_discount_percent | NUMERIC(5,2) | Initial discount, % |
| discount_step_percent | NUMERIC(5,2) | Discount increment step, % |

**Relationships:**
- `1 → 1` regions

---

##### 4️⃣ **settlements** - Settlements
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| region_id | INTEGER | FK → regions.id |
| name | VARCHAR(200) | Settlement name |
| type | ENUM | Type (city, village, etc.) |
| postal_code | INTEGER | Postal code (optional) |
| location | POINT | PostGIS - center coordinates (optional) |

**Relationships:**
- `Many → 1` regions
- `1 → Many` districts
- `1 → Many` delivery_points

**Enum SettlementType:**
- город (city)
- пгт (urban-type settlement)
- село (village)
- деревня (hamlet)
- поселок (settlement)
- станица (stanitsa)
- хутор (khutor)
- аул (aul)

---

##### 5️⃣ **districts** - Settlement districts
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| settlement_id | INTEGER | FK → settlements.id |
| name | VARCHAR(200) | District name |
| boundary | POLYGON | PostGIS - district boundary (optional) |

**Relationships:**
- `Many → 1` settlements
- `1 → Many` delivery_points (optional)

---

##### 6️⃣ **distribution_centers** - Distribution centers (DC)
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| region_id | INTEGER | FK → regions.id |
| name | VARCHAR(200) | DC name |
| location | POINT | PostGIS - DC coordinates (with spatial index) |
| address | TEXT | DC address (optional) |
| is_active | BOOLEAN | Whether DC is active (default true) |

**Relationships:**
- `Many → 1` regions

**Usage:**
- Calculator finds nearest active DC to supplier
- Distance to DC is used in delivery cost calculation

---

##### 7️⃣ **sectors** - Delivery sectors
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| region_id | INTEGER | FK → regions.id |
| name | VARCHAR(200) | Sector name (optional) |
| description | TEXT | Sector description (optional) |
| boundary | POLYGON | PostGIS - sector boundary (with spatial index) |

**Relationships:**
- `Many → 1` regions

**Usage:**
- Sectors are used for grouping delivery points
- Calculator checks if points fall within sectors using `ST_Within`
- Number of sectors affects final delivery cost

**Sector creation:**
- Sector polygons created manually via [geojson.io](https://geojson.io/)
- Data stored in [`сектора.json`](./сектора.json) file
- Import via `import_sectors.py` script

---

##### 8️⃣ **delivery_points** - Delivery points
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| name | VARCHAR(255) | Delivery point name |
| name_normalized | TEXT | Normalized name (for search) |
| type | VARCHAR(100) | Point type (store, pickup point, etc.) |
| title | TEXT | Title / additional description |
| settlement_id | INTEGER | FK → settlements.id |
| district_id | INTEGER | FK → districts.id (optional) |
| address | TEXT | Address |
| address_comment | TEXT | Address comment |
| landmark | VARCHAR(255) | Landmark |
| location | POINT | PostGIS - coordinates (with spatial index) |
| category_id | INTEGER | FK → categories.id (optional) |
| subcategory_id | INTEGER | FK → subcategories.id (optional) |
| **Contacts (MVP - in main table)** |
| phone | TEXT | Phone number(s) - may contain multiple comma-separated |
| mobile | TEXT | Mobile number(s) - may contain multiple comma-separated |
| email | TEXT | Email(s) - may contain multiple comma-separated |
| **Schedule (MVP - as text)** |
| schedule | TEXT | Working hours in text format |
| **Service fields** |
| is_active | BOOLEAN | Whether point is active (default true) |
| created_at | TIMESTAMP | Creation date (automatic) |
| updated_at | TIMESTAMP | Update date (automatic) |

**Relationships:**
- `Many → 1` settlements
- `Many → 1` districts (optional)
- `Many → 1` categories (optional)
- `Many → 1` subcategories (optional)
- `Many → Many` tags (via delivery_point_tags table)

**Indexes:**
- name (for search)
- name_normalized (for normalized search)
- location (PostGIS spatial index)
- settlement_id, district_id

**Search capabilities:**
- Autocomplete by name (prefix search)
- Fuzzy search with typos via `pg_trgm` (similarity)
- Filter by sectors via `ST_Within`
- Filter by bbox (bounding box)
- Filter by tags

---

##### 9️⃣ **categories** - Establishment categories
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| name | VARCHAR(100) | Category name (unique) |
| slug | VARCHAR(100) | URL-friendly name (unique, auto-generated) |

**Relationships:**
- `1 → Many` subcategories
- `1 → Many` delivery_points

**Examples:** Food products, Clothing and shoes, Electronics, etc.

---

##### 🔟 **subcategories** - Subcategories
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| category_id | INTEGER | FK → categories.id |
| name | VARCHAR(100) | Subcategory name |
| slug | VARCHAR(100) | URL-friendly name (auto-generated) |

**Relationships:**
- `Many → 1` categories
- `1 → Many` delivery_points

---

##### 1️⃣1️⃣ **tags** - Tags (categories)
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| name | VARCHAR(100) | Tag name (unique) |
| slug | VARCHAR(100) | URL-friendly name (unique, auto-generated) |

**Relationships:**
- `Many → Many` delivery_points (via delivery_point_tags)

**Usage:**
- Filter delivery points by tags
- One tag can belong to many delivery points
- One delivery point can have multiple tags

---

##### 1️⃣2️⃣ **delivery_point_tags** - Delivery point and tag relationship
| Field | Type | Description |
|------|-----|----------|
| delivery_point_id | INTEGER | FK → delivery_points.id, PRIMARY KEY |
| tag_id | INTEGER | FK → tags.id, PRIMARY KEY |

**Relationship type:** Many-to-Many between delivery_points and tags

---

##### 1️⃣3️⃣ **product_categories** - Product categories _(not yet used)_
| Field | Type | Description |
|------|-----|----------|
| id | INTEGER | PRIMARY KEY |
| name | VARCHAR(100) | Category name (unique) |
| slug | VARCHAR(100) | URL-friendly name (unique, auto-generated) |
| description | TEXT | Category description |
| cost_multiplier | NUMERIC(5,2) | Cost multiplier (not yet used) |

**Status:** Table created for future functionality, not yet used in calculator.

---

### 🔍 Geodata Features

#### PostGIS data types
- **POINT** - for coordinates (delivery points, DCs, settlements)
- **POLYGON** - for boundaries (sectors, districts)
- **SRID 4326** - WGS84 coordinate system (GPS standard)

#### Spatial indexes
All geometric fields (`location`, `boundary`) have spatial indexes for fast query execution:
```sql
ST_Within(point, polygon)  -- Check if point is within polygon
ST_Distance(point1, point2) -- Calculate distance
```

#### Code usage example
```python
# Check if delivery point falls within sector
query = select(DeliveryPoint, Sector).join(
    Sector,
    func.ST_Within(DeliveryPoint.location, Sector.boundary)
)
```

---

### ✅ Current State (MVP)

Implemented functionality is sufficient for MVP:

✅ **Complete geographic hierarchy** - from country to delivery point  
✅ **Pricing and calculation parameters** - flexible configuration per region  
✅ **Delivery sectors** - point grouping for calculations  
✅ **Distribution centers** - for calculating distance from supplier  
✅ **Powerful delivery point search** - autocomplete, fuzzy search, geo-filters  
✅ **Point categorization** - categories, subcategories, tags  
✅ **Geospatial queries** - via PostGIS  
✅ **Database migrations** - via Alembic for schema versioning  

---

### 🚀 Planned Improvements (Post-MVP)

#### 1️⃣ **Delivery point contacts**
- Move to separate `delivery_point_contacts` table
- Support for different contact types (phone, email, messengers)
- Mark primary contact

#### 2️⃣ **Working hours**
- Structured storage in `delivery_point_schedules` table
- "Open now" filter and search by working hours
- Support for different schedules by day of week

#### 3️⃣ **Product categories**
- Use `cost_multiplier` from `product_categories` table
- Different rates for fragile/bulky/perishable goods
- Seasonal coefficients

#### 4️⃣ **Pricing change history**
- `region_pricing_history` table for audit trail
- Ability to rollback to previous values

#### 5️⃣ **Calculation caching**
- `calculation_cache` table to store results
- Save external API limits (OpenRouteService)
- Speed up repeated queries

#### 6️⃣ **Analytics**
- Calculation logs, API usage statistics
- Popular route analysis for optimization

---

### 📌 Database Conclusion

**Current database schema is fully functional for MVP:**
- ✅ All necessary data for delivery cost calculation
- ✅ Efficient geodata operations via PostGIS
- ✅ Flexible pricing system
- ✅ Powerful delivery point search and filtering

**Planned improvements don't block launch:**
- 📊 Will improve user experience
- 🚀 Will add new filtering capabilities
- 📈 Will enable analytics collection
- 💰 Will optimize external API costs

---

## 🔧 Data Import Scripts {#import-scripts}

The `scripts/` directory contains three scripts for initial data loading into the database.

### 1️⃣ **import_delivery_points.py** - Import delivery points from Excel

**Purpose:** Load delivery points from `sochi_address.xlsx` file into the database.

**Features:**
- Parse Excel file with delivery points
- Automatic hierarchy creation: settlements → districts → delivery points
- Name normalization for search (lowercase, ё→е replacement, special character removal)
- Tag creation and assignment (categories)
- Batch operations (100 records per batch) for performance
- Coordinate and data validation
- Detailed import statistics with progress bar

**Usage:**
```bash
poetry run python scripts/import_delivery_points.py
poetry run python scripts/import_delivery_points.py --debug  # Debug mode
```

**Result:** ~5000 delivery points for Krasnodar Region (Sochi and surroundings)

---

### 2️⃣ **import_sectors.py** - Import delivery sectors from GeoJSON

**Purpose:** Load delivery sector polygons from `сектора.json` file.

**Features:**
- Read GeoJSON FeatureCollection
- Convert Shapely geometry to PostGIS POLYGON
- Link sectors to region (Krasnodar Region)
- Validate polygon geometry
- Create spatial indexes

**Usage:**
```bash
poetry run python scripts/import_sectors.py
```

**Data source:** Polygons created manually via [geojson.io](https://geojson.io/), saved in [`сектора.json`](./сектора.json)

**Result:** ~45 delivery sectors for cost calculation

---

### 3️⃣ **seed_distribution_centers.py** - Add distribution centers

**Purpose:** Create distribution centers (DCs) with automatic coordinate retrieval from addresses.

**Features:**
- Address geocoding via **Yandex Geocoder API**
- Get precise DC coordinates
- Link to region
- Check for duplicates before adding
- Ability to skip existing records

**Requirements:**
- Yandex API key in `.env`: `YANDEX_API_KEY`
- Free tier: up to 1000 requests/day

**Usage:**
```bash
poetry run python scripts/seed_distribution_centers.py
```

**Data:** 8 DCs for Krasnodar Region (Adler, Khosta, Central, Lazarevsky districts)

---

### 📝 Script Execution Order

```bash
# 1. Apply migrations
poetry run alembic upgrade head

# 2. Add distribution centers
poetry run python scripts/seed_distribution_centers.py

# 3. Import sectors
poetry run python scripts/import_sectors.py

# 4. Import delivery points
poetry run python scripts/import_delivery_points.py
```

**Note:** Scripts are idempotent - can be run multiple times, no duplicates will be created.

---

## 🌐 API Endpoints {#api-endpoints}

API is available at `/api/v1/` and automatically documented via **OpenAPI (Swagger)**.

**Documentation:** 
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- 📚 This documentation in HTML: `/docs/overview` (opens as a beautiful page in browser)

### 📍 API Structure

```
/api/v1/
  ├── /countries          # Countries
  ├── /regions            # Regions
  ├── /sectors            # Delivery sectors
  ├── /delivery-points    # Delivery points
  ├── /tags               # Tags (categories)
  └── /calculator         # Delivery cost calculator
```

---

### 1️⃣ Countries

#### `GET /api/v1/countries`
Get list of all countries.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Россия",
    "code": "RU"
  }
]
```

#### `GET /api/v1/countries/{country_id}`
Get country by ID.

**Response:** `200 OK` or `404 Not Found`

---

### 2️⃣ Regions

#### `GET /api/v1/regions`
Get list of all regions.

**Query Parameters:**
- `country_id` (optional) - filter by country

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Краснодарский край",
    "type": "край",
    "country": {
      "id": 1,
      "name": "Россия",
      "code": "RU"
    }
  }
]
```

#### `GET /api/v1/regions/{region_id}`
Get detailed region information.

**Response:** Full information including DCs, pricing, and statistics

#### `GET /api/v1/regions/{region_id}/pricing`
Get pricing and calculation parameters for region.

**Response:** All parameters from `region_pricing` table

#### `PATCH /api/v1/regions/{region_id}/pricing`
Update pricing (partial update).

**Body Example:**
```json
{
  "fuel_price_per_liter": "75.00",
  "driver_hourly_rate": "600.00"
}
```

---

### 3️⃣ Sectors - Delivery sectors

#### `GET /api/v1/sectors?region_id={id}`
Get all region sectors with boundaries in GeoJSON format.

**Query Parameters:**
- `region_id` (required) - Region ID

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "region_id": 1,
    "name": "Адлерский сектор 1",
    "description": "Сектор доставки в Адлерском районе",
    "boundary": {
      "type": "Polygon",
      "coordinates": [[[39.723, 43.585], [39.730, 43.585], ...]]
    }
  }
]
```

---

### 4️⃣ Delivery Points

#### `POST /api/v1/delivery-points/search`
Powerful delivery point search with filters.

**Body:**
```json
{
  "region_id": 1,
  "only_in_sectors": false,
  "search": "магазин",
  "bbox": {
    "min_lng": 39.7,
    "min_lat": 43.5,
    "max_lng": 39.8,
    "max_lat": 43.6
  },
  "tag_ids": [1, 2],
  "limit": 10
}
```

**Search capabilities:**
- ✅ **Autocomplete** by name (min 3 characters)
- ✅ **Fuzzy search** with typos (from 5 characters, via pg_trgm)
- ✅ **Geo-filters**: bbox, only in sectors
- ✅ **Filter by tags** (OR logic)
- ✅ Text normalization (lowercase, ё→е, special character removal)

**Response:** Array of delivery points with coordinates in GeoJSON

---

### 5️⃣ Tags

#### `GET /api/v1/tags`
Get all tags for filtering delivery points.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Продукты питания",
    "slug": "produkty-pitaniya"
  }
]
```

---

### 6️⃣ Calculator - Delivery Cost Calculator 🧮

Two operation modes: calculation by specific points or by approximate quantity.

---

#### `POST /api/v1/calculator/by-points`
**Calculate cost for specific delivery points**

Calculator automatically determines number of points and sectors from provided IDs.

**Request Body:**
```json
{
  "region_id": 1,
  "supplier_location": {
    "latitude": 43.585472,
    "longitude": 39.723098
  },
  "product": {
    "length_cm": 20,
    "width_cm": 10,
    "height_cm": 10,
    "weight_kg": 1.0,
    "items_per_box": 15
  },
  "delivery_point_ids": [1, 2, 3, ...]
}
```

**Response:**
```json
{
  "items_in_standard_box": 18,
  "cost_per_item": 38.29,
  "cost_per_supplier_box": 574.35,
  "delivery_points_used": 150,
  "delivery_points_ignored": 5,
  "sectors_count": 3,
  "distance_to_dc_km": 15.50,
  "nearest_dc_name": "РЦ Сочи"
}
```

**Ignored points:**
- Points outside region sectors (not within polygons)
- Inactive points (`is_active = false`)

---

#### `POST /api/v1/calculator/estimate`
**Calculate approximate cost by point quantity**

For preliminary estimation when specific points haven't been selected yet.

**Request Body:**
```json
{
  "region_id": 1,
  "supplier_location": {
    "latitude": 43.585472,
    "longitude": 39.723098
  },
  "product": {
    "length_cm": 20,
    "width_cm": 10,
    "height_cm": 10,
    "weight_kg": 1.0,
    "items_per_box": 15
  },
  "delivery": {
    "num_points": 300,
    "num_sectors": 10
  }
}
```

**`num_sectors` parameter:**
- If not specified → uses maximum number of sectors in region
- If specified → uses for calculation

**Response:**
```json
{
  "items_in_standard_box": 18,
  "cost_per_item": 38.29,
  "cost_per_supplier_box": 574.35,
  "distance_to_dc_km": 15.50,
  "nearest_dc_name": "РЦ Сочи"
}
```

---

### 📐 Calculator Business Logic

#### Stage 1: Find Nearest DC

1. **Select candidates:**
   - Get all active DCs (`is_active = true`)
   - Calculate straight-line distance from supplier to each DC using **Haversine** formula

2. **Select top-3 nearest:**
   - DCs are sorted by straight-line distance
   - Take 3 nearest candidates

3. **Calculate real route:**
   - For top-3, request real road distance via **OpenRouteService API**
   - If API is unavailable → use coefficient: `straight_line_distance × 1.4`
   - Select DC with minimum road distance

**Result:** Distance to DC (`distance_to_dc_km`) for cost calculation

---

#### Stage 2: Determine Points and Sectors

**For `/by-points`:**
- Via PostGIS query `ST_Within` check if each point falls within any sector of the region
- Count unique points and sectors
- Points outside sectors are ignored

**For `/estimate`:**
- Use provided `num_points` and `num_sectors`
- If `num_sectors` not specified → take `COUNT(*)` from `sectors` table

---

#### Stage 3: Calculate Trip Cost

All calculations are based on pricing from `region_pricing` table.

##### 3.1 Driver cost
```
driver_cost = planned_work_hours × driver_hourly_rate
```

##### 3.2 Company revenue
```
company_revenue = service_fee_per_kg × standard_trip_weight
```

##### 3.3 Fuel consumption
```
fuel_liters = (fuel_consumption_per_100km / 100) × (distance_to_dc_km × 2)
fuel_cost = fuel_liters × fuel_price_per_liter
```
_× 2 because round trip_

##### 3.4 Vehicle depreciation
```
transport_cost = fuel_cost × depreciation_coefficient
```

##### 3.5 Warehouse processing at DC
```
warehouse_cost = warehouse_processing_per_kg × standard_trip_weight
```

##### 3.6 Delivery cost (with discounts)

**If points less than minimum:**
```
delivery_cost = num_sectors × delivery_point_cost × min_points_for_discount
```

**If enough points for discount:**
```
discount_steps = (num_points - min_points_for_discount) / discount_step_points
discount_percent = initial_discount_percent + (discount_steps × discount_step_percent)

base_cost = num_sectors × delivery_point_cost × min_points_for_discount
delivery_cost = base_cost × (1 - discount_percent / 100)
```

**Discount system example:**
- Minimum for discount: 100 points
- Increment step: 50 points
- Initial discount: 5%
- Discount step: 5%

| Points | Discount |
|-------|--------|
| < 100 | 0% |
| 100-149 | 5% |
| 150-199 | 10% |
| 200-249 | 15% |
| 250+ | 20% |

##### 3.7 Total trip cost
```
total_trip_cost = driver_cost + company_revenue + transport_cost + 
                  warehouse_cost + delivery_cost
```

##### 3.8 Standard box cost
```
num_standard_boxes = standard_trip_weight / standard_box_max_weight
standard_box_cost = total_trip_cost / num_standard_boxes
```

---

#### Stage 4: Calculate Product Capacity

Determine how many supplier products fit in standard box.

##### 4.1 By dimensions
```
n_length = standard_box_length ÷ product.length_cm
n_width = standard_box_width ÷ product.width_cm  
n_height = standard_box_height ÷ product.height_cm

items_by_dimensions = n_length × n_width × n_height
```
_Integer division_

##### 4.2 By weight
```
items_by_weight = standard_box_max_weight ÷ product.weight_kg
```

##### 4.3 Final quantity
```
items_in_standard_box = MIN(items_by_dimensions, items_by_weight)
```
_Take minimum of two constraints_

**Example:**
- Standard box: 60×40×40 cm, max 30 kg
- Supplier product: 20×10×10 cm, 1 kg
- By dimensions: (60÷20) × (40÷10) × (40÷10) = 3 × 4 × 4 = **48 pcs**
- By weight: 30 ÷ 1 = **30 pcs**
- **Total: 30 pcs** (weight constraint)

---

#### Stage 5: Final Cost

##### 5.1 Cost per item
```
cost_per_item = standard_box_cost / items_in_standard_box
```

##### 5.2 Cost per supplier box
```
cost_per_supplier_box = cost_per_item × items_per_box
```

Results are rounded to 2 decimal places.

---

### 🔑 Key Calculator Features

✅ **Real road consideration** - via OpenRouteService API or coefficient  
✅ **Geospatial queries** - check points in sectors via PostGIS  
✅ **Discount system** - progressive scale based on number of points  
✅ **Dual constraint** - by weight AND dimensions  
✅ **Data validation** - via Pydantic schemas  
✅ **Error handling** - clear error messages  

---

## 🗺 Working with Geodata {#geodata}

The project actively uses geospatial data and PostGIS functions for working with coordinates, distances, and polygons.

### 📍 Geodata Types in Project

#### 1. **POINT** - Points (coordinates)
Used to store locations:
- Delivery points (`delivery_points.location`)
- Distribution centers (`distribution_centers.location`)
- Settlement centers (`settlements.location`)

**Format:** Longitude, Latitude

**SQL example:**
```sql
-- Create point
ST_SetSRID(ST_MakePoint(39.723098, 43.585472), 4326)
```

**Python example (Shapely):**
```python
from shapely.geometry import Point
point = Point(39.723098, 43.585472)  # lon, lat
```

**GeoJSON format:**
```json
{
  "type": "Point",
  "coordinates": [39.723098, 43.585472]
}
```

---

#### 2. **POLYGON** - Polygons (areas)
Used to store boundaries:
- Delivery sectors (`sectors.boundary`)
- Settlement districts (`districts.boundary`)

**SQL example:**
```sql
-- Create polygon
ST_SetSRID(
  ST_GeomFromGeoJSON('{"type":"Polygon","coordinates":[[[39.7,43.5],[39.8,43.5],[39.8,43.6],[39.7,43.6],[39.7,43.5]]]}'),
  4326
)
```

**GeoJSON format:**
```json
{
  "type": "Polygon",
  "coordinates": [
    [
      [39.7, 43.5],
      [39.8, 43.5],
      [39.8, 43.6],
      [39.7, 43.6],
      [39.7, 43.5]
    ]
  ]
}
```

---

### 🌐 Coordinate System: SRID 4326 (WGS84)

**SRID 4326** = **WGS84** coordinate system - standard for GPS and web maps.

**Characteristics:**
- Used by GPS, Google Maps, OpenStreetMap
- Coordinates in degrees (latitude: -90 to +90, longitude: -180 to +180)
- Distances measured in degrees, not meters

**Why 4326:**
- ✅ Universal - works worldwide
- ✅ Compatible with most mapping services
- ✅ Easy to obtain data from external sources

---

### 🔍 Main PostGIS Geospatial Functions

#### 1. **ST_Within** - Check if point is within polygon

Used to check if delivery points fall within sectors.

**SQL example:**
```sql
SELECT dp.id, dp.name, s.name as sector_name
FROM delivery_points dp
JOIN sectors s ON ST_Within(dp.location, s.boundary)
WHERE s.region_id = 1;
```

**Python (SQLAlchemy):**
```python
from sqlalchemy import func, select

query = select(DeliveryPoint, Sector).join(
    Sector,
    func.ST_Within(DeliveryPoint.location, Sector.boundary)
).where(Sector.region_id == 1)
```

**Usage in project:**
- Calculator checks which points fall within region sectors
- Search for delivery points only inside sectors

---

#### 2. **ST_Distance** - Distance between points

Calculates distance between two points in degrees.

**SQL example:**
```sql
SELECT 
    dc.name,
    ST_Distance(
        ST_SetSRID(ST_MakePoint(39.723098, 43.585472), 4326),
        dc.location
    ) as distance_degrees
FROM distribution_centers dc
ORDER BY distance_degrees
LIMIT 1;
```

**⚠️ Important:** `ST_Distance` in SRID 4326 returns distance in **degrees**, not kilometers!

**For distance in meters/kilometers:**
```sql
-- Use ST_Distance with geography
SELECT 
    ST_Distance(
        geography(ST_SetSRID(ST_MakePoint(39.723098, 43.585472), 4326)),
        geography(dc.location)
    ) / 1000 as distance_km
FROM distribution_centers dc;
```

**Project uses Haversine formula** (Python) to calculate straight-line distance in km.

---

#### 3. **ST_MakeEnvelope** - Create bounding box

Used to filter points by bounding rectangle.

**SQL example:**
```sql
SELECT dp.*
FROM delivery_points dp
WHERE ST_Within(
    dp.location,
    ST_MakeEnvelope(39.7, 43.5, 39.8, 43.6, 4326)
);
-- min_lng, min_lat, max_lng, max_lat, SRID
```

**Python (SQLAlchemy):**
```python
from geoalchemy2.functions import ST_MakeEnvelope, ST_Within

bbox_polygon = ST_MakeEnvelope(
    filters.bbox.min_lng,
    filters.bbox.min_lat,
    filters.bbox.max_lng,
    filters.bbox.max_lat,
    4326
)
query = query.where(ST_Within(DeliveryPoint.location, bbox_polygon))
```

**Usage:** Search for delivery points in visible map area.

---

#### 4. **ST_AsGeoJSON** - Convert to GeoJSON

Converts PostGIS geometry to GeoJSON for sending to client.

**SQL example:**
```sql
SELECT 
    id,
    name,
    ST_AsGeoJSON(location) as location_geojson
FROM delivery_points;
```

**Python (SQLAlchemy):**
```python
from geoalchemy2.functions import ST_AsGeoJSON

query = select(
    DeliveryPoint.id,
    DeliveryPoint.name,
    ST_AsGeoJSON(DeliveryPoint.location).label('location_geojson')
)

# In code
import json
location_data = json.loads(row.location_geojson)
# {'type': 'Point', 'coordinates': [39.723098, 43.585472]}
```

---

### ⚡ Spatial Indexes

All geometric fields have **GIST indexes** for fast queries.

**Auto-creation via GeoAlchemy2:**
```python
location: Mapped[str] = mapped_column(
    Geometry(geometry_type='POINT', srid=4326, spatial_index=True),
    nullable=False
)
```

**SQL equivalent:**
```sql
CREATE INDEX idx_delivery_points_location 
ON delivery_points 
USING GIST (location);
```

**Benefits:**
- ✅ Fast point search within radius
- ✅ Efficient point-in-polygon checks
- ✅ Fast sorting by distance

**Complexity without index:** O(n) - check all records  
**Complexity with index:** O(log n) - binary tree search

---

### 📏 Distance Calculation in Project

#### Method 1: **Haversine Formula** (straight-line distance)

Calculates "as-the-crow-flies" distance between two points on sphere (Earth).

**Python implementation:**
```python
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """Distance in kilometers."""
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    earth_radius = 6371.0  # km
    return earth_radius * c
```

**Usage:**
- Fast preliminary selection of nearest DCs
- Fallback if routing API is unavailable

---

#### Method 2: **OpenRouteService API** (road distance)

Calculates real distance along roads.

**Features:**
- ✅ Considers real roads, turns, restrictions
- ✅ More accurate for delivery cost calculation
- ❌ Requires internet and API key
- ❌ Request limits (2000/day free)

**Strategy in project:**
1. Haversine to select top-3 nearest DCs
2. OpenRouteService API only for top-3
3. If API unavailable → coefficient 1.4 to straight-line distance

---

### 🛠 Working with Geodata in Code

#### Create point from coordinates

**Python (GeoAlchemy2):**
```python
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

# Create point
point = Point(39.723098, 43.585472)  # lon, lat

# Convert for SQLAlchemy
from_shape(point, srid=4326)
```

#### Extract coordinates from database

**Python:**
```python
from geoalchemy2.shape import to_shape

# From database
delivery_point = await db.get(DeliveryPoint, 1)

# Convert to Shapely
shape = to_shape(delivery_point.location)

latitude = shape.y
longitude = shape.x
```

#### Create polygon from GeoJSON

**Python:**
```python
from shapely.geometry import shape as shapely_shape
from geoalchemy2.shape import from_shape
import json

# GeoJSON data
geojson_data = {
    "type": "Polygon",
    "coordinates": [[[39.7, 43.5], [39.8, 43.5], [39.8, 43.6], [39.7, 43.5]]]
}

# Convert
polygon = shapely_shape(geojson_data)
geoalchemy_polygon = from_shape(polygon, srid=4326)

# Save to database
sector = Sector(
    region_id=1,
    name="Sector 1",
    boundary=geoalchemy_polygon
)
```

---

### 📊 Usage Examples in Project

#### 1. Find delivery points in sectors

```python
from sqlalchemy import select, func, and_

# Points inside region sectors
query = select(DeliveryPoint, Sector).join(
    Sector,
    func.ST_Within(DeliveryPoint.location, Sector.boundary)
).where(
    and_(
        Sector.region_id == region_id,
        DeliveryPoint.is_active == True
    )
)

result = await db.execute(query)
```

#### 2. Find points in bounding box

```python
from geoalchemy2.functions import ST_MakeEnvelope, ST_Within

bbox_polygon = ST_MakeEnvelope(
    min_lng, min_lat, max_lng, max_lat, 4326
)

query = select(DeliveryPoint).where(
    ST_Within(DeliveryPoint.location, bbox_polygon)
)
```

#### 3. Find nearest DC

```python
# 1. Fast selection via Haversine
dc_distances = []
for dc in distribution_centers:
    dc_lat, dc_lon = extract_coordinates(dc.location)
    distance = haversine_distance(supplier_lat, supplier_lon, dc_lat, dc_lon)
    dc_distances.append((dc, distance))

# Top-3 nearest
top_3 = sorted(dc_distances, key=lambda x: x[1])[:3]

# 2. Accurate distance via OpenRouteService API
for dc, _ in top_3:
    road_distance = await get_route_distance(supplier, dc)
```

---

### 🎯 Benefits of Using PostGIS

✅ **Performance** - spatial indexes speed up queries by hundreds of times  
✅ **Accuracy** - professional geospatial algorithms  
✅ **Standardization** - compatibility with GeoJSON, WKT, WKB  
✅ **Extensibility** - hundreds of functions for working with geometry  
✅ **Integration** - works inside PostgreSQL, no external services needed  

---

### 🔗 Useful Links

- [PostGIS Documentation](https://postgis.net/documentation/)
- [GeoAlchemy2 Documentation](https://geoalchemy-2.readthedocs.io/)
- [Shapely Documentation](https://shapely.readthedocs.io/)
- [GeoJSON Specification](https://geojson.org/)
- [geojson.io](https://geojson.io/) - visual GeoJSON editor

---

_Documentation will be updated as the project develops._

