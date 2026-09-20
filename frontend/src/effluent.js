const missing = (value) => value === '' || value === null || value === undefined || !Number.isFinite(Number(value));

export function predictEffluent(model, inputs) {
  const { features, parameters } = model;
  return features.reduce((total, field, index) => {
    const raw = inputs[field];
    const value = missing(raw) ? parameters.featureMedians[index] : Number(raw);
    const standardized = (value - parameters.featureMeans[index]) / parameters.featureScales[index];
    return total + parameters.coefficients[index] * standardized;
  }, parameters.intercept);
}

export function validateEffluentInputs(inputs) {
  const ranges = {
    'PH-E': [0, 14],
    'COND-E': [0, Infinity],
    'SS-E': [0, Infinity],
    'DQO-E': [0, Infinity]
  };
  const labels = { 'PH-E': '進水 pH', 'COND-E': '進水導電度', 'SS-E': '進水 SS', 'DQO-E': '進水 COD' };
  const missingFields = [];
  const invalidFields = [];
  for (const [field, [minimum, maximum]] of Object.entries(ranges)) {
    if (missing(inputs[field])) missingFields.push(labels[field]);
    else if (Number(inputs[field]) < minimum || Number(inputs[field]) > maximum) invalidFields.push(labels[field]);
  }
  return { ok: !missingFields.length && !invalidFields.length, missing: missingFields, invalid: invalidFields };
}

function empiricalQuantile(values, fraction) {
  const ordered = [...values].sort((a, b) => a - b);
  const position = (ordered.length - 1) * fraction;
  const lower = Math.floor(position);
  const upper = Math.min(lower + 1, ordered.length - 1);
  const weight = position - lower;
  return ordered[lower] * (1 - weight) + ordered[upper] * weight;
}

export function estimateExceedanceRisk(model, predicted, limit) {
  const residuals = model?.uncertainty?.testResiduals?.map(Number).filter(Number.isFinite) || [];
  if (!residuals.length || missing(predicted) || missing(limit)) return null;
  const center = Number(predicted);
  const threshold = Number(limit);
  const lower = center + empiricalQuantile(residuals, 0.1);
  const upper = center + empiricalQuantile(residuals, 0.9);
  const exceedances = residuals.filter((residual) => center + residual > threshold).length;
  return {
    probability: exceedances / residuals.length,
    lower,
    upper,
    sampleCount: residuals.length,
    method: 'held_out_empirical_residuals'
  };
}
export function assessMaximum(value, limit, warningRatio = 0.8) {
  if (missing(value) || missing(limit) || Number(limit) <= 0) {
    return { status: 'unassessed', margin: null, ratio: null, label: '尚未評估' };
  }
  const numeric = Number(value);
  const maximum = Number(limit);
  const ratio = numeric / maximum;
  const margin = maximum - numeric;
  if (numeric > maximum) return { status: 'exceeds', margin, ratio, label: '預測超出限值' };
  if (ratio >= warningRatio) return { status: 'near', margin, ratio, label: '接近限值' };
  return { status: 'below', margin, ratio, label: '預測低於限值' };
}

export function assessRange(value, minimum, maximum, warningFraction = 0.1) {
  if (missing(value) || missing(minimum) || missing(maximum) || Number(minimum) >= Number(maximum)) {
    return { status: 'unassessed', margin: null, ratio: null, label: '尚未評估' };
  }
  const numeric = Number(value);
  const low = Number(minimum);
  const high = Number(maximum);
  const margin = Math.min(numeric - low, high - numeric);
  if (numeric < low || numeric > high) return { status: 'exceeds', margin, ratio: 1, label: '預測超出範圍' };
  const edgeFraction = margin / (high - low);
  if (edgeFraction <= warningFraction) return { status: 'near', margin, ratio: 1 - edgeFraction, label: '接近範圍界限' };
  return { status: 'below', margin, ratio: 1 - edgeFraction, label: '預測位於範圍內' };
}

export function modelDeploymentState(model) {
  const beatsBaseline = Boolean(model?.metrics?.beatsBaseline);
  return beatsBaseline
    ? { ready: true, label: '通過公開資料基準', detail: '仍需化工廠外部驗證' }
    : { ready: false, label: '尚未優於基準', detail: '不可作為現場部署模型' };
}
