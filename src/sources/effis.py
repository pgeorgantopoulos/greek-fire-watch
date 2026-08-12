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
import xml.etree.ElementTree as ET
from typing import Any

from shapely.geometry import shape

from . import http
from .errors import SourceSkipped

logger = logging.getLogger(__name__)

_OWS_NS = {"ows": "http://www.opengis.net/ows/1.1"}


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

    response = http.get(base_url, params=params)

    # The WFS backend reports its own errors as an OGC ows:ExceptionReport
    # body (seen returned with HTTP 400 during the 2026-08-10 EFFIS outage,
    # but OWS services are also known to send these with a 200). Pull the
    # real reason out before falling back to a generic HTTP status error, and
    # check it ahead of raise_for_status() so a non-2xx status doesn't hide
    # the more useful message.
    body = response.text
    exception_text = _extract_ows_exception(body)
    if exception_text:
        raise RuntimeError(f"EFFIS WFS service error: {exception_text}")

    response.raise_for_status()

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


def _extract_ows_exception(body: str) -> str | None:
    if not body.lstrip().startswith("<"):
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    texts = [el.text.strip() for el in root.findall(".//ows:ExceptionText", _OWS_NS) if el.text]
    return "; ".join(texts) or None


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
