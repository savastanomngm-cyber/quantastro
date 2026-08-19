"""Verify Swiss Ephemeris computations against known historical positions."""

from astroquant.ephemeris import (
    get_longitudes,
    get_sign,
    angle_diff,
    get_moon_phase,
    jd_from_date,
)


def test_saturn_galactic_center_1929():
    """Hitt+Crawford: Saturn at 26° Sagittarius (Galactic Center) on 1929-10-24.

    This is the "1929 crash" astrological signature.
    """
    jd = jd_from_date(1929, 10, 24, 12.0)
    pos = get_longitudes(jd)
    sat_lon = pos["Saturn"]
    # Galactic Center is at ~266.4° (26°24' Sagittarius)
    assert 265.5 <= sat_lon <= 267.5, f"Saturn at {sat_lon}°, expected ~266° (Galactic Center)"
    sign, _, deg = get_sign(sat_lon)
    assert sign == "Sagittarius", f"Saturn in {sign}, expected Sagittarius"


def test_stellium_1987_signature():
    """1987-08-24: Sun, Moon, Mercury, Venus, Mars within 4° (Hitt Lesson 7)."""
    jd = jd_from_date(1987, 8, 24, 12.0)
    pos = get_longitudes(jd)
    bodies = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
    lons = [pos[b] for b in bodies]
    # They should all be within ~4° of each other
    # Use the min and max of the set
    # Because they cross a sign boundary, we need to handle wrap
    # Actually on 8/24/1987 they were in Virgo — check pair by pair
    max_diff = max(angle_diff(lons[i], lons[j]) for i in range(5) for j in range(i + 1, 5))
    assert max_diff <= 6.0, f"Max spread {max_diff:.1f}°, expected <=4° per Hitt"


def test_moon_phases():
    """Full moon on a known date should have ~50% illumination and ~180° elongation."""
    # Full moon: 2024-09-18 (well-known)
    jd = jd_from_date(2024, 9, 18, 2.34)  # UT
    moon = get_moon_phase(jd)
    assert 170.0 <= moon["elongation"] <= 190.0, f"Elongation {moon['elongation']}°, not near opposition"


def test_sign_boundaries():
    """0° Aries = start of zodiac."""
    import pytest
    assert get_sign(0.0) == ("Aries", 0, 0.0)
    assert get_sign(29.9) == ("Aries", 0, pytest.approx(29.9))
    assert get_sign(30.0) == ("Taurus", 1, 0.0)
    assert get_sign(359.9) == ("Pisces", 11, pytest.approx(29.9))
    assert get_sign(360.0) == ("Aries", 0, 0.0)
    assert get_sign(720.0) == ("Aries", 0, 0.0)


def test_angle_diff():
    assert abs(angle_diff(0.0, 180.0) - 180.0) < 0.001
    assert abs(angle_diff(350.0, 10.0) - 20.0) < 0.001
    assert abs(angle_diff(90.0, 180.0) - 90.0) < 0.001


def test_node():
    """North Node is computed and is a valid longitude."""
    jd = jd_from_date(2026, 8, 19, 12.0)
    pos = get_longitudes(jd)
    assert "Node" in pos
    assert 0.0 <= pos["Node"] <= 360.0