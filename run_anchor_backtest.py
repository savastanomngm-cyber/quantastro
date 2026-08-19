#!/usr/bin/env python3
"""Grid backtest: compare anchor methods for the golden fib envelope."""

import argparse
from astroquant.anchor_backtest import grid_backtest


def main():
    p = argparse.ArgumentParser(description="Grid backtest — compare fib anchors")
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2026-08-01")
    args = p.parse_args()

    result = grid_backtest(args.ticker, args.start, args.end)
    if "error" in result:
        print(result["error"])
        return

    print(result["summary"])


if __name__ == "__main__":
    main()