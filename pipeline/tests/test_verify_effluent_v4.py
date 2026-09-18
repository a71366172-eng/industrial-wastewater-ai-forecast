import json
import tempfile
import unittest
from pathlib import Path

from pipeline.verify_effluent_v4 import verify_artifacts


class EffluentV4VerificationTests(unittest.TestCase):
    def test_current_effluent_and_legal_artifacts_are_reproducible(self):
        report = verify_artifacts(
            Path('data/public/water-treatment.data'),
            Path('frontend/public/data/effluent-model-v4.json'),
            Path('frontend/public/data/legal-profiles.json'),
        )
        self.assertTrue(report['ok'], report)

    def test_tampered_limit_is_rejected(self):
        profile = json.loads(Path('frontend/public/data/legal-profiles.json').read_text(encoding='utf-8'))
        profile['profiles'][0]['limits']['ss']['max'] = 999
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profiles.json'
            path.write_text(json.dumps(profile), encoding='utf-8')
            report = verify_artifacts(
                Path('data/public/water-treatment.data'),
                Path('frontend/public/data/effluent-model-v4.json'),
                path,
            )
        self.assertFalse(report['ok'])
        self.assertIn('SS 中央基準必須為 30 mg/L', report['errors'])


if __name__ == '__main__':
    unittest.main()
