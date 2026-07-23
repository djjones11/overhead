"""
Airframe & route metadata lookup.

Uses hexdb.io (https://hexdb.io) - a free, keyless community database - to
resolve:
  * ICAO24 hex address -> registration, manufacturer, model
  * Callsign            -> scheduled origin/destination airports

Results are cached on disk (see `services.cache.TTLCache`) since airframe
metadata almost never changes and route lookups repeat frequently for the
same flight number throughout a single flight.

Military aircraft don't have a commercial "route" and often lack registry
data; a lightweight heuristic (`looks_military`) flags them so the frontend
can show a distinct badge (and, in future, trigger military-alert
notifications).
"""
from __future__ import annotations

import logging

import httpx

from ..config import Settings
from .cache import TTLCache

logger = logging.getLogger("overhead.lookup")

# ICAO24 address blocks and callsign patterns commonly used by military /
# government aircraft. Not exhaustive - intended as a "good enough" heuristic.
_MILITARY_CALLSIGN_PREFIXES = (
    "RCH", "CNV", "REACH", "NATO", "FORTE", "DUKE", "HOIST", "SAM",
    "ASCOT", "IAM", "GAF", "FAF", "CFC", "NAF", "MMF",
)


class AircraftLookupService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._metadata_cache = TTLCache(
            settings.photo_cache_dir.parent / "metadata_cache.json",
            default_ttl_seconds=settings.metadata_cache_ttl_hours * 3600,
        )
        self._route_cache = TTLCache(
            settings.photo_cache_dir.parent / "route_cache.json",
            default_ttl_seconds=6 * 3600,  # routes/schedules can change more often
        )

    async def get_airframe(self, icao24: str) -> dict:
        icao24 = icao24.lower()
        cached = await self._metadata_cache.get(icao24)
        if cached is not None:
            return cached

        result = {"registration": None, "manufacturer": None, "model": None}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"https://hexdb.io/api/v1/aircraft/{icao24}")
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    result = {
                        "registration": data.get("Registration") or data.get("registration"),
                        "manufacturer": data.get("Manufacturer") or data.get("manufacturer"),
                        "model": data.get("Type") or data.get("ICAOTypeCode") or data.get("type"),
                    }
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Airframe lookup failed for %s: %s", icao24, exc)

        await self._metadata_cache.set(icao24, result)
        return result

    async def get_route(self, callsign: str) -> dict:
        callsign = callsign.strip().upper()
        cached = await self._route_cache.get(callsign)
        if cached is not None:
            return cached

        result = {"origin": None, "destination": None}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"https://hexdb.io/api/v1/route/icao/{callsign}")
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    result = {
                        "origin": _airport_from_hexdb(data, "Origin"),
                        "destination": _airport_from_hexdb(data, "Destination"),
                    }
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("Route lookup failed for %s: %s", callsign, exc)

        await self._route_cache.set(callsign, result)
        return result

    @staticmethod
    def looks_military(callsign: str | None, icao24: str | None) -> bool:
        if callsign:
            upper = callsign.strip().upper()
            if any(upper.startswith(prefix) for prefix in _MILITARY_CALLSIGN_PREFIXES):
                return True
        return False

    @staticmethod
    def looks_helicopter(model: str | None) -> bool:
        if not model:
            return False
        model_upper = model.upper()
        helicopter_markers = ("H145", "H135", "H160", "AS350", "AS365", "EC1", "R44", "R66", "S-76", "S76", "UH-", "AW1")
        return any(marker in model_upper for marker in helicopter_markers)


def _airport_from_hexdb(data: dict, prefix: str) -> dict | None:
    icao = data.get(f"{prefix}ICAO") or data.get(f"{prefix.lower()}_icao")
    if not icao:
        return None
    return {
        "icao": icao,
        "iata": data.get(f"{prefix}IATA") or data.get(f"{prefix.lower()}_iata"),
        "name": data.get(f"{prefix}Name") or data.get(f"{prefix.lower()}_name"),
        "city": data.get(f"{prefix}City") or data.get(f"{prefix.lower()}_city"),
        "country": None,
    }
