"""Entry point: fetch all sources, build the daily report, render the HTML site.

Usage:
    python -m src.main
"""

from __future__ import annotations

import logging

from . import build_report, render_html
from .config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config()
    report = build_report.build(config)
    render_html.render(config, report)


if __name__ == "__main__":
    main()
