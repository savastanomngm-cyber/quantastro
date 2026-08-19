"""Verify intraday angle-crossing engine."""

from astroquant.intraday import (
    find_angle_crossings,
    day_character,
    trading_crossings,
    EXCHANGES,
)
from astroquant.ephemeris import jd_from_date


def test_exchanges_defined():
    for name in ["CHICAGO", "NYC", "LONDON", "TOKYO"]:
        assert name in EXCHANGES


def test_find_angle_crossings_chicago_sunrise():
    """The Sun always rises once per day → exactly one ASC crossing for Sun."""
    jd = jd_from_date(2026, 8, 19, 12.0)
    crossings = find_angle_crossings(
        jd, 41.8781, -87.6298, step_minutes=5,
        planets=["Sun"], start_hour=0, end_hour=24,
    )
    asc_crossings = [c for c in crossings if c["angle"] == "ASC"]
    dsc_crossings = [c for c in crossings if c["angle"] == "DSC"]
    # Sun rises once and sets once
    assert len(asc_crossings) == 1, f"Got {len(asc_crossings)} ASC crossings"
    assert len(dsc_crossings) == 1, f"Got {len(dsc_crossings)} DSC crossings"


def test_sunrise_time_reasonable_chicago():
    """Chicago sunrise in August ~ 11:50-12:30 UT (05:50-06:30 CDT)."""
    jd = jd_from_date(2026, 8, 19, 12.0)
    crossings = find_angle_crossings(
        jd, 41.8781, -87.6298, step_minutes=5,
        planets=["Sun"], start_hour=0, end_hour=24,
    )
    asc = [c for c in crossings if c["angle"] == "ASC"][0]
    hour = int(asc["time_ut"].split(":")[0])
    assert 10 <= hour <= 14, f"Sunrise at {asc['time_ut']} UT, expected ~11-13 UT"


def test_day_character():
    jd = jd_from_date(2026, 8, 19, 12.0)
    dc = day_character(jd, 41.8781, -87.6298, 14.5)
    assert "asc_degree" in dc
    assert "asc_sign" in dc
    assert 0 <= dc["asc_degree"] <= 360
    assert isinstance(dc["planets_on_angles"], list)


def test_trading_crossings():
    jd = jd_from_date(2026, 8, 19, 12.0)
    crossings, dc = trading_crossings(jd, "CHICAGO", step_minutes=15)
    assert isinstance(crossings, list)
    assert "asc_sign" in dc
    # All crossings should have local time
    for c in crossings:
        assert "time_local" in c