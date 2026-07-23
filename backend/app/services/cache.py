"""
Tiny JSON-backed TTL cache.

Used for anything fetched from a slow/rate-limited third-party API
(aircraft metadata, routes, photos) where a full database table would be
overkill. Safe for the single-process use case of this app; if Overhead is
ever scaled to multiple workers this should be swapped for Redis.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any


class TTLCache:
    def __init__(self, path: Path, default_ttl_seconds: float):
        self.path = path
        self.default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data))

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            self._load()
            entry = self._data.get(key)
            if not entry:
                return None
            if entry["expires_at"] < time.time():
                del self._data[key]
                return None
            return entry["value"]

    async def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        async with self._lock:
            self._load()
            self._data[key] = {
                "value": value,
                "expires_at": time.time() + (ttl_seconds or self.default_ttl),
            }
            self._save()
