#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Sequence

from .render import render_text
from .report import DEFAULT_ANALYSIS_DAYS, build_analysis_report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build a unified stock or market analysis report for stock-master skill.')
    parser.add_argument('symbol', help='Stock symbol or natural-language query, e.g. SH603966 / 603966 / 今天A股市场怎么样')
    parser.add_argument('--days', type=int, default=DEFAULT_ANALYSIS_DAYS)
    parser.add_argument('--pretty', action='store_true')
    parser.add_argument('--format', choices=['json', 'text'], default='json')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_analysis_report(args.symbol, days=args.days)
    if args.format == 'text':
        print(render_text(report))
        return 0
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(report, ensure_ascii=False))
    return 0
