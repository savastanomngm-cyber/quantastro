#!/usr/bin/env python3
"""Full rulebook backtest."""

import argparse
from astroquant.rulebook_backtest import backtest_rulebook


def main():
    p = argparse.ArgumentParser(description="Backtest the full rulebook")
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--asset", default="ES", choices=["ES", "NQ", "GC"])
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2026-08-01")
    args = p.parse_args()

    result = backtest_rulebook(args.ticker, args.asset, args.start, args.end)
    if "error" in result:
        print(result["error"])
        return
    print(result["summary"])


if __name__ == "__main__":
    main()