"""Pydantic models describing API responses sent to the frontend."""
from __future__ import annotations

from pydantic import BaseModel


class AirportInfo(BaseModel):
    icao: str | None = None
    iata: str | None = None
    name: str | None = None
    city: str | None = None
    country: str | None = None


class AircraftPhoto(BaseModel):
    url: str | None = None
    thumbnail_url: str | None = None
    photographer: str | None = None
    source: str | None = None


class AirlineInfo(BaseModel):
    name: str | None = None
    icao: str | None = None
    iata: str | None = None
    logo_url: str | None = None


class SelectedAircraft(BaseModel):
    icao24: str
    callsign: str | None = None
    flight_number: str | None = None
    registration: str | None = None

    manufacturer: str | None = None
    model: str | None = None
    is_military: bool = False
    is_helicopter: bool = False

    airline: AirlineInfo = AirlineInfo()
    origin: AirportInfo = AirportInfo()
    destination: AirportInfo = AirportInfo()
    photo: AircraftPhoto = AircraftPhoto()

    latitude: float
    longitude: float
    altitude_ft: float | None = None
    ground_speed_kt: float | None = None
    heading_deg: float | None = None
    vertical_rate_fpm: float | None = None

    distance_km: float
    bearing_from_home_deg: float
    is_approaching: bool
    eta_seconds: float | None = None

    summary: str

    last_updated: str  # ISO timestamp


class HomeLocation(BaseModel):
    latitude: float
    longitude: float
    radius_km: float


class OverheadResponse(BaseModel):
    home: HomeLocation
    aircraft: SelectedAircraft | None = None
    candidate_count: int = 0
    server_time: str
    provider: str
    provider_ok: bool = True
    message: str | None = None


class ConfigResponse(BaseModel):
    home: HomeLocation
    poll_interval_seconds: float
    provider: str
