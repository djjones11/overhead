"""
ADS-B data source abstraction.

Supports three free/low-cost providers behind a single interface:

* adsb.fi        - no API key, community-run, generous rate limits (default)
* adsbexchange   - RapidAPI-hosted, requires an API key
* opensky        - free, optional OAuth2 client credentials for higher limits

`get_provider()` returns the configured provider. If a live request fails
(network error, rate limit, bad response) the provider raises
`ProviderUnavailable` so the caller can serve stale/cached data gracefully
instead of crashing the whole polling loop.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import Settings

logger = logging.getLogger("overhead.adsb")


class ProviderUnavailable(Exception):
    """Raised when a provider cannot currently supply data."""


@dataclass
class RawAircraft:
    """Normalised representation of a live ADS-B state, regardless of provider."""

    icao24: str
    callsign: str | None
    latitude: float | None
    longitude: float | None
    altitude_ft: float | None
    ground_speed_kt: float | None
    heading_deg: float | None
    vertical_rate_fpm: float | None
    on_ground: bool = False


class AdsbProvider(Protocol):
    name: str

    async def fetch_nearby(self, lat: float, lon: float, radius_km: float) -> list[RawAircraft]:
        ...


class AdsbFiProvider:
    """https://github.com/adsbfi/opendata - free public API, no key required."""

    name = "adsbfi"
    BASE_URL = "https://opendata.adsb.fi/api/v2"

    async def fetch_nearby(self, lat: float, lon: float, radius_km: float) -> list[RawAircraft]:
        radius_nm = max(1.0, radius_km / 1.852)
        url = f"{self.BASE_URL}/lat/{lat}/lon/{lon}/dist/{radius_nm:.1f}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers={"User-Agent": "Overhead/1.0"})
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(f"adsb.fi request failed: {exc}") from exc

        aircraft = []
        for entry in data.get("ac", []):
            aircraft.append(
                RawAircraft(
                    icao24=str(entry.get("hex", "")).lower(),
                    callsign=(entry.get("flight") or "").strip() or None,
                    latitude=entry.get("lat"),
                    longitude=entry.get("lon"),
                    altitude_ft=_safe_float(entry.get("alt_baro")),
                    ground_speed_kt=_safe_float(entry.get("gs")),
                    heading_deg=_safe_float(entry.get("track")),
                    vertical_rate_fpm=_safe_float(entry.get("baro_rate")),
                    on_ground=entry.get("alt_baro") == "ground",
                )
            )
        return aircraft


class AdsbExchangeProvider:
    """RapidAPI-hosted ADS-B Exchange (requires an API key)."""

    name = "adsbexchange"
    BASE_URL = "https://adsbexchange-com1.p.rapidapi.com/v2"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    async def fetch_nearby(self, lat: float, lon: float, radius_km: float) -> list[RawAircraft]:
        if not self.api_key:
            raise ProviderUnavailable("adsbexchange: no API key configured")

        radius_nm = max(1.0, radius_km / 1.852)
        url = f"{self.BASE_URL}/lat/{lat}/lon/{lon}/dist/{radius_nm:.0f}/"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com",
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(f"adsbexchange request failed: {exc}") from exc

        aircraft = []
        for entry in data.get("ac", []):
            aircraft.append(
                RawAircraft(
                    icao24=str(entry.get("hex", "")).lower(),
                    callsign=(entry.get("flight") or "").strip() or None,
                    latitude=entry.get("lat"),
                    longitude=entry.get("lon"),
                    altitude_ft=_safe_float(entry.get("alt_baro")),
                    ground_speed_kt=_safe_float(entry.get("gs")),
                    heading_deg=_safe_float(entry.get("track")),
                    vertical_rate_fpm=_safe_float(entry.get("baro_rate")),
                    on_ground=entry.get("alt_baro") == "ground",
                )
            )
        return aircraft


class OpenSkyProvider:
    """https://opensky-network.org/ REST API. Works anonymously with lower limits."""

    name = "opensky"
    BASE_URL = "https://opensky-network.org/api"
    TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

    def __init__(self, client_id: str | None, client_secret: str | None):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_token(self) -> str | None:
        if not self.client_id or not self.client_secret:
            return None
        if self._token and time.time() < self._token_expiry - 30:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                self._token = payload["access_token"]
                self._token_expiry = time.time() + payload.get("expires_in", 1800)
                return self._token
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("OpenSky auth failed, falling back to anonymous: %s", exc)
            return None

    async def fetch_nearby(self, lat: float, lon: float, radius_km: float) -> list[RawAircraft]:
        # Roughly convert a radius in km to a lat/lon bounding box.
        dlat = radius_km / 111.0
        dlon = radius_km / (111.0 * max(0.1, abs(_cos_deg(lat))))
        params = {
            "lamin": lat - dlat,
            "lamax": lat + dlat,
            "lomin": lon - dlon,
            "lomax": lon + dlon,
        }
        headers = {}
        token = await self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{self.BASE_URL}/states/all", params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(f"opensky request failed: {exc}") from exc

        aircraft = []
        for state in data.get("states") or []:
            # OpenSky returns positional arrays; see API docs for indices.
            icao24, callsign = state[0], (state[1] or "").strip() or None
            longitude, latitude, _baro_alt, on_ground = state[5], state[6], state[7], state[8]
            velocity, heading, vertical_rate = state[9], state[10], state[11]
            geo_alt = state[13] if len(state) > 13 else None
            altitude_m = geo_alt if geo_alt is not None else _baro_alt
            aircraft.append(
                RawAircraft(
                    icao24=icao24,
                    callsign=callsign,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_ft=_meters_to_feet(altitude_m),
                    ground_speed_kt=_ms_to_knots(velocity),
                    heading_deg=heading,
                    vertical_rate_fpm=_ms_to_fpm(vertical_rate),
                    on_ground=bool(on_ground),
                )
            )
        return aircraft


def get_provider(settings: Settings) -> AdsbProvider:
    if settings.adsb_provider == "adsbexchange":
        return AdsbExchangeProvider(settings.adsbexchange_api_key)
    if settings.adsb_provider == "opensky":
        return OpenSkyProvider(settings.opensky_client_id, settings.opensky_client_secret)
    return AdsbFiProvider()


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _meters_to_feet(value) -> float | None:
    v = _safe_float(value)
    return v * 3.28084 if v is not None else None


def _ms_to_knots(value) -> float | None:
    v = _safe_float(value)
    return v * 1.94384 if v is not None else None


def _ms_to_fpm(value) -> float | None:
    v = _safe_float(value)
    return v * 196.850 if v is not None else None


def _cos_deg(deg: float) -> float:
    import math

    return math.cos(math.radians(deg))
