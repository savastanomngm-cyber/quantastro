#!/usr/bin/env python3
"""Single-day signal card — deep research edition.

Sources: Hitt *AstroEcon* (1997-2000), Weingarten *Investing by the Stars* (2000).

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
from astroquant.bradley import bradley_index
from astroquant.midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from astroquant.optimize import compute_confluence_score, stellium_volatility_signal
from astroquant.knowledge import (
    COMPLEX_PATTERN_RULES,
    PLANET_MEANINGS,
    PLANET_MARKET_SIGNATURE,
    PLANET_PAIR_KEYWORDS,
    MOON_SIGN_ASSET_BIAS,
    ANGLE_CROSSING_SIGNIFICANCE,
    HISTORICAL_DATES,
    planet_pair_meaning,
)

W = 64
HR = "─" * W


# ── verdict ────────────────────────────────────────────────────────────

def verdict(conf: int, brad: float, hard: int, soft: int,
            stellium: bool, gc: bool, usp_hit: bool, t_sq: bool, yod: bool) -> tuple:
    """Return (emoji, label, extra_note)."""

    # Historical date match
    for hist_date, info in HISTORICAL_DATES.items():
        if _date_str == hist_date:
            return ("⚠️", f"HISTORICAL: {info['event']}", info['hitt_notes'])

    if usp_hit:
        return ("⚠️", "MAJOR CYCLE — Uranus=Saturn/Pluto active", "Hitt's #1 signal. Inflection point. Historical hits: 1776, 1852, 1929, 1997.")
    if brad >= 30:
        return ("⚠️", f"EXTREME BRADLEY ({brad:+.0f})", "Historically large moves. Fade if already at extremes.")
    if brad <= -20:
        return ("⚠️", f"EXTREME BRADLEY ({brad:+.0f})", "Historically sharp declines.")
    if stellium and gc:
        return ("⚠️", "STELLIUM + GRAND CROSS", "Extreme volatility. No directional edge. Reduce size.")
    if gc:
        return ("🟡", "GRAND CROSS", "Chaotic. Tight stops. Lock in hedges.")
    if yod and t_sq:
        return ("🟡", "YOD + T-SQUARE", "Fateful stress. Apex planets are the focus. Wait for resolution.")
    if conf <= -2:
        return ("🟢", f"STRESS BOUNCE (conf. {conf:+d})", "Historically: stress extremes mean-revert upward for equities.")
    if conf >= 3:
        return ("🟢", "STRONG BULL CONFLUENCE", "Weingarten Rule of Three satisfied.")
    if conf <= -1:
        return ("🟡", "CAUTION — stress building", "Tighten stops. Wait for clearer signal.")
    if brad >= 15 and soft > hard:
        return ("🟢", "BULLISH — soft dominance", "Continuation / inertia bias per Hitt Lesson 5.")
    if brad <= -15 and hard > soft:
        return ("🔴", "BEARISH — hard dominance", "Trend-change pressure per Hitt Lesson 5.")
    if soft > hard + 4:
        return ("🟢", "MILDLY BULLISH", "Soft-aspect dominance → continuation (Hitt).")
    if hard > soft + 4:
        return ("🔴", "MILDLY BEARISH", "Hard-aspect dominance → trend-change candidate (Hitt).")
    if t_sq:
        return ("🟡", "T-SQUARE active", "Focused stress. Apex planet is the key.")
    return ("⚪", "NEUTRAL", "No directional edge. Trade technicals.")


# ── render ─────────────────────────────────────────────────────────────

def render(date_str: str, exchange: str,
           morning_open: float = None, morning_high: float = None,
           morning_low: float = None, current_price: float = None):
    global _date_str
    _date_str = date_str

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("Bad date. Use YYYY-MM-DD.")
        return

    jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)
    pos = get_longitudes(jd)
    spd = get_speeds(jd)
    moon_phase = get_moon_phase(jd)
    aspects = find_all_aspects(pos)
    cp = detect_all_complex_patterns(pos)
    bi = bradley_index(pos)
    hits = all_key_midpoint_hits(pos, orb=1.0)
    usp = uranus_saturn_pluto(pos, orb=2.0)
    st_vol = stellium_volatility_signal(pos)

    hard = sum(1 for a in aspects if a["type"] in ("conjunction", "square", "opposition"))
    soft = sum(1 for a in aspects if a["type"] in ("sextile", "trine"))
    conf = compute_confluence_score(pos, spd, cp, bi["total"], len(hits))
    elong = moon_phase["elongation"]

    stellium = cp.get("stellium") is not None
    gc = cp.get("grand_cross") is not None
    t_sq = cp.get("t_square") is not None
    yod = cp.get("yod") is not None
    gtrine = cp.get("grand_trine") is not None

    moon_sign, _, _ = get_sign(pos["Moon"])
    moon_bias = MOON_SIGN_ASSET_BIAS.get(moon_sign, {"bias": "-", "note": ""})

    # phase
    if elong <= 15 or elong >= 345:
        phase = "🌑 NEW"
    elif 165 <= elong <= 195:
        phase = "🌕 FULL"
    elif 90 <= elong <= 105:
        phase = "🌓 1Q"
    elif 255 <= elong <= 270:
        phase = "🌗 3Q"
    elif elong < 90:
        phase = "🌒 WXC"
    elif elong < 165:
        phase = "🌔 WXG"
    elif elong < 255:
        phase = "🌖 WNG"
    else:
        phase = "🌘 WNC"

    rx_list = [p for p in PLANETS if spd.get(p, 0) < 0]

    # Featured planets — those on angles at open or with tightest orbs
    featured = []
    top3 = sorted(aspects, key=lambda a: a["orb"])[:3]
    for a in top3:
        for p in (a["p1"], a["p2"]):
            if p not in featured:
                featured.append(p)
    featured = featured[:4]

    direction, label, note = verdict(
        conf["score"], bi["total"], hard, soft, stellium, gc,
        usp is not None, t_sq, yod,
    )

    # ── header ─────────────────────────────────────────────────────
    print()
    print(f"╔{HR}╗")
    print(f"║  {'ASTROECON SIGNAL — ' + date_str:<{W-2}}║")
    if mood := PLANET_MARKET_SIGNATURE.get(featured[0], "") if featured else "":
        print(f"║  Day character: {mood:<{W-18}}║")
    print(f"╠{HR}╣")
    print(f"║  {direction} {label:<{W-7}}║")
    print(f"║  {note:<{W-2}}║")
    print(f"╠{HR}╣")

    # ── status bar ─────────────────────────────────────────────────
    rx_str = ",".join(rx_list) if rx_list else "none"
    usp_str = "🔴 U=Sat/Plu" if usp else "no U=Sat/Plu"
    print(f"║  {phase}  ·  Moon {moon_sign} ({moon_bias['bias']})  ·  Rx: {rx_str:<14} ║")
    print(f"║  Confl {conf['score']:+d}  ·  Bradley {bi['total']:+.0f}  ·  Hard {hard}/Soft {soft}  ·  Midpts {len(hits):<2}  ·  {usp_str}  ║")
    print(f"╠{HR}╣")

    # ── complex patterns ───────────────────────────────────────────
    any_pat = False
    for key, lbl in [("stellium","🔴 STELLIUM"),("grand_cross","🔴 GRAND CROSS"),
                     ("t_square","🟠 T-SQUARE"),("yod","🟡 YOD"),
                     ("grand_trine","🟢 GRAND TRINE")]:
        pat = cp.get(key)
        if pat:
            any_pat = True
            source = COMPLEX_PATTERN_RULES.get(key, "")
            # Truncate source to fit
            print(f"║  {lbl}: {source[:W-14]:<{W-14}}║")
    if not any_pat:
        print(f"║  No complex aspect patterns.                                            ║")
    print(f"╠{HR}╣")

    # ── top aspects with Hitt keywords ─────────────────────────────
    print(f"║  ACTIVE ASPECTS (closest orbs, Hitt Lesson 9):                         ║")
    for a in top3:
        meaning = planet_pair_meaning(a["p1"], a["p2"], a["type"])
        line = f"║    {a['p1']:<8} {a['type']:<11} {a['p2']:<8} orb {a['orb']:.2f}°"
        if meaning:
            line += f"  → {meaning}"
        print(f"{line:<{W-1}}║")

    # ── featured planets ───────────────────────────────────────────
    print(f"╠{HR}╣")
    print(f"║  FEATURED PLANETS:                                                     ║")
    for p in featured:
        desc = PLANET_MEANINGS.get(p, "")
        print(f"║    {p:<8}  {desc:<{W-13}}║")
    print(f"╠{HR}╣")

    # ── midpoint hits ──────────────────────────────────────────────
    if hits:
        print(f"║  MIDPOINT HITS (Ebertin):                                              ║")
        for h in hits[:3]:
            kw = h.get("ebertin_keywords", "")[:W-22]
            print(f"║    {h['target']}= {h['pair'][0]}/{h['pair'][1]}  orb {h['orb']:.2f}°  → {kw:<{W-22}}║")
    else:
        print(f"║  No key midpoint hits.                                                 ║")

    # ── stellium vol ────────────────────────────────────────────────
    if st_vol:
        print(f"╠{HR}╣")
        print(f"║  STELLIUM VOLATILITY: {st_vol['volatility_multiplier']}×  →  pos. size {st_vol['suggested_position_fraction']:.0%},  stop {st_vol['suggested_stop_multiplier']:.1f}×      ║")

    # ── golden fib envelope ───────────────────────────────────────
    if morning_open and morning_high and morning_low:
        from astroquant.fibrisk import envelope_from_morning, render_envelope
        from astroquant.confluence import (
            compute_confluence, render_confluence,
            score_reversal_calibrated,
        )

        env = envelope_from_morning(morning_open, morning_high, morning_low)
        print(f"╠{HR}╣")
        fib_text = render_envelope(env, current_price)
        for line in fib_text.split("\n"):
            print(f"║  {line:<{W-4}}║")

        if current_price:
            extreme = env.is_at_extreme(current_price, pct=15.0)
            if extreme:
                # Recompute with calibrated scorer
                extreme_name, _, dist_pct = env.nearest_level(current_price)
                cal = score_reversal_calibrated(
                    extreme=extreme_name,
                    top_aspects=sorted(aspects, key=lambda a: a["orb"])[:6],
                    complex_patterns=cp,
                    midpoint_hits=hits,
                    usp_hit=usp is not None,
                    merc_rx=spd.get("Mercury", 0) < 0,
                    saturn_rx=spd.get("Saturn", 0) < 0,
                    jupiter_rx=spd.get("Jupiter", 0) < 0,
                    moon_phase_label="FULL" if 165 <= elong <= 195 else "NEW" if elong <= 15 or elong >= 345 else "",
                    is_upper=extreme_name.startswith("+"),
                    dist_into_extreme_pct=dist_pct,
                )
                stars = "★" * cal["score"] + "☆" * (5 - cal["score"])
                print(f"╠{HR}╣")
                print(f"║  FIB EXTREME: {extreme_name}  |  CALIBRATED CONFLUENCE: {stars} ({cal['confidence']})║")
                print(f"║  Action: {cal['action']}  |  Predicted 5d return: {cal['predicted_return']:+.2%} ║")
                for r in cal["reasons"]:
                    print(f"║    {r:<{W-6}}║")

    # ── intraday ────────────────────────────────────────────────────
    from astroquant.intraday import trading_crossings
    crossings, dc = trading_crossings(jd, exchange, step_minutes=15)
    has_dc = dc.get("planets_on_angles") and len(dc["planets_on_angles"]) > 0
    if has_dc:
        print(f"╠{HR}╣")
        print(f"║  AT OPEN ({exchange}):                                                  ║")
        for pa in sorted(dc["planets_on_angles"], key=lambda x: x["orb"]):
            sig = ANGLE_CROSSING_SIGNIFICANCE.get(pa["planet"], "")[:W-26]
            print(f"║    {pa['planet']} on {pa['angle']}  orb {pa['orb']:.1f}°  → {sig:<{W-26}}║")
        if dc.get("dominant_planet"):
            dp = dc["dominant_planet"]
            dp_sig = PLANET_MARKET_SIGNATURE.get(dp, "")
            print(f"║    Dominant: {dp} — {dp_sig:<{W-17}}║")

    if crossings:
        print(f"╠{HR}╣")
        print(f"║  INTRADAY CROSSINGS (trading hours):                                   ║")
        for c in crossings[:10]:
            sig_short = ANGLE_CROSSING_SIGNIFICANCE.get(c["planet"], "")[:W-22]
            print(f"║    {c['time_local']}  {c['planet']:<8} {c['angle']}  → {sig_short:<{W-22}}║")

    print(f"╚{HR}╝")
    print()


# ── main ──────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Deep-research single-day astro signal card")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("--exchange", "-e", default="CHICAGO",
                   choices=["CHICAGO", "NYC", "LONDON", "TOKYO"])
    p.add_argument("--open", type=float, default=None, help="Morning open price (for fib envelope)")
    p.add_argument("--high", type=float, default=None, help="Morning high price")
    p.add_argument("--low", type=float, default=None, help="Morning low price")
    p.add_argument("--price", type=float, default=None, help="Current price (for fib positioning)")
    args = p.parse_args()
    render(args.date, args.exchange, args.open, args.high, args.low, args.price)


if __name__ == "__main__":
    main()