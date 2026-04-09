#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Protocol, TypeAlias

from stock_master.datasource import DataSource
from stock_master.common.symbols import normalize_symbol

from .summaries import (
    summarize_capital,
    summarize_fundamental,
    summarize_news,
    summarize_prediction,
    summarize_technical,
)

BundlePayload: TypeAlias = dict[str, Any]
ReportPayload: TypeAlias = dict[str, Any]


class BundleSource(Protocol):
    def get_bundle(self, symbol: str, days: int = 120) -> BundlePayload: ...


def build_report(symbol: str, days: int = 120, datasource: BundleSource | None = None) -> ReportPayload:
    ds = datasource or DataSource()
    bundle = ds.get_bundle(symbol, days=days)
    technical = summarize_technical(bundle)
    capital = summarize_capital(bundle)
    fundamental = summarize_fundamental(bundle)
    news = summarize_news(bundle)
    prediction = summarize_prediction(technical, capital, fundamental)
    return {
        'symbol': normalize_symbol(symbol),
        'data_snapshot': {
            'quote': bundle.get('quote'),
            'snapshot': bundle.get('snapshot'),
        },
        'technical': technical,
        'fundamental': fundamental,
        'capital_flow': capital,
        'news': news,
        'prediction': prediction,
        'raw_bundle': bundle,
    }
