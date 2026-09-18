export function predictEfficiency(artifact, inputs) {
  const { model } = artifact;
  return Object.keys(model.coefficients).reduce((result, field) => {
    const numeric = Number(inputs[field]);
    const value = Number.isFinite(numeric) ? numeric : model.medians[field];
    const standardized = (value - model.means[field]) / model.scales[field];
    return result + model.coefficients[field] * standardized;
  }, model.intercept);
}

export function validateInputs(features, inputs) {
  const missing = [];
  const outOfRange = [];
  for (const feature of features) {
    const raw = inputs[feature.field];
    const numeric = Number(raw);
    if (raw === '' || raw === null || raw === undefined || !Number.isFinite(numeric)) {
      missing.push(feature.field);
    } else if (numeric < feature.min || numeric > feature.max) {
      outOfRange.push(feature.field);
    }
  }
  return { ok: missing.length === 0, missing, outOfRange };
}

export function assessEfficiency(value, threshold) {
  if (value < threshold) {
    return {
      level: 'attention',
      label: '需注意',
      message: '估計效率低於研究門檻，建議複測並檢查初沉池操作。'
    };
  }
  return {
    level: 'stable',
    label: '研究範圍內',
    message: '估計效率高於研究門檻，仍應搭配實際出水檢測判讀。'
  };
}

export function predictRiskProbability(artifact, inputs) {
  const { model } = artifact;
  let score = model.intercept;
  for (const field of Object.keys(model.coefficients)) {
    const value = Number(inputs[field]);
    const safeValue = Number.isFinite(value) ? value : model.medians[field];
    score += model.coefficients[field] * ((safeValue - model.means[field]) / model.scales[field]);
  }
  const bounded = Math.max(Math.min(score, 35), -35);
  return 1 / (1 + Math.exp(-bounded));
}

