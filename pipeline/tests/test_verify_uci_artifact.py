import unittest

from pipeline.verify_uci_artifact import artifacts_match


class ArtifactVerificationTests(unittest.TestCase):
    def test_generated_time_does_not_make_reproducible_artifacts_different(self):
        expected = {"generated_at": "2026-01-01T00:00:00Z", "model": {"alpha": 1}, "metrics": {"mae": 2}}
        actual = {"generated_at": "2026-02-01T00:00:00Z", "model": {"alpha": 1}, "metrics": {"mae": 2}}

        self.assertTrue(artifacts_match(expected, actual))

    def test_tiny_cross_platform_float_difference_is_accepted(self):
        expected = {"generated_at": "a", "model": {"coefficient": 1.000000000001}, "values": [2.0]}
        actual = {"generated_at": "b", "model": {"coefficient": 1.000000000002}, "values": [2.000000000001]}

        self.assertTrue(artifacts_match(expected, actual))
    def test_model_change_is_detected(self):
        expected = {"generated_at": "a", "model": {"alpha": 1}}
        actual = {"generated_at": "b", "model": {"alpha": 10}}

        self.assertFalse(artifacts_match(expected, actual))


if __name__ == "__main__":
    unittest.main()
