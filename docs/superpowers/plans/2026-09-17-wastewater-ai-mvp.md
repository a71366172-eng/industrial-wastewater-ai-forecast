# 工業廢水放流水 AI 預報 MVP 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立一個可在本機與 GitHub Pages 使用的放流水水質預報展示 MVP，先以固定公開格式的示範資料驗證前端、資料契約與過期狀態，再接入真實資料管線。

**Architecture:** 網站是零依賴的靜態 HTML/CSS/JavaScript，從 `public/data/manifest.json` 讀取版本化快照。純函式資料層負責驗證快照與計算顯示狀態，前端只呈現資料，不在瀏覽器訓練或呼叫含機密的來源 API。Python 管線與 GitHub Actions 先建立目錄與契約位置，等資料驗證關卡通過後再接入。

**Tech Stack:** HTML、CSS、原生 JavaScript、Node.js 內建 `node:test`、Python 3.11（後續資料管線）、GitHub Pages／Actions（部署檔先備妥）。

## Global Constraints

- 第一版只使用示範資料；每個示範值在網站上標示為「示範資料」，不得冒充環境部實測結果。
- 不在前端放置 API 金鑰、完整原始資料、私人資料或訓練模型二進位檔。
- 所有時間使用含時區的 ISO 8601 格式，介面顯示臺灣時間。
- 缺值使用 `null`；過期資料顯示過期狀態並停止呈現為當前預報。
- 每個生產函式先寫一個會正確失敗的測試，再以最小實作通過測試。
- 本輪不建立遠端 GitHub 儲存庫、不推送、不發布公開網站。

---

### Task 1: 建立資料契約與純函式資料層

**Files:**
- Create: `frontend/src/data.js`
- Create: `frontend/tests/data.test.mjs`
- Create: `frontend/public/data/manifest.json`
- Create: `frontend/public/data/observations.json`
- Create: `frontend/public/data/forecasts.json`
- Create: `frontend/public/data/events.json`

**Interfaces:**
- `validateManifest(manifest) -> { ok: true, value } | { ok: false, errors: string[] }`
- `getFreshness(manifest, now = new Date()) -> 'fresh' | 'stale' | 'unknown'`
- `formatTaipeiTime(isoString) -> string`
- `summarizeForecast(forecast, threshold) -> { value, status, label }`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { getFreshness, validateManifest } from '../src/data.js';

test('rejects a manifest without version and generated time', () => {
  const result = validateManifest({ mode: 'demo' });
  assert.equal(result.ok, false);
  assert.deepEqual(result.errors, ['schema_version is required', 'generated_at is required']);
});

test('marks a snapshot stale after valid_until', () => {
  const manifest = { generated_at: '2026-09-17T08:00:00+08:00', valid_until: '2026-09-17T09:00:00+08:00' };
  assert.equal(getFreshness(manifest, new Date('2026-09-17T01:30:00Z')), 'stale');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test frontend/tests/data.test.mjs`

Expected: FAIL because `frontend/src/data.js` does not exist yet.

- [ ] **Step 3: Write the minimal implementation and demo data**

Implement the four named functions with no network calls. Require `schema_version`, `generated_at`, and `valid_until`; compare `valid_until` to `now`; return `unknown` for invalid dates. Use one demo station, one demo metric, six observations, three forecasts, and one clearly labeled research event.

- [ ] **Step 4: Run the focused test and full test command**

Run: `node --test frontend/tests/data.test.mjs`

Expected: PASS with 2 tests and 0 failures. Keep the test output free of warnings.

### Task 2: Build the monitoring dashboard

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`
- Create: `frontend/src/app.js`
- Create: `frontend/tests/app.test.mjs`

**Interfaces:**
- `renderStatus(manifest, now) -> HTMLElement`
- `renderTrend(observations, forecasts, threshold) -> SVGElement`
- `renderEvents(events) -> HTMLElement`

- [ ] **Step 1: Write the failing rendering test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildStatusText } from '../src/app.js';

test('explains that a stale snapshot pauses the current forecast', () => {
  assert.equal(buildStatusText('stale'), '資料已過期，暫停顯示為當前預報');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test frontend/tests/app.test.mjs`

Expected: FAIL because `buildStatusText` is not defined.

- [ ] **Step 3: Implement the minimal UI**

Create five visible areas from the plan: monitoring overview, trend and forecast, anomaly events, model performance, and data/project notes. Use a water-instrument visual language: pale water background, dark navy text, cyan observed line, indigo forecast line, amber warning, and explicit text labels. Render the release-time boundary between observations and forecasts. Include a station/metric selector, freshness badge, responsive layout, keyboard-visible focus, and a table fallback for the SVG trend.

- [ ] **Step 4: Run tests and a browser-independent smoke check**

Run: `node --test frontend/tests/*.test.mjs`

Expected: PASS with all tests green. Then verify `frontend/index.html` references only local assets and the demo JSON paths.

### Task 3: Add local validation and GitHub Pages workflow scaffolding

**Files:**
- Create: `package.json`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy.yml`
- Create: `README.md`
- Create: `docs/data-contract.md`

**Interfaces:**
- `npm test` runs every `frontend/tests/*.test.mjs` file.
- CI runs `npm test` and rejects missing demo data files.
- Deploy builds a static artifact from `frontend/` and publishes it through GitHub Pages when enabled by the repository owner.

- [ ] **Step 1: Write the failing repository smoke test**

Add `frontend/tests/repository.test.mjs`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';

test('demo snapshot includes the required files', () => {
  for (const path of [
    'frontend/index.html',
    'frontend/public/data/manifest.json',
    'frontend/public/data/observations.json',
    'frontend/public/data/forecasts.json'
  ]) assert.equal(existsSync(path), true, path);
});
```

- [ ] **Step 2: Run the repository test to verify it fails**

Run: `node --test frontend/tests/repository.test.mjs`

Expected: FAIL until the listed files are present.

- [ ] **Step 3: Add package scripts and workflows**

Set `npm test` to `node --test frontend/tests/*.test.mjs`. The CI workflow runs on pull requests and pushes to `main`, installs no external dependencies, and executes `npm test`. The deploy workflow is manually triggerable and runs the same test before uploading `frontend/` as the Pages artifact. Leave workflow permissions minimal and do not add secrets.

- [ ] **Step 4: Run the full local verification**

Run: `npm test`

Expected: PASS with all tests green. Run a text check that no `.env`, token-looking value, or `node_modules` path is tracked by the planned files.

### Task 4: Document handoff and update project progress

**Files:**
- Modify: `專案計畫書.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `README.md`

- [ ] **Step 1: Record the MVP boundary**

Document that this milestone uses demo data, static frontend assets, and manual deployment; real data ingestion, model training, and remote repository setup remain gated by the data validation checkpoint.

- [ ] **Step 2: Verify documentation links and commands**

Run: `npm test` and inspect every local path referenced by `README.md`.

- [ ] **Step 3: Record verification evidence**

Append the exact test command, pass count, files created, and known limitations to `progress.md`.

## Self-review checklist

- [ ] Every production function has a test that was observed failing first.
- [ ] Demo data is visibly labeled and cannot be confused with official measurements.
- [ ] The UI has an explicit stale-data state and a table fallback.
- [ ] GitHub workflows do not require secrets for the demo milestone.
- [ ] The implementation does not claim that a remote repository or public website exists.
