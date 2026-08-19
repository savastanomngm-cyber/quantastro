"""CLI: produces a complete astro-econ signal report for a given date.

Usage:
    python -m astroquant.run 2026-08-19
    python -m astroquant.run 1987-10-19 --exchange NYC
    python -m astroquant.run 1929-10-24 --exchange LONDON

The report includes every signal tier discussed in *Investing by the Stars*
and *AstroEcon*: daily aspects, complex patterns, midpoints, Bradley index,
moon phase, intraday angle crossings, and a synthesized daily bias.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from .ephemeris import (
    PLANETS,
    get_longitudes,
    get_moon_phase,
    get_sign,
    get_speeds,
    jd_from_date,
)
from .aspects import find_all_aspects, classify_aspect, detect_all_complex_patterns
from .midpoints import (
    all_key_midpoint_hits,
    midpoint_scan,
    uranus_saturn_pluto,
)
from .bradley import bradley_index, bradley_interpretation
from .intraday import EXCHANGES, trading_crossings

SEPARATOR = f"\n{'─' * 72}\n"


def _phase_label(elongation: float) -> str:
    if elongation <= 15.0 or elongation >= 345.0:
        return "🌑 NEW MOON (exhaustion / fresh start)"
    elif 15.0 < elongation < 90.0:
        return "🌒 WAXING CRESCENT"
    elif 90.0 <= elongation <= 105.0:
        return "🌓 FIRST QUARTER (crisis / test point)"
    elif 105.0 < elongation < 165.0:
        return "🌔 WAXING GIBBOUS"
    elif 165.0 <= elongation <= 195.0:
        return "🌕 FULL MOON (momentum / peak / deliverance)"
    elif 195.0 < elongation < 255.0:
        return "🌖 WANING GIBBOUS"
    elif 255.0 <= elongation <= 270.0:
        return "🌗 LAST QUARTER (crisis / release)"
    else:
        return "🌘 WANING CRESCENT (balsamic / seeding)"


def _daily_bias(
    aspect_count: int,
    hard_count: int,
    soft_count: int,
    complex_patterns: dict,
    bradley_total: float,
    moon_elongation: float,
    is_merc_rx: bool,
    midpoints: list,
) -> str:
    """Synthesize a Hitt-style daily bias from all computed signals."""
    parts = []

    # Aspect dominance
    if hard_count > soft_count + 3:
        parts.append("⚠️ HARD-ASPECT DOMINANCE → trend-change alert")
    elif soft_count > hard_count + 3:
        parts.append("✅ SOFT-ASPECT DOMINANCE → continuation / inertia")

    # Complex patterns
    if complex_patterns.get("stellium"):
        n = complex_patterns["stellium"]["bodies_count"]
        sign = complex_patterns["stellium"]["sign"]
        parts.append(f"🔴 STELLIUM ({n} bodies in {sign}) → major cycle inflection")
    if complex_patterns.get("grand_cross"):
        parts.append("🔴 GRAND CROSS → chaotic, high stress")
    if complex_patterns.get("t_square"):
        parts.append("🟠 T-SQUARE → focused stress, conflict")
    if complex_patterns.get("grand_trine"):
        parts.append("🟢 GRAND TRINE → easy continuation, inertia")
    if complex_patterns.get("yod"):
        parts.append("🟡 YOD → fateful pivot, focused energy")

    # Mercury retrograde
    if is_merc_rx:
        parts.append("🛑 MERCURY Rx → whipsaws, false signals, tighten stops")

    # Moon phase
    if moon_elongation <= 15.0 or moon_elongation >= 345.0:
        parts.append("🌑 NEW MOON → fade extremes, mean-reversion bias")
    elif 165.0 <= moon_elongation <= 195.0:
        parts.append("🌕 FULL MOON → momentum bias, trust the trend")
    elif 255.0 <= moon_elongation <= 270.0:
        parts.append("🌗 LAST QUARTER → release, potential reversal")

    # Bradley index
    if bradley_total >= 4.0:
        parts.append(f"📈 BRADLEY {bradley_total} → bullish pressure")
    elif bradley_total <= -4.0:
        parts.append(f"📉 BRADLEY {bradley_total} → bearish pressure")

    if not parts:
        return "NEUTRAL — no strong directional signals. Trade technicals only."

    return " | ".join(parts)


def run_report(date_str: str, exchange_name: str = "CHICAGO") -> str:
    """Generate a full text report for a date + exchange. Returns markdown."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return f"❌ Invalid date: {date_str}. Use YYYY-MM-DD."

    exc = EXCHANGES[exchange_name.upper()]
    jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)  # noon UT

    # ── Ephemeris ────────────────────────────────────
    positions = get_longitudes(jd)
    speeds = get_speeds(jd)
    moon = get_moon_phase(jd)

    # ── Aspects ──────────────────────────────────────
    aspects = find_all_aspects(positions)
    hard_aspects = [a for a in aspects if a["type"] in ("conjunction", "square", "opposition")]
    soft_aspects = [a for a in aspects if a["type"] in ("sextile", "trine")]

    # ── Complex patterns ─────────────────────────────
    complex_patterns = detect_all_complex_patterns(positions)

    # ── Midpoints ─────────────────────────────────────
    key_hits = all_key_midpoint_hits(positions, orb=1.0)
    usp = uranus_saturn_pluto(positions, orb=1.0)

    # ── Bradley index ─────────────────────────────────
    bi = bradley_index(positions)
    bradley_intrp = bradley_interpretation(bi["total"])

    # ── Mercury Rx ────────────────────────────────────
    is_merc_rx = speeds.get("Mercury", 0.0) < 0

    # ── Intraday ──────────────────────────────────────
    crossings, day_char = trading_crossings(jd, exchange_name)

    # ── Build report ──────────────────────────────────
    lines = []
    lines.append(f"# ASTRO-ECONOMIC SIGNAL REPORT: {date_str}")
    lines.append(f"")
    lines.append(f"**Exchange:** {exc.name} ({exchange_name.upper()})")
    lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(SEPARATOR)

    # 1. POSITIONS
    lines.append("## 1. DAILY PLANETARY POSITIONS (Noon UTC)")
    lines.append("")
    lines.append("| Planet | Longitude | Sign | Deg in Sign | Rx? |")
    lines.append("|--------|-----------|------|-------------|-----|")
    for name in PLANETS:
        lon = positions.get(name)
        if lon is None:
            continue
        sign, _, deg = get_sign(lon)
        rx = "🔄 Rx" if speeds.get(name, 0.0) < 0 else ""
        lines.append(f"| {name} | {lon:.2f}° | {sign} | {deg:.2f}° | {rx} |")

    # Node
    node_lon = positions.get("Node")
    if node_lon is not None:
        sign, _, deg = get_sign(node_lon)
        lines.append(f"| North Node | {node_lon:.2f}° | {sign} | {deg:.2f}° | — |")
    lines.append(SEPARATOR)

    # 2. MOON PHASE
    lines.append("## 2. MOON PHASE")
    lines.append("")
    elong = moon["elongation"]
    lines.append(f"- **Phase:** {_phase_label(elong)}")
    lines.append(f"- **Elongation:** {elong:.1f}°")
    lines.append(f"- **Illumination:** {moon['illumination']:.1%}")
    lines.append(f"- **Age (days since New):** {moon['age']:.1f} days")
    lines.append(SEPARATOR)

    # 3. ASPECT SUMMARY
    lines.append("## 3. ASPECT SUMMARY")
    lines.append("")
    lines.append(f"- **Total aspects within orb:** {len(aspects)}")
    lines.append(f"- **Hard aspects (trend-change):** {len(hard_aspects)}")
    lines.append(f"- **Soft aspects (continuation):** {len(soft_aspects)}")
    lines.append("")
    if aspects:
        lines.append("| P1 | P2 | Type | Angle | Orb |")
        lines.append("|----|----|------|-------|-----|")
        for a in aspects[:20]:  # limit display
            lines.append(f"| {a['p1']} | {a['p2']} | {a['type']} | {a['angle']}° | {a['orb']}° |")
    else:
        lines.append("*No major aspects found.*")
    lines.append(SEPARATOR)

    # 4. COMPLEX PATTERNS
    lines.append("## 4. COMPLEX ASPECT PATTERNS")
    lines.append("")
    for name, pattern in complex_patterns.items():
        if pattern:
            lines.append(f"### {name.upper()}")
            lines.append("")
            if name == "stellium":
                lines.append(f"- **Bodies ({pattern['bodies_count']}):** {', '.join(pattern['bodies'])}")
                lines.append(f"- **Sign:** {pattern['sign']}")
                lines.append(f"- **Range:** {pattern['degree_range']}°")
                lines.append(f"- **Hitt's rule:** Major cycle inflection — often marks multi-year tops or bottoms.")
            elif name == "grand_cross":
                lines.append(f"- **Opposition 1:** {pattern['opposition_1'][0]} ↔ {pattern['opposition_1'][1]}")
                lines.append(f"- **Opposition 2:** {pattern['opposition_2'][0]} ↔ {pattern['opposition_2'][1]}")
                lines.append(f"- **Hitt's rule:** Chaotic, difficult to control.  Lock in hedges.")
            elif name == "t_square":
                lines.append(f"- **Opposition:** {pattern['opposition'][0]} ↔ {pattern['opposition'][1]}")
                lines.append(f"- **Apex (squaring both):** {pattern['apex']}")
                lines.append(f"- **Hitt's rule:** Focused stress/conflict. Apex planet is key.")
            elif name == "grand_trine":
                lines.append(f"- **Bodies:** {', '.join(pattern['bodies'])}")
                lines.append(f"- **Hitt's rule:** Continuation, inertia. NOT a trend-change signal.")
            elif name == "yod":
                lines.append(f"- **Sextile:** {pattern['sextile'][0]} ✶ {pattern['sextile'][1]}")
                lines.append(f"- **Apex (quincunx both):** {pattern['apex']}")
                lines.append(f"- **Hitt's rule:** Fateful pivot — apex planet is the focus of energy.")
            lines.append("")
    if not any(complex_patterns.values()):
        lines.append("*No complex aspect patterns detected.*")
    lines.append(SEPARATOR)

    # 5. MIDPOINTS
    lines.append("## 5. MIDPOINT COMBINATIONS")
    lines.append("")
    if usp:
        lines.append(f"### 🔴 URANUS = SATURN / PLUTO (Hitt's #1 Signal)")
        lines.append(f"- **Midpoint:** {usp['midpoint_deg']:.3f}° | **Orb:** {usp['orb']:.3f}°")
        lines.append(f"- **Historical hits:** {', '.join(map(str, usp['historical_years']))}")
        lines.append(f"- **Hitt:** 'the most important midpoint combination I have found to date'")
        lines.append("")
    if key_hits:
        lines.append("### Key midpoint hits (from Hitt Lesson 10)")
        lines.append("")
        for h in key_hits:
            lines.append(f"- **{h['target']} = {h['pair'][0]}/{h['pair'][1]}** (orb {h['orb']:.3f}°)")
            lines.append(f"  *{h['ebertin_keywords']}*")
    else:
        lines.append("*No key midpoint hits within orb.*")
    lines.append(SEPARATOR)

    # 6. BRADLEY INDEX
    lines.append("## 6. BRADLEY DAILY ASPECT SUM")
    lines.append("")
    lines.append(f"- **Total:** {bi['total']}")
    lines.append(f"- **Hard component:** {bi['hard_sum']}")
    lines.append(f"- **Soft component:** {bi['soft_sum']}")
    lines.append(f"- **Aspect count:** {bi['aspect_count']}")
    lines.append(f"- **Interpretation:** {bradley_intrp}")
    lines.append(SEPARATOR)

    # 7. INTRADAY
    lines.append(f"## 7. INTRADAY ANGLE CROSSINGS ({exc.name})")
    lines.append(f"")
    lines.append(f"**Trading hours:** {exc.trading_start:.0f}:{int((exc.trading_start%1)*60):02d}–{exc.trading_end:.0f}:{int((exc.trading_end%1)*60):02d} local")
    lines.append(f"**UTC offset:** {exc.utc_offset:+g}h")
    lines.append("")
    lines.append("### Day character at market open")
    lines.append("")
    lines.append(f"- **ASC:** {day_char['asc_degree']:.2f}° {day_char['asc_sign']}")
    lines.append(f"- **MC:** {day_char['mc_degree']:.2f}° {day_char['mc_sign']}")
    if day_char["planets_on_angles"]:
        lines.append(f"- **Planets on angles at open:**")
        for pa in day_char["planets_on_angles"]:
            lines.append(f"  - {pa['planet']} on {pa['angle']} (orb {pa['orb']}°) — {pa['sign']} {pa['deg_in_sign']}°")
        lines.append(f"- **Dominant planet:** {day_char['dominant_planet']}")
    else:
        lines.append("*No planets near angles at open.*")
    lines.append("")
    if crossings:
        lines.append("### Angle-crossing timetable")
        lines.append("")
        lines.append("| Local Time | Planet | Angle | Significance |")
        lines.append("|------------|--------|-------|-------------|")
        for c in crossings:
            lines.append(f"| {c['time_local']} | {c['planet']} | {c['angle']} | {c['significance']} |")
    else:
        lines.append("*No angle crossings during trading hours.*")
    lines.append(SEPARATOR)

    # 8. DAILY BIAS
    bias = _daily_bias(
        len(aspects), len(hard_aspects), len(soft_aspects),
        complex_patterns, bi["total"], elong, is_merc_rx, key_hits,
    )
    lines.append("## 8. SYNTHESIZED DAILY BIAS")
    lines.append("")
    lines.append(f"> **{bias}**")
    lines.append(SEPARATOR)

    lines.append("*Generated by astroquant — deterministic rule-based engine, no AI interpretation.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Astro-Econ signal report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python -m astroquant.run 2026-08-19\n"
               "  python -m astroquant.run 1987-10-19 --exchange NYC\n"
               "  python -m astroquant.run 1929-10-24 --exchange LONDON",
    )
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument(
        "--exchange", "-e", default="CHICAGO",
        choices=["CHICAGO", "NYC", "LONDON", "TOKYO"],
        help="Exchange location (default: CHICAGO for CME/S&P futures)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of markdown report",
    )
    args = parser.parse_args()

    if args.json:
        import json
        jd = jd_from_date(*map(int, args.date.split("-")), 12.0)
        pos = get_longitudes(jd)
        from .aspects import detect_all_complex_patterns
        from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto
        from .bradley import bradley_index
        output = {
            "date": args.date,
            "planets": {k: round(v, 3) for k, v in pos.items()},
            "complex_patterns": {k: v for k, v in detect_all_complex_patterns(pos).items() if v},
            "midpoint_hits": [{"target": h["target"], "pair": list(h["pair"]), "orb": h["orb"]} for h in all_key_midpoint_hits(pos)],
            "uranus_saturn_pluto": uranus_saturn_pluto(pos),
            "bradley": bradley_index(pos),
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(run_report(args.date, args.exchange))


if __name__ == "__main__":
    main()