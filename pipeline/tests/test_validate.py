import json
import tempfile
import unittest
from pathlib import Path

from pipeline.validate import validate_file


class ValidateCliTests(unittest.TestCase):
    def test_local_file_without_metric_mapping_creates_non_publishable_report(self):
        row = {
            "cno": "A001", "abbr": "示範", "dp_no": "DP01", "desp": "放流口",
            "m_date": "2026-09-17", "m_time": "08:00:00", "m_val": "72.5",
            "status": "正常", "unit": "mg/L", "std1": "90", "std2": "",
            "std_s": "研究用", "twd97x": "0", "twd97y": "0", "wgs84x": "120", "wgs84y": "23",
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "rows.json"
            output_path = Path(directory) / "report.json"
            input_path.write_text(json.dumps([row]), encoding="utf-8")
            report = validate_file(input_path, output_path)
            self.assertFalse(report["can_publish"])
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["metric_mapping_status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
