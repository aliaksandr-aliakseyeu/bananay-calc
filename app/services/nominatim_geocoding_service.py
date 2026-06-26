"""Nominatim geocoding client with rate limiting and file cache."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "BananayCalcImport/1.0"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / ".cache" / "nominatim_batumi.json"
MIN_REQUEST_INTERVAL_SEC = 1.05


class NominatimGeocodingService:
    """Reverse and forward geocoding via OpenStreetMap Nominatim."""

    def __init__(
        self,
        cache_path: Path | None = None,
        min_interval_sec: float = MIN_REQUEST_INTERVAL_SEC,
    ) -> None:
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self.min_interval_sec = min_interval_sec
        self._last_request_at = 0.0
        self._cache: dict[str, Any] = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load Nominatim cache: %s", exc)
        return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)

    def _request(self, path: str, params: dict[str, str], cache_key: str) -> dict[str, Any] | list[Any] | None:
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._throttle()
        headers = {"User-Agent": USER_AGENT}

        for attempt in range(3):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(f"{NOMINATIM_BASE_URL}/{path}", params=params, headers=headers)
                    self._last_request_at = time.monotonic()

                if response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue

                response.raise_for_status()
                data = response.json()
                self._cache[cache_key] = data
                self._save_cache()
                return data
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                logger.warning("Nominatim request failed (attempt %s): %s", attempt + 1, exc)
                time.sleep(2 ** attempt)

        return None

    @staticmethod
    def format_short_address(result: dict[str, Any]) -> str | None:
        """Build a short English-style address from a Nominatim result."""
        address = result.get("address")
        if not isinstance(address, dict):
            display_name = result.get("display_name")
            if isinstance(display_name, str):
                return ", ".join(display_name.split(",")[:3])
            return None

        parts: list[str] = []
        locality = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )
        if locality:
            parts.append(str(locality))

        road = address.get("road")
        if road:
            street = str(road)
            house_number = address.get("house_number")
            if house_number:
                street += f", {house_number}"
            parts.append(street)

        if parts:
            return ", ".join(parts)

        display_name = result.get("display_name")
        if isinstance(display_name, str):
            return ", ".join(display_name.split(",")[:2])
        return None

    def reverse_address(self, lat: float, lng: float, lang: str = "en") -> str | None:
        """Reverse geocode coordinates to a short address."""
        cache_key = f"reverse:{lat:.6f},{lng:.6f}:{lang}"
        params = {
            "lat": str(lat),
            "lon": str(lng),
            "format": "json",
            "addressdetails": "1",
            "accept-language": lang,
        }
        data = self._request("reverse", params, cache_key)
        if not isinstance(data, dict) or not data.get("place_id"):
            return None
        return self.format_short_address(data)

    def search_place_name(
        self,
        query: str,
        *,
        country_code: str = "ge",
        lang: str = "en",
        lat: float | None = None,
        lng: float | None = None,
    ) -> str | None:
        """Forward geocode a place name; return the POI name if found in Latin script."""
        cache_key = f"search:{query}:{country_code}:{lang}"
        params: dict[str, str] = {
            "q": query,
            "format": "json",
            "addressdetails": "1",
            "limit": "5",
            "accept-language": lang,
            "countrycodes": country_code,
        }
        if lat is not None and lng is not None:
            delta = 0.01
            params["viewbox"] = f"{lng - delta},{lat + delta},{lng + delta},{lat - delta}"
            params["bounded"] = "1"

        data = self._request("search", params, cache_key)
        if not isinstance(data, list) or not data:
            return None

        for item in data:
            name = item.get("name")
            if isinstance(name, str) and _is_latin_text(name):
                return name.strip()

        return None

    def flush_cache(self) -> None:
        """Persist cache to disk."""
        self._save_cache()


def _is_latin_text(text: str) -> bool:
    """True if text contains Latin letters and no Cyrillic/Georgian."""
    has_latin = any("A" <= ch <= "Z" or "a" <= ch <= "z" for ch in text)
    has_cyrillic = any("\u0400" <= ch <= "\u04FF" for ch in text)
    has_georgian = any("\u10A0" <= ch <= "\u10FF" for ch in text)
    return has_latin and not has_cyrillic and not has_georgian
