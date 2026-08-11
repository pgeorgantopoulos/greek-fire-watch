import pytest

from src.sources import firms


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def _config(base_url="https://example.test/api"):
    return {
        "sources": {
            "firms": {
                "enabled": True,
                "api_key": "test-key",
                "base_url": base_url,
                "sensor": "VIIRS_SNPP_NRT",
                "day_range": 1,
            }
        },
        "region": {"bbox": {"west": 19.0, "south": 34.5, "east": 29.7, "north": 41.8}},
    }


def test_fetch_parses_csv_rows(monkeypatch):
    csv_body = (
        "latitude,longitude,acq_date,acq_time,satellite,confidence,frp,bright_ti4,daynight\n"
        "38.1,23.7,2026-08-10,1230,N,n,12.3,330.5,D\n"
    )
    monkeypatch.setattr(firms.http, "get", lambda url, **kw: _FakeResponse(csv_body))

    detections = firms.fetch(_config())

    assert len(detections) == 1
    assert detections[0]["lat"] == 38.1
    assert detections[0]["lon"] == 23.7
    assert detections[0]["acquired_at"] == "2026-08-10T12:30:00Z"


def test_fetch_raises_on_api_error_body_instead_of_swallowing_it(monkeypatch):
    # FIRMS responds HTTP 200 with a plain-text error message (not CSV) on a
    # bad/expired key or an exceeded transaction limit. This must surface as
    # a failure so it isn't reported as a successful zero-detection day.
    monkeypatch.setattr(firms.http, "get", lambda url, **kw: _FakeResponse("Invalid MAP_KEY"))

    with pytest.raises(RuntimeError, match="Invalid MAP_KEY"):
        firms.fetch(_config())


def test_disabled_source_returns_empty_list():
    config = _config()
    config["sources"]["firms"]["enabled"] = False
    assert firms.fetch(config) == []


def test_missing_api_key_raises_source_skipped():
    config = _config()
    config["sources"]["firms"]["api_key"] = None
    with pytest.raises(firms.SourceSkipped):
        firms.fetch(config)
