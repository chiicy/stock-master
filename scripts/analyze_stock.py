#!/usr/bin/env python3
from __future__ import annotations

import sys

from _bootstrap import ensure_local_venv, ensure_src_path

ensure_local_venv(__file__, sys.argv[1:])
ensure_src_path()

from stock_master.analysis.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
