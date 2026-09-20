import csv
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.moenv_ems import (
    aggregate_public_summary,
    build_api_url,
    build_public_preview_request,
    download_records,
    download_public_preview_records,
    load_csv_records,
    normalize_api_record,
    redact_api_url,
)


class MoenvEmsTests(unittest.TestCase):
    def test_builds_paginated_official_api_url_and_redacts_key(self):
        url = build_api_url('secret-key', offset=1000, limit=1000, output_format='json')
        self.assertIn('/api/v2/EMS_S_03?', url)
        self.assertIn('offset=1000', url)
        self.assertIn('limit=1000', url)
        self.assertIn('api_key=secret-key', url)
        self.assertNotIn('secret-key', redact_api_url(url))
        self.assertIn('api_key=%2A%2A%2A', redact_api_url(url))

    def test_builds_public_preview_request_without_api_key(self):
        url, payload = build_public_preview_request(offset=20, limit=10)
        self.assertEqual(url, 'https://data.moenv.gov.tw/api/frontstage/datastore.search')
        self.assertEqual(payload['resource_id'], 'f3804119-2cf8-48f5-9df4-09008b5b4f7b')
        self.assertEqual(payload['offset'], 20)
        self.assertEqual(payload['limit'], 10)
        self.assertNotIn('api_key', payload)

    def test_public_preview_download_stops_after_short_page(self):
        offsets = []

        def fake_fetcher(*, offset, limit):
            offsets.append(offset)
            count = 2 if offset == 0 else 1
            return [{'parameter': 'COD', 'value': 50 + index, 'unit': 'mg/l'} for index in range(count)]

        records = download_public_preview_records(page_size=2, max_pages=5, fetcher=fake_fetcher)
        self.assertEqual(len(records), 3)
        self.assertEqual(offsets, [0, 2])

    def test_download_stops_after_short_page_without_logging_key(self):
        offsets = []

        def fake_fetcher(api_key, *, offset, limit):
            offsets.append(offset)
            return [{'parameter': 'COD', 'value': offset + index, 'unit': 'mg/L'} for index in range(2 if offset == 0 else 1)]

        records = download_records('secret-key', page_size=2, max_pages=5, fetcher=fake_fetcher)
        self.assertEqual(len(records), 3)
        self.assertEqual(offsets, [0, 2])

    def test_normalizes_api_fields_case_insensitively(self):
        record = normalize_api_record({
            'ems_no': 'A01',
            'fac_name': '工廠',
            'emi_item': '化學需氧量',
            'emi_value': '72.5',
            'emi_units': 'mg/L',
            'emi_sdate': '2026-01-01',
            'emi_edate': '2026-03-31',
            'let_watertype': '河川',
        })
        self.assertEqual(record['plant_id'], 'A01')
        self.assertEqual(record['parameter'], 'COD')
        self.assertEqual(record['value'], 72.5)
        self.assertEqual(record['temporal_resolution'], 'reporting_period')

    def test_loads_official_csv_with_bom_and_lowercase_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ems.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['ems_no', 'emi_item', 'emi_value', 'emi_units'])
                writer.writeheader()
                writer.writerow({'ems_no': 'A01', 'emi_item': '懸浮固體', 'emi_value': '20', 'emi_units': 'mg/L'})
            records = load_csv_records(path)
        self.assertEqual(records[0]['parameter'], 'SS')
        self.assertEqual(records[0]['value'], 20.0)

    def test_public_summary_contains_no_facility_identity(self):
        records = [
            {'plant_id': 'EMS-A-001', 'facility_name': '甲化工測試廠', 'address': '臺北市測試路1號', 'permit_id': 'PERMIT-001', 'parameter': 'COD', 'value': 60.0, 'unit': 'mg/L'},
            {'plant_id': 'EMS-B-002', 'facility_name': '乙化工測試廠', 'address': '高雄市測試路2號', 'permit_id': 'PERMIT-002', 'parameter': 'COD', 'value': 80.0, 'unit': 'mg/L'},
            {'plant_id': 'EMS-A-001', 'facility_name': '甲化工測試廠', 'address': '臺北市測試路1號', 'permit_id': 'PERMIT-001', 'parameter': 'SS', 'value': 20.0, 'unit': 'mg/L'},
        ]
        summary = aggregate_public_summary(records)
        self.assertEqual(summary['parameters']['COD']['count'], 2)
        self.assertEqual(summary['parameters']['COD']['median'], 70.0)
        serialized = str(summary)
        for private_value in ('EMS-A-001', 'EMS-B-002', '甲化工測試廠', '乙化工測試廠', 'PERMIT-001', 'PERMIT-002', '臺北市測試路1號', '高雄市測試路2號'):
            self.assertNotIn(private_value, serialized)


if __name__ == '__main__':
    unittest.main()
