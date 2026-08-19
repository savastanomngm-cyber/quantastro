"""Verify aspect classification and complex pattern detection."""

from astroquant.aspects import (
    classify_aspect,
    find_all_aspects,
    find_stellium,
    find_grand_cross,
    find_t_square,
    find_grand_trine,
    find_yod,
    detect_all_complex_patterns,
)
from astroquant.ephemeris import get_longitudes, jd_from_date


def test_classify_aspect():
    assert classify_aspect(0.0) == "conjunction"
    assert classify_aspect(60.0) == "sextile"
    assert classify_aspect(90.0) == "square"
    assert classify_aspect(120.0) == "trine"
    assert classify_aspect(180.0) == "opposition"
    assert classify_aspect(45.0) is None  # no aspect at 45°


def test_classify_with_orb():
    # 92° is square within 6° orb but not within 1°
    assert classify_aspect(92.0, {"square": 6.0}) == "square"
    assert classify_aspect(92.0, {"square": 1.0}) is None


def test_find_all_aspects_basic():
    pos = {
        "Sun": 0.0, "Moon": 90.0, "Mercury": 180.0, "Venus": 120.0,
    }
    aspects = find_all_aspects(pos, orbs={"conjunction": 8, "square": 6, "opposition": 6, "sextile": 4, "trine": 8})
    types = {frozenset([a["p1"], a["p2"]]) + tuple([a["type"]]) for a in aspects} if False else {(frozenset([a["p1"], a["p2"]]), a["type"]) for a in aspects}
    assert (frozenset(["Sun", "Moon"]), "square") in types
    assert (frozenset(["Sun", "Mercury"]), "opposition") in types
    assert (frozenset(["Sun", "Venus"]), "trine") in types


def test_stellium_synthetic():
    # 5 bodies in one spot
    pos = {
        "Sun": 10.0, "Moon": 11.0, "Mercury": 12.0, "Venus": 13.0, "Mars": 14.0,
        "Jupiter": 100.0, "Saturn": 200.0, "Uranus": 250.0, "Neptune": 300.0, "Pluto": 330.0,
    }
    st = find_stellium(pos, min_bodies=4, max_orb=8.0, planets=["Sun", "Moon", "Mercury", "Venus", "Mars"])
    assert st is not None
    assert st["bodies_count"] == 5


def test_stellium_no_false_positive():
    pos = {
        "Sun": 0.0, "Moon": 40.0, "Mercury": 80.0, "Venus": 120.0, "Mars": 160.0,
        "Jupiter": 200.0, "Saturn": 240.0, "Uranus": 280.0, "Neptune": 320.0, "Pluto": 350.0,
    }
    st = find_stellium(pos, min_bodies=4, max_orb=8.0)
    assert st is None


def test_grand_cross_synthetic():
    # 4 bodies at 0, 90, 180, 270
    pos = {
        "Saturn": 0.0, "Uranus": 90.0, "Mars": 180.0, "Pluto": 270.0,
        "Sun": 50.0, "Moon": 150.0, "Mercury": 250.0, "Venus": 350.0,
    }
    gc = find_grand_cross(pos, square_orb=6.0, opp_orb=6.0, planets=["Saturn", "Uranus", "Mars", "Pluto"])
    assert gc is not None
    assert len(set(gc["bodies"])) == 4


def test_t_square_synthetic():
    # opposition + apex square
    pos = {
        "Saturn": 0.0, "Uranus": 180.0, "Mars": 90.0,
    }
    ts = find_t_square(pos, square_orb=6.0, opp_orb=6.0, planets=["Saturn", "Uranus", "Mars"])
    assert ts is not None
    assert ts["apex"] == "Mars"
    assert ts["opposition"] == ("Saturn", "Uranus")


def test_grand_trine_synthetic():
    pos = {
        "Sun": 0.0, "Moon": 120.0, "Mars": 240.0,
    }
    gt = find_grand_trine(pos, trine_orb=8.0, planets=["Sun", "Moon", "Mars"])
    assert gt is not None
    assert set(gt["bodies"]) == {"Sun", "Moon", "Mars"}


def test_yod_synthetic():
    # sextile at 60°, apex at 180° (150° from each... wait: apex at midpoint+90)
    # sextile: A=0, B=60.  Apex must be quincunx (150°) to both.
    # midpoint of A,B = 30°.  Apex quincunx to A(0°) → 150° or 210°.
    # quincunx to B(60°) → 210° or -30°.  Common = 210°... 
    # Actually: quincunx to A means apex at 150° or 210°. 
    # quincunx to B(60) means apex at 210° or -30°(=330). Common = 210°.
    pos = {"A": 0.0, "B": 60.0, "C": 210.0}
    yod = find_yod(pos, sextile_orb=4.0, quincunx_orb=3.0, planets=["A", "B", "C"])
    assert yod is not None
    assert yod["apex"] == "C"


def test_detect_all():
    pos = {
        "Sun": 10.0, "Moon": 11.0, "Mercury": 12.0, "Venus": 13.0, "Mars": 14.0,
        "Jupiter": 100.0, "Saturn": 200.0, "Uranus": 250.0, "Neptune": 300.0, "Pluto": 330.0,
    }
    res = detect_all_complex_patterns(pos)
    assert res["stellium"] is not None