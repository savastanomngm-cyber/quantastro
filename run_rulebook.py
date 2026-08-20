#!/usr/bin/env python3
"""Rulebook output for a single day.

Usage:
  python3 run_rulebook.py 2026-08-19 --prev-close 5840 --prev-high 5845 --prev-low 5790 --prev-open 5820 --close 5872
  python3 run_rulebook.py 2026-08-19 --ticker SPY  (auto-fetches yesterday's data)
"""

import argparse
from datetime import datetime

from astroquant.risklayer import rulebook_output


def main():
    p = argparse.ArgumentParser(description="Single-day rulebook")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("--prev-open", type=float, help="Previous day open")
    p.add_argument("--prev-high", type=float, help="Previous day high")
    p.add_argument("--prev-low", type=float, help="Previous day low")
    p.add_argument("--prev-close", type=float, help="Previous day close")
    p.add_argument("--close", type=float, help="Today's close (or current price)")
    p.add_argument("--ticker", default=None, help="Auto-fetch yesterday's data from yfinance")
    p.add_argument("--asset", default="ES", choices=["ES", "NQ", "GC"])
    args = p.parse_args()

    # Auto-fetch if no manual data
    if args.prev_high is None and args.ticker:
        import yfinance as yf
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        # Get the most recent trading day BEFORE the typed date (the anchor
        # candle). yfinance end is EXCLUSIVE, so iloc[-1] = previous session.
        data = yf.download(args.ticker, start=(dt - __import__('datetime').timedelta(days=8)).strftime("%Y-%m-%d"),
                           end=args.date, progress=False)
        if len(data) >= 1:
            prev = data.iloc[-1]
            args.prev_open = float(prev[("Open", args.ticker)])
            args.prev_high = float(prev[("High", args.ticker)])
            args.prev_low = float(prev[("Low", args.ticker)])
            args.prev_close = float(prev[("Close", args.ticker)])

    if args.prev_high is None:
        print("Error: need --prev-high or an OLDER ticker date with data from the prior session")
        return

    rb = rulebook_output(
        date_str=args.date,
        asset=args.asset,
        prev_open=args.prev_open,
        prev_high=args.prev_high,
        prev_low=args.prev_low,
        prev_close=args.prev_close or args.prev_high,
        current_close=args.close,
    )

    W = 62
    HR = "─" * W

    print()
    print(f"╔{HR}╗")
    print(f"║  RULEBOOK — {args.date} ({args.asset}){'':<{W-18-len(args.date)-len(args.asset)}}║")
    print(f"╠{HR}╣")

    d = rb["direction"]
    dir_emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(d, "⚪")
    print(f"║  {dir_emoji} DIRECTION: {d:<10}  SIZE: {rb['size_multiplier']:.2f}×{'':<{W-35}}║")
    print(f"║  Moon: {rb['moon_sign']:<8}  Phase: {rb['moon_phase'] or '-':<4}  "
          f"Hg Rx: {'YES' if rb['mercury_rx'] else 'no':<4}  Sa Rx: {'YES' if rb['saturn_rx'] else 'no':<4}║")
    print(f"║  Fib extreme: {rb['fib_extreme'] or 'none':<12}  "
          f"Confluence: {rb['fib_confluence']['score'] if rb['fib_confluence'] else '-'}/5{'':<10}║")
    print(f"╠{HR}╣")

    print(f"║  TIER-1 TILTS (size-changing):{'':<{W-33}}║")
    for t in rb["tier1_tilts"]:
        print(f"║    {t:<{W-6}}║")
    if not rb["tier1_tilts"]:
        print(f"║    (none active){'':<{W-17}}║")

    print(f"╠{HR}╣")
    print(f"║  TIER-2 CONTEXT (monitor only):{'':<{W-33}}║")
    for c in rb["tier2_context"]:
        print(f"║    {c:<{W-6}}║")
    if not rb["tier2_context"]:
        print(f"║    (none){'':<{W-9}}║")

    if rb["fib_extreme"] and rb["fib_confluence"]:
        print(f"╠{HR}╣")
        cal = rb["fib_confluence"]
        stars = "★" * cal["score"] + "☆" * (5 - cal["score"])
        print(f"║  CALIBRATED: {stars}  {cal['confidence']:<{W-19}}║")
        print(f"║  Predicted 5d return: {cal.get('predicted_return',0):+.2%}{'':<{W-27}}║")
        for r in cal.get("reasons", [])[:6]:
            print(f"║    {r:<{W-6}}║")

    print(f"╚{HR}╝")
    print()


if __name__ == "__main__":
    main()