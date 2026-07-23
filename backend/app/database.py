"""SQLite persistence layer (aircraft sighting history)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Sighting(Base):
    """A single record of an aircraft being the 'selected' overhead aircraft.

    Kept intentionally simple so future features (history view, stats
    dashboard, military/helicopter alerts) can query it directly.
    """

    __tablename__ = "sightings"

    id: Mapped[int] = mapped_column(primary_key=True)
    icao24: Mapped[str] = mapped_column(index=True)
    callsign: Mapped[str | None]
    registration: Mapped[str | None]
    manufacturer: Mapped[str | None]
    model: Mapped[str | None]
    airline_name: Mapped[str | None]
    origin_icao: Mapped[str | None]
    destination_icao: Mapped[str | None]
    is_military: Mapped[bool] = mapped_column(default=False)
    is_helicopter: Mapped[bool] = mapped_column(default=False)
    closest_distance_km: Mapped[float | None]
    max_altitude_ft: Mapped[float | None]
    first_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)


def init_db() -> None:
    if settings.database_url.startswith("sqlite"):
        _ensure_sqlite_dir()
    Base.metadata.create_all(bind=engine)


def _ensure_sqlite_dir() -> None:
    # sqlite:///path/to/file.db -> path/to
    path = settings.database_url.split("sqlite:///", 1)[-1]
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
