#!/usr/bin/env python3
"""Recalibrate confluence scoring weights from historical extreme events."""

import argparse
from astroquant.recalibrate import run_recalibration


def main():
    p = argparse.ArgumentParser(description="Recalibrate confluence weights")
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2022-01-01")
    p.add_argument("--fwd", type=int, default=5, help="Forward days for target")
    args = p.parse_args()

    result = run_recalibration(args.ticker, args.start, args.end, args.fwd)
    if "error" in result:
        print(result["error"])
        return
    print(result["summary"])


if __name__ == "__main__":
    main()