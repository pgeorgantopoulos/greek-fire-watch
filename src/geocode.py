"""Reverse-geocode lat/lon detections to a Greek region/municipality name
using an offline GeoJSON boundaries dataset (point-in-polygon).

See data/boundaries/README.md — the bundled greece_regions.geojson is a
placeholder (a single polygon covering all of Greece) until a real
regions/municipalities dataset is dropped in.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape

logger = logging.getLogger(__name__)


class Geocoder:
    def __init__(self, boundaries_path: Path, name_field: str, fallback_name: str):
        self.name_field = name_field
        self.fallback_name = fallback_name
        self._regions: list[tuple[Any, str]] = []
        self._load(boundaries_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Boundaries file not found at %s — geocoding will fall back to '%s'.", path, self.fallback_name)
            return

        with open(path, encoding="utf-8") as f:
            geojson = json.load(f)

        for feature in geojson.get("features", []):
            geometry = feature.get("geometry")
            properties = feature.get("properties", {}) or {}
            name = properties.get(self.name_field)
            if not geometry or not name:
                continue
            try:
                self._regions.append((shape(geometry), name))
            except Exception:
                logger.warning("Skipping boundary feature with unparseable geometry: %s", properties)

    def lookup(self, lat: float, lon: float) -> str:
        point = Point(lon, lat)
        for polygon, name in self._regions:
            if polygon.contains(point) or polygon.touches(point):
                return name
        return self.fallback_name


def build_geocoder(config: dict[str, Any]) -> Geocoder:
    geo_cfg = config["geocoding"]
    from .config import resolve_path

    return Geocoder(
        boundaries_path=resolve_path(geo_cfg["boundaries_file"]),
        name_field=geo_cfg.get("name_field", "name"),
        fallback_name=geo_cfg.get("fallback_name", "Unknown region"),
    )
