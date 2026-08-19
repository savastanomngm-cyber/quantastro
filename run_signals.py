#!/usr/bin/env python3
"""Print all astro signals for a single date as a clean table.

Usage:
  python3 run_signals.py 2026-08-19
  python3 run_signals.py 1987-10-19 --exchange NYC
"""

import argparse
from datetime import datetime

from astroquant.ephemeris import (
    PLANETS, get_longitudes, get_moon_phase, get_sign, get_speeds, jd_from_date,
)
from astroquant.aspects import find_all_aspects, detect_all_complex_patterns
from astroquant.bradley import bradley_index, BRADLEY_WEIGHTS
from astroquant.midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from astroquant.optimize import compute_confluence_score, stellium_volatility_signal

SEP = "─" * 78


def _phase_label(elongation: float) -> str:
    if elongation <= 15 or elongation >= 345:
        return "🌑 NEW MOON"
    elif 165 <= elongation <= 195:
        return "🌕 FULL MOON"
    elif 90 <= elongation <= 105:
        return "🌓 FIRST QUARTER"
    elif 255 <= elongation <= 270:
        return "🌗 LAST QUARTER"
    elif elongation < 90:
        return "🌒 WAXING CRESCENT"
    elif elongation < 165:
        return "🌔 WAXING GIBBOUS"
    elif elongation < 255:
        return "🌖 WANING GIBBOUS"
    else:
        return "🌘 WANING CRESCENT"


def main():
    parser = argparse.ArgumentParser(
        description="AstroQuant — single-date signal dump"
    )
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument("--exchange", "-e", default="CHICAGO",
                        choices=["CHICAGO", "NYC", "LONDON", "TOKYO"],
                        help="Exchange for intraday crossings (default: CHICAGO)")
    args = parser.parse_args()

    try:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid date: {args.date}. Use YYYY-MM-DD.")
        return

    jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)

    # ── Compute all signals ──────────────────────────────
    pos = get_longitudes(jd)
    spd = get_speeds(jd)
    moon = get_moon_phase(jd)
    aspects = find_all_aspects(pos)
    cp = detect_all_complex_patterns(pos)
    bi = bradley_index(pos)
    hits = all_key_midpoint_hits(pos, orb=1.0)
    usp = uranus_saturn_pluto(pos, orb=2.0)
    st_vol = stellium_volatility_signal(pos)

    hard = sum(1 for a in aspects if a["type"] in ("conjunction", "square", "opposition"))
    soft = sum(1 for a in aspects if a["type"] in ("sextile", "trine"))
    elong = moon["elongation"]

    conf = compute_confluence_score(pos, spd, cp, bi["total"], len(hits))

    # ═══════════════════════════════════════════════════════
    print()
    print(f"  ASTRO SIGNALS — {args.date}")
    print(f"  {'='*60}")
    print()

    # 1. Positions
    print("  ┌─ PLANETARY POSITIONS ──────────────────────────────┐")
    print(f"  │ {'Planet':<10} {'Long':>7}  {'Sign':<12} {'Deg':>5}  Rx │")
    print(f"  │ {'-'*10} {'-'*7}  {'-'*12} {'-'*5}  {'-'*2} │")
    for name in PLANETS:
        lon = pos.get(name)
        if lon is None:
            continue
        sign, _, deg = get_sign(lon)
        rx = "🔄" if spd.get(name, 0) < 0 else " "
        print(f"  │ {name:<10} {lon:>7.2f}°  {sign:<12} {deg:>5.2f}°  {rx} │")
    node_lon = pos.get("Node", 0)
    ns, _, nd = get_sign(node_lon)
    print(f"  │ {'Node':<10} {node_lon:>7.2f}°  {ns:<12} {nd:>5.2f}°  — │")
    print("  └────────────────────────────────────────────────────┘")
    print()

    # 2. Moon
    print(f"  🌙 MOON:  {_phase_label(elong)}")
    print(f"     Elongation {elong:.1f}°  |  Illumination {moon['illumination']:.1%}  |  Age {moon['age']:.1f} days")
    print()

    # 3. Aspects
    print(f"  📐 ASPECTS:  {hard} hard  |  {soft} soft  |  {bi['aspect_count']} total")
    top = sorted(aspects, key=lambda a: a["orb"])[:6]
    for a in top:
        print(f"     {a['p1']:<10} {a['type']:<12} {a['p2']:<10}  orb {a['orb']:.2f}°")
    print()

    # 4. Complex patterns
    has_any = False
    labels = {
        "stellium": ("🔴 STELLIUM", "bodies_count"),
        "grand_cross": ("🔴 GRAND CROSS", None),
        "t_square": ("🟠 T-SQUARE", "apex"),
        "yod": ("🟡 YOD", "apex"),
        "grand_trine": ("🟢 GRAND TRINE", None),
    }
    for key, (label, detail_field) in labels.items():
        pat = cp.get(key)
        if pat:
            has_any = True
            extra = ""
            if detail_field and detail_field in pat:
                extra = f" (apex: {pat[detail_field]})"
            elif key == "stellium":
                extra = f" ({pat['bodies_count']} bodies in {pat['sign']}, range {pat['degree_range']}°)"
            print(f"  {label}{extra}")
    if not has_any:
        print("  — no complex patterns —")
    print()

    # 5. Midpoints
    print(f"  📍 MIDPOINTS:  {len(hits)} key hit(s)")
    if usp:
        print(f"     🔴 Uranus = Saturn/Pluto  (orb {usp['orb']:.3f}°) ← Hitt's #1")
    for h in hits[:5]:
        print(f"     {h['target']} = {h['pair'][0]}/{h['pair'][1]}  (orb {h['orb']:.3f}°)")
    print()

    # 6. Bradley
    print(f"  📊 BRADLEY:  total {bi['total']}  (hard {bi['hard_sum']}  soft {bi['soft_sum']})")
    print()

    # 7. Confluence
    print(f"  ⚖️  CONFLUENCE SCORE:  {conf['score']:+d}")
    print(f"     Bull: {conf['bull_count']}  Bear: {conf['bear_count']}  →  {conf['interpretation']}")
    print(f"     Flags: {', '.join(conf['flags'])}")
    print()

    # 8. Stellium volatility
    if st_vol:
        print(f"  📈 STELLIUM VOLATILITY:  {st_vol['volatility_multiplier']}×")
        print(f"     Position size: {st_vol['suggested_position_fraction']:.0%}")
        print(f"     Stop width:    {st_vol['suggested_stop_multiplier']:.1f}×")
        print(f"     {st_vol['hitt_rule']}")
    else:
        print("  📈 STELLIUM VOLATILITY:  none (1.0× baseline)")
    print()

    # 9. Retrogrades
    rx_list = [p for p in PLANETS if spd.get(p, 0) < 0]
    if rx_list:
        print(f"  🔄 RETROGRADE:  {', '.join(rx_list)}")
    else:
        print("  🔄 RETROGRADE:  none")
    print()

    # 10. Intraday (lite)
    from astroquant.intraday import trading_crossings
    crossings, dc = trading_crossings(jd, args.exchange, step_minutes=10)
    if crossings:
        print(f"  ⏱️  INTRADAY ({args.exchange}):")
        for c in crossings[:12]:
            print(f"     {c['time_local']}  {c['planet']:<8} {c['angle']}  → {c['significance']}")
    print()


if __name__ == "__main__":
    main()