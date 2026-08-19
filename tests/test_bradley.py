"""Verify Bradley-style daily aspect sum."""

from astroquant.bradley import (
    bradley_index,
    bradley_empirical_index,
    bradley_interpretation,
    BRADLEY_WEIGHTS,
)
from astroquant.ephemeris import get_longitudes, jd_from_date


def test_bradley_weights_exist():
    for aspect in ["conjunction", "sextile", "square", "trine", "opposition"]:
        assert aspect in BRADLEY_WEIGHTS


def test_bradley_index_valid():
    pos = get_longitudes(jd_from_date(2026, 8, 19, 12.0))
    bi = bradley_index(pos)
    assert "total" in bi
    assert "hard_sum" in bi
    assert "soft_sum" in bi
    assert isinstance(bi["aspect_count"], int)
    assert bi["aspect_count"] > 0


def test_bradley_synthetic_known():
    # Two planets exactly conjunct → +3 weight
    pos = {"A": 0.0, "B": 0.0}
    bi = bradley_index(pos, planets=["A", "B"])
    assert bi["total"] == 3.0

    # Two planets exactly opposite → -1.5 weight
    pos2 = {"A": 0.0, "B": 180.0}
    bi2 = bradley_index(pos2, planets=["A", "B"])
    assert bi2["total"] == -1.5


def test_bradley_empirical():
    pos = get_longitudes(jd_from_date(2026, 8, 19, 12.0))
    custom = {"conjunction": 1.0, "opposition": -1.0, "square": -0.5}
    val = bradley_empirical_index(pos, custom)
    assert isinstance(val, float)


def test_interpretation_directional():
    assert "BEARISH" in bradley_interpretation(-10.0)
    assert "BULLISH" in bradley_interpretation(10.0)


def test_bradley_on_crash_dates():
    """Bradley index should be computable for historical crash dates."""
    for date in [(1929, 10, 24), (1987, 10, 19), (2008, 10, 1)]:
        pos = get_longitudes(jd_from_date(*date, 12.0))
        bi = bradley_index(pos)
        assert isinstance(bi["total"], float)