# Greek Fire Watch

A daily-refreshed static report of active fire activity within Greek
borders, combining:

- **[NASA FIRMS](https://firms.modaps.eosdis.gov/)** — near-real-time active
  fire detections (satellite hotspots).
- **[EFFIS](https://effis.jrc.ec.europa.eu/)** — European Forest Fire
  Information System active fire data.
- **Greek Civil Protection RSS** — official announcements, filtered to
  fire-related items.

FRIMS and EFFIS already provide their own interactive maps, so this project
doesn't try to rebuild one. Instead it produces a compact **daily report
page**: summary stats, a table of individual detections (reverse-geocoded to
a Greek region/municipality), Civil Protection news, and links out to the
official maps for visual follow-up.

## How it works

1. `src/sources/*.py` fetch each data source independently. A failure in one
   source doesn't block the others — the report records per-source status.
2. `src/geocode.py` reverse-geocodes each detection's lat/lon to a region
   name using an offline boundaries file (point-in-polygon).
3. `src/build_report.py` combines everything into `reports/YYYY-MM-DD.json`.
4. `src/render_html.py` renders that JSON into `docs/index.html` (today) and
   `docs/archive/YYYY-MM-DD.html` (kept), plus an archive index.
5. `.github/workflows/daily-report.yml` runs the whole pipeline on a daily
   cron, commits the new report + rendered HTML.

```
src/main.py  →  build_report.build()  →  reports/YYYY-MM-DD.json
                                      ↓
                        render_html.render()  →  docs/index.html
                                                  docs/archive/YYYY-MM-DD.html
                                                  docs/archive/index.html
```

## Repo layout

```
config.yaml                  Region bbox, source URLs/keys, geocoding config
src/
  config.py                  Loads config.yaml, resolves API keys from env vars
  sources/
    firms.py                 NASA FIRMS fetcher (CSV API)
    effis.py                 EFFIS fetcher (GeoJSON)
    civil_protection_rss.py  RSS fetcher + fire-keyword filter
  geocode.py                 Offline reverse geocoding (lat/lon -> region name)
  build_report.py            Combines sources into a daily report JSON
  render_html.py             Renders report JSON -> static HTML via Jinja2
  main.py                    Pipeline entry point
templates/                   Jinja2 HTML templates
data/boundaries/             Offline boundaries GeoJSON for geocoding (see its README)
reports/                     Daily report JSON archive (committed)
docs/                        Generated static site (GitHub Pages source)
tests/                       Unit tests for geocoding and RSS filtering
.github/workflows/           Daily cron pipeline
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure data sources

`config.yaml` is wired up with real endpoints for all three sources:

- **FIRMS**: uses the official
  [Area API](https://firms.modaps.eosdis.gov/api/area/csv) (`sources.firms`).
  Requires a free `MAP_KEY` from https://firms.modaps.eosdis.gov/api/map_key/,
  set as the `FIRMS_MAP_KEY` env var. (The interactive map at
  `firms.modaps.eosdis.nasa.gov/map/...` is just the viewer — it's not the
  data API and doesn't need a key.)
- **EFFIS**: uses an OGC/WFS endpoint (`ies-ows.jrc.ec.europa.eu/effis/ows`,
  layer `ercc.hs_24hrs_point`) discovered by tracing the network calls of the
  EFFIS "Current Situation" viewer app — it isn't a documented public API, so
  treat it as unstable/subject to change. As of 2026-08-10 it was returning a
  backend error (`OracleSpatial... Connection failure`) for every layer, an
  outage on EFFIS's side. Because of that, `src/sources/effis.py` couldn't be
  verified against a real response — its property-name guesses
  (`lastupdate`/`date`/`acq_date`, `area_ha`/`burnt_area_ha`, etc.) should be
  revisited once the service is confirmed working.
- **Civil Protection RSS**: `https://civilprotection.gov.gr/cp_hartes.rss` —
  confirmed working, but note this is the **daily fire-risk-forecast map
  archive** ("Ημερήσιος Χάρτης Πρόβλεψης Κινδύνου Πυρκαγιάς"), one item/day
  linking to a risk-map image — not incident/announcement news. There's no
  description text on these items. Swap in a different feed URL here if an
  actual announcements feed turns up later.

If a source's endpoint is unreachable or errors, it's skipped gracefully
(logged as `disabled`/`error` in the report's status row) rather than failing
the whole pipeline.

### Boundaries data (for region names)

`data/boundaries/greece_regions.geojson` currently ships as a **placeholder**
(a single box labeled "Greece") — see `data/boundaries/README.md` for how to
replace it with real Greek administrative boundaries so detections
reverse-geocode to actual region/municipality names.

### Run locally

```bash
python -m src.main
```

This writes `reports/<today>.json` and renders `docs/index.html`. Open
`docs/index.html` in a browser to preview.

### Run tests

```bash
pytest
```

## Deployment (GitHub Pages)

Once this becomes a git repo with a GitHub remote:

1. Push, then in repo Settings → Pages, set source to "Deploy from a branch",
   branch `main`, folder `/docs`.
2. Add `FIRMS_MAP_KEY` (and any other secrets) under Settings → Secrets and
   variables → Actions.
3. The `daily-report` workflow runs on a daily cron (`workflow_dispatch` is
   also enabled for manual runs) and commits the refreshed `reports/` and
   `docs/` back to `main`.

## Data attribution & usage limits

- NASA FIRMS: cite NASA/USGS/LANCE FIRMS per their
  [citation guidelines](https://firms.modaps.eosdis.gov/citation/); NRT data
  is not validated for accuracy — see their disclaimer.
- EFFIS: cite the Joint Research Centre / Copernicus EFFIS per their terms.
- Greek Civil Protection: link back to the original announcement (already
  done in the news section); do not represent this project as an official
  source.

Fill in exact citation text once source URLs are finalized.

## Known limitations / roadmap

- No deduplication between FIRMS and EFFIS detections of the same fire —
  they're listed separately, tagged by source.
- Boundaries dataset is a placeholder until replaced (see above).
- EFFIS's WFS endpoint is undocumented/unofficial and was down during
  development — its response schema (property names) is unverified; revisit
  `src/sources/effis.py` once it's confirmed reachable.
- Civil Protection RSS currently points at a daily risk-map feed, not an
  incident-news feed — consider swapping in a proper announcements feed if
  one is found.
- No automated tests yet for the FIRMS/EFFIS fetchers themselves (only
  geocoding and RSS filtering) since they depend on live endpoints — worth
  adding fixture-based tests once real response samples are available.
