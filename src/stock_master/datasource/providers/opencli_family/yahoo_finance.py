from __future__ import annotations

from stock_master.common.symbols import normalize_symbol

from ...interface import ProviderResult
from .base import OpenCliFamilyProvider


class OpenCliYahooFinanceProvider(OpenCliFamilyProvider):
    def __init__(self, backend, available: bool) -> None:
        super().__init__("opencli-yahoo-finance", backend, available)

    def get_quote(self, symbol: str) -> ProviderResult:
        normalized = normalize_symbol(symbol)
        if self._is_a_share_symbol(normalized):
            return False
        result = self._opencli_json("yahoo-finance", "quote", normalized)
        if result is False:
            return False
        return self._normalize_quote_payload(result, symbol=symbol, source_channel="yahoo-finance.quote")
