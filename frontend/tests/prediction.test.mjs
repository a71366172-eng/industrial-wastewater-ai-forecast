import test from 'node:test';
import assert from 'node:assert/strict';

import { assessEfficiency, predictEfficiency, predictRiskProbability, validateInputs } from '../src/prediction.js';

const artifact = {
  features: [
    { field: 'PH-E', min: 6.9, max: 8.7 },
    { field: 'COND-E', min: 651, max: 3230 },
    { field: 'SS-E', min: 98, max: 2008 },
    { field: 'DQO-E', min: 81, max: 941 }
  ],
  target: { warning_threshold: 50 },
  model: {
    intercept: 55,
    medians: { 'PH-E': 7.8, 'COND-E': 1400, 'SS-E': 220, 'DQO-E': 400 },
    means: { 'PH-E': 7.8, 'COND-E': 1400, 'SS-E': 220, 'DQO-E': 400 },
    scales: { 'PH-E': 0.2, 'COND-E': 300, 'SS-E': 100, 'DQO-E': 120 },
    coefficients: { 'PH-E': 1, 'COND-E': 2, 'SS-E': -3, 'DQO-E': -4 }
  }
};

test('predicts the exported ridge model in the browser', () => {
  const value = predictEfficiency(artifact, {
    'PH-E': 8.0,
    'COND-E': 1700,
    'SS-E': 320,
    'DQO-E': 520
  });

  assert.equal(value, 51);
});

test('reports missing and out-of-range inputs before prediction', () => {
  const result = validateInputs(artifact.features, {
    'PH-E': '',
    'COND-E': 4000,
    'SS-E': 220,
    'DQO-E': 400
  });

  assert.equal(result.ok, false);
  assert.deepEqual(result.missing, ['PH-E']);
  assert.deepEqual(result.outOfRange, ['COND-E']);
});

test('classifies efficiency below the research threshold as attention', () => {
  assert.deepEqual(assessEfficiency(49.9, 50), {
    level: 'attention',
    label: '需注意',
    message: '估計效率低於研究門檻，建議複測並檢查初沉池操作。'
  });
});


test('predicts exported risk probability within probability bounds', () => {
  const probability = predictRiskProbability({ model: artifact.model }, { 'PH-E': 8.0, 'COND-E': 1700, 'SS-E': 320, 'DQO-E': 520 });
  assert.equal(typeof probability, 'number');
  assert.ok(probability >= 0 && probability <= 1);
});

