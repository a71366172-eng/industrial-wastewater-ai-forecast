import tempfile
import unittest
from pathlib import Path

from pipeline.release_check import check_release


class ReleaseCheckTests(unittest.TestCase):
    def test_release_requires_v2_entry_model_and_risk_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontend").mkdir()
            (root / "frontend" / "index.html").write_text('src/app-v3.js', encoding="utf-8")
            (root / "frontend" / "public").mkdir()
            (root / "frontend" / "public" / "data").mkdir()
            (root / "frontend" / "public" / "data" / "uci-model.json").write_text(
                '{"schema_version":"2.0","risk":{"metrics":{"recall":0.1}}}', encoding="utf-8"
            )

            result = check_release(root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_release_reports_missing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontend").mkdir()
            (root / "frontend" / "index.html").write_text('src/app-v3.js', encoding="utf-8")

            result = check_release(root)

        self.assertFalse(result["ok"])
        self.assertIn("model artifact is missing", result["errors"])


if __name__ == "__main__":
    unittest.main()

