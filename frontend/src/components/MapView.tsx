import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Polyline, useMap, Circle } from "react-leaflet";
import L from "leaflet";

interface MapViewProps {
  homeLat: number;
  homeLon: number;
  radiusKm: number;
  aircraftLat?: number;
  aircraftLon?: number;
  headingDeg?: number | null;
  className?: string;
}

const homeIcon = L.divIcon({
  className: "",
  html: `<div style="width:14px;height:14px;border-radius:9999px;background:#0a84ff;box-shadow:0 0 0 6px rgba(10,132,255,0.25);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

function planeIcon(headingDeg: number | null | undefined) {
  const rotation = headingDeg ?? 0;
  return L.divIcon({
    className: "",
    html: `<div style="transform: rotate(${rotation}deg); font-size: 26px; line-height: 1; filter: drop-shadow(0 0 6px rgba(255,255,255,0.5));">✈</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

/** Keeps the map framed around both points as the aircraft moves. */
function AutoFrame({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length < 2) return;
    const bounds = L.latLngBounds(points);
    map.flyToBounds(bounds, { padding: [40, 40], animate: true, duration: 0.8, maxZoom: 12 });
  }, [points, map]);
  return null;
}

export default function MapView({
  homeLat,
  homeLon,
  radiusKm,
  aircraftLat,
  aircraftLon,
  headingDeg,
  className,
}: MapViewProps) {
  const points = useMemo<[number, number][]>(() => {
    const pts: [number, number][] = [[homeLat, homeLon]];
    if (aircraftLat !== undefined && aircraftLon !== undefined) pts.push([aircraftLat, aircraftLon]);
    return pts;
  }, [homeLat, homeLon, aircraftLat, aircraftLon]);

  return (
    <div className={className}>
      <MapContainer
        center={[homeLat, homeLon]}
        zoom={11}
        zoomControl={false}
        attributionControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        className="h-full w-full rounded-2xl"
      >
        <TileLayer
          className="map-dark-tiles"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Circle
          center={[homeLat, homeLon]}
          radius={radiusKm * 1000}
          pathOptions={{ color: "#0a84ff", opacity: 0.3, weight: 1.5, fillOpacity: 0.03 }}
        />
        <Marker position={[homeLat, homeLon]} icon={homeIcon} />
        {aircraftLat !== undefined && aircraftLon !== undefined && (
          <>
            <Marker position={[aircraftLat, aircraftLon]} icon={planeIcon(headingDeg)} />
            <Polyline
              positions={[
                [homeLat, homeLon],
                [aircraftLat, aircraftLon],
              ]}
              pathOptions={{ color: "#0a84ff", opacity: 0.5, weight: 2, dashArray: "4 6" }}
            />
          </>
        )}
        <AutoFrame points={points} />
      </MapContainer>
    </div>
  );
}
