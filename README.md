# Overhead ✈️

A modern, touch-friendly display that shows what's flying over your home
right now — Apple-style dark UI, large typography, smooth transitions.
Point it at a wall-mounted iPad, an old MacBook, or a kiosk touchscreen and
let it tell you what just went overhead.

> "easyJet Airbus A320neo approaching Heathrow from Barcelona. Passing
> overhead in approximately 42 seconds."

---

## Contents

- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Configuration reference](#configuration-reference)
- [Choosing an ADS-B provider](#choosing-an-adsb-provider)
- [Data sources & attribution](#data-sources--attribution)
- [Screenshots](#screenshots)
- [Roadmap / extension points](#roadmap--extension-points)
- [Troubleshooting](#troubleshooting)

---

## How it works

```
┌────────────────┐   poll every N sec   ┌─────────────────────┐
│  ADS-B provider │ ───────────────────▶ │  FastAPI backend     │
│ adsb.fi /        │                      │  - selection logic   │
│ adsbexchange /   │                      │  - metadata lookups  │
│ opensky          │                      │  - SQLite history    │
└────────────────┘                       └──────────┬──────────┘
                                                     │ WebSocket
                                                     │ (REST fallback)
                                          ┌──────────▼──────────┐
                                          │  React frontend      │
                                          │  dark, full-screen   │
                                          │  Apple-style display │
                                          └──────────────────────┘
```

Every `POLL_INTERVAL_SECONDS` (default 4s), the backend:

1. Fetches all aircraft currently within `RADIUS_KM` of your home from the
   configured ADS-B provider.
2. Scores every candidate: aircraft **heading towards** your home always
   beat aircraft heading away, and within each group the **closest** wins.
   This keeps the display stable — once a plane "wins" a pass, it keeps the
   screen until it's gone, rather than flickering between candidates.
3. Enriches the winner with airline name & logo, aircraft manufacturer/model,
   registration, route (origin/destination), and a photo — pulling from
   free public sources and caching the results (metadata rarely changes, so
   there's no need to hit these APIs repeatedly for the same aircraft).
4. Builds a natural-language summary sentence.
5. Pushes the result to any connected frontend over WebSocket (falling back
   to REST polling automatically if the socket can't connect).
6. Records the sighting to SQLite for future history/stats features.

If nothing is within range, the frontend shows an idle screen with a subtle
world map, the current time, and "No aircraft currently overhead."

If the upstream ADS-B API is temporarily unreachable, the backend keeps
serving the last known aircraft (flagged as stale) rather than blanking the
screen — see `AircraftTracker._poll_once` in `backend/app/services/tracker.py`.

---

## Project structure

```
overhead/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app + lifespan (starts the tracker)
│   │   ├── config.py              # env-driven Settings (pydantic-settings)
│   │   ├── database.py            # SQLAlchemy engine + Sighting model
│   │   ├── schemas.py             # API response models
│   │   ├── data/airlines.json     # extensible airline reference table
│   │   ├── services/
│   │   │   ├── adsb.py            # adsb.fi / ADS-B Exchange / OpenSky clients
│   │   │   ├── geo.py             # distance / bearing / ETA math
│   │   │   ├── selection.py       # candidate scoring & picking
│   │   │   ├── summary.py         # natural-language headline builder
│   │   │   ├── aircraft_lookup.py # registration/type/route lookup (hexdb.io)
│   │   │   ├── airline.py         # airline name + logo resolution
│   │   │   ├── photos.py          # PlaneSpotters photo lookup + caching
│   │   │   ├── cache.py           # tiny JSON TTL cache
│   │   │   └── tracker.py         # background polling orchestrator
│   │   └── routers/aircraft.py    # REST + WebSocket endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AircraftDisplay.tsx  # main "hero" view
│   │   │   ├── SummaryHeadline.tsx
│   │   │   ├── InfoTile.tsx
│   │   │   ├── MapView.tsx          # Leaflet mini-map
│   │   │   └── IdleScreen.tsx
│   │   ├── hooks/useAircraftData.ts # WebSocket + REST-fallback data hook
│   │   ├── types/aircraft.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── nginx.conf                  # prod reverse proxy for /api and /ws
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

The backend and frontend are fully decoupled — the frontend only talks to
`/api/*` and `/ws/*`, so you can redeploy, scale, or replace either half
independently.

---

## Quick start (Docker)

**Prerequisites:** Docker + Docker Compose.

1. Clone the repo and copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your home coordinates:

   ```dotenv
   HOME_LAT=51.5074
   HOME_LON=-0.1278
   RADIUS_KM=5.0
   ```

   (Tip: right-click your home on Google Maps and copy the coordinates, or
   use [Wikipedia's GeoHack](https://geohack.toolforge.org/).)

3. Build and start everything:

   ```bash
   docker compose up --build -d
   ```

4. Open the display:

   ```
   http://localhost:8080
   ```

   On a touchscreen or MacBook, open that URL in full-screen /
   kiosk mode (e.g. Safari's "Add to Dock" full-screen mode, or Chrome with
   `--kiosk http://localhost:8080`).

The backend API is also exposed directly on `http://localhost:8000` if you
want to inspect `/api/overhead` or `/api/health` while debugging.

---

## Local development

Running the two halves natively (with hot reload) is faster while
iterating on the UI or backend logic.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # if you haven't already
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite's dev server proxies `/api` and `/ws` to `http://localhost:8000` (see
`vite.config.ts`), so open `http://localhost:5173` and it'll talk straight
to your locally running backend.

---

## Configuration reference

All configuration lives in environment variables, read by
`backend/app/config.py`. Copy `.env.example` to `.env` and adjust as
needed — no code changes required.

| Variable | Default | Description |
|---|---|---|
| `HOME_LAT` / `HOME_LON` | London | Your home coordinates, decimal degrees |
| `RADIUS_KM` | `5.0` | Search radius around home |
| `ADSB_PROVIDER` | `adsbfi` | `adsbfi`, `adsbexchange`, or `opensky` |
| `ADSBEXCHANGE_API_KEY` | — | RapidAPI key, only if using `adsbexchange` |
| `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` | — | Optional OAuth2 creds for higher OpenSky limits |
| `POLL_INTERVAL_SECONDS` | `4` | How often to poll the ADS-B provider |
| `AIRCRAFT_STALE_SECONDS` | `20` | How long to trust a cached position before considering it stale |
| `MIN_ALTITUDE_FT` | `0` | Set > 0 to ignore very low-altitude / taxiing aircraft |
| `APPROACH_BONUS_THRESHOLD_DEG` | `30` | Heading tolerance for "approaching home" |
| `ENABLE_PHOTO_LOOKUP` | `true` | Disable to skip PlaneSpotters photo calls entirely |
| `LOG_LEVEL` | `INFO` | Standard Python logging level |
| `CORS_ORIGINS` | `["*"]` | JSON list of allowed origins |

---

## Choosing an ADS-B provider

| Provider | Key required? | Notes |
|---|---|---|
| **adsb.fi** (default) | No | Free, community-run, generous limits. Best default for personal use. |
| **ADS-B Exchange** | Yes (RapidAPI) | Widest coverage including many aircraft that opt out of other feeds; requires a paid/free RapidAPI subscription. |
| **OpenSky Network** | Optional | Free anonymous access works but is rate-limited; register a free client ID/secret at [opensky-network.org](https://opensky-network.org/my-opensky) for higher limits. |

Switch providers any time by changing `ADSB_PROVIDER` in `.env` and
restarting the backend — no code changes needed thanks to the
`AdsbProvider` abstraction in `backend/app/services/adsb.py`.

---

## Data sources & attribution

- **Live positions:** [adsb.fi](https://adsb.fi) / [ADS-B Exchange](https://www.adsbexchange.com) / [OpenSky Network](https://opensky-network.org)
- **Aircraft & route metadata:** [hexdb.io](https://hexdb.io)
- **Aircraft photos:** [PlaneSpotters.net](https://www.planespotters.net) (photographer credited in the UI, as required by their terms)
- **Airline logos:** [AirHex](https://airhex.com) public logo CDN
- **Map tiles:** [OpenStreetMap](https://www.openstreetmap.org) contributors

Please respect each provider's terms of use and rate limits, especially if
you fork this for a public-facing deployment rather than a single personal
display.

---

## Screenshots

> This repo ships as source only — build and run it locally (see
> [Quick start](#quick-start-docker)) to see it live. Once running, the two
> states you'll see are:
>
> - **Aircraft overhead:** large photo, airline logo, natural-language
>   headline, route card, mini-map, and a row of stat tiles (distance,
>   altitude, speed, heading, ETA).
> - **Idle screen:** large clock, faint world map backdrop, and "No
>   aircraft currently overhead."
>
> Feel free to add your own screenshots to `docs/` and link them here once
> you have it running over your house.

---

## Roadmap / extension points

The codebase is deliberately structured so these are additive, not
rewrites:

- **Aircraft history** — `Sighting` rows are already recorded in SQLite on
  every pass (`backend/app/database.py`); add a `/api/history` endpoint and
  a history view.
- **Military aircraft alerts** — `AircraftLookupService.looks_military()`
  already flags these per-candidate; hook a notification (push, webhook,
  sound) into `AircraftTracker._poll_once`.
- **Helicopter alerts** — same pattern via `looks_helicopter()`.
- **Favourite airlines** — add a `favourite_airlines` setting and boost
  those candidates in `services/selection.py`.
- **Statistics dashboard** — query the `sightings` table (busiest hours,
  most common airlines/types, closest passes).
- **Home Assistant integration** — the backend already exposes clean JSON
  over REST/WebSocket; add an MQTT publisher alongside the WebSocket push
  in `routers/aircraft.py`.
- **Full-screen kiosk mode** — the frontend already has no browser chrome
  dependencies; wrap it in `chromium --kiosk` or an iPad Guided Access
  profile pointed at the deployed URL.
- **Audio announcements** — call the Web Speech API (`speechSynthesis`)
  with `aircraft.summary` whenever a new `icao24` appears in `App.tsx`.
- **Weather overlay** — the map component (`MapView.tsx`) is a normal
  `react-leaflet` map; add a weather tile layer or a small corner widget.

---

## Troubleshooting

- **Idle screen never changes, even though planes are clearly overhead** —
  check `docker compose logs backend`. A common cause is an incorrect
  `HOME_LAT`/`HOME_LON` (swapped, or wrong sign for West/South), or a
  `RADIUS_KM` that's too small for your local traffic altitude.
- **"Live data temporarily unavailable" message** — the configured
  provider is rate-limiting or unreachable. The backend keeps showing the
  last known aircraft; it'll recover automatically on the next successful
  poll. Consider switching providers (see above) if this persists.
- **No photos ever appear** — some registrations simply have no photo on
  PlaneSpotters, especially private/GA aircraft. This is expected and the
  UI falls back to a plane glyph.
- **WebSocket doesn't connect behind a reverse proxy** — the frontend
  automatically falls back to REST polling every 4 seconds, so the display
  keeps working; just make sure your proxy forwards `Upgrade`/`Connection`
  headers for `/ws/` if you want the lower-latency socket path (see
  `frontend/nginx.conf` for a working example).
