"""Fetch active fire detections from NASA FIRMS for the configured bounding box.

API docs: https://firms.modaps.eosdis.gov/api/
Requires a free MAP_KEY (env var configured via sources.firms.api_key_env in config.yaml).
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def fetch(config: dict[str, Any]) -> list[dict[str, Any]]:
    firms_cfg = config["sources"]["firms"]
    if not firms_cfg.get("enabled"):
        return []

    api_key = firms_cfg.get("api_key")
    if not api_key:
        logger.warning(
            "FIRMS source enabled but %s is not set — skipping.",
            firms_cfg.get("api_key_env", "FIRMS_MAP_KEY"),
        )
        return []

    bbox = config["region"]["bbox"]
    area = f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"
    sensor = firms_cfg.get("sensor", "VIIRS_SNPP_NRT")
    day_range = firms_cfg.get("day_range", 1)

    url = f"{firms_cfg['base_url']}/{api_key}/{sensor}/{area}/{day_range}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # FIRMS returns a one-line error message (not CSV) on bad key/params.
    if "Invalid" in response.text[:200] or "Error" in response.text[:200]:
        logger.warning("FIRMS API returned an error: %s", response.text[:200])
        return []

    reader = csv.DictReader(io.StringIO(response.text))
    detections = []
    for row in reader:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (KeyError, ValueError):
            continue

        acq_date = row.get("acq_date", "")
        acq_time = row.get("acq_time", "").zfill(4) if row.get("acq_time") else ""
        acquired_at = f"{acq_date}T{acq_time[:2]}:{acq_time[2:]}:00Z" if acq_date and acq_time else acq_date

        detections.append(
            {
                "source": "FIRMS",
                "sensor": row.get("satellite") or sensor,
                "lat": lat,
                "lon": lon,
                "acquired_at": acquired_at,
                "confidence": row.get("confidence"),
                "frp": _to_float(row.get("frp")),
                "brightness": _to_float(row.get("bright_ti4") or row.get("brightness")),
                "daynight": row.get("daynight"),
                "map_link": _map_link(firms_cfg.get("map_link_template", ""), lat, lon),
                "raw": row,
            }
        )

    return detections


def _to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _map_link(template: str, lat: float, lon: float) -> str | None:
    if not template:
        return None
    return template.format(lat=lat, lon=lon)
