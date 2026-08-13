"""Combine FIRMS, EFFIS and Civil Protection RSS into a single daily report.

Each source is fetched independently and a failure in one does not prevent
the others from contributing — the report records which sources succeeded.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import resolve_path
from .geocode import build_country_boundary, build_geocoder
from .sources import civil_protection_rss, effis, firms
from .sources.errors import SourceSkipped

logger = logging.getLogger(__name__)

FETCHERS = {
    "FIRMS": firms.fetch,
    "EFFIS": effis.fetch,
}


def build(config: dict[str, Any]) -> dict[str, Any]:
    tz = ZoneInfo(config["region"].get("timezone", "UTC"))
    now = datetime.now(tz)
    report_date = now.date().isoformat()

    geocoder = build_geocoder(config)
    country = build_country_boundary(config)

    detections: list[dict[str, Any]] = []
    source_status: dict[str, str] = {}

    for name, fetcher in FETCHERS.items():
        if not _source_enabled(config, name):
            source_status[name] = "disabled"
            continue
        try:
            results = fetcher(config)
            # The fetch bbox is a rectangle over Greece, so it also picks up
            # slivers of neighboring countries and open sea — keep only
            # points that actually fall inside Greece's border.
            results = [r for r in results if country.contains(r["lat"], r["lon"])]
            for item in results:
                item["region"] = geocoder.lookup(item["lat"], item["lon"])
            detections.extend(results)
            source_status[name] = "ok"
        except SourceSkipped as exc:
            logger.warning("%s skipped: %s", name, exc)
            source_status[name] = f"skipped: {exc}"
        except Exception as exc:  # noqa: BLE001 - a bad source must not kill the report
            logger.exception("Failed to fetch %s", name)
            source_status[name] = f"error: {exc}"

    if not _source_enabled(config, "civil_protection_rss"):
        news = []
        source_status["CivilProtectionRSS"] = "disabled"
    else:
        try:
            news = civil_protection_rss.fetch(config)
            source_status["CivilProtectionRSS"] = "ok"
        except SourceSkipped as exc:
            logger.warning("CivilProtectionRSS skipped: %s", exc)
            news = []
            source_status["CivilProtectionRSS"] = f"skipped: {exc}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch Civil Protection RSS")
            news = []
            source_status["CivilProtectionRSS"] = f"error: {exc}"

    detections.sort(key=lambda d: d.get("acquired_at") or "", reverse=True)

    summary = _build_summary(detections)

    report = {
        "date": report_date,
        "generated_at": now.isoformat(),
        "region": config["region"]["name"],
        "source_status": source_status,
        "summary": summary,
        "detections": detections,
        "news": news,
    }

    _write_report(config, report_date, report)
    return report


def _source_enabled(config: dict[str, Any], key: str) -> bool:
    return bool(config.get("sources", {}).get(key.lower(), {}).get("enabled"))


def _build_summary(detections: list[dict[str, Any]]) -> dict[str, Any]:
    by_source = Counter(d["source"] for d in detections)
    by_region = Counter(d.get("region", "Unknown region") for d in detections)

    return {
        "total_detections": len(detections),
        "by_source": dict(by_source),
        "top_regions": by_region.most_common(10),
    }


def _write_report(config: dict[str, Any], report_date: str, report: dict[str, Any]) -> None:
    reports_dir = resolve_path(config["output"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)

    out_path = reports_dir / f"{report_date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("Wrote report to %s", out_path)
