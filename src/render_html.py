"""Render the daily report JSON into static HTML via Jinja2.

Produces:
  docs/index.html                — today's report (always overwritten)
  docs/archive/YYYY-MM-DD.html   — dated copy, kept
  docs/archive/index.html        — index of all archived reports
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import REPO_ROOT, resolve_path

logger = logging.getLogger(__name__)

TEMPLATES_DIR = REPO_ROOT / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def render(config: dict[str, Any], report: dict[str, Any]) -> None:
    env = _env()
    site_dir = resolve_path(config["output"]["site_dir"])
    archive_dir = site_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    report_template = env.get_template("report.html.j2")
    html = report_template.render(report=report)

    (site_dir / "index.html").write_text(html, encoding="utf-8")
    (archive_dir / f"{report['date']}.html").write_text(html, encoding="utf-8")
    logger.info("Rendered docs/index.html and docs/archive/%s.html", report["date"])

    _render_archive_index(env, config, archive_dir)


def _render_archive_index(env: Environment, config: dict[str, Any], archive_dir: Path) -> None:
    reports_dir = resolve_path(config["output"]["reports_dir"])
    dates = sorted(
        (p.stem for p in reports_dir.glob("*.json")),
        reverse=True,
    )

    index_template = env.get_template("archive_index.html.j2")
    html = index_template.render(dates=dates)
    (archive_dir / "index.html").write_text(html, encoding="utf-8")
    logger.info("Rendered docs/archive/index.html (%d reports)", len(dates))
