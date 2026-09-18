const requiredFields = ['schema_version', 'generated_at'];

function isDate(value) {
  return typeof value === 'string' && !Number.isNaN(Date.parse(value));
}

export function validateManifest(manifest) {
  const errors = [];
  for (const field of requiredFields) {
    if (!manifest || typeof manifest[field] !== 'string' || manifest[field].trim() === '') {
      errors.push(`${field} is required`);
    }
  }

  if (errors.length === 0 && (!isDate(manifest.valid_until))) {
    errors.push('valid_until must be an ISO date');
  }

  if (manifest?.generated_at && !isDate(manifest.generated_at)) {
    errors.push('generated_at must be an ISO date');
  }

  return errors.length ? { ok: false, errors } : { ok: true, value: manifest };
}

export function getFreshness(manifest, now = new Date()) {
  if (!isDate(manifest?.valid_until) || Number.isNaN(now.getTime())) return 'unknown';
  return now.getTime() >= Date.parse(manifest.valid_until) ? 'stale' : 'fresh';
}

export function formatTaipeiTime(isoString) {
  if (!isDate(isoString)) return '時間未知';
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(new Date(isoString));
}

export function summarizeForecast(forecast, threshold) {
  const value = Number(forecast?.predicted_value);
  const hasValue = Number.isFinite(value);
  const limit = Number(threshold);
  const isWarning = hasValue && Number.isFinite(limit) && value >= limit;
  return {
    value: hasValue ? value : null,
    status: isWarning ? 'warning' : 'normal',
    label: hasValue ? (isWarning ? '接近研究警戒' : '研究範圍內') : '暫無預測'
  };
}
