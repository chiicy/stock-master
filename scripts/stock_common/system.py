#!/usr/bin/env python3
from __future__ import annotations

import shutil


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None
