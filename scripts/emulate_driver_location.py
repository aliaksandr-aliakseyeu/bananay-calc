"""
Emulate driver movement along a route and POST locations to the API (variant A: as driver).

Где прописать JWT водителя:
  В файле .env в КОРНЕ проекта bananay_calc (рядом с pyproject.toml):
    DRIVER_TOKEN=сюда_вставить_jwt_водителя
    API_BASE_URL=http://localhost:8000
    OPENROUTESERVICE_API_KEY=ключ_как_в_бэкенде

  JWT взять: зайти в приложение водителя под тем водителем, который назначен на заказ,
  в DevTools / Network скопировать заголовок Authorization (Bearer ...) или получить
  токен через POST /api/v1/driver-auth/login (phone + code).

Usage:
  1. Get driver JWT (see above).
  2. Add DRIVER_TOKEN and OPENROUTESERVICE_API_KEY to .env in project root.
  3. Run: poetry run python scripts/emulate_driver_location.py
     Or:  TASK_ID=1 EMULATE_SPEED_KMH=50 poetry run python scripts/emulate_driver_location.py
"""
import math
import os
import sys
import time

import httpx

try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

def _env(key: str, default: str = "") -> str:
    """Get env var, strip and take first line (avoid merged .env lines / encoding junk)."""
    v = os.environ.get(key, default).strip()
    v = v.split("\n")[0].split("\r")[0].strip()
    v = "".join(c for c in v if ord(c) < 0x10000 and c not in "\x00\r\n")
    return v


API_BASE_URL = _env("API_BASE_URL") or "http://localhost:8000"
DRIVER_TOKEN = _env("DRIVER_TOKEN")
OPENROUTESERVICE_API_KEY = _env("OPENROUTESERVICE_API_KEY")
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

TASK_ID = int(os.environ.get("TASK_ID", "1"))
WAREHOUSE_LAT, WAREHOUSE_LON = 43.653366, 39.64989
DC1_LAT, DC1_LON = 43.493591, 39.889214
DC2_LAT, DC2_LON = 43.644115, 39.753254

SPEED_KMH = float(os.environ.get("EMULATE_SPEED_KMH", "45"))
INTERVAL_SEC = int(os.environ.get("EMULATE_INTERVAL_SEC", "15"))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def fetch_route_geometry(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> list[tuple[float, float]]:
    """Get route as list of (lat, lon) from OpenRouteService."""
    params = {
        "api_key": OPENROUTESERVICE_API_KEY,
        "start": f"{from_lon},{from_lat}",
        "end": f"{to_lon},{to_lat}",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.get(ORS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    if not data.get("features"):
        raise RuntimeError("No route in OpenRouteService response")
    coords = data["features"][0]["geometry"]["coordinates"]
    return [(c[1], c[0]) for c in coords]


def build_full_route() -> list[tuple[float, float]]:
    leg1 = fetch_route_geometry(WAREHOUSE_LAT, WAREHOUSE_LON, DC1_LAT, DC1_LON)
    leg2 = fetch_route_geometry(DC1_LAT, DC1_LON, DC2_LAT, DC2_LON)
    return leg1 + leg2[1:]


def route_length_km(points: list[tuple[float, float]]) -> float:
    return sum(
        haversine_km(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(len(points) - 1)
    )


def position_at_distance(points: list[tuple[float, float]], distance_km: float) -> tuple[float, float]:
    """Return (lat, lon) at given distance along the polyline (in km)."""
    if distance_km <= 0:
        return points[0]
    total = 0.0
    for i in range(len(points) - 1):
        seg = haversine_km(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        if total + seg >= distance_km:
            t = (distance_km - total) / seg if seg > 0 else 1
            lat = points[i][0] + t * (points[i + 1][0] - points[i][0])
            lon = points[i][1] + t * (points[i + 1][1] - points[i][1])
            return (lat, lon)
        total += seg
    return points[-1]


def post_location(lat: float, lon: float) -> bool:
    url = f"{API_BASE_URL}/api/v1/driver/delivery-tasks/{TASK_ID}/location"
    headers = {
        "Authorization": f"Bearer {DRIVER_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {"lat": lat, "lon": lon}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=body, headers=headers)
            if r.status_code != 200:
                print(f"  POST {r.status_code}: {r.text[:200]}")
                return False
            return True
    except Exception as e:
        print(f"  POST error: {e}")
        return False


def main() -> None:
    if not DRIVER_TOKEN:
        print("Set DRIVER_TOKEN in .env (project root). Get JWT by logging in as the driver.")
        print("Example: DRIVER_TOKEN=eyJhbGciOiJIUzI1NiIs...")
        sys.exit(1)
    if not OPENROUTESERVICE_API_KEY:
        print("Set OPENROUTESERVICE_API_KEY in .env (same key as backend).")
        sys.exit(1)

    print("Building route (warehouse -> DC1 -> DC2)...")
    route = build_full_route()
    total_km = route_length_km(route)
    duration_h = total_km / SPEED_KMH
    step_km = SPEED_KMH * (INTERVAL_SEC / 3600.0)
    n_steps = max(1, int(total_km / step_km))
    print(f"  Route: {len(route)} points, {total_km:.2f} km, ~{duration_h*60:.0f} min at {SPEED_KMH} km/h")
    print(f"  Sending location every {INTERVAL_SEC} s (~{n_steps} steps)")
    print()

    distance_km = 0.0
    step = 0
    while distance_km < total_km:
        lat, lon = position_at_distance(route, distance_km)
        ok = post_location(lat, lon)
        print(f"  step {step+1}: ({lat:.5f}, {lon:.5f}) km={distance_km:.2f}  {'OK' if ok else 'FAIL'}")
        distance_km += step_km
        step += 1
        if distance_km < total_km:
            time.sleep(INTERVAL_SEC)

    lat, lon = route[-1]
    post_location(lat, lon)
    print(f"  final: ({lat:.5f}, {lon:.5f})  Done.")


if __name__ == "__main__":
    main()
