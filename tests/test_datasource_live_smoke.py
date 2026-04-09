from __future__ import annotations

import os
import unittest
from typing import Any

from stock_master.datasource import DataSource

RUN_LIVE = os.environ.get('STOCK_MASTER_RUN_LIVE') == '1'
LIVE_SYMBOL = os.environ.get('STOCK_MASTER_LIVE_SYMBOL', '603966')
LIVE_QUERY = os.environ.get('STOCK_MASTER_LIVE_QUERY', LIVE_SYMBOL)


def extract_rows(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [item for item in obj if isinstance(item, dict)]
    if isinstance(obj, dict):
        for key in ('items', 'rows', 'data', 'result', 'list'):
            value = obj.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def pick_sector_codes(rows: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in ('board_code', '板块代码', '代码', 'code', 'symbol', 'secid'):
            value = row.get(key)
            if value is None:
                continue
            text = str(value)
            if text not in seen:
                seen.append(text)
    return seen


@unittest.skipUnless(RUN_LIVE, 'Set STOCK_MASTER_RUN_LIVE=1 to run live datasource smoke tests.')
class DataSourceLiveSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ds = DataSource()

    def assert_payload(self, name: str, payload: Any) -> None:
        self.assertIsNotNone(payload, msg=f'{name} returned None')
        self.assertIsInstance(payload, dict, msg=f'{name} should return dict payload')

        if name in {'news', 'research', 'announcements'}:
            if payload.get('status') == 'placeholder':
                self.assertIn('fallback_path', payload, msg=f'{name} placeholder payload should expose fallback path')
                return
            self.assertEqual(payload.get('source'), 'merged')
            self.assertIsInstance(payload.get('sources'), list, msg=f'{name} merged payload should expose sources')
            self.assertIn('fallback_path', payload, msg=f'{name} merged payload should expose fallback path')
            return

        if payload.get('status') == 'empty':
            self.assertIn('fallback_path', payload, msg=f'{name} empty payload should expose fallback path')
            return

        self.assertTrue(
            payload.get('source') or payload.get('status') in {'ok', 'placeholder'},
            msg=f'{name} should expose source or status',
        )

    def test_live_fetches_public_capabilities(self) -> None:
        outputs: dict[str, Any] = {
            'search': self.ds.get_search(LIVE_QUERY),
            'quote': self.ds.get_quote(LIVE_SYMBOL),
            'snapshot': self.ds.get_snapshot(LIVE_SYMBOL),
            'kline': self.ds.get_kline(LIVE_SYMBOL, days=20),
            'intraday': self.ds.get_intraday(LIVE_SYMBOL),
            'money_flow': self.ds.get_money_flow(LIVE_SYMBOL),
            'north_flow': self.ds.get_north_flow(),
            'sector_flow': self.ds.get_sector_money_flow(),
            'financial': self.ds.get_financial(LIVE_SYMBOL),
            'report': self.ds.get_report(LIVE_SYMBOL),
            'announcements': self.ds.get_announcements(LIVE_SYMBOL),
            'sector_list': self.ds.get_sector_list(),
            'limit_up': self.ds.get_limit_up(),
            'limit_down': self.ds.get_limit_down(),
            'news': self.ds.get_news(LIVE_SYMBOL),
            'research': self.ds.get_research(LIVE_SYMBOL),
        }

        for name, payload in outputs.items():
            with self.subTest(capability=name):
                self.assert_payload(name, payload)

        sector_rows = extract_rows(outputs['sector_list'])
        sector_codes = pick_sector_codes(sector_rows) + ['BK0428', 'BK0145', 'BK1030']
        members = None
        for sector_code in sector_codes[:10]:
            members = self.ds.get_sector_members(sector_code)
            if members is not None and members.get('status') != 'empty':
                break
        if members is not None and members.get('status') != 'empty':
            self.assert_payload('sector_members', members)


if __name__ == '__main__':
    unittest.main()
