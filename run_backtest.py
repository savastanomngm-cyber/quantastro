#!/usr/bin/env python3
"""Standalone backtest runner: fetch market data + compute astro signals + analyze."""

import argparse
import sys

from astroquant.backtest import fetch_and_analyze


def main():
    parser = argparse.ArgumentParser(
        description="AstroQuant backtest — correlate astro signals with market returns",
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--ticker", default="SPY", help="yfinance ticker (default: SPY)")
    parser.add_argument("--no-zscore", action="store_true", help="Skip Bradley decile analysis")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")
    args = parser.parse_args()

    result = fetch_and_analyze(
        start=args.start,
        end=args.end,
        ticker=args.ticker,
        include_zscore=not args.no_zscore,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json as _json
        # Exclude the DataFrame objects from JSON serialization
        out = {k: v for k, v in result.items()
               if k not in ("signal_df",) and not hasattr(v, "to_dict")}
        print(_json.dumps(out, indent=2, default=str))
    else:
        print(result["summary"])


if __name__ == "__main__":
    main()