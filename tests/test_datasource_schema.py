from __future__ import annotations

import unittest

from stock_master.datasource.schema import ensure_payload_contract, ensure_record_contract, wrap_placeholder_payload


class DataSourceSchemaTests(unittest.TestCase):
    def test_quote_payload_contract_preserves_common_fields_and_collects_extensions(self) -> None:
        payload = ensure_payload_contract(
            {
                'symbol': '603966',
                'price': 13.9,
                '最新价': 13.9,
                'provider_rank': 1,
            },
            capability='quote',
            symbol='603966',
            source_channel='opencli-xq.quote',
        )

        self.assertEqual(payload['symbol'], 'SH603966')
        self.assertEqual(payload['capability'], 'quote')
        self.assertEqual(payload['market'], 'a_share')
        self.assertEqual(payload['source_channel'], 'opencli-xq.quote')
        self.assertEqual(payload['meta']['schema_version'], 1)
        self.assertEqual(payload['extensions'], {'provider_rank': 1})

    def test_record_contract_keeps_raw_row_and_does_not_treat_id_as_extension(self) -> None:
        record = ensure_record_contract(
            {
                'id': 'news-1',
                'title': '市场快讯',
                'custom_score': 0.8,
            },
            capability='news',
            kind='news',
            source_channel='sinafinance.news',
            include_raw=True,
        )

        self.assertEqual(record['id'], 'news-1')
        self.assertEqual(record['kind'], 'news')
        self.assertEqual(record['meta']['capability'], 'news')
        self.assertEqual(record['extensions'], {'custom_score': 0.8})
        self.assertEqual(record['raw']['title'], '市场快讯')
        self.assertNotIn('id', record['extensions'])

    def test_items_container_rows_are_normalized_with_default_kind(self) -> None:
        payload = ensure_payload_contract(
            {
                'symbol': 'AAPL',
                'items': [{'title': 'Coverage update'}],
            },
            capability='research',
        )

        self.assertEqual(payload['capability'], 'research')
        self.assertEqual(payload['meta']['primary_container'], 'items')
        self.assertEqual(payload['items'][0]['kind'], 'research')
        self.assertEqual(payload['items'][0]['meta']['capability'], 'research')

    def test_placeholder_payload_uses_same_envelope(self) -> None:
        payload = wrap_placeholder_payload(
            capability='news',
            symbol='603966',
            note='消息面暂缺',
            fallback_path=['akshare', 'opencli-sinafinance'],
        )

        self.assertEqual(payload['status'], 'placeholder')
        self.assertEqual(payload['symbol'], 'SH603966')
        self.assertEqual(payload['capability'], 'news')
        self.assertEqual(payload['meta']['schema_version'], 1)
        self.assertEqual(payload['fallback_path'], ['akshare', 'opencli-sinafinance'])


if __name__ == '__main__':
    unittest.main()
