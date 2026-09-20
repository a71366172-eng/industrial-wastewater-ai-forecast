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
  assert.ok(data.models['SS-S'].testSeries.length > 20);
  assert.ok(data.models['DQO-S'].testSeries.length > 20);
  assert.deepEqual(Object.keys(data.models['DQO-S'].testSeries[0]), ['date', 'actual', 'predicted']);
});

test('MOENV public summary is anonymized and loaded by the source page', () => {
  const summary = JSON.parse(readFileSync('frontend/public/data/moenv-ems-summary.json', 'utf8'));
  assert.equal(summary.source, 'MOENV EMS_S_03');
  assert.equal(summary.privacy, 'aggregated_no_facility_identity');
  assert.equal(summary.input_mode, 'public_preview');
  assert.equal(summary.reference_scenario.legal_interpretation, 'reference_only_not_compliance');
  assert.ok(summary.record_count > 0);
  assert.ok(summary.parameters.COD.count > 0);
  assert.ok(summary.parameters.SS.count > 0);
  assert.ok(summary.parameters.pH.count > 0);
  const serialized = JSON.stringify(summary);
  for (const privateField of ['plant_id', 'facility_name', 'address', 'permit_id', 'ems_no', 'fac_name', 'per_no']) {
    assert.doesNotMatch(serialized, new RegExp(privateField, 'i'));
  }
  const app = readFileSync('frontend/src/app-v4.js', 'utf8');
  assert.match(app, /moenv-ems-summary\.json/);
  assert.match(app, /情境基準內/);
  assert.match(app, /不是個別事業合規率/);
  assert.match(app, /moenv-trend-chart/);
  assert.match(app, /data-trend-param/);
  assert.match(app, /超過參考限值機率/);
  assert.match(app, /forecast-cod-probability/);
  assert.match(app, /data-page="trends"/);
  assert.match(app, /validation-trend-chart/);
  assert.match(app, /實際值/);
  assert.match(app, /預測值/);
});
test('monitoring cadence follows the official automatic monitoring profile', () => {
  const profile = JSON.parse(readFileSync('frontend/public/data/monitoring-profile.json', 'utf8'));
  assert.equal(profile.modelGridMinutes, 60);
  assert.equal(profile.parameters.pH.transmissionMinutes, 5);
  assert.equal(profile.parameters.conductivity.transmissionMinutes, 5);
  assert.equal(profile.parameters.COD.transmissionMinutes, 60);
  assert.equal(profile.parameters.SS.transmissionMinutes, 60);
  assert.equal(profile.status, 'awaiting_high_frequency_data');
  const app = readFileSync('frontend/src/app-v4.js', 'utf8');
  assert.match(app, /monitoring-profile\.json/);
  assert.match(app, /未來 1 小時/);
});
