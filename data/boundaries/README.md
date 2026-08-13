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

`greece_regions.geojson` holds the 13 Greek administrative regions
("Περιφέρειες") plus Mount Athos (14 features). Source:
[geoBoundaries](https://www.geoboundaries.org/) `GRC-ADM2`, CC BY 4.0
(EuroGeoGraphics / data.humdata.org). The dataset's `shapeName` values are
Greeklish transliterations (and one, "Anatolikis Makedonias kai Thr*", is
truncated in the source itself) — `properties.name` on each feature has been
rewritten to the standard English region name (e.g. "Attica", "Central
Macedonia") so `geocoding.name_field: name` in `config.yaml` resolves
cleanly. `Geocoder` (src/geocode.py) applies the same ~3km buffer as
`CountryBoundary` to absorb border-precision noise between adjacent regions.

To go finer-grained (municipality level), replace this file with a GeoJSON
`FeatureCollection` of polygons for Greece, for example:

- Greek official administrative boundaries ("Καλλικράτης" municipalities)
  from [geodata.gov.gr](https://geodata.gov.gr/) (search for "Όρια Δήμων").
- [geoBoundaries](https://www.geoboundaries.org/) `GRC-ADM3` (326 municipalities).
- [GADM](https://gadm.org/download_country.html) level-2 boundaries for Greece.

Requirements for the replacement file:

- Valid GeoJSON `FeatureCollection`, geometries in WGS84 (lon/lat), `Polygon`
  or `MultiPolygon`.
- Each feature's `properties` must include a name field matching
  `geocoding.name_field` in `config.yaml` (defaults to `name`) — rename a
  column/property or update the config to match whatever field the dataset
  uses (e.g. `NAME_1`, `shapeName`, `dimos_name`).
