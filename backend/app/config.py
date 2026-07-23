"""
Application configuration.

All settings are read from environment variables (or a `.env` file) so the
same Docker image can be reused for any home location or ADS-B provider
simply by changing the environment. See `.env.example` in the project root
for the full list of options.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Home location -----------------------------------------------
    home_lat: float = 51.5074
    home_lon: float = -0.1278
    radius_km: float = 5.0

    # --- ADS-B data source ---------------------------------------------
    # "adsbfi"       -> https://adsb.fi (free, no key, generous limits)
    # "adsbexchange" -> https://www.adsbexchange.com (RapidAPI key required)
    # "opensky"      -> https://opensky-network.org (free, optional auth)
    adsb_provider: Literal["adsbfi", "adsbexchange", "opensky"] = "adsbfi"
    adsbexchange_api_key: str | None = None
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None

    # --- Polling / behaviour --------------------------------------------
    poll_interval_seconds: float = 4.0
    aircraft_stale_seconds: float = 20.0
    min_altitude_ft: int = 0  # set > 0 to ignore aircraft on the ground
    approach_bonus_threshold_deg: float = 30.0  # "approaching" heading tolerance

    # --- External metadata / images -------------------------------------
    enable_photo_lookup: bool = True
    photo_cache_dir: Path = BASE_DIR / "app" / "cache" / "photos"
    metadata_cache_ttl_hours: int = 24 * 14  # airframe metadata rarely changes

    # --- Storage ----------------------------------------------------------
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'overhead.db'}"

    # --- CORS / server -----------------------------------------------------
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
