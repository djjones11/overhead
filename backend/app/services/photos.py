"""
Aircraft photo lookup with local caching.

Primary source: PlaneSpotters.net's free public photo API
(https://www.planespotters.net/photo/api), keyed by registration. It
requires no API key and its terms permit hotlinking with attribution, which
we surface via `photographer` / `source` fields for the frontend to display.

Photo *metadata* (the remote URL) is cached in the shared TTL cache; the
actual JPEG bytes are cached to disk under `photo_cache_dir` and served back
by the frontend directly from PlaneSpotters unless local caching is
explicitly downloaded via `ensure_downloaded`. This keeps the common case
cheap (no image proxying through our own server) while still allowing a
fully offline/cached mode later if desired.
"""
from __future__ import annotations

import logging
import re

import httpx

from ..config import Settings
from .cache import TTLCache

logger = logging.getLogger("overhead.photos")

_SAFE_REG_RE = re.compile(r"[^A-Za-z0-9-]")


class PhotoService:
    _EMPTY_RESULT_TTL_SECONDS = 6 * 3600  # retry misses periodically rather than caching "no photo" for a month
    _HIT_RESULT_TTL_SECONDS = 30 * 24 * 3600

    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache = TTLCache(
            settings.photo_cache_dir.parent / "photo_cache.json",
            default_ttl_seconds=self._HIT_RESULT_TTL_SECONDS,
        )

    async def get_photo(self, registration: str | None, icao24: str) -> dict:
        empty = {"url": None, "thumbnail_url": None, "photographer": None, "source": None}
        if not self.settings.enable_photo_lookup:
            return empty

        key = (registration or icao24 or "").upper()
        if not key:
            return empty

        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        result = empty
        if registration:
            result = await self._fetch_from_planespotters(registration)

        # Cache hits for a long time (aircraft photos don't change), but
        # cache "we found nothing" for only a few hours - PlaneSpotters adds
        # new photos constantly, and a registration with no photo today may
        # well have one next week.
        ttl = self._HIT_RESULT_TTL_SECONDS if result["url"] else self._EMPTY_RESULT_TTL_SECONDS
        await self._cache.set(key, result, ttl_seconds=ttl)
        return result

    async def _fetch_from_planespotters(self, registration: str) -> dict:
        reg = _SAFE_REG_RE.sub("", registration.upper())
        if not reg:
            return {"url": None, "thumbnail_url": None, "photographer": None, "source": None}

        url = f"https://api.planespotters.net/pub/photos/reg/{reg}"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers={"User-Agent": "Overhead/1.0"})
                if resp.status_code != 200:
                    logger.warning("PlaneSpotters lookup for %s returned HTTP %s", reg, resp.status_code)
                    return {"url": None, "thumbnail_url": None, "photographer": None, "source": None}
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("PlaneSpotters lookup failed for %s: %s", reg, exc)
            return {"url": None, "thumbnail_url": None, "photographer": None, "source": None}

        photos = data.get("photos") or []
        if not photos:
            logger.info("No PlaneSpotters photo found for registration %s", reg)
            return {"url": None, "thumbnail_url": None, "photographer": None, "source": None}

        photo = photos[0]
        # "thumbnail_large" (~600px) is the highest resolution the free public
        # API exposes without authentication - PlaneSpotters reserves their
        # full-resolution originals for logged-in / paying use on their own
        # site. This is a real limitation of the free tier, not a bug.
        return {
            "url": (photo.get("thumbnail_large") or {}).get("src") or (photo.get("thumbnail") or {}).get("src"),
            "thumbnail_url": (photo.get("thumbnail") or {}).get("src"),
            "photographer": photo.get("photographer"),
            "source": "planespotters.net",
        }