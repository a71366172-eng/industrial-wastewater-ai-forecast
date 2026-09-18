import test from 'node:test';
import assert from 'node:assert/strict';
import { getFreshness, validateManifest } from '../src/data.js';

test('rejects a manifest without version and generated time', () => {
  const result = validateManifest({ mode: 'demo' });
  assert.equal(result.ok, false);
  assert.deepEqual(result.errors, ['schema_version is required', 'generated_at is required']);
});

test('marks a snapshot stale after valid_until', () => {
  const manifest = {
    generated_at: '2026-09-17T08:00:00+08:00',
    valid_until: '2026-09-17T09:00:00+08:00'
  };
  assert.equal(getFreshness(manifest, new Date('2026-09-17T01:30:00Z')), 'stale');
});
