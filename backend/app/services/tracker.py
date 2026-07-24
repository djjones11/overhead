"""
The `AircraftTracker` is the heart of the backend: a single background task
that polls the configured ADS-B provider on a timer, works out which
aircraft is currently most relevant, enriches it with airframe/route/photo
metadata, and caches the fully-built response in memory so HTTP/WebSocket
requests are always instant regardless of upstream API latency.

Design notes for future features:
  * Every poll's winning aircraft (and near-misses) can be persisted to
    SQLite (`record_sighting`) - this already gives you the raw material for
    a "history" view or stats dashboard.
  * `is_military` / `is_helicopter` flags are computed per-candidate, so
    alerting hooks can be added in `_process_candidates` without touching
    the rest of the pipeline.
  * The class holds no FastAPI-specific state, so it's reusable from a CLI
    script, tests, or a future Home Assistant push integration.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import Settings
from ..database import SessionLocal, Sighting
from ..schemas import (
    AircraftPhoto,
    AirlineInfo,
    AirportInfo,
    HomeLocation,
    OverheadResponse,
    RadarBlip,
    SelectedAircraft,
)
from .adsb import ProviderUnavailable, get_provider
from .aircraft_lookup import AircraftLookupService
from .airline import flight_number_from_callsign, resolve_airline
from .photos import PhotoService
from .selection import Candidate, build_candidates, pick_best
from .summary import build_summary

logger = logging.getLogger("overhead.tracker")


class AircraftTracker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = get_provider(settings)
        self.lookup = AircraftLookupService(settings)
        self.photos = PhotoService(settings)

        self._current: OverheadResponse | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._last_good_provider_ok = True

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_forever())
            logger.info("Aircraft tracker started (provider=%s)", self.provider.name)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def get_current(self) -> OverheadResponse:
        async with self._lock:
            if self._current is not None:
                return self._current
        # No poll has completed yet - return an honest "starting up" state.
        return OverheadResponse(
            home=HomeLocation(
                latitude=self.settings.home_lat,
                longitude=self.settings.home_lon,
                radius_km=self.settings.radius_km,
            ),
            aircraft=None,
            candidate_count=0,
            server_time=_now_iso(),
            provider=self.provider.name,
            provider_ok=True,
            message="Starting up...",
        )

    # -- main loop -----------------------------------------------------------
    async def _run_forever(self) -> None:
        while True:
            try:
                await self._poll_once()
            except Exception:  # noqa: BLE001 - keep the loop alive no matter what
                logger.exception("Unexpected error during poll")
            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def _poll_once(self) -> None:
        settings = self.settings
        provider_ok = True
        message = None

        try:
            raw_aircraft = await self.provider.fetch_nearby(
                settings.home_lat, settings.home_lon, settings.radius_km
            )
        except ProviderUnavailable as exc:
            logger.warning("Provider unavailable: %s", exc)
            provider_ok = False
            message = "Live data temporarily unavailable - showing last known state."
            raw_aircraft = []
            if self._current and self._current.aircraft:
                # Keep serving the last good aircraft rather than flashing to idle.
                async with self._lock:
                    self._current = self._current.model_copy(
                        update={"provider_ok": False, "message": message, "server_time": _now_iso()}
                    )
                return

        candidates = build_candidates(
            raw_aircraft,
            settings.home_lat,
            settings.home_lon,
            settings.radius_km,
            settings.approach_bonus_threshold_deg,
            settings.min_altitude_ft,
        )
        best = pick_best(candidates)

        selected = await self._build_selected(best) if best else None

        radar = [
            RadarBlip(
                icao24=c.raw.icao24,
                callsign=c.raw.callsign,
                distance_km=round(c.distance_km, 3),
                bearing_from_home_deg=round(c.bearing_from_home_deg, 1),
                altitude_ft=c.raw.altitude_ft,
                heading_deg=c.raw.heading_deg,
                is_approaching=c.approaching,
                is_selected=(best is not None and c.raw.icao24 == best.raw.icao24),
            )
            for c in candidates
        ]

        response = OverheadResponse(
            home=HomeLocation(latitude=settings.home_lat, longitude=settings.home_lon, radius_km=settings.radius_km),
            aircraft=selected,
            candidate_count=len(candidates),
            radar=radar,
            server_time=_now_iso(),
            provider=self.provider.name,
            provider_ok=provider_ok,
            message=message,
        )

        async with self._lock:
            self._current = response

        if selected:
            self._record_sighting(selected, best)

    async def _build_selected(self, candidate: Candidate) -> SelectedAircraft:
        raw = candidate.raw
        route: dict = {}

        airline = resolve_airline(raw.callsign)
        airframe = await self.lookup.get_airframe(raw.icao24)
        if raw.callsign:
            route = await self.lookup.get_route(raw.callsign)

        is_military = self.lookup.looks_military(raw.callsign, raw.icao24)
        is_helicopter = self.lookup.looks_helicopter(airframe.get("model"))

        photo = await self.photos.get_photo(airframe.get("registration"), raw.icao24)

        origin = AirportInfo(**route.get("origin")) if route.get("origin") else AirportInfo()
        destination = AirportInfo(**route.get("destination")) if route.get("destination") else AirportInfo()

        summary = build_summary(
            airline_name=airline.get("name"),
            manufacturer=airframe.get("manufacturer"),
            model=airframe.get("model"),
            destination_name=destination.name or destination.city,
            origin_name=origin.name or origin.city,
            approaching=candidate.approaching,
            eta_seconds=candidate.eta_seconds,
            is_military=is_military,
            callsign=raw.callsign,
        )

        return SelectedAircraft(
            icao24=raw.icao24,
            callsign=raw.callsign,
            flight_number=flight_number_from_callsign(raw.callsign),
            registration=airframe.get("registration"),
            manufacturer=airframe.get("manufacturer"),
            model=airframe.get("model"),
            is_military=is_military,
            is_helicopter=is_helicopter,
            airline=AirlineInfo(**airline),
            origin=origin,
            destination=destination,
            photo=AircraftPhoto(**photo),
            latitude=raw.latitude,
            longitude=raw.longitude,
            altitude_ft=raw.altitude_ft,
            ground_speed_kt=raw.ground_speed_kt,
            heading_deg=raw.heading_deg,
            vertical_rate_fpm=raw.vertical_rate_fpm,
            distance_km=round(candidate.distance_km, 3),
            bearing_from_home_deg=round(candidate.bearing_from_home_deg, 1),
            is_approaching=candidate.approaching,
            eta_seconds=round(candidate.eta_seconds) if candidate.eta_seconds else None,
            summary=summary,
            last_updated=_now_iso(),
        )

    def _record_sighting(self, selected: SelectedAircraft, candidate: Candidate) -> None:
        db: Session = SessionLocal()
        try:
            existing = (
                db.query(Sighting)
                .filter(Sighting.icao24 == selected.icao24)
                .order_by(Sighting.id.desc())
                .first()
            )
            now = datetime.utcnow()
            # Treat as the same "pass" if seen again within a couple of minutes.
            if existing and (now - existing.last_seen).total_seconds() < 120:
                existing.last_seen = now
                existing.closest_distance_km = min(existing.closest_distance_km or 1e9, selected.distance_km)
                existing.max_altitude_ft = max(existing.max_altitude_ft or 0, selected.altitude_ft or 0)
            else:
                db.add(
                    Sighting(
                        icao24=selected.icao24,
                        callsign=selected.callsign,
                        registration=selected.registration,
                        manufacturer=selected.manufacturer,
                        model=selected.model,
                        airline_name=selected.airline.name,
                        origin_icao=selected.origin.icao,
                        destination_icao=selected.destination.icao,
                        is_military=selected.is_military,
                        is_helicopter=selected.is_helicopter,
                        closest_distance_km=selected.distance_km,
                        max_altitude_ft=selected.altitude_ft,
                        first_seen=now,
                        last_seen=now,
                    )
                )
            db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to record sighting")
            db.rollback()
        finally:
            db.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()