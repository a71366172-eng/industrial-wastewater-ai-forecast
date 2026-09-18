import {
  formatTaipeiTime,
  getFreshness,
  summarizeForecast,
  validateManifest
} from './data.js';

export function buildStatusText(status) {
  if (status === 'fresh') return '資料在有效期間內';
  if (status === 'stale') return '資料已過期，暫停顯示為當前預報';
  return '資料新鮮度未知，僅供歷史回放';
}

export function forecastDisplay(status, value, unit) {
  if (status !== 'fresh') return { value: '—', label: buildStatusText(status) };
  const numeric = Number(value);
  return {
    value: Number.isFinite(numeric) ? `${numeric.toFixed(0)} ${unit}` : '—',
    label: '下一個小時預測'
  };
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[character]));
}

function valueText(value, unit = '') {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(0)} ${unit}` : '—';
}

function renderStatus(container, manifest) {
  const status = getFreshness(manifest);
  container.className = `freshness freshness--${status}`;
  container.innerHTML = `<span class="status-dot" aria-hidden="true"></span><span>${escapeHtml(buildStatusText(status))}</span>`;
  return status;
}

function renderTrend(container, observations, forecasts, threshold, unit) {
  const points = [
    ...observations.map((item) => ({ time: item.observed_at, value: item.value, type: 'observed' })),
    ...forecasts.map((item) => ({ time: item.target_start, value: item.predicted_value, type: 'forecast' }))
  ];
  const values = points.map((point) => Number(point.value)).filter(Number.isFinite);
  const max = Math.max(Number(threshold), ...values, 1) * 1.12;
  const min = Math.min(0, ...values);
  const width = 760;
  const height = 280;
  const x = (index) => 28 + (index * (width - 56)) / Math.max(points.length - 1, 1);
  const y = (value) => height - 30 - ((Number(value) - min) / (max - min)) * (height - 58);
  const line = (items) => items.map((item) => `${x(item.index).toFixed(1)},${y(item.value).toFixed(1)}`).join(' ');
  const observed = points.map((point, index) => ({ ...point, index })).filter((point) => point.type === 'observed');
  const forecast = points.map((point, index) => ({ ...point, index })).filter((point) => point.type === 'forecast');
  const thresholdY = y(threshold);
  const releaseX = x(Math.max(observed.length - 0.5, 0));
  const labels = points.map((point, index) => `<text x="${x(index)}" y="${height - 8}" text-anchor="middle">${escapeHtml(formatTaipeiTime(point.time).slice(5, 11))}</text>`).join('');
  container.innerHTML = `<svg class="trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="trend-title trend-desc">
    <title id="trend-title">放流水 ${escapeHtml(unit)} 趨勢與預報</title>
    <desc id="trend-desc">青色為示範實測，靛色為示範預測，虛線為研究警戒值。</desc>
    <line class="threshold-line" x1="28" y1="${thresholdY}" x2="${width - 28}" y2="${thresholdY}" />
    <text class="threshold-label" x="${width - 32}" y="${thresholdY - 8}" text-anchor="end">研究警戒 ${threshold}</text>
    <line class="release-line" x1="${releaseX}" y1="18" x2="${releaseX}" y2="${height - 26}" />
    <text class="release-label" x="${releaseX + 8}" y="30">預報發布</text>
    <polyline class="observed-line" points="${line(observed)}" />
    <polyline class="forecast-line" points="${line(forecast)}" />
    ${points.map((point, index) => `<circle class="point point--${point.type}" cx="${x(index)}" cy="${y(point.value)}" r="4"><title>${escapeHtml(formatTaipeiTime(point.time))}：${escapeHtml(valueText(point.value, unit))}</title></circle>`).join('')}
    ${labels}
  </svg>`;
}

function renderObservationsTable(container, observations, forecasts, unit) {
  const rows = [...observations.map((item) => ({ time: item.observed_at, kind: '實測', value: item.value })), ...forecasts.map((item) => ({ time: item.target_start, kind: '預測', value: item.predicted_value }))];
  container.innerHTML = `<table><caption>趨勢資料表</caption><thead><tr><th scope="col">時間</th><th scope="col">類型</th><th scope="col">數值</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(formatTaipeiTime(row.time))}</td><td>${row.kind}</td><td>${escapeHtml(valueText(row.value, unit))}</td></tr>`).join('')}</tbody></table>`;
}

function renderEvents(container, events) {
  container.innerHTML = events.length ? events.map((event) => `<article class="event-card"><div><span class="eyebrow">研究事件</span><h3>${escapeHtml(event.label)}</h3></div><time datetime="${escapeHtml(event.start)}">${escapeHtml(formatTaipeiTime(event.start))} 起</time></article>`).join('') : '<p class="empty-state">目前沒有已記錄事件。</p>';
}

async function loadJson(path) {
  const response = await fetch(`public/data/${path}`);
  if (!response.ok) throw new Error(`無法讀取 ${path}`);
  return response.json();
}

async function boot() {
  const error = document.querySelector('#error-state');
  try {
    const manifest = await loadJson('manifest.json');
    const validation = validateManifest(manifest);
    if (!validation.ok) throw new Error(validation.errors.join('、'));
    const [observations, forecasts, events] = await Promise.all([
      loadJson(manifest.observations_path),
      loadJson(manifest.forecasts_path),
      loadJson(manifest.events_path)
    ]);
    document.querySelector('#station-name').textContent = manifest.station_name;
    document.querySelector('#metric-name').textContent = `${manifest.metric_name} · ${manifest.unit}`;
    document.querySelector('#current-value').textContent = valueText(observations.at(-1)?.value, manifest.unit);

    document.querySelector('#snapshot-time').textContent = `快照：${formatTaipeiTime(manifest.generated_at)}`;
    document.querySelector('#source-link').href = manifest.source.url;
    const freshness = renderStatus(document.querySelector('#freshness'), manifest);
    const forecast = summarizeForecast(forecasts[0], manifest.threshold);
    const display = forecastDisplay(freshness, forecast.value, manifest.unit);
    document.querySelector('#next-value').textContent = display.value;
    document.querySelector('#next-label').textContent = display.label;
    renderTrend(document.querySelector('#trend'), observations, forecasts, manifest.threshold, manifest.unit);
    renderObservationsTable(document.querySelector('#trend-table'), observations, forecasts, manifest.unit);
    renderEvents(document.querySelector('#events'), events);
    document.querySelector('#demo-note').hidden = manifest.mode !== 'demo';
  } catch (cause) {
    error.hidden = false;
    error.textContent = `資料載入失敗：${cause.message}`;
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', boot);
}

export { renderStatus, renderTrend, renderEvents };
