import tempfile
import unittest
from pathlib import Path

from pipeline.uci import FEATURES, TARGET, load_dataset, parse_row


class UciDatasetTests(unittest.TestCase):
    def test_parse_row_maps_only_the_four_influent_features_and_efficiency_target(self):
        fields = ["1"] * 39
        fields[0] = "D-1/3/90"
        fields[3] = "7.8"
        fields[5] = "407"
        fields[6] = "166"
        fields[9] = "2110"
        fields[31] = "58.8"

        row = parse_row(",".join(fields))

        self.assertEqual(row.date.isoformat(), "1990-03-01")
        self.assertEqual(
            row.features,
            {"PH-E": 7.8, "COND-E": 2110.0, "SS-E": 166.0, "DQO-E": 407.0},
        )
        self.assertEqual(row.target, 58.8)
        self.assertEqual(FEATURES, ("PH-E", "COND-E", "SS-E", "DQO-E"))
        self.assertEqual(TARGET, "RD-SS-P")

    def test_parse_row_keeps_missing_values_explicit(self):
        fields = ["1"] * 39
        fields[0] = "D-2/3/90"
        fields[3] = "7.7"
        fields[5] = "?"
        fields[6] = "214"
        fields[9] = "2660"
        fields[31] = "?"

        row = parse_row(",".join(fields))

        self.assertIsNone(row.features["DQO-E"])
        self.assertIsNone(row.target)

    def test_load_dataset_sorts_dates_and_reports_unusable_rows(self):
        first = ["1"] * 39
        first[0], first[3], first[5], first[6], first[9], first[31] = (
            "D-2/3/90", "7.7", "443", "214", "2660", "60.7"
        )
        second = ["1"] * 39
        second[0], second[3], second[5], second[6], second[9], second[31] = (
            "D-1/3/90", "7.8", "407", "166", "2110", "58.8"
        )
        unusable = ["1"] * 39
        unusable[0], unusable[3], unusable[5], unusable[6], unusable[9], unusable[31] = (
            "D-3/3/90", "7.9", "450", "220", "2500", "?"
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.data"
            path.write_text("\n".join([",".join(first), ",".join(second), ",".join(unusable)]), encoding="utf-8")
            dataset = load_dataset(path)

        self.assertEqual([row.date.isoformat() for row in dataset.rows], ["1990-03-01", "1990-03-02"])
        self.assertEqual(dataset.report["raw_rows"], 3)
        self.assertEqual(dataset.report["usable_rows"], 2)
        self.assertEqual(dataset.report["missing_target_rows"], 1)


if __name__ == "__main__":
    unittest.main()
