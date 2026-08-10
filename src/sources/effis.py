"""Fetch active fire data from EFFIS (European Forest Fire Information System).

EFFIS's public "Current Situation" viewer (forest-fire.emergency.copernicus.eu)
is a client-side app with no documented public data API. Its network calls
were traced to an OGC WFS service at ies-ows.jrc.ec.europa.eu/effis/ows,
layer `ercc.hs_24hrs_point` (fire hotspots, last 24h) — this is NOT an
officially documented endpoint for external use, so it may change or break
without notice. As of 2026-08-10 it was returning a backend error
("OracleSpatial... Connection failure") across all layers, i.e. an outage on
EFFIS's side, not a request-format issue.

Because we can't currently confirm the exact GeoJSON property names (the
service is down), this module stays generic about feature geometry (point or
polygon) and tries a handful of likely property name candidates.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from shapely.geometry import shape

from .errors import SourceSkipped

logger = logging.getLogger(__name__)


def fetch(config: dict[str, Any]) -> list[dict[str, Any]]:
    effis_cfg = config["sources"]["effis"]
    if not effis_cfg.get("enabled"):
        return []

    base_url = effis_cfg.get("base_url")
    type_name = effis_cfg.get("type_name")
    if not base_url or not type_name:
        raise SourceSkipped("sources.effis.base_url/type_name is not set")

    bbox = config["region"]["bbox"]
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "application/json",
        "bbox": f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']},EPSG:4326",
    }

    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()

    body = response.text
    if body.lstrip().startswith("<"):
        raise RuntimeError(f"EFFIS WFS returned a non-JSON (likely error) response: {body[:300]}")

    geojson = response.json()

    detections = []
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry")
        properties = feature.get("properties", {}) or {}
        if not geometry:
            continue

        try:
            geom = shape(geometry)
            point = geom if geom.geom_type == "Point" else geom.representative_point()
            lon, lat = point.x, point.y
        except Exception:
            logger.warning("EFFIS feature has unparseable geometry, skipping: %s", geometry)
            continue

        detections.append(
            {
                "source": "EFFIS",
                "lat": lat,
                "lon": lon,
                "acquired_at": _first_present(properties, ["lastupdate", "date", "acq_date"]),
                "confidence": properties.get("confidence"),
                "area_ha": _to_float(_first_present(properties, ["area_ha", "burnt_area_ha"])),
                "name": properties.get("name") or properties.get("place"),
                "map_link": _map_link(effis_cfg.get("map_link_template", ""), lat, lon),
                "raw": properties,
            }
        )

    return detections


def _first_present(d: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if d.get(key) not in (None, ""):
            return d[key]
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_link(template: str, lat: float, lon: float) -> str | None:
    if not template:
        return None
    return template.format(lat=lat, lon=lon)
