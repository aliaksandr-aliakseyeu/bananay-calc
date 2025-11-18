"""Distance calculation service."""
import logging
import math
from typing import Any

import httpx
from geoalchemy2.shape import to_shape
from shapely.geometry import Point

from app.core.config import settings

logger = logging.getLogger(__name__)


class DistanceService:
    """Service for calculating distances between locations."""

    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points on earth.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in kilometers
        """
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        earth_radius = 6371.0

        return earth_radius * c

    @staticmethod
    def extract_coordinates(geometry: Any) -> tuple[float, float]:
        """
        Extract latitude and longitude from PostGIS geometry.

        Args:
            geometry: GeoAlchemy2 geometry object

        Returns:
            Tuple of (latitude, longitude)
        """
        shape: Point = to_shape(geometry)
        return shape.y, shape.x

    @staticmethod
    async def get_openrouteservice_route_distance(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> float | None:
        """
        Get actual route distance using OpenRouteService API.

        Args:
            from_lat: Starting point latitude
            from_lon: Starting point longitude
            to_lat: Destination latitude
            to_lon: Destination longitude

        Returns:
            Distance in kilometers or None if API call failed
        """
        if not settings.OPENROUTESERVICE_API_KEY:
            logger.warning("OpenRouteService API key not configured")
            return None

        try:
            params = {
                "api_key": settings.OPENROUTESERVICE_API_KEY,
                "start": f"{from_lon},{from_lat}",
                "end": f"{to_lon},{to_lat}",
            }

            async with httpx.AsyncClient(
                timeout=settings.OPENROUTESERVICE_TIMEOUT
            ) as client:
                response = await client.get(
                    settings.OPENROUTESERVICE_API_URL,
                    params=params
                )
                response.raise_for_status()

                data = response.json()

                if "features" in data and len(data["features"]) > 0:
                    summary = data["features"][0].get("properties", {}).get("summary", {})
                    distance_meters = summary.get("distance")
                    if distance_meters is not None:
                        return distance_meters / 1000.0  # Convert to km

                logger.warning("Unexpected OpenRouteService API response format: %s", data)
                return None

        except httpx.TimeoutException:
            logger.warning(
                "OpenRouteService API timeout for route from (%s,%s) to (%s,%s)",
                from_lat, from_lon, to_lat, to_lon
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                "OpenRouteService API HTTP error: %s - %s",
                e.response.status_code,
                e.response.text
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error calling OpenRouteService API: %s",
                str(e),
                exc_info=True
            )
            return None

    @staticmethod
    async def get_yandex_route_distance(
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> float | None:
        """
        Get actual route distance using Yandex Router API.

        Args:
            from_lat: Starting point latitude
            from_lon: Starting point longitude
            to_lat: Destination latitude
            to_lon: Destination longitude

        Returns:
            Distance in kilometers or None if API call failed
        """
        if not settings.YANDEX_API_KEY:
            logger.warning("Yandex API key not configured")
            return None

        try:
            waypoints = f"{from_lon},{from_lat}|{to_lon},{to_lat}"

            params = {
                "apikey": settings.YANDEX_API_KEY,
                "waypoints": waypoints,
                "mode": "driving",
            }

            async with httpx.AsyncClient(
                timeout=settings.YANDEX_API_TIMEOUT
            ) as client:
                response = await client.get(
                    settings.YANDEX_ROUTER_API_URL,
                    params=params
                )
                response.raise_for_status()

                data = response.json()

                if "route" in data and "distance" in data["route"]:
                    distance_meters = data["route"]["distance"]
                    return distance_meters / 1000.0  # Convert to km

                logger.warning("Unexpected Yandex API response format: %s", data)
                return None

        except httpx.TimeoutException:
            logger.warning(
                "Yandex API timeout for route from (%s,%s) to (%s,%s)",
                from_lat, from_lon, to_lat, to_lon
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Yandex API HTTP error: %s - %s",
                e.response.status_code,
                e.response.text
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error calling Yandex API: %s",
                str(e),
                exc_info=True
            )
            return None

    @classmethod
    async def calculate_distance_with_fallback(
        cls,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> tuple[float, str]:
        """
        Calculate distance using configured routing provider with fallback.

        Tries routing API based on ROUTING_PROVIDER setting:
        - 'openroute': OpenRouteService (free, 2000 req/day)
        - 'yandex': Yandex Router API (paid)
        - 'fallback': uses coefficient immediately

        If API fails, falls back to straight line distance × coefficient.

        Args:
            from_lat: Starting point latitude
            from_lon: Starting point longitude
            to_lat: Destination latitude
            to_lon: Destination longitude

        Returns:
            Tuple of (distance_km, calculation_method)
            where calculation_method is 'openroute_api', 'yandex_api' or 'fallback_coefficient'
        """
        provider = settings.ROUTING_PROVIDER.lower()
        api_distance = None

        if provider == "openroute":
            api_distance = await cls.get_openrouteservice_route_distance(
                from_lat, from_lon, to_lat, to_lon
            )
            if api_distance is not None:
                logger.info(
                    "OpenRouteService route distance: %.2f km from (%s,%s) to (%s,%s)",
                    api_distance, from_lat, from_lon, to_lat, to_lon
                )
                return api_distance, "openroute_api"

        elif provider == "yandex":
            api_distance = await cls.get_yandex_route_distance(
                from_lat, from_lon, to_lat, to_lon
            )
            if api_distance is not None:
                logger.info(
                    "Yandex route distance: %.2f km from (%s,%s) to (%s,%s)",
                    api_distance, from_lat, from_lon, to_lat, to_lon
                )
                return api_distance, "yandex_api"

        elif provider != "fallback":
            logger.warning(
                "Unknown ROUTING_PROVIDER: %s. Using fallback.",
                provider
            )

        straight_distance = cls.haversine_distance(
            from_lat, from_lon, to_lat, to_lon
        )
        fallback_distance = straight_distance * settings.DISTANCE_FALLBACK_COEFFICIENT

        logger.info(
            "Using fallback distance calculation: %.2f km (straight: %.2f km)",
            fallback_distance,
            straight_distance
        )

        return fallback_distance, "fallback_coefficient"
