import { assessEfficiency, predictEfficiency, predictRiskProbability, validateInputs } from './prediction.js';

const number = (value, digits = 1) => Number(value).toFixed(digits);

function pageShell() {
  document.body.innerHTML = `
    <header class="topbar">
      <a class="brand" href="./" aria-label="回到首頁"><span class="brand-symbol">WQ</span><span>水質前哨</span></a>
      <div class="topbar-meta"><span class="live-dot"></span>公開資料研究原型 <span>v0.2</span></div>
    </header>
    <main>
      <section class="hero">
        <div>
          <p class="kicker">工業廢水處理決策支援</p>
          <h1>從進水端，<br><em>先看見處理風險。</em></h1>
          <p class="lede">輸入 pH、導電度、SS 與 COD，估計初沉池懸浮固體去除效率。結果用於研究與人工複核，不直接控制加藥。</p>
        </div>
        <div class="hero-stamp"><span>DATA MODE</span><strong>UCI 1990–91</strong><small>都市污水每日資料 · 外部驗證前不代表工業現場</small></div>
      </section>

      <div id="load-error" class="notice notice--error" role="alert" hidden></div>
      <section class="workbench" aria-label="水質估計工作台">
        <form id="prediction-form" class="input-panel">
          <div class="section-title"><span>01</span><div><p>進水條件</p><h2>今天的水有多難處理？</h2></div></div>
          <div id="feature-fields" class="feature-fields"></div>
          <div id="input-message" class="input-message" aria-live="polite"></div>
          <div class="form-actions"><button type="submit">估計處理效率 <span>→</span></button><button type="button" id="load-example" class="button-quiet">載入歷史案例</button></div>
        </form>

        <section class="process-panel" aria-labelledby="result-heading">
          <div class="section-title section-title--light"><span>02</span><div><p>處理推估</p><h2 id="result-heading">進水 → 初沉池 → 放流</h2></div></div>
          <div class="process-line" aria-hidden="true"><span class="water-node">進水</span><i></i><span class="settler-node"><b></b>初沉池</span><i></i><span class="water-node">後續處理</span></div>
          <div id="result-card" class="result-card result-card--idle">
            <p>初沉池 SS 去除效率</p>
            <div><strong id="prediction-value">—</strong><span>%</span></div>
            <span id="risk-badge" class="risk-badge">等待輸入</span>
            <p id="prediction-message" class="result-message">載入案例或輸入四項進水數據後開始估計。</p>
          </div>
          <p class="model-disclaimer">這是歷史資料的關聯估計，不是法規合格判定，也不提供具體投藥量。</p>
        </section>
      </section>

      <section class="evidence-grid">
        <article class="evidence-card evidence-card--score">
          <div class="section-title"><span>03</span><div><p>模型成效</p><h2>測試集沒有被藏起來</h2></div></div>
          <div class="score-row"><div><strong id="model-mae">—</strong><span>模型 MAE<br>百分點</span></div><div><strong id="baseline-mae">—</strong><span>基準 MAE<br>百分點</span></div><div><strong id="improvement">—</strong><span>相對改善</span></div></div>
          <div id="model-verdict" class="model-verdict"></div>
        </article>
        <article class="evidence-card evidence-card--data">
          <p class="kicker">資料品質</p><h2>每個數字都有邊界</h2>
          <dl id="data-facts"></dl>
          <a id="source-link" href="#" target="_blank" rel="noreferrer">查看 UCI 原始資料 ↗</a>
        </article>
      </section>

      <section class="cases-section" aria-labelledby="cases-heading">
        <div class="cases-heading"><div><p class="kicker">保留測試集</p><h2 id="cases-heading">歷史案例：實際值與模型估計</h2></div><p>選一列即可帶入四項進水值。這些案例只用於測試，沒有參與最終模型擬合。</p></div>
        <div class="table-scroll"><table><thead><tr><th>日期</th><th>進水 pH</th><th>導電度</th><th>SS</th><th>COD</th><th>實際效率</th><th>模型估計</th><th></th></tr></thead><tbody id="case-rows"></tbody></table></div>
      </section>

      <section class="next-step"><span>下一階段</span><h2>加入工業現場資料、投藥量與水力停留時間，才有資格談真正的提前預警與加藥建議。</h2></section>
    </main>
    <footer><span>水質前哨 · Wastewater Quality Sentinel</span><span>研究用途 · 2026</span></footer>`;
}

function renderFields(artifact) {
  const container = document.querySelector('#feature-fields');
  container.innerHTML = artifact.features.map((feature) => `
    <label class="feature-field">
      <span>${feature.label}<small>${feature.field}</small></span>
      <div><input name="${feature.field}" type="number" step="any" min="${feature.min}" max="${feature.max}" required><b>${feature.unit}</b></div>
      <small>資料範圍 ${number(feature.min)}–${number(feature.max)}</small>
    </label>`).join('');
}

function readInputs(artifact) {
  return Object.fromEntries(artifact.features.map(({ field }) => [field, document.querySelector(`[name="${field}"]`).value]));
}

function fillInputs(artifact, values) {
  artifact.features.forEach(({ field }) => { document.querySelector(`[name="${field}"]`).value = values[field] ?? ''; });
}

function showPrediction(artifact) {
  const values = readInputs(artifact);
  const validation = validateInputs(artifact.features, values);
  const message = document.querySelector('#input-message');
  if (!validation.ok) {
    message.textContent = `請填入全部四項數值：${validation.missing.join('、')}`;
    return;
  }
  const estimate = predictEfficiency(artifact, values);
  const assessment = assessEfficiency(estimate, artifact.target.warning_threshold);
  const riskProbability = artifact.risk ? predictRiskProbability(artifact.risk, values) : null;
  document.querySelector('#prediction-value').textContent = number(estimate);
  const card = document.querySelector('#result-card');
  card.className = `result-card result-card--${assessment.level}`;
  const badge = document.querySelector('#risk-badge');
  badge.textContent = riskProbability === null ? assessment.label : `${assessment.label} · 風險 ${number(riskProbability * 100, 0)}%`;
  document.querySelector('#prediction-message').textContent = assessment.message;
  message.textContent = validation.outOfRange.length
    ? `注意：${validation.outOfRange.join('、')} 超出模型訓練範圍，結果屬外推。`
    : '四項輸入皆在模型開發資料範圍內。';
  message.className = `input-message ${validation.outOfRange.length ? 'input-message--warn' : 'input-message--ok'}`;
}

function renderEvidence(artifact) {
  const { metrics, split, data_report: report } = artifact;
  document.querySelector('#model-mae').textContent = number(metrics.model_mae, 2);
  document.querySelector('#baseline-mae').textContent = number(metrics.baseline_mae, 2);
  document.querySelector('#improvement').textContent = `${number(metrics.improvement_percent, 1)}%`;
  const passesGoal = metrics.improvement_percent >= 10 && metrics.r2 > 0;
  const risk = artifact.risk?.metrics;
  document.querySelector('#model-verdict').innerHTML = `<b>${passesGoal ? '效率模型可進一步驗證' : '尚未達到部署門檻'}</b><span>效率 R² ${number(metrics.r2, 2)}；風險分類召回率 ${risk ? number(risk.recall * 100, 1) : '—'}%、精確率 ${risk ? number(risk.precision * 100, 1) : '—'}%，目前只作研究分析。</span>`;
  document.querySelector('#data-facts').innerHTML = `
    <div><dt>原始列數</dt><dd>${report.raw_rows}</dd></div>
    <div><dt>可用目標列</dt><dd>${report.usable_rows}</dd></div>
    <div><dt>訓練／驗證／測試</dt><dd>${split.train} / ${split.validation} / ${split.test}</dd></div>
    <div><dt>含缺值輸入</dt><dd>${report.rows_with_missing_features}</dd></div>`;
  document.querySelector('#source-link').href = artifact.source.url;
}

function renderCases(artifact) {
  const cases = artifact.test_cases.filter((item) => artifact.features.every(({ field }) => Number.isFinite(Number(item.inputs[field])))).slice(-8).reverse();
  const body = document.querySelector('#case-rows');
  body.innerHTML = cases.map((item, index) => `
    <tr><td>${item.date}</td><td>${item.inputs['PH-E'] ?? '—'}</td><td>${item.inputs['COND-E'] ?? '—'}</td><td>${item.inputs['SS-E'] ?? '—'}</td><td>${item.inputs['DQO-E'] ?? '—'}</td><td>${number(item.actual)}%</td><td>${number(item.predicted)}%</td><td><button type="button" class="case-button" data-case="${index}">帶入</button></td></tr>`).join('');
  body.addEventListener('click', (event) => {
    const button = event.target.closest('[data-case]');
    if (!button) return;
    fillInputs(artifact, cases[Number(button.dataset.case)].inputs);
    showPrediction(artifact);
    document.querySelector('#prediction-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

async function boot() {
  pageShell();
  try {
    const response = await fetch('public/data/uci-model.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const artifact = await response.json();
    renderFields(artifact);
    renderEvidence(artifact);
    renderCases(artifact);
    const example = artifact.test_cases.find((item) => artifact.features.every(({ field }) => Number.isFinite(Number(item.inputs[field]))));
    document.querySelector('#prediction-form').addEventListener('submit', (event) => { event.preventDefault(); showPrediction(artifact); });
    document.querySelector('#load-example').addEventListener('click', () => { fillInputs(artifact, example.inputs); showPrediction(artifact); });
    fillInputs(artifact, example.inputs);
    showPrediction(artifact);
  } catch (error) {
    const notice = document.querySelector('#load-error');
    notice.hidden = false;
    notice.textContent = `模型資料載入失敗：${error.message}。請使用本機 HTTP 伺服器開啟網站。`;
  }
}

if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', boot);


