import unittest
from datetime import date, timedelta

from pipeline.train_uci import build_artifact
from pipeline.uci import TreatmentRow


def sample(day):
    return TreatmentRow(
        date=date(2024, 1, 1) + timedelta(days=day),
        features={
            "PH-E": 7.0 + day / 100,
            "COND-E": 1000 + day * 10,
            "SS-E": 100 + day * 2,
            "DQO-E": 200 + day * 3,
        },
        target=40 + day,
    )


class TrainingArtifactTests(unittest.TestCase):
    def test_artifact_exposes_reproducible_model_and_historical_test_cases(self):
        artifact = build_artifact([sample(day) for day in range(20)], {"raw_rows": 20})

        self.assertEqual(artifact["schema_version"], "2.0")
        self.assertEqual(artifact["target"]["field"], "RD-SS-P")
        self.assertEqual(len(artifact["features"]), 4)
        self.assertEqual(artifact["split"], {"train": 12, "validation": 4, "test": 4})
        self.assertEqual(len(artifact["test_cases"]), 4)
        self.assertIn("model_mae", artifact["metrics"])
        self.assertIn("baseline_mae", artifact["metrics"])
        self.assertIn("coefficients", artifact["model"])
        self.assertEqual(artifact["mode"], "historical-research")


if __name__ == "__main__":
    unittest.main()
