#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from stock_common.system import command_exists


class CommandBackend:
    """Thin subprocess/backend wrapper for provider adapters."""

    def __init__(
        self,
        python_venv: str,
        opencli_command: str = 'opencli',
        module_root: str | None = None,
        command_exists_fn: Callable[[str], bool] = command_exists,
    ) -> None:
        self.python_venv = python_venv
        self.opencli_command = opencli_command
        self.module_root = module_root or str(Path(__file__).resolve().parents[1])
        self._command_exists = command_exists_fn
        self.opencli_available = command_exists_fn(opencli_command)

    def check_module(self, name: str) -> bool:
        try:
            out = subprocess.run(
                [self.python_bin(), '-c', f'import importlib; importlib.import_module({name!r})'],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception:
            return False
        return out.returncode == 0

    def run_json(self, args: list[str], timeout: int = 60, cwd: str | None = None) -> Any:
        try:
            out = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        except Exception:
            return None
        if out.returncode != 0:
            return None
        text = out.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            if not line.startswith(('{', '[')):
                continue
            try:
                return json.loads(line)
            except Exception:
                continue
        return text

    def opencli_json(self, *parts: str) -> Any:
        if not self.opencli_available:
            return None
        return self.run_json([self.opencli_command, *parts, '-f', 'json'], timeout=90)

    def python_bin(self) -> str:
        return self.python_venv if os.path.exists(self.python_venv) else 'python3'

    def run_module_json(self, module: str, action: str, payload: dict[str, Any], timeout: int = 90) -> Any:
        return self.run_json(
            [self.python_bin(), '-m', module, action, json.dumps(payload, ensure_ascii=False)],
            timeout=timeout,
            cwd=self.module_root,
        )
