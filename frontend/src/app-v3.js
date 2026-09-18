import { predictEfficiency, predictRiskProbability, validateInputs } from './prediction.js';

const fmt = (value, digits = 1) => Number(value).toFixed(digits);
const completeCase = (artifact, item) => artifact.features.every(({ field }) => Number.isFinite(Number(item.inputs[field])));

function layout() {
  document.body.innerHTML = `
    <header class="app-header">
      <a class="brand" href="#overview"><span class="brand-symbol">WQ</span><span><b>水質前哨</b><small>Wastewater AI Lab</small></span></a>
      <nav aria-label="主要功能">
        <button data-view="overview" class="nav-item is-active">總覽</button>
        <button data-view="assessment" class="nav-item">進水評估</button>
        <button data-view="history" class="nav-item">歷史驗證</button>
        <button data-view="performance" class="nav-item">模型成效</button>
        <button data-view="data" class="nav-item">資料說明</button>
      </nav>
      <span class="mode-chip"><i></i>歷史研究模式</span>
    </header>
    <main class="app-main">
      <div id="load-error" class="notice notice--error" role="alert" hidden></div>

      <section class="view is-active" data-page="overview">
        <div class="page-heading"><div><p class="kicker">控制室總覽</p><h1>進水變化，先轉成可判讀的訊號。</h1></div><p>以四項進水資料估計初沉池 SS 去除效率。這是公開都市污水資料的研究原型，供人工複測與製程檢查。</p></div>
        <div class="status-strip">
          <div><span>資料模式</span><strong>UCI 歷史資料</strong><small>1990–1991 · 每日</small></div>
          <div><span>模型版本</span><strong>Ridge + Logistic</strong><small id="generated-at">產物載入中</small></div>
          <div><span>部署判定</span><strong class="status-warn">尚未達門檻</strong><small>需工業現場外部驗證</small></div>
        </div>
        <div class="overview-grid">
          <article class="control-card">
            <div class="card-head"><div><p class="kicker">目前範例</p><h2>進水條件</h2></div><button data-go="assessment" class="text-button">調整輸入 →</button></div>
            <div id="overview-inputs" class="mini-readings"></div>
          </article>
          <article class="prediction-card">
            <p class="kicker">模型輸出</p><div class="big-value"><strong id="overview-efficiency">—</strong><span>%</span></div>
            <p>初沉池 SS 去除效率估計</p><div id="overview-risk" class="risk-line">等待模型資料</div>
          </article>
        </div>
        <article class="process-card">
          <div class="card-head"><div><p class="kicker">處理流程</p><h2>從進水檢測到人工處置</h2></div><span class="research-label">研究流程 · 非自動控制</span></div>
          <ol class="process-steps"><li><b>01</b><span>進水檢測<small>pH／導電度／SS／COD</small></span></li><li><b>02</b><span>模型估計<small>效率與低效率風險分數</small></span></li><li><b>03</b><span>人工複測<small>確認出水與設備狀態</small></span></li><li><b>04</b><span>製程檢查<small>由操作人員評估調整</small></span></li></ol>
        </article>
      </section>

      <section class="view" data-page="assessment">
        <div class="page-heading"><div><p class="kicker">進水評估</p><h1>輸入今天的進流水質。</h1></div><p>四項數值都必須有檢測結果。超出訓練資料範圍時仍可估計，但會標記為外推。</p></div>
        <div class="assessment-grid">
          <form id="prediction-form" class="form-card"><div id="feature-fields" class="feature-fields"></div><div id="input-message" class="input-message" aria-live="polite"></div><div class="form-actions"><button type="submit">執行研究估計</button><button id="load-example" type="button" class="button-quiet">載入保留案例</button></div></form>
          <article id="assessment-result" class="result-panel result-panel--idle"><p class="kicker">估計結果</p><div class="big-value"><strong id="prediction-value">—</strong><span>%</span></div><h2>初沉池 SS 去除效率</h2><div class="result-grid"><div><span>低效率風險分數</span><strong id="risk-score">—</strong></div><div><span>研究門檻</span><strong id="risk-threshold">50%</strong></div></div><p id="prediction-message">請輸入四項進水數值。</p><aside>本頁不判定放流水法規合格，也不提供投藥劑量。</aside></article>
        </div>
      </section>

      <section class="view" data-page="history">
        <div class="page-heading"><div><p class="kicker">歷史驗證</p><h1>模型在哪些日子判斷錯誤？</h1></div><p>只顯示保留測試集。實際值與預測值的差距，才是評估模型能否使用的依據。</p></div>
        <article class="chart-card"><div class="card-head"><div><h2>實際效率與模型估計</h2><p>最後 36 筆保留測試資料</p></div><div class="chart-legend"><span><i class="actual"></i>實際</span><span><i class="predicted"></i>預測</span><span><i class="threshold"></i>研究門檻</span></div></div><div id="history-chart" class="history-chart"></div></article>
        <article class="table-card"><div class="card-head"><div><h2>近期測試案例</h2><p>點選案例後送到進水評估頁</p></div></div><div class="table-scroll"><table><thead><tr><th>日期</th><th>進水 pH</th><th>導電度</th><th>SS</th><th>COD</th><th>實際效率</th><th>預測效率</th><th>誤差</th><th></th></tr></thead><tbody id="case-rows"></tbody></table></div></article>
      </section>

      <section class="view" data-page="performance">
        <div class="page-heading"><div><p class="kicker">模型成效</p><h1>成效未達標，也要完整呈現。</h1></div><p>時間順序切分為訓練、驗證、測試；測試資料不參與補值、調參或模型擬合。</p></div>
        <div class="metric-grid"><article><span>效率模型 MAE</span><strong id="model-mae">—</strong><small>百分點</small></article><article><span>中位數基準 MAE</span><strong id="baseline-mae">—</strong><small>百分點</small></article><article><span>風險召回率</span><strong id="risk-recall">—</strong><small>低效率事件</small></article><article><span>風險精確率</span><strong id="risk-precision">—</strong><small>研究分類</small></article></div>
        <div class="performance-grid"><article class="explain-card"><p class="kicker">時間切分</p><div id="split-bar" class="split-bar"></div><dl id="split-facts"></dl></article><article class="warning-card"><p class="kicker">目前結論</p><h2>四項進水特徵不足以支撐現場部署。</h2><p id="performance-note"></p><ul><li>補充流量、投藥量、溫度與製程狀態</li><li>取得工業廢水現場資料進行外部驗證</li><li>確認採樣時間與水力停留時間後再談提前量</li></ul></article></div>
      </section>

      <section class="view" data-page="data">
        <div class="page-heading"><div><p class="kicker">資料說明</p><h1>來源、欄位與限制都可追溯。</h1></div><p>本專題依 Kaggle 搜尋方向追溯到 UCI 原始資料；目前沒有宣稱已核對 Kaggle 轉載檔。</p></div>
        <div class="data-grid"><article class="source-card"><p class="kicker">主要來源</p><h2>UCI Water Treatment Plant</h2><p>527 筆都市污水處理廠每日紀錄，1993 年提供，UCI 標示 CC BY 4.0。</p><a id="source-link" href="#" target="_blank" rel="noreferrer">查看原始資料 ↗</a><dl id="data-facts"></dl></article><article class="dictionary-card"><p class="kicker">欄位字典</p><div id="feature-dictionary"></div></article></div>
        <article class="limits-card"><p class="kicker">不可跨越的界線</p><div><section><b>不是工業現場資料</b><p>公開資料來自都市污水廠，模型不能直接代表特定產業。</p></section><section><b>不是提前數小時預報</b><p>每日資料沒有足夠的採樣可用時間與水力停留資訊。</p></section><section><b>不是法規合格判定</b><p>50% 是低效率研究門檻，不是放流水法定限值。</p></section><section><b>不是加藥建議</b><p>資料沒有藥劑種類與投加量，無法推導安全劑量。</p></section></div></article>
      </section>
    </main>
    <footer><span>工業廢水放流水質監測與預報 · 研究原型</span><span>資料、模型、限制同頁可查</span></footer>`;
}

function goTo(view) {
  document.querySelectorAll('.view').forEach((page) => page.classList.toggle('is-active', page.dataset.page === view));
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('is-active', item.dataset.view === view));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderFields(artifact) {
  document.querySelector('#feature-fields').innerHTML = artifact.features.map((feature) => `<label class="feature-field"><span>${feature.label}<small>${feature.field}</small></span><div><input name="${feature.field}" type="number" step="any" min="${feature.min}" max="${feature.max}" required><b>${feature.unit}</b></div><small>開發資料範圍 ${fmt(feature.min)}–${fmt(feature.max)}</small></label>`).join('');
  document.querySelector('#feature-dictionary').innerHTML = artifact.features.map((feature) => `<div><b>${feature.field}</b><span>${feature.label}</span><small>${feature.unit} · ${fmt(feature.min)}–${fmt(feature.max)}</small></div>`).join('');
}

function inputsFromForm(artifact) {
  return Object.fromEntries(artifact.features.map(({ field }) => [field, document.querySelector(`[name="${field}"]`).value]));
}

function fillInputs(artifact, values) {
  artifact.features.forEach(({ field }) => { document.querySelector(`[name="${field}"]`).value = values[field] ?? ''; });
}

function evaluate(artifact, inputs) {
  const efficiency = predictEfficiency(artifact, inputs);
  const risk = predictRiskProbability(artifact.risk, inputs);
  const validation = validateInputs(artifact.features, inputs);
  return { efficiency, risk, validation };
}

function renderCurrent(artifact, inputs) {
  const { efficiency, risk, validation } = evaluate(artifact, inputs);
  const lowEfficiency = efficiency < artifact.target.warning_threshold;
  document.querySelector('#prediction-value').textContent = fmt(efficiency);
  document.querySelector('#risk-score').textContent = `${fmt(risk * 100, 0)} / 100`;
  document.querySelector('#overview-efficiency').textContent = fmt(efficiency);
  document.querySelector('#overview-risk').innerHTML = `<b>${lowEfficiency ? '需人工複測' : '研究範圍內'}</b><span>低效率風險分數 ${fmt(risk * 100, 0)} / 100</span>`;
  document.querySelector('#overview-inputs').innerHTML = artifact.features.map(({ field, label, unit }) => `<div><span>${label}</span><strong>${fmt(inputs[field])}</strong><small>${unit}</small></div>`).join('');
  const panel = document.querySelector('#assessment-result');
  panel.className = `result-panel ${lowEfficiency ? 'result-panel--attention' : 'result-panel--stable'}`;
  document.querySelector('#prediction-message').textContent = lowEfficiency ? '估計效率低於研究門檻，建議複測出水並檢查初沉池操作。' : '估計效率高於研究門檻，仍需搭配實際出水檢測。';
  const inputMessage = document.querySelector('#input-message');
  inputMessage.textContent = validation.outOfRange.length ? `${validation.outOfRange.join('、')} 超出開發資料範圍，本次結果屬外推。` : '四項輸入皆在模型開發資料範圍內。';
  inputMessage.className = `input-message ${validation.outOfRange.length ? 'input-message--warn' : 'input-message--ok'}`;
}

function renderHistory(artifact) {
  const cases = artifact.test_cases.filter((item) => completeCase(artifact, item));
  const chartCases = cases.slice(-36);
  const width = 960, height = 300, pad = 34;
  const values = chartCases.flatMap((item) => [item.actual, item.predicted, artifact.target.warning_threshold]);
  const min = Math.min(...values) - 5, max = Math.max(...values) + 5;
  const x = (index) => pad + index * (width - pad * 2) / Math.max(chartCases.length - 1, 1);
  const y = (value) => height - pad - (value - min) * (height - pad * 2) / (max - min);
  const points = (field) => chartCases.map((item, index) => `${x(index)},${y(item[field])}`).join(' ');
  document.querySelector('#history-chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="保留測試集實際與預測效率曲線"><line class="chart-threshold" x1="${pad}" y1="${y(artifact.target.warning_threshold)}" x2="${width-pad}" y2="${y(artifact.target.warning_threshold)}"></line><polyline class="chart-actual" points="${points('actual')}"></polyline><polyline class="chart-predicted" points="${points('predicted')}"></polyline>${chartCases.map((item, index) => `<circle class="chart-point" cx="${x(index)}" cy="${y(item.actual)}" r="3"><title>${item.date} 實際 ${fmt(item.actual)}%</title></circle>`).join('')}</svg>`;
  const recent = cases.slice(-10).reverse();
  document.querySelector('#case-rows').innerHTML = recent.map((item, index) => `<tr><td>${item.date}</td><td>${item.inputs['PH-E']}</td><td>${item.inputs['COND-E']}</td><td>${item.inputs['SS-E']}</td><td>${item.inputs['DQO-E']}</td><td>${fmt(item.actual)}%</td><td>${fmt(item.predicted)}%</td><td>${fmt(Math.abs(item.actual-item.predicted))}</td><td><button class="case-button" data-case="${index}">評估</button></td></tr>`).join('');
  document.querySelector('#case-rows').addEventListener('click', (event) => { const button = event.target.closest('[data-case]'); if (!button) return; fillInputs(artifact, recent[Number(button.dataset.case)].inputs); renderCurrent(artifact, inputsFromForm(artifact)); goTo('assessment'); });
}

function renderMetadata(artifact) {
  const risk = artifact.risk.metrics;
  document.querySelector('#generated-at').textContent = `產生於 ${new Date(artifact.generated_at).toLocaleDateString('zh-TW')}`;
  document.querySelector('#model-mae').textContent = fmt(artifact.metrics.model_mae, 2);
  document.querySelector('#baseline-mae').textContent = fmt(artifact.metrics.baseline_mae, 2);
  document.querySelector('#risk-recall').textContent = `${fmt(risk.recall * 100, 1)}%`;
  document.querySelector('#risk-precision').textContent = `${fmt(risk.precision * 100, 1)}%`;
  const total = artifact.split.train + artifact.split.validation + artifact.split.test;
  document.querySelector('#split-bar').innerHTML = `<span style="width:${artifact.split.train/total*100}%">訓練</span><span style="width:${artifact.split.validation/total*100}%">驗證</span><span style="width:${artifact.split.test/total*100}%">測試</span>`;
  document.querySelector('#split-facts').innerHTML = `<div><dt>訓練</dt><dd>${artifact.split.train}</dd></div><div><dt>驗證</dt><dd>${artifact.split.validation}</dd></div><div><dt>測試</dt><dd>${artifact.split.test}</dd></div><div><dt>低效率事件</dt><dd>${risk.test_events}</dd></div>`;
  document.querySelector('#performance-note').textContent = `效率模型只比中位數基準改善 ${fmt(artifact.metrics.improvement_percent, 1)}%，分類模型只抓到 ${risk.true_positive}/${risk.test_events} 個低效率事件。`;
  document.querySelector('#source-link').href = artifact.source.url;
  document.querySelector('#data-facts').innerHTML = `<div><dt>原始資料列</dt><dd>${artifact.data_report.raw_rows}</dd></div><div><dt>可用效率目標</dt><dd>${artifact.data_report.usable_rows}</dd></div><div><dt>含缺值輸入列</dt><dd>${artifact.data_report.rows_with_missing_features}</dd></div><div><dt>資料模式</dt><dd>${artifact.mode}</dd></div>`;
}

async function boot() {
  layout();
  document.addEventListener('click', (event) => { const trigger = event.target.closest('[data-view], [data-go]'); if (trigger) goTo(trigger.dataset.view || trigger.dataset.go); });
  try {
    const response = await fetch('public/data/uci-model.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const artifact = await response.json();
    renderFields(artifact); renderHistory(artifact); renderMetadata(artifact);
    const example = artifact.test_cases.find((item) => completeCase(artifact, item));
    fillInputs(artifact, example.inputs); renderCurrent(artifact, example.inputs);
    document.querySelector('#prediction-form').addEventListener('submit', (event) => { event.preventDefault(); const inputs = inputsFromForm(artifact); const validation = validateInputs(artifact.features, inputs); if (!validation.ok) { document.querySelector('#input-message').textContent = `缺少：${validation.missing.join('、')}`; return; } renderCurrent(artifact, inputs); });
    document.querySelector('#load-example').addEventListener('click', () => { fillInputs(artifact, example.inputs); renderCurrent(artifact, example.inputs); });
  } catch (error) { const notice = document.querySelector('#load-error'); notice.hidden = false; notice.textContent = `資料載入失敗：${error.message}`; }
}

if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', boot);
