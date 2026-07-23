"""
Resolve an airline's name/IATA code and logo from a flight's ICAO callsign.

The callsign's first 3 letters are the ICAO airline designator (e.g. "EZY"
for easyJet). We keep a small bundled JSON table (`app/data/airlines.json`)
covering major scheduled carriers - easy to extend by editing that file, no
code changes required.

Logos are served from AirHex's free public logo CDN, keyed by IATA code.
No API key or attribution is required for the low-resolution endpoint used
here. If the airline is unknown or has no IATA code, `logo_url` is left
`None` and the frontend shows a generic placeholder.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "airlines.json"
_AIRLINES: dict[str, dict] = json.loads(_DATA_PATH.read_text())

_LOGO_TEMPLATE = "https://content.airhex.com/content/logos/airlines_{iata}_200_200_s.png"


def resolve_airline(callsign: str | None) -> dict:
    if not callsign or len(callsign) < 3:
        return {"name": None, "icao": None, "iata": None, "logo_url": None}

    designator = callsign.strip().upper()[:3]
    entry = _AIRLINES.get(designator)
    if not entry:
        return {"name": None, "icao": designator, "iata": None, "logo_url": None}

    iata = entry.get("iata")
    return {
        "name": entry.get("name"),
        "icao": designator,
        "iata": iata,
        "logo_url": _LOGO_TEMPLATE.format(iata=iata) if iata else None,
    }


def flight_number_from_callsign(callsign: str | None) -> str | None:
    """Best-effort human-friendly flight number, e.g. 'EZY123' -> 'U2 123'."""
    if not callsign:
        return None
    callsign = callsign.strip().upper()
    designator, digits = callsign[:3], callsign[3:].lstrip("0") or "0"
    entry = _AIRLINES.get(designator)
    if entry and entry.get("iata"):
        return f"{entry['iata']}{digits}"
    return callsign
