import type { SelectedAircraft, HomeLocation } from "../types/aircraft";
import SummaryHeadline from "./SummaryHeadline";
import InfoTile from "./InfoTile";
import MapView from "./MapView";

interface AircraftDisplayProps {
  aircraft: SelectedAircraft;
  home: HomeLocation;
}

function formatEta(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 90) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)} min`;
}

function compassFromDeg(deg: number | null | undefined): string {
  if (deg === null || deg === undefined) return "—";
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

export default function AircraftDisplay({ aircraft, home }: AircraftDisplayProps) {
  const photoUrl = aircraft.photo.url;
  const craftName = [aircraft.manufacturer, aircraft.model].filter(Boolean).join(" ") || "Unknown aircraft";

  return (
    <div
      key={aircraft.icao24}
      className="h-full w-full flex flex-col animate-slide-up"
    >
      {/* Top: headline + airline */}
      <div className="flex items-start justify-between gap-6 px-8 pt-8 md:px-12 md:pt-10">
        <SummaryHeadline
          summary={aircraft.summary}
          isMilitary={aircraft.is_military}
          isHelicopter={aircraft.is_helicopter}
        />
        {aircraft.airline.logo_url && (
          <img
            src={aircraft.airline.logo_url}
            alt={aircraft.airline.name ?? "Airline logo"}
            className="h-14 w-auto max-w-[160px] object-contain bg-white/95 rounded-xl px-3 py-2 shadow-lg shrink-0"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        )}
      </div>

      {/* Middle: photo + facts + map */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-5 gap-6 px-8 pb-8 pt-6 md:px-12 md:pb-10">
        {/* Photo */}
        <div className="lg:col-span-3 relative rounded-3xl overflow-hidden bg-surface-card border border-surface-border/60 min-h-[240px]">
          {photoUrl ? (
            <img src={photoUrl} alt={craftName} className="absolute inset-0 h-full w-full object-cover" />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-white/20 text-8xl">✈</div>
          )}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent p-6">
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-2xl font-semibold text-white">
                {aircraft.airline.name ?? aircraft.flight_number ?? aircraft.callsign ?? "Unknown"}
              </span>
              {aircraft.flight_number && (
                <span className="text-lg font-medium text-white/60">{aircraft.flight_number}</span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-white/60 text-base">
              <span>{craftName}</span>
              {aircraft.registration && (
                <>
                  <span className="w-1 h-1 rounded-full bg-white/30" />
                  <span className="font-mono">{aircraft.registration}</span>
                </>
              )}
            </div>
            {aircraft.photo.photographer && (
              <p className="text-xs text-white/30 mt-2">
                Photo: {aircraft.photo.photographer} via {aircraft.photo.source}
              </p>
            )}
          </div>
        </div>

        {/* Right column: route + map */}
        <div className="lg:col-span-2 flex flex-col gap-6 min-h-0">
          <div className="flex items-center justify-between bg-surface-card/80 rounded-2xl border border-surface-border/60 px-6 py-5">
            <RouteEndpoint label="From" airport={aircraft.origin} />
            <div className="flex-1 mx-4 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent relative">
              <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-white/40 text-sm">✈</span>
            </div>
            <RouteEndpoint label="To" airport={aircraft.destination} align="right" />
          </div>

          <MapView
            className="flex-1 min-h-[180px]"
            homeLat={home.latitude}
            homeLon={home.longitude}
            radiusKm={home.radius_km}
            aircraftLat={aircraft.latitude}
            aircraftLon={aircraft.longitude}
            headingDeg={aircraft.heading_deg}
          />
        </div>
      </div>

      {/* Bottom: stat tiles */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 px-8 pb-8 md:px-12 md:pb-10">
        <InfoTile label="Distance" value={aircraft.distance_km.toFixed(1)} unit="km" accent />
        <InfoTile label="Altitude" value={aircraft.altitude_ft ? Math.round(aircraft.altitude_ft).toLocaleString() : "—"} unit="ft" />
        <InfoTile label="Speed" value={aircraft.ground_speed_kt ? Math.round(aircraft.ground_speed_kt).toString() : "—"} unit="kt" />
        <InfoTile
          label="Heading"
          value={aircraft.heading_deg !== null ? `${Math.round(aircraft.heading_deg)}°` : "—"}
          unit={compassFromDeg(aircraft.heading_deg)}
        />
        <InfoTile label="Overhead in" value={formatEta(aircraft.eta_seconds)} accent={aircraft.is_approaching} />
      </div>
    </div>
  );
}

function RouteEndpoint({
  label,
  airport,
  align = "left",
}: {
  label: string;
  airport: SelectedAircraft["origin"];
  align?: "left" | "right";
}) {
  const code = airport.iata || airport.icao || "—";
  const city = airport.city || airport.name || "Unknown";
  return (
    <div className={`flex flex-col ${align === "right" ? "items-end text-right" : "items-start text-left"}`}>
      <span className="text-[11px] uppercase tracking-wider text-white/40 font-medium">{label}</span>
      <span className="text-2xl font-semibold text-white tabular-nums">{code}</span>
      <span className="text-sm text-white/50 max-w-[140px] truncate">{city}</span>
    </div>
  );
}
