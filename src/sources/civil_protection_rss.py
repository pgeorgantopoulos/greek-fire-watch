"""Fetch and filter the Greek Civil Protection RSS feed for fire-related news.

The feed URL is a placeholder in config.yaml (sources.civil_protection_rss.url) —
fill it in once confirmed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser

from .errors import SourceSkipped

logger = logging.getLogger(__name__)


def fetch(config: dict[str, Any]) -> list[dict[str, Any]]:
    rss_cfg = config["sources"]["civil_protection_rss"]
    if not rss_cfg.get("enabled"):
        return []

    url = rss_cfg.get("url")
    if not url:
        raise SourceSkipped("sources.civil_protection_rss.url is not set")

    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Failed to parse Civil Protection RSS feed: {feed.get('bozo_exception')}")

    keywords = [k.lower() for k in rss_cfg.get("keyword_filter", [])]
    max_items = rss_cfg.get("max_items", 30)

    items = []
    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")

        if keywords and not _matches_keywords(title, summary, keywords):
            continue

        published = entry.get("published_parsed")
        published_iso = (
            datetime(*published[:6], tzinfo=timezone.utc).isoformat() if published else None
        )

        items.append(
            {
                "title": title,
                "summary": summary,
                "link": entry.get("link"),
                "published_at": published_iso,
            }
        )

        if len(items) >= max_items:
            break

    return items


def _matches_keywords(title: str, summary: str, keywords: list[str]) -> bool:
    haystack = f"{title} {summary}".lower()
    return any(keyword in haystack for keyword in keywords)
