from pathlib import Path

import pytest
import requests

from src.sources import civil_protection_rss

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"


def _config(keyword_filter):
    return {
        "sources": {
            "civil_protection_rss": {
                "enabled": True,
                "url": str(FIXTURE),
                "keyword_filter": keyword_filter,
                "max_items": 30,
            }
        }
    }


def test_keyword_filter_keeps_only_fire_related_items():
    items = civil_protection_rss.fetch(_config(["πυρκαγιά"]))
    assert len(items) == 1
    assert "πυρκαγιά" in items[0]["title"].lower() or "πυρκαγιά" in items[0]["title"]


def test_empty_keyword_filter_keeps_all_items():
    items = civil_protection_rss.fetch(_config([]))
    assert len(items) == 2


def test_disabled_source_returns_empty_list():
    config = _config([])
    config["sources"]["civil_protection_rss"]["enabled"] = False
    assert civil_protection_rss.fetch(config) == []


class _FakeForbiddenResponse:
    status_code = 403
    text = "<html><body>Access Denied</body></html>"

    def raise_for_status(self):
        raise requests.HTTPError("403 Client Error: Forbidden for url: https://example.test/feed.rss")


def test_http_error_includes_response_body_snippet(monkeypatch):
    monkeypatch.setattr(civil_protection_rss.http, "get", lambda url, **kw: _FakeForbiddenResponse())

    config = _config([])
    config["sources"]["civil_protection_rss"]["url"] = "https://example.test/feed.rss"

    with pytest.raises(RuntimeError, match="Access Denied"):
        civil_protection_rss.fetch(config)
