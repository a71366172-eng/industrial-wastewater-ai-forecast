import test from 'node:test';
import assert from 'node:assert/strict';
import { buildStatusText, forecastDisplay } from '../src/app.js';

test('explains that a stale snapshot pauses the current forecast', () => {
  assert.equal(buildStatusText('stale'), '資料已過期，暫停顯示為當前預報');
});

test('hides the current forecast value when a snapshot is stale', () => {
  assert.deepEqual(forecastDisplay('stale', 76, 'mg/L'), { value: '—', label: '資料已過期，暫停顯示為當前預報' });
});
