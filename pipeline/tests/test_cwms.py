import unittest
from urllib.parse import parse_qs, urlparse

from pipeline.cwms import (
    MetricMappingError,
    build_api_url,
    normalize_row,
    validate_rows,
)


def complete_row():
    return {
        "cno": "A001",
        "abbr": "示範對象",
        "dp_no": "DP01",
        "desp": "放流口",
        "m_date": "2026-09-17",
        "m_time": "08:00:00",
        "m_val": "72.5",
        "status": "正常",
        "unit": "mg/L",
        "std1": "90",
        "std2": "",
        "std_s": "研究用",
        "twd97x": "0",
        "twd97y": "0",
        "wgs84x": "120.0",
        "wgs84y": "23.5",
    }


class CwmsTests(unittest.TestCase):
    def test_api_url_requires_an_explicit_key(self):
        with self.assertRaisesRegex(ValueError, "MOENV_API_KEY is required"):
            build_api_url("wqx_p_50", "")

    def test_api_url_contains_official_query_parameters(self):
        url = build_api_url("wqx_p_50", "secret", limit=5)
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["format"], ["JSON"])
        self.assertEqual(query["limit"], ["5"])
        self.assertEqual(query["sort"], ["ImportDate desc"])
        self.assertEqual(query["api_key"], ["secret"])


    def test_reports_a_required_column_missing_from_any_row(self):
        incomplete = complete_row()
        del incomplete["m_val"]
        report = validate_rows([complete_row(), incomplete], metric_mapping=None)
        self.assertIn("m_val", report.missing_columns)
        self.assertFalse(report.can_publish)
    def test_unresolved_metric_mapping_cannot_be_published(self):
        report = validate_rows([complete_row()], metric_mapping=None)
        self.assertFalse(report.can_publish)
        self.assertEqual(report.metric_mapping_status, "unresolved")
        self.assertIn("metric mapping is unresolved", report.errors)


    def test_normalize_row_uses_taipei_offset_after_metric_mapping(self):
        result = normalize_row(
            complete_row(),
            {"metric_id": "cod", "metric_name": "化學需氧量（COD）"},
        )
        self.assertEqual(result["observed_at"], "2026-09-17T08:00:00+08:00")
        self.assertEqual(result["value"], 72.5)
    def test_normalize_row_requires_confirmed_metric_mapping(self):
        with self.assertRaises(MetricMappingError):
            normalize_row(complete_row(), None)


if __name__ == "__main__":
    unittest.main()
