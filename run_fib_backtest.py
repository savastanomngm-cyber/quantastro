#!/usr/bin/env python3
"""Golden fib + astro confluence backtest.

Usage:
  python3 run_fib_backtest.py --ticker SPY
  python3 run_fib_backtest.py --ticker GLD --start 2020-01-01 --end 2026-08-01
"""

import argparse

from astroquant.fib_backtest import run_fib_backtest


def main():
    p = argparse.ArgumentParser(description="Backtest golden fib + astro confluence")
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2026-08-01")
    args = p.parse_args()

    result = run_fib_backtest(args.ticker, args.start, args.end)

    if "error" in result:
        print(result["error"])
        return

    print(result["summary"])


if __name__ == "__main__":
    main()