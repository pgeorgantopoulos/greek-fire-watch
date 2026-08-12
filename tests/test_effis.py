import pytest

from src.sources import effis

# Actual body observed from the live WFS endpoint on 2026-08-12 (HTTP 400).
EXCEPTION_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<ows:ExceptionReport xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0" xml:lang="en-US" xsi:schemaLocation="http://www.opengis.net/ows/1.1 http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd">
  <ows:Exception exceptionCode="NoApplicableCode" locator="mapserv">
    <ows:ExceptionText>msOracleSpatialLayerOpen(): OracleSpatial error. Cannot create OCI Handlers. Connection failure. Check your logs and the connection string. </ows:ExceptionText>
  </ows:Exception>
</ows:ExceptionReport>"""


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        import json

        return json.loads(self.text)


def _config():
    return {
        "sources": {
            "effis": {
                "enabled": True,
                "base_url": "https://example.test/effis/ows",
                "type_name": "ms:ercc.hs_24hrs_point",
                "map_link_template": "",
            }
        },
        "region": {"bbox": {"west": 19.0, "south": 34.5, "east": 29.7, "north": 41.8}},
    }


def test_fetch_surfaces_ows_exception_text(monkeypatch):
    monkeypatch.setattr(effis.http, "get", lambda url, **kw: _FakeResponse(EXCEPTION_BODY))

    with pytest.raises(RuntimeError, match="OracleSpatial error"):
        effis.fetch(_config())


def test_fetch_parses_geojson_point_feature(monkeypatch):
    geojson = (
        '{"features": [{"geometry": {"type": "Point", "coordinates": [23.7, 38.1]}, '
        '"properties": {"lastupdate": "2026-08-12"}}]}'
    )
    monkeypatch.setattr(effis.http, "get", lambda url, **kw: _FakeResponse(geojson))

    detections = effis.fetch(_config())

    assert len(detections) == 1
    assert detections[0]["lat"] == 38.1
    assert detections[0]["lon"] == 23.7


def test_disabled_source_returns_empty_list():
    config = _config()
    config["sources"]["effis"]["enabled"] = False
    assert effis.fetch(config) == []
