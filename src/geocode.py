"""Reverse-geocode lat/lon detections to a Greek region/municipality name
using an offline GeoJSON boundaries dataset (point-in-polygon), and check
whether a point actually falls inside Greece's national border.

See data/boundaries/README.md — the bundled greece_regions.geojson is a
placeholder (a single polygon covering all of Greece) until a real
regions/municipalities dataset is dropped in. greece_country.geojson is the
real national outline, used only to filter detections down to Greece.
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


class CountryBoundary:
    """Point-in-polygon check against Greece's actual national border.

    Used to drop FIRMS/EFFIS detections that fall inside the rectangular
    fetch bounding box but outside Greece (neighboring countries, open sea).
    Fails open (contains() -> True) if no boundary data is loaded, so a
    missing/misconfigured file disables filtering rather than dropping every
    detection.
    """

    # Degrees of buffer applied around the loaded polygons (~3km at Greece's
    # latitude) to absorb coastline-precision noise in the boundary dataset
    # and detection geolocation — without it, real coastal/harbor points can
    # land just outside the mapped shoreline and be misclassified as foreign.
    # Neighboring countries' mainland points are tens to hundreds of km away,
    # so this margin doesn't risk admitting them.
    BUFFER_DEGREES = 0.03

    def __init__(self, boundaries_path: Path):
        self._polygons: list[Any] = []
        self._load(boundaries_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Country boundary file not found at %s — Greece-only filtering is disabled.", path)
            return

        with open(path, encoding="utf-8") as f:
            geojson = json.load(f)

        for feature in geojson.get("features", []):
            geometry = feature.get("geometry")
            if not geometry:
                continue
            try:
                self._polygons.append(shape(geometry).buffer(self.BUFFER_DEGREES))
            except Exception:
                logger.warning("Skipping country boundary feature with unparseable geometry")

    def contains(self, lat: float, lon: float) -> bool:
        if not self._polygons:
            return True
        point = Point(lon, lat)
        return any(polygon.contains(point) or polygon.touches(point) for polygon in self._polygons)


def build_country_boundary(config: dict[str, Any]) -> CountryBoundary:
    geo_cfg = config["geocoding"]
    from .config import resolve_path

    return CountryBoundary(boundaries_path=resolve_path(geo_cfg["country_boundary_file"]))
