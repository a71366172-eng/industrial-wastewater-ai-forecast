import unittest
from datetime import date, timedelta

from pipeline.modeling import evaluate, fit_ridge, split_chronologically
from pipeline.uci import FEATURES, TreatmentRow


def sample(day, ph, conductivity, ss, cod, target):
    return TreatmentRow(
        date=date(2024, 1, 1) + timedelta(days=day),
        features={"PH-E": ph, "COND-E": conductivity, "SS-E": ss, "DQO-E": cod},
        target=target,
    )


class ModelingTests(unittest.TestCase):
    def test_split_chronologically_keeps_future_rows_out_of_training(self):
        rows = [sample(day, 7.0, 1000, 100, 200, 40 + day) for day in range(10)]

        train, validation, test = split_chronologically(rows)

        self.assertEqual([len(train), len(validation), len(test)], [6, 2, 2])
        self.assertLess(max(row.date for row in train), min(row.date for row in validation))
        self.assertLess(max(row.date for row in validation), min(row.date for row in test))

    def test_ridge_uses_training_medians_for_missing_inputs(self):
        rows = [
            sample(0, 7.0, 1000, 100, 200, 20),
            sample(1, 8.0, 2000, 200, 300, 40),
            sample(2, None, 3000, 300, 400, 60),
        ]

        model = fit_ridge(rows, alpha=1.0)

        self.assertEqual(model.medians["PH-E"], 7.5)
        prediction = model.predict({"PH-E": None, "COND-E": 1000, "SS-E": 100, "DQO-E": 200})
        self.assertIsInstance(prediction, float)

    def test_evaluate_compares_model_with_training_median_baseline(self):
        train = [
            sample(day, 7 + day / 100, 1000 + day, 100 + day, 200 + day, 10 + 2 * day)
            for day in range(8)
        ]
        test = [sample(8, 7.08, 1008, 108, 208, 26), sample(9, 7.09, 1009, 109, 209, 28)]
        model = fit_ridge(train, alpha=0.01)

        metrics = evaluate(model, train, test)

        self.assertEqual(metrics["test_rows"], 2)
        self.assertAlmostEqual(metrics["baseline_mae"], 10.0)
        self.assertLess(metrics["model_mae"], metrics["baseline_mae"])
        self.assertEqual(tuple(model.feature_names), FEATURES)


if __name__ == "__main__":
    unittest.main()

