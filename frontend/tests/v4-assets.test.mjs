import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('deployable v4 assets are included under frontend', () => {
  for (const path of [
    'frontend/index.html',
    'frontend/styles-v4.css',
    'frontend/src/app-v4.js',
    'frontend/src/effluent.js',
    'frontend/public/data/effluent-model-v4.json',
    'frontend/public/data/legal-profiles.json',
    'frontend/public/data/templates/chemical_plant_training_template.csv'
  ]) assert.equal(existsSync(path), true, path);
  assert.match(readFileSync('frontend/index.html', 'utf8'), /src\/app-v4\.js/);
  assert.match(readFileSync('frontend/src/app-v4.js', 'utf8'), /public\/data\/templates\/chemical_plant_training_template\.csv/);
});

test('chemical profile keeps the reviewed central limits and source', () => {
  const data = JSON.parse(readFileSync('frontend/public/data/legal-profiles.json', 'utf8'));
  const profile = data.profiles[0];
  assert.equal(profile.industry, '化工業');
  assert.equal(profile.dischargeRoute, 'surface_water');
  assert.deepEqual(profile.limits.ph, { kind: 'range', min: 6, max: 9, unit: 'pH' });
  assert.equal(profile.limits.ss.max, 30);
  assert.equal(profile.limits.cod.max, 100);
  assert.match(profile.source.attachmentUrl, /^https:\/\/oaout\.moenv\.gov\.tw\//);
});

test('effluent artifact cannot advertise production deployment', () => {
  const data = JSON.parse(readFileSync('frontend/public/data/effluent-model-v4.json', 'utf8'));
  assert.equal(data.deploymentStatus, 'research_only');
  assert.equal(data.models['SS-S'].metrics.beatsBaseline, false);
  assert.equal(data.models['DQO-S'].metrics.beatsBaseline, true);
});
