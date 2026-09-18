import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

test('repository skeleton includes package scripts and workflows', () => {
  for (const path of [
    'package.json',
    '.github/workflows/ci.yml',
    '.github/workflows/deploy.yml'
  ]) assert.equal(existsSync(path), true, path);
});
