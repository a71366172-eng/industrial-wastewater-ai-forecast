import test from 'node:test';
import assert from 'node:assert/strict';

import {
  assessMaximum,
  assessRange,
  modelDeploymentState,
  predictEffluent
} from '../src/effluent.js';

const model = {
  features: ['PH-E', 'COND-E', 'SS-E', 'DQO-E'],
  metrics: { beatsBaseline: true, mae: 4 },
  parameters: {
    featureMedians: [7.8, 1400, 200, 400],
    featureMeans: [7.8, 1400, 200, 400],
    featureScales: [0.2, 300, 100, 120],
    coefficients: [1, 2, 3, 4],
    intercept: 20
  }
};

test('predicts effluent concentration from the exported array parameters', () => {
  assert.equal(predictEffluent(model, {
    'PH-E': 8.0,
    'COND-E': 1700,
    'SS-E': 300,
    'DQO-E': 520
  }), 30);
});

test('uses training medians for a missing feature without hiding validation', () => {
  assert.equal(predictEffluent(model, {
    'PH-E': '',
    'COND-E': 1400,
    'SS-E': 200,
    'DQO-E': 400
  }), 20);
});

test('classifies maximum limit using an operating warning ratio', () => {
  assert.equal(assessMaximum(18, 30).status, 'below');
  assert.equal(assessMaximum(27, 30).status, 'near');
  assert.equal(assessMaximum(31, 30).status, 'exceeds');
  assert.equal(assessMaximum(null, 30).status, 'unassessed');
});

test('pH without a prediction remains unassessed', () => {
  assert.equal(assessRange(null, 6, 9).status, 'unassessed');
  assert.equal(assessRange(9.2, 6, 9).status, 'exceeds');
});

test('a model that loses to baseline cannot be deployment ready', () => {
  assert.equal(modelDeploymentState({ metrics: { beatsBaseline: false } }).ready, false);
  assert.equal(modelDeploymentState(model).ready, true);
});
