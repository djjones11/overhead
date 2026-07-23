"""Builds the human-readable headline shown at the top of the display."""
from __future__ import annotations


def build_summary(
    airline_name: str | None,
    manufacturer: str | None,
    model: str | None,
    destination_name: str | None,
    origin_name: str | None,
    approaching: bool,
    eta_seconds: float | None,
    is_military: bool,
    callsign: str | None,
) -> str:
    who = airline_name or (callsign and f"Flight {callsign}") or "An unidentified aircraft"
    if is_military and not airline_name:
        who = "A military aircraft"

    craft = " ".join(part for part in [manufacturer, model] if part) or "aircraft"

    route = ""
    if destination_name and origin_name:
        route = f" approaching {destination_name} from {origin_name}"
    elif destination_name:
        route = f" heading to {destination_name}"
    elif origin_name:
        route = f" from {origin_name}"

    base = f"{who} {craft}{route}.".replace("  ", " ")

    if approaching and eta_seconds is not None:
        if eta_seconds < 90:
            timing = f"Passing overhead in approximately {round(eta_seconds)} seconds."
        else:
            timing = f"Passing overhead in approximately {round(eta_seconds / 60)} minutes."
        return f"{base} {timing}"
    if approaching:
        return f"{base} Approaching your location."
    return f"{base} Nearby, but not on a direct overhead path."
