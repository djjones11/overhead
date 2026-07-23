"""Great-circle geometry helpers used for aircraft selection & ETA."""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (degrees, 0-360) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def angle_diff_deg(a: float, b: float) -> float:
    """Smallest absolute difference between two compass bearings."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def is_approaching(
    aircraft_lat: float,
    aircraft_lon: float,
    heading_deg: float | None,
    home_lat: float,
    home_lon: float,
    tolerance_deg: float = 30.0,
) -> bool:
    """True if the aircraft's heading points roughly towards home."""
    if heading_deg is None:
        return False
    bearing_to_home = bearing_deg(aircraft_lat, aircraft_lon, home_lat, home_lon)
    return angle_diff_deg(heading_deg, bearing_to_home) <= tolerance_deg


def eta_seconds(
    distance_km: float,
    ground_speed_kt: float | None,
    approaching: bool,
) -> float | None:
    """Very rough time-to-overhead estimate assuming constant speed & course.

    Returns None when we have no meaningful speed or the aircraft is moving
    away from home (ETA would be nonsensical/negative).
    """
    if not ground_speed_kt or ground_speed_kt <= 1 or not approaching:
        return None
    speed_km_s = (ground_speed_kt * 1.852) / 3600.0
    if speed_km_s <= 0:
        return None
    return distance_km / speed_km_s
