from __future__ import annotations

import os
import unittest
from pathlib import Path

from stock_master.datasource.backend import CommandBackend
from stock_master.datasource.providers import build_provider_map

RUN_LIVE = os.environ.get('STOCK_MASTER_RUN_LIVE') == '1'
LIVE_SYMBOL = os.environ.get('STOCK_MASTER_LIVE_SYMBOL', '603966')
DEFAULT_PYTHON_VENV = str(Path(__file__).resolve().parents[1] / '.venv' / 'bin' / 'python')


@unittest.skipUnless(RUN_LIVE, 'Set STOCK_MASTER_RUN_LIVE=1 to run live provider tests.')
class ProviderLiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        backend = CommandBackend(DEFAULT_PYTHON_VENV)
        availability = {
            'akshare': backend.check_module('akshare'),
            'adata': backend.check_module('adata'),
            'baostock': backend.check_module('baostock'),
            'opencli': backend.opencli_available,
        }
        cls.providers = build_provider_map(backend, availability)

    def assert_contract(self, result: object) -> None:
        self.assertTrue(result is False or isinstance(result, dict))

    def test_akshare_quote_and_kline(self) -> None:
        provider = self.providers['akshare']
        if not provider.available:
            self.skipTest('akshare not available')
        self.assert_contract(provider.get_quote(LIVE_SYMBOL))
        self.assert_contract(provider.get_kline(LIVE_SYMBOL, 10))

    def test_adata_search(self) -> None:
        provider = self.providers['adata']
        if not provider.available:
            self.skipTest('adata not available')
        result = provider.get_search(LIVE_SYMBOL)
        self.assert_contract(result)

    def test_baostock_kline(self) -> None:
        provider = self.providers['baostock']
        if not provider.available:
            self.skipTest('baostock not available')
        result = provider.get_kline(LIVE_SYMBOL, 10)
        self.assert_contract(result)

    def test_opencli_sector_list(self) -> None:
        provider = self.providers['opencli']
        if not provider.available:
            self.skipTest('opencli not available')
        result = provider.get_sector_list()
        self.assert_contract(result)


if __name__ == '__main__':
    unittest.main()
