import unittest
from datetime import datetime, timedelta, timezone

from pipeline.multihorizon import HourlyRow, build_examples, fit_horizon_model, split_examples


def row(hour, influent_cod=200, effluent_cod=50, effluent_ss=10):
    return HourlyRow(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hour),
        plant_id='P1', influent_ph=7.0, influent_conductivity=1000 + hour,
        influent_ss=100 + hour, influent_cod=influent_cod,
        effluent_ss=effluent_ss, effluent_cod=effluent_cod,
    )


class MultiHorizonTests(unittest.TestCase):
    def test_builds_one_three_six_hour_future_exceedance_labels(self):
        rows = [row(hour, effluent_cod=120 if hour == 5 else 50) for hour in range(12)]
        examples = build_examples(rows, horizons=(1, 3, 6), cod_limit=100, ss_limit=30)
        at_four = next(item for item in examples if item.timestamp.hour == 4)
        self.assertEqual(at_four.labels, {1: 1, 3: 1, 6: 1})
        at_one = next(item for item in examples if item.timestamp.hour == 1)
        self.assertEqual(at_one.labels, {1: 0, 3: 0, 6: 1})

    def test_future_outcome_changes_labels_but_never_current_features(self):
        normal = [row(hour) for hour in range(12)]
        event = [row(hour, effluent_cod=150 if hour == 5 else 50) for hour in range(12)]
        before = next(item for item in build_examples(normal) if item.timestamp.hour == 4)
        after = next(item for item in build_examples(event) if item.timestamp.hour == 4)
        self.assertEqual(before.features, after.features)
        self.assertNotEqual(before.labels, after.labels)

    def test_chronological_split_and_probability_model(self):
        rows = [row(hour, influent_cod=100 + hour * 10, effluent_cod=120 if hour % 5 == 0 else 50) for hour in range(80)]
        examples = build_examples(rows)
        train, validation, test = split_examples(examples)
        self.assertLess(max(item.timestamp for item in train), min(item.timestamp for item in validation))
        self.assertLess(max(item.timestamp for item in validation), min(item.timestamp for item in test))
        model = fit_horizon_model(train, horizon=3, steps=200)
        probability = model.predict_proba(test[0].features)
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)


if __name__ == '__main__':
    unittest.main()
