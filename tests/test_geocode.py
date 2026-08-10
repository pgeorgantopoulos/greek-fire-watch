from pathlib import Path

from src.geocode import Geocoder

FIXTURE = Path(__file__).parent / "fixtures" / "sample_boundaries.geojson"


def test_lookup_inside_polygon():
    geocoder = Geocoder(FIXTURE, name_field="name", fallback_name="Unknown")
    assert geocoder.lookup(lat=0.5, lon=0.5) == "West Square"
    assert geocoder.lookup(lat=0.5, lon=2.5) == "East Square"


def test_lookup_outside_all_polygons_returns_fallback():
    geocoder = Geocoder(FIXTURE, name_field="name", fallback_name="Unknown")
    assert geocoder.lookup(lat=10.0, lon=10.0) == "Unknown"


def test_missing_boundaries_file_falls_back_gracefully(tmp_path):
    missing = tmp_path / "does_not_exist.geojson"
    geocoder = Geocoder(missing, name_field="name", fallback_name="Unknown")
    assert geocoder.lookup(lat=0.5, lon=0.5) == "Unknown"
