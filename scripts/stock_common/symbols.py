#!/usr/bin/env python3
from __future__ import annotations

import re


def normalize_symbol(symbol: str) -> str:
    text = str(symbol).strip().upper()
    if re.fullmatch(r'\d{6}', text):
        if text.startswith(('6', '9')):
            return f'SH{text}'
        if text.startswith(('0', '3')):
            return f'SZ{text}'
        if text.startswith(('4', '8')):
            return f'BJ{text}'
    return text


def code_only(symbol: str) -> str:
    return re.sub(r'^(SH|SZ|BJ)', '', normalize_symbol(symbol))
