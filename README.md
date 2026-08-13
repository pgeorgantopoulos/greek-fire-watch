# Greek Fire Watch

A daily-refreshed static report of active fire activity within Greek
borders, combining:

- **[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)** — near-real-time
  active fire detections from satellite (VIIRS/MODIS hotspots).
- **[EFFIS](https://effis.jrc.ec.europa.eu/)** — European Forest Fire
  Information System active fire data.
- **Greek Civil Protection RSS** — official feed, filtered to fire-related
  items.

FIRMS and EFFIS already provide their own interactive maps, so this project
doesn't try to rebuild one. Instead it produces a compact **daily report
page** — current-day summary stats, a table of individual detections
(reverse-geocoded to a Greek region/municipality), Civil Protection items,
links out to the official maps for visual follow-up — plus an **all-time
history view** (trend chart + table) built from the accumulated daily
archive, so the site shows both "what's happening today" and "how this
compares to prior days."

**Live site:** https://pgeorgantopoulos.github.io/greek-fire-watch/
**Repo:** https://github.com/pgeorgantopoulos/greek-fire-watch (public, so
GitHub Pages can serve it on the free plan)

## How it works

1. `src/sources/*.py` fetch each data source independently. A failure in one
   source doesn't block the others — the report records a per-source status:
   `ok` (fetched successfully — including a legitimate zero-detections day),
   `disabled` (turned off in `config.yaml`), `skipped: <reason>` (enabled but
   missing required config, e.g. no API key), or `error: <reason>` (ran and
   failed).
2. `src/geocode.py` reverse-geocodes each detection's lat/lon to a region
   name using an offline boundaries file (point-in-polygon).
3. `src/build_report.py` combines everything into `reports/YYYY-MM-DD.json`
   — the source of truth for that day, kept permanently.
4. `src/aggregate.py` scans the *entire* `reports/*.json` archive (not just
   today) into all-time totals — days tracked, all-time detection count,
   average/day, all-time top regions, and a per-day series.
5. `src/chart.py` turns that per-day series into inline-SVG line/area chart
   geometry (points, path strings, gridline ticks) — computed in Python so
   it's unit-testable, rather than doing the math in the template.
6. `src/render_html.py` renders `report.html.j2` **twice** (once for
   `docs/index.html` with root-relative links, once for
   `docs/archive/YYYY-MM-DD.html` with one-level-up-relative links — they're
   not byte-identical, because a page one directory deeper needs different
   relative paths) and rebuilds `docs/archive/index.html`.
7. `.github/workflows/daily-report.yml` runs the whole pipeline on a daily
   cron (`workflow_dispatch` also enabled for manual runs), commits the new
   report + rendered HTML back to `main`. GitHub Pages serves `docs/` from
   `main` on every push.

```
src/main.py
  → build_report.build()        → reports/YYYY-MM-DD.json   (per-day source of truth)
  → aggregate.build()           → all-time totals + per-day series (reads the whole archive)
  → chart.build_line_chart()    → SVG geometry for the trend chart
  → render_html.render()        → docs/index.html                  (base_path="")
                                   docs/archive/YYYY-MM-DD.html      (base_path="../")
                                   docs/archive/index.html
```

## Repo layout

```
config.yaml                  Region bbox, source URLs/keys, geocoding config
src/
  config.py                  Loads config.yaml, resolves API keys from env vars
  sources/
    firms.py                 NASA FIRMS fetcher (CSV Area API)
    effis.py                 EFFIS fetcher (OGC/WFS GeoJSON) — unofficial endpoint, see below
    civil_protection_rss.py  RSS fetcher + fire-keyword filter
    errors.py                SourceSkipped — raised for missing config, distinct from a real fetch error
  geocode.py                 Offline reverse geocoding (lat/lon -> region name)
  build_report.py            Combines sources into a daily report JSON
  aggregate.py                Scans reports/*.json into all-time totals + per-day series
  chart.py                   Pure-Python SVG geometry for the trend chart (testable, no template math)
  render_html.py             Renders report + history JSON -> static HTML via Jinja2
  main.py                    Pipeline entry point
templates/
  report.html.j2             Main report page (today's data + history section)
  archive_index.html.j2      Archive listing page
data/boundaries/             Offline boundaries GeoJSON for geocoding + Greece-only filtering (see its README)
reports/                     Daily report JSON archive (committed, append-only)
docs/                        Generated static site (GitHub Pages source: main branch, /docs)
tests/                       Unit tests: geocoding, RSS keyword filtering, chart geometry
.github/workflows/           Daily cron pipeline (daily-report.yml)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**If `python3 -m venv` fails with an `ensurepip is not available` error**
(missing the OS-level `python3-venv` package and you can't/don't want to
`apt install` it): create the venv without pip, then bootstrap pip inside it
directly — this doesn't need sudo:

```bash
python3 -m venv .venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
.venv/bin/pip install -r requirements.txt
```

### Configure data sources

`config.yaml` is wired up with real, tested endpoints for all three sources:

- **FIRMS**: uses the official
  [Area API](https://firms.modaps.eosdis.nasa.gov/api/area/csv)
  (`sources.firms`). Requires a free `MAP_KEY` from
  https://firms.modaps.eosdis.nasa.gov/api/map_key/, read from the
  `FIRMS_MAP_KEY` env var (already set as a secret on the GitHub repo for the
  Actions workflow). **Note the hostname is `firms.modaps.eosdis.nasa.gov`**
  — `firms.modaps.eosdis.gov` (missing `.nasa`) looks plausible but doesn't
  resolve at all; this was a real bug caught only once a live key was tested
  end-to-end, both locally and in CI.
- **EFFIS**: uses an OGC/WFS endpoint (`ies-ows.jrc.ec.europa.eu/effis/ows`,
  layer `ercc.hs_24hrs_point`, fire hotspots last 24h) discovered by tracing
  the network calls of the EFFIS "Current Situation" viewer app (its
  Content-Security-Policy header lists allowed API hosts) — it is **not** a
  documented public API, so treat it as unstable/subject to change without
  notice. As of 2026-08-10 it was returning a backend error
  (`OracleSpatial... Connection failure`) for *every* layer on the service —
  confirmed as a real outage on EFFIS's side (not a malformed request) by
  testing multiple layers and a `DescribeFeatureType` call. Because it's been
  down throughout development, `src/sources/effis.py`'s property-name
  guesses (`lastupdate`/`date`/`acq_date`, `area_ha`/`burnt_area_ha`, etc.)
  are **unverified against a real response** — revisit once the service is
  confirmed working.
- **Civil Protection RSS**: `https://civilprotection.gov.gr/cp_hartes.rss` —
  confirmed working end-to-end (including from GitHub Actions, after pinning
  an explicit user-agent — see Known limitations). Note this is the **daily
  fire-risk-forecast map archive** ("Ημερήσιος Χάρτης Πρόβλεψης Κινδύνου
  Πυρκαγιάς"), one item per day linking to a risk-level map image — **not**
  incident/announcement news, and items have no description text. Swap in a
  different feed URL here if a genuine announcements feed turns up later.

If a source's endpoint is unreachable, unconfigured, or errors, it's skipped
gracefully — the report records why per-source (see status states above)
rather than failing the whole pipeline.

### Boundaries data (for region names + Greece-only filtering)

`data/boundaries/greece_regions.geojson` holds the 13 Greek administrative
regions plus Mount Athos, used to label each detection's `region`.
`data/boundaries/greece_country.geojson` is Greece's real national outline,
used to drop FIRMS/EFFIS detections that fall inside the rectangular fetch
bbox but outside Greece (neighboring countries, open sea). See
`data/boundaries/README.md` for dataset provenance and how to go
finer-grained (municipality level).

### Run locally

```bash
FIRMS_MAP_KEY=your_key_here python -m src.main
```

This writes `reports/<today>.json` and renders `docs/index.html` +
`docs/archive/...`. Open `docs/index.html` in a browser to preview. Without
`FIRMS_MAP_KEY` set, the FIRMS source is skipped (reported as `skipped:
FIRMS_MAP_KEY is not set`) but the rest of the pipeline still runs.

### Run tests

```bash
pytest
```

Covers: point-in-polygon geocoding (incl. missing-boundaries-file fallback),
RSS keyword filtering (incl. disabled source), and trend-chart geometry
(incl. the <2-days and all-zero-days edge cases). Not yet covered: the
FIRMS/EFFIS fetchers themselves, or `aggregate.py` — see TODOs.

## Deployment (GitHub Pages)

**Already live.** For reference, this is how it's set up:

1. Repo is public (required — GitHub Pages needs a public repo or a
   paid plan for a private one) with Pages enabled: Settings → Pages →
   source = `main` branch, `/docs` folder.
2. `FIRMS_MAP_KEY` is set as a repo secret (Settings → Secrets and variables
   → Actions) for the workflow to use.
3. `daily-report.yml` runs the pipeline on its cron schedule (currently
   06:00 UTC daily — adjust in the workflow file) and on manual
   `workflow_dispatch`, committing the refreshed `reports/` and `docs/` back
   to `main`. Every push to `main` triggers a Pages rebuild automatically.

**Caution for anyone pushing manually:** `reports/` and `docs/` are
regenerated content, and the daily workflow commits to them too. If you run
the pipeline locally and push around the same time the scheduled workflow
runs, you can get a merge conflict on those generated files — resolve by
keeping whichever regeneration is actually correct/current (check
`source_status` and `summary.total_detections` in the conflicting
`reports/*.json` versions), not by guessing.

## Data attribution & usage limits

- NASA FIRMS: cite NASA/USGS/LANCE FIRMS per their
  [citation guidelines](https://firms.modaps.eosdis.nasa.gov/citation/); NRT
  (near-real-time) data is not validated for accuracy — see their
  disclaimer. Don't represent detections as confirmed/verified fires.
- EFFIS: cite the Joint Research Centre / Copernicus EFFIS per their terms.
  Since the API used here is unofficial/undocumented (see above), don't
  present it as an officially sanctioned integration.
- Greek Civil Protection: link back to the original item (already done in
  the news section); do not represent this project as an official source —
  it is an unofficial, best-effort aggregator, not a channel for emergency
  information. In an actual emergency, direct people to official Civil
  Protection channels (112, civilprotection.gov.gr), not this site.

## Known limitations

- **No deduplication** between FIRMS and EFFIS detections of the same
  physical fire — they're listed separately, tagged by source. A single
  fire visible to both satellites would currently count twice in totals.
- **EFFIS's WFS endpoint is undocumented/unofficial and was down throughout
  development** — schema unverified, could break silently if EFFIS changes
  their internal API.
- **Civil Protection RSS is a risk-map feed, not incident news** — doesn't
  fully satisfy "news on new fires" the way an announcements feed would.
- **feedparser's default fetch behaved differently in GitHub Actions than
  locally** (a "mismatched tag" XML error, most likely a bot-block/challenge
  page instead of the real feed) — worked around with an explicit
  browser-like `User-Agent` (`src/sources/civil_protection_rss.py`), but the
  underlying cause on the server side wasn't confirmed, so it could
  recur if the site's protection changes.
- **No health/failure alerting** — if a source errors or the daily workflow
  fails outright, the only signal is the report's status row (or GitHub's
  own Actions failure notification, if you have those on). Nothing pages
  anyone.
- **FIRMS `confidence` values are raw, not normalized** — VIIRS uses
  `l`/`n`/`h` (low/nominal/high), MODIS uses `0-100` or
  `low`/`nominal`/`high`; the report just displays whatever the API returns
  without mapping it to a consistent label.

## TODOs / Roadmap

**Data quality**
- [ ] Optionally go finer-grained than region-level boundaries (municipality)
  — see `data/boundaries/README.md` for candidate sources and required format.
- [ ] Once EFFIS's WFS service is back up, verify `src/sources/effis.py`'s
  property-name guesses against a real response and fix any that are wrong.
- [ ] Look for a genuine Civil Protection incident/announcement feed (vs.
  the current daily risk-map archive) and swap `config.yaml`'s
  `civil_protection_rss.url` if one exists.
- [ ] Normalize FIRMS `confidence` values (VIIRS l/n/h vs MODIS numeric) to
  a consistent display label.
- [ ] Deduplicate FIRMS/EFFIS detections that likely represent the same
  physical fire (e.g. by proximity + time window), or at minimum flag
  probable overlaps in the report instead of double-counting in totals.
- [ ] Consider also pulling MODIS (`MODIS_NRT`) alongside VIIRS from FIRMS
  for broader coverage — currently only `VIIRS_SNPP_NRT` is configured.

**Testing**
- [ ] Add fixture-based tests for `src/sources/firms.py` and
  `src/sources/effis.py` (capture a real response sample once available and
  assert parsing), similar to the existing RSS fixture tests.
- [ ] Add unit tests for `src/aggregate.py` (currently only `chart.py`'s
  geometry is tested, not the scanning/summing logic that feeds it).
- [ ] Add an end-to-end smoke test that runs `src.main` against recorded
  fixture responses (via `responses`/`requests-mock`) and asserts the
  rendered HTML contains expected content, catching template/rendering
  regressions that unit tests miss.

**Site / UX**
- [ ] Dark mode for the generated report page (not implemented — currently
  one fixed light theme).
- [ ] Map deep-links: `map_link_template` is configured but empty for both
  FIRMS and EFFIS in `config.yaml` — fill in real per-coordinate deep-link
  URL formats if/once available so "view on map" links actually work.
- [ ] Show the next scheduled run time somewhere on the page, so readers
  know how fresh "today's" data can be expected to be.
- [ ] A status/build badge (e.g. GitHub Actions workflow badge) in the
  README and/or on the page itself, so a broken daily run is visible at a
  glance rather than only discoverable by checking the Actions tab.

**Ops**
- [ ] Some form of failure alerting for the daily workflow (e.g. a
  notification if `daily-report.yml` fails, or if a source has errored for
  N consecutive days).
- [ ] Decide on and document a policy for what happens if the daily workflow
  and a manual local run race (see "Caution for anyone pushing manually"
  above) — right now it's manual conflict resolution.
