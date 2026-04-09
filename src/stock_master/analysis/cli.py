#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Sequence

from .render import render_text
from .report import build_report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build a unified stock analysis bundle/report for stock-master skill.')
    parser.add_argument('symbol', help='Stock symbol, e.g. SH603966 or 603966')
    parser.add_argument('--days', type=int, default=120)
    parser.add_argument('--pretty', action='store_true')
    parser.add_argument('--format', choices=['json', 'text'], default='json')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.symbol, days=args.days)
    if args.format == 'text':
        print(render_text(report))
        return 0
    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(report, ensure_ascii=False))
    return 0
