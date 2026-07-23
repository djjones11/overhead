from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers.aircraft import router as aircraft_router
from .services.tracker import AircraftTracker

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("overhead")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.settings = settings
    app.state.tracker = AircraftTracker(settings)
    app.state.tracker.start()
    logger.info(
        "Overhead backend ready. Home=(%.5f, %.5f) radius=%.1fkm provider=%s",
        settings.home_lat, settings.home_lon, settings.radius_km, settings.adsb_provider,
    )
    yield
    await app.state.tracker.stop()


app = FastAPI(title="Overhead", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aircraft_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
