#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
VENV_PYTHON = ROOT / '.venv' / 'bin' / 'python'


def _ensure_local_venv() -> None:
    if not VENV_PYTHON.exists() or Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    try:
        import akshare  # noqa: F401
        import adata  # noqa: F401
        import baostock  # noqa: F401
    except ModuleNotFoundError:
        raise SystemExit(
            __import__('subprocess').call([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
        )


_ensure_local_venv()

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stock_master.analysis.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
