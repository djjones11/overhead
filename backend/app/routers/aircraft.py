from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from ..schemas import ConfigResponse, HomeLocation, OverheadResponse

logger = logging.getLogger("overhead.api")

router = APIRouter()


@router.get("/api/overhead", response_model=OverheadResponse)
async def get_overhead(request: Request) -> OverheadResponse:
    """One-shot snapshot of the currently selected aircraft (polling fallback)."""
    return await request.app.state.tracker.get_current()


@router.get("/api/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    settings = request.app.state.settings
    return ConfigResponse(
        home=HomeLocation(latitude=settings.home_lat, longitude=settings.home_lon, radius_km=settings.radius_km),
        poll_interval_seconds=settings.poll_interval_seconds,
        provider=settings.adsb_provider,
    )


@router.websocket("/ws/overhead")
async def overhead_ws(websocket: WebSocket) -> None:
    """Push the latest snapshot to connected clients every poll interval.

    Falling back to REST polling on the frontend is trivial if a proxy in
    front of this app doesn't support WebSockets - see `useAircraftData.ts`.
    """
    await websocket.accept()
    tracker = websocket.app.state.tracker
    settings = websocket.app.state.settings
    try:
        while True:
            snapshot = await tracker.get_current()
            await websocket.send_text(snapshot.model_dump_json())
            await asyncio.sleep(settings.poll_interval_seconds)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
