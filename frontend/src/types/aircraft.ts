export interface AirportInfo {
  icao: string | null;
  iata: string | null;
  name: string | null;
  city: string | null;
  country: string | null;
}

export interface AircraftPhoto {
  url: string | null;
  thumbnail_url: string | null;
  photographer: string | null;
  source: string | null;
}

export interface AirlineInfo {
  name: string | null;
  icao: string | null;
  iata: string | null;
  logo_url: string | null;
}

export interface SelectedAircraft {
  icao24: string;
  callsign: string | null;
  flight_number: string | null;
  registration: string | null;

  manufacturer: string | null;
  model: string | null;
  is_military: boolean;
  is_helicopter: boolean;

  airline: AirlineInfo;
  origin: AirportInfo;
  destination: AirportInfo;
  photo: AircraftPhoto;

  latitude: number;
  longitude: number;
  altitude_ft: number | null;
  ground_speed_kt: number | null;
  heading_deg: number | null;
  vertical_rate_fpm: number | null;

  distance_km: number;
  bearing_from_home_deg: number;
  is_approaching: boolean;
  eta_seconds: number | null;

  summary: string;
  last_updated: string;
}

export interface HomeLocation {
  latitude: number;
  longitude: number;
  radius_km: number;
}

export interface OverheadResponse {
  home: HomeLocation;
  aircraft: SelectedAircraft | null;
  candidate_count: number;
  server_time: string;
  provider: string;
  provider_ok: boolean;
  message: string | null;
}

export interface ConfigResponse {
  home: HomeLocation;
  poll_interval_seconds: number;
  provider: string;
}
