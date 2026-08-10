"""Build an all-time aggregate view (past + current) from the daily report archive."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .config import resolve_path


def build(config: dict[str, Any]) -> dict[str, Any]:
    reports_dir = resolve_path(config["output"]["reports_dir"])

    daily: list[dict[str, Any]] = []
    all_time_by_source: Counter[str] = Counter()
    all_time_by_region: Counter[str] = Counter()

    for path in sorted(reports_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            day_report = json.load(f)

        detections = day_report.get("detections", [])
        by_source = Counter(d["source"] for d in detections)
        by_region = Counter(d.get("region", "Unknown region") for d in detections)

        daily.append(
            {
                "date": day_report["date"],
                "total": len(detections),
                "by_source": dict(by_source),
                "news_count": len(day_report.get("news", [])),
            }
        )
        all_time_by_source.update(by_source)
        all_time_by_region.update(by_region)

    days_tracked = len(daily)
    all_time_total = sum(d["total"] for d in daily)
    avg_per_day = round(all_time_total / days_tracked, 1) if days_tracked else 0

    return {
        "daily": daily,
        "days_tracked": days_tracked,
        "all_time_total": all_time_total,
        "avg_per_day": avg_per_day,
        "all_time_by_source": dict(all_time_by_source),
        "all_time_top_regions": all_time_by_region.most_common(10),
    }
