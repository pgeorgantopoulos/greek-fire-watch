from src.chart import build_line_chart


def test_returns_none_with_fewer_than_two_days():
    assert build_line_chart([]) is None
    assert build_line_chart([{"date": "2026-08-01", "total": 3}]) is None


def test_builds_points_for_each_day():
    daily = [
        {"date": "2026-08-01", "total": 2},
        {"date": "2026-08-02", "total": 5},
        {"date": "2026-08-03", "total": 0},
    ]
    result = build_line_chart(daily)
    assert result is not None
    assert len(result["points"]) == 3
    assert [p["date"] for p in result["points"]] == ["2026-08-01", "2026-08-02", "2026-08-03"]
    xs = [p["x"] for p in result["points"]]
    assert xs == sorted(xs)
    for p in result["points"]:
        assert 0 <= p["y"] <= result["height"]


def test_all_zero_days_does_not_crash():
    daily = [{"date": "2026-08-01", "total": 0}, {"date": "2026-08-02", "total": 0}]
    result = build_line_chart(daily)
    assert result is not None
    assert all(p["y"] == result["plot_bottom"] for p in result["points"])
