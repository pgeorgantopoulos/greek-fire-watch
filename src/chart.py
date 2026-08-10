"""Server-side geometry for the small inline-SVG trend chart on the report page.

Computed in Python (not Jinja) so the scaling math is testable and the
template only has to place pre-computed coordinates.
"""

from __future__ import annotations

import math
from typing import Any

WIDTH = 640
HEIGHT = 220
PAD_LEFT = 36
PAD_RIGHT = 12
PAD_TOP = 16
PAD_BOTTOM = 28


def build_line_chart(daily: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Build chart geometry for daily detection totals. None if <2 days of data."""
    if len(daily) < 2:
        return None

    totals = [d["total"] for d in daily]
    nice_max = _nice_max(max(totals))

    plot_w = WIDTH - PAD_LEFT - PAD_RIGHT
    plot_h = HEIGHT - PAD_TOP - PAD_BOTTOM
    n = len(daily)

    def x_at(i: int) -> float:
        return PAD_LEFT + (plot_w * i / (n - 1) if n > 1 else 0)

    def y_at(value: float) -> float:
        if nice_max == 0:
            return PAD_TOP + plot_h
        return PAD_TOP + plot_h * (1 - value / nice_max)

    points = [
        {
            "x": round(x_at(i), 2),
            "y": round(y_at(d["total"]), 2),
            "date": d["date"],
            "total": d["total"],
        }
        for i, d in enumerate(daily)
    ]

    line_d = "M " + " L ".join(f"{p['x']},{p['y']}" for p in points)
    baseline_y = round(PAD_TOP + plot_h, 2)
    area_d = (
        line_d
        + f" L {points[-1]['x']},{baseline_y} L {points[0]['x']},{baseline_y} Z"
    )

    y_ticks = [
        {"y": round(y_at(v), 2), "label": str(v)}
        for v in _tick_values(nice_max)
    ]

    # Avoid crowding: show at most ~8 x-axis labels.
    label_stride = max(1, math.ceil(n / 8))
    x_ticks = [p for i, p in enumerate(points) if i % label_stride == 0 or i == n - 1]

    return {
        "width": WIDTH,
        "height": HEIGHT,
        "plot_bottom": baseline_y,
        "points": points,
        "line_d": line_d,
        "area_d": area_d,
        "y_ticks": y_ticks,
        "x_ticks": x_ticks,
    }


def _nice_max(raw_max: float) -> float:
    if raw_max <= 0:
        return 4  # still draw a few gridlines on an all-zero chart
    magnitude = 10 ** math.floor(math.log10(raw_max))
    for step in (1, 2, 4, 5, 10):
        candidate = step * magnitude
        if candidate >= raw_max:
            return candidate
    return 10 * magnitude


def _tick_values(nice_max: float) -> list[float]:
    steps = 4
    return [round(nice_max * i / steps) for i in range(steps + 1)]
