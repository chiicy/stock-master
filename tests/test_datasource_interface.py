from __future__ import annotations

import unittest

from stock_master.datasource.backend import CommandBackend
from stock_master.datasource.interface import StockDataProvider
from stock_master.datasource.providers import build_provider_map, order_providers, reorder_provider_sequence
from stock_master.datasource.providers.adata import AdataProvider
from stock_master.datasource.providers.akshare import AkshareProvider
from stock_master.datasource.providers.baostock import BaoStockProvider
from stock_master.datasource.providers.opencli import OpenCliProvider


class InterfaceContractTests(unittest.TestCase):
    def test_real_providers_implement_interface(self) -> None:
        for provider_cls in (AkshareProvider, AdataProvider, BaoStockProvider, OpenCliProvider):
            self.assertTrue(issubclass(provider_cls, StockDataProvider))

    def test_default_interface_methods_return_false(self) -> None:
        class EmptyProvider(StockDataProvider):
            name = 'empty'
            available = True

        provider = EmptyProvider()

        self.assertFalse(provider.get_quote('603966'))
        self.assertFalse(provider.get_kline('603966', 10))
        self.assertFalse(provider.get_income_statement('603966'))
        self.assertFalse(provider.get_announcements('603966'))
        self.assertFalse(provider.get_sector_members('BK0428'))

    def test_build_provider_map_and_ordering_follow_priority(self) -> None:
        backend = CommandBackend('/tmp/does-not-exist/python')
        provider_map = build_provider_map(
            backend,
            {
                'akshare': True,
                'adata': True,
                'baostock': True,
                'opencli': True,
            },
        )

        ordered = order_providers(provider_map, ['adata', 'opencli-xq', 'akshare'])

        self.assertIn('opencli', provider_map)
        self.assertIn('opencli-xq', provider_map)
        self.assertIn('opencli-dc', provider_map)
        self.assertIn('opencli-yahoo-finance', provider_map)
        self.assertEqual([provider.name for provider in ordered], ['adata', 'opencli-xq', 'akshare'])

    def test_reorder_provider_sequence_prefers_grouped_names_but_keeps_remaining_order(self) -> None:
        backend = CommandBackend('/tmp/does-not-exist/python')
        provider_map = build_provider_map(
            backend,
            {
                'akshare': True,
                'adata': True,
                'opencli': True,
            },
        )

        providers = [provider_map[name] for name in ['opencli-xueqiu', 'akshare', 'adata', 'opencli-iwc']]
        reordered = reorder_provider_sequence(providers, [['opencli-iwc'], ['akshare']])

        self.assertEqual([provider.name for provider in reordered], ['opencli-iwc', 'akshare', 'opencli-xueqiu', 'adata'])


if __name__ == '__main__':
    unittest.main()
