import unittest
from datetime import date, timedelta

from pipeline.classification import evaluate_classifier, fit_logistic, label_efficiency
from pipeline.uci import TreatmentRow


def row(day, ss, target):
    return TreatmentRow(
        date=date(2024, 1, 1) + timedelta(days=day),
        features={"PH-E": 7.5, "COND-E": 1200, "SS-E": ss, "DQO-E": 300},
        target=target,
    )


class ClassificationTests(unittest.TestCase):
    def test_efficiency_label_uses_research_threshold(self):
        self.assertEqual(label_efficiency(49.99, 50), 1)
        self.assertEqual(label_efficiency(50, 50), 0)

    def test_logistic_classifier_predicts_risk_probability(self):
        training = [row(day, 100 + day * 20, 70 - day * 3) for day in range(8)]
        model = fit_logistic(training, threshold=50)

        probability = model.predict_proba({"PH-E": 7.5, "COND-E": 1200, "SS-E": 260, "DQO-E": 300})

        self.assertGreater(probability, 0.5)
        self.assertIn("PH-E", model.coefficients)

    def test_evaluation_reports_event_count_and_recall(self):
        training = [row(day, 100 + day * 20, 70 - day * 3) for day in range(8)]
        test = [row(8, 260, 46), row(9, 120, 58)]
        model = fit_logistic(training, threshold=50)

        metrics = evaluate_classifier(model, test)

        self.assertEqual(metrics["test_events"], 1)
        self.assertIn("recall", metrics)
        self.assertIn("precision", metrics)


if __name__ == "__main__":
    unittest.main()


