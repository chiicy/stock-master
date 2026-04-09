from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
REQUIRED_MODULES = ("akshare", "adata", "baostock")


def ensure_local_venv(script_path: str, argv: Sequence[str]) -> None:
    if not VENV_PYTHON.exists() or Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    try:
        for module_name in REQUIRED_MODULES:
            __import__(module_name)
    except ModuleNotFoundError:
        raise SystemExit(subprocess.call([str(VENV_PYTHON), str(Path(script_path).resolve()), *argv]))


def ensure_src_path() -> None:
    src_path = str(SRC)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
