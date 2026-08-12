"""Fetch and filter the Greek Civil Protection RSS feed for fire-related news.

The feed URL is a placeholder in config.yaml (sources.civil_protection_rss.url) —
fill it in once confirmed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from . import http
from .errors import SourceSkipped

logger = logging.getLogger(__name__)


def fetch(config: dict[str, Any]) -> list[dict[str, Any]]:
    rss_cfg = config["sources"]["civil_protection_rss"]
    if not rss_cfg.get("enabled"):
        return []

    url = rss_cfg.get("url")
    if not url:
        raise SourceSkipped("sources.civil_protection_rss.url is not set")

    if url.startswith("http://") or url.startswith("https://"):
        # feedparser's own fetch path has no timeout and can hang
        # indefinitely on an unresponsive server — fetch through the shared
        # bounded-timeout/retry session instead and hand it the bytes.
        # Some sites respond differently (or block) feedparser's default
        # urllib-based user-agent than a browser-like one — the shared
        # session pins an explicit UA rather than risk an opaque XML parse
        # failure caused by a block/challenge page instead of the feed.
        response = http.get(url)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            # raise_for_status() drops the response body, so a block/challenge
            # page (WAF, geoblock, permission-denied) looks identical to any
            # other 4xx/5xx in the logs. Keep a snippet so a future failure
            # (e.g. this only reproduces from the GitHub Actions runner IP,
            # not from a browser or this dev machine — confirmed 2026-08-12)
            # can actually be told apart from a real config/URL problem.
            snippet = response.text[:300].strip().replace("\n", " ")
            detail = f" — response body: {snippet}" if snippet else ""
            raise RuntimeError(f"Failed to fetch Civil Protection RSS ({exc}){detail}") from exc
        feed = feedparser.parse(response.content)
    else:
        feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        status = feed.get("status")
        raise RuntimeError(
            f"Failed to parse Civil Protection RSS feed (HTTP status={status}): {feed.get('bozo_exception')}"
        )

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
