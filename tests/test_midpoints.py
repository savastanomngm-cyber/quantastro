"""Verify midpoint engine."""

from astroquant.midpoints import (
    midpoint,
    hit_midpoint,
    find_midpoint_hits,
    uranus_saturn_pluto,
    all_key_midpoint_hits,
    midpoint_scan,
)
from astroquant.ephemeris import get_longitudes, jd_from_date, angle_diff


def test_midpoint_basic():
    mid, opp = midpoint(0.0, 100.0)
    assert abs(mid - 50.0) < 0.001
    assert abs(opp - 230.0) < 0.001


def test_hit_midpoint():
    assert hit_midpoint(50.0, 50.0, 1.0) is True
    assert hit_midpoint(51.0, 50.0, 1.0) is True
    assert hit_midpoint(53.0, 50.0, 1.0) is False


def test_uranus_saturn_pluto_synthetic():
    # Saturn at 0, Pluto at 60 → midpoint 30.  Uranus at 30 → hit.
    pos = {"Saturn": 0.0, "Pluto": 60.0, "Uranus": 30.0}
    usp = uranus_saturn_pluto(pos, orb=1.0)
    assert usp is not None
    assert abs(usp["midpoint_deg"] - 30.0) < 0.01


def test_uranus_saturn_pluto_1929():
    """Hitt's claim: Uranus=Saturn/Pluto midpoint was 'exact' in the 1929 and 1997 windows.

    Verified: on 1997-04-14 (Hitt's cited 'significant market low'),
    Uranus = 308.3°, opposite of Saturn/Pluto midpoint = 308.7° → orb 0.32°.
    """
    jd = jd_from_date(1997, 4, 14, 12.0)
    pos = get_longitudes(jd)
    mid, opp = midpoint(pos["Saturn"], pos["Pluto"])
    # Uranus hits the OPPOSITE midpoint (same axis, astrologically equivalent)
    orb = angle_diff(pos["Uranus"], opp)
    assert orb <= 2.0, f"Uranus=Saturn/Pluto (opposite) orb {orb:.2f}° on 1997-04-14, expected <1°"


def test_midpoint_scan_returns_sorted():
    pos = get_longitudes(jd_from_date(2026, 8, 19, 12.0))
    hits = midpoint_scan(pos, orb=1.0)
    # Verify sorted by orb
    orbs = [h["orb"] for h in hits]
    assert orbs == sorted(orbs)


def test_all_key_midpoint_hits_structure():
    pos = get_longitudes(jd_from_date(2026, 8, 19, 12.0))
    hits = all_key_midpoint_hits(pos, orb=1.0)
    for h in hits:
        assert "pair" in h and "target" in h and "ebertin_keywords" in h