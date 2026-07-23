"""
Decide which single aircraft, among everything currently within range, is
"the" aircraft to show.

Strategy: aircraft actively heading towards home are always preferred over
aircraft heading away, even if the latter is momentarily closer (it's about
to become irrelevant). Within each group, the closest aircraft wins. This
keeps the display feeling intuitive: once a plane is picked it usually
"wins" the whole pass overhead rather than flicking between candidates.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adsb import RawAircraft
from .geo import bearing_deg, eta_seconds, haversine_km, is_approaching


@dataclass
class Candidate:
    raw: RawAircraft
    distance_km: float
    bearing_from_home_deg: float
    approaching: bool
    eta_seconds: float | None


def build_candidates(
    aircraft: list[RawAircraft],
    home_lat: float,
    home_lon: float,
    radius_km: float,
    approach_tolerance_deg: float,
    min_altitude_ft: float,
) -> list[Candidate]:
    candidates = []
    for ac in aircraft:
        if ac.latitude is None or ac.longitude is None:
            continue
        if ac.on_ground:
            continue
        if min_altitude_ft and (ac.altitude_ft or 0) < min_altitude_ft:
            continue

        distance = haversine_km(home_lat, home_lon, ac.latitude, ac.longitude)
        if distance > radius_km:
            continue

        approaching = is_approaching(
            ac.latitude, ac.longitude, ac.heading_deg, home_lat, home_lon, approach_tolerance_deg
        )
        candidates.append(
            Candidate(
                raw=ac,
                distance_km=distance,
                bearing_from_home_deg=bearing_deg(home_lat, home_lon, ac.latitude, ac.longitude),
                approaching=approaching,
                eta_seconds=eta_seconds(distance, ac.ground_speed_kt, approaching),
            )
        )
    return candidates


def pick_best(candidates: list[Candidate]) -> Candidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: (not c.approaching, c.distance_km))[0]
