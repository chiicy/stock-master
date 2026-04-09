from __future__ import annotations

import json

from stock_master.analysis.cli import main as analyze_main
from stock_master.datasource import DataSource


def diagnostics_main() -> int:
    print(json.dumps(DataSource().diagnostics(), ensure_ascii=False, indent=2))
    return 0


__all__ = ['analyze_main', 'diagnostics_main']
