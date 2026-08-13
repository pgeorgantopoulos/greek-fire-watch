# Boundaries data

`greece_country.geojson` is the real national outline of Greece (single
country, `MultiPolygon`, ~130 islands+mainland), used to filter out
FIRMS/EFFIS detections that fall inside the rectangular fetch bounding box
but outside Greece itself (e.g. Albania, North Macedonia, Bulgaria, Turkey,
or open sea — a rectangle over Greece unavoidably covers slivers of all of
these). Source: [geoBoundaries](https://www.geoboundaries.org/) `GRC-ADM0`,
full-resolution geometry, CC BY 4.0 (EuroGeoGraphics / data.humdata.org).
`CountryBoundary` (src/geocode.py) applies a small (~3km) buffer around it to
absorb coastline-precision noise so real coastal/harbor detections aren't
misclassified as foreign — neighboring countries' mainlands are tens to
hundreds of km further out, so this doesn't risk admitting them. See
`geocoding.country_boundary_file` in `config.yaml`.

`greece_regions.geojson` is currently a **placeholder**: a single rectangular
polygon covering the whole Greece bounding box, labeled accordingly. Every
detection will reverse-geocode to that one label until this file is replaced
with a real dataset.

To get proper region/municipality names, replace this file with a GeoJSON
`FeatureCollection` of polygons for Greece, for example:

- Greek official administrative boundaries ("Καλλικράτης" regions/municipalities)
  from [geodata.gov.gr](https://geodata.gov.gr/) (search for "Όρια Δήμων" / "Όρια
  Περιφερειών").
- [GADM](https://gadm.org/download_country.html) level-1 (regions) or level-2
  (municipalities) boundaries for Greece.
- [Natural Earth](https://www.naturalearthdata.com/) admin-1 states/provinces,
  filtered to Greece (coarser, region-level only).

Requirements for the replacement file:

- Valid GeoJSON `FeatureCollection`, geometries in WGS84 (lon/lat), `Polygon`
  or `MultiPolygon`.
- Each feature's `properties` must include a name field matching
  `geocoding.name_field` in `config.yaml` (defaults to `name`) — rename a
  column/property or update the config to match whatever field the dataset
  uses (e.g. `NAME_1`, `shapeName`, `dimos_name`).

If the dataset has two levels (region + municipality), you can either load
two boundary files and extend `Geocoder` to look up both, or pick the
granularity you want for v1 and keep it to one file.
