import {
  assessMaximum,
  modelDeploymentState,
  predictEffluent,
  validateEffluentInputs
} from './effluent.js';

const format = (value, digits = 1) => Number(value).toFixed(digits);
const featureMeta = {
  'PH-E': { label: '進水 pH', unit: 'pH', step: '0.01' },
  'COND-E': { label: '進水導電度', unit: 'μS/cm', step: '1' },
  'SS-E': { label: '進水 SS', unit: 'mg/L', step: '1' },
  'DQO-E': { label: '進水 COD', unit: 'mg/L', step: '1' }
};

function shell() {
  document.body.innerHTML = `
    <header class="topbar">
      <a class="identity" href="#overview"><span class="identity-mark">水</span><span><b>放流前哨</b><small>化工業水質預警研究系統</small></span></a>
      <nav aria-label="主要功能">
        <button data-page-link="overview">法規總覽</button>
        <button data-page-link="forecast">進水預報</button>
        <button data-page-link="models">模型成效</button>
        <button data-page-link="sources">資料與法規</button>
      </nav>
      <span class="research-chip">研究原型</span>
    </header>
    <main>
      <div id="fatal" class="fatal" role="alert" hidden></div>
      <section class="page" data-page="overview">
        <header class="hero">
          <div><p class="eyebrow">CHEMICAL EFFLUENT / CENTRAL BASELINE</p><h1>離限值還有<br><em>多少餘裕？</em></h1></div>
          <div class="hero-copy"><p>依化工業中央附表四基準，比較 AI 放流水濃度預測。模型提供操作預警，正式合規仍以有效許可與合格檢測結果為準。</p><a id="law-link" target="_blank" rel="noreferrer">查看官方法規 ↗</a></div>
        </header>
        <div class="profile-ribbon">
          <div><span>預設業別</span><strong id="profile-industry">—</strong></div>
          <div><span>排放情境</span><strong>直接排放至地面水體</strong></div>
          <div><span>基準生效日</span><strong id="profile-date">—</strong></div>
          <div><span>規則狀態</span><strong class="amber">中央基準｜可由許可覆寫</strong></div>
        </div>
        <div class="compliance-board">
          <article class="limit-card" id="ss-card">
            <div class="limit-head"><span>SS</span><b id="ss-state">載入中</b></div>
            <div class="gauge"><i id="ss-gauge"></i><span class="limit-line">限值</span></div>
            <div class="reading"><strong id="ss-value">—</strong><span>mg/L</span></div>
            <dl><div><dt>中央基準</dt><dd id="ss-limit">—</dd></div><div><dt>預測餘裕</dt><dd id="ss-margin">—</dd></div></dl>
            <p id="ss-model-state">模型狀態載入中</p>
          </article>
          <article class="limit-card" id="cod-card">
            <div class="limit-head"><span>COD</span><b id="cod-state">載入中</b></div>
            <div class="gauge"><i id="cod-gauge"></i><span class="limit-line">限值</span></div>
            <div class="reading"><strong id="cod-value">—</strong><span>mg/L</span></div>
            <dl><div><dt>中央基準</dt><dd id="cod-limit">—</dd></div><div><dt>預測餘裕</dt><dd id="cod-margin">—</dd></div></dl>
            <p id="cod-model-state">模型狀態載入中</p>
          </article>
          <article class="limit-card unavailable">
            <div class="limit-head"><span>pH</span><b>尚未評估</b></div>
            <div class="gauge empty"><i></i><span class="limit-line">6.0–9.0</span></div>
            <div class="reading"><strong>—</strong><span>pH</span></div>
            <dl><div><dt>中央範圍</dt><dd id="ph-range">—</dd></div><div><dt>預測餘裕</dt><dd>無</dd></div></dl>
            <p>目前資料未建立可信的放流水 pH 模型。</p>
          </article>
        </div>
        <aside class="legal-caveat"><b>判讀前提</b><p id="profile-caveat"></p></aside>
      </section>

      <section class="page" data-page="forecast">
        <header class="section-heading"><p class="eyebrow">FORECAST WORKBENCH</p><h1>用進流水質預測放流水濃度</h1><p>輸入四項進水數據。結果會同步與化工業中央基準比較，但不取代採樣檢驗。</p></header>
        <div class="workbench">
          <form id="forecast-form" class="input-panel">
            <div id="input-fields"></div>
            <div id="input-feedback" class="feedback"></div>
            <button type="submit">重新計算預報</button>
          </form>
          <div class="forecast-output">
            <p class="eyebrow">NEXT SAMPLE ESTIMATE</p>
            <div class="forecast-pair">
              <article><span>放流水 SS</span><strong id="forecast-ss">—</strong><small>mg/L</small><b id="forecast-ss-status">—</b></article>
              <article><span>放流水 COD</span><strong id="forecast-cod">—</strong><small>mg/L</small><b id="forecast-cod-status">—</b></article>
            </div>
            <div class="decision-note"><b>操作說明</b><p id="forecast-note">等待輸入。</p></div>
          </div>
        </div>
      </section>

      <section class="page" data-page="models">
        <header class="section-heading"><p class="eyebrow">MODEL GATE</p><h1>先贏過簡單基準，才談部署</h1><p>公開資料以時間順序切分；最後 20% 只用於測試。</p></header>
        <div id="model-cards" class="model-grid"></div>
        <article class="gate-note"><h2>目前部署結論</h2><p>COD-S 僅小幅優於基準，仍需臺灣化工廠外部驗證；SS-S 未優於基準，禁止標成可部署。兩者都不能作為正式合規證明。</p></article>
      </section>

      <section class="page" data-page="sources">
        <header class="section-heading"><p class="eyebrow">TRACEABILITY</p><h1>每個數字都要知道從哪裡來</h1></header>
        <div class="source-grid">
          <article><span>法規</span><h2 id="source-law-title">—</h2><p>pH、SS、COD 限值由版本化設定檔載入。個案許可、地方加嚴、環評或總量管制較嚴時必須覆寫。</p><a id="source-law-link" target="_blank" rel="noreferrer">官方附表四 ↗</a></article>
          <article><span>公開模型資料</span><h2>UCI Water Treatment Plant</h2><p>1990–1991 西班牙都市污水歷史資料，只用於驗證資料管線與建模方法，不代表臺灣化工廠。</p></article>
          <article><span>臺灣公開申報資料</span><h2>環境部 EMS_S_03</h2><p>可補充放流口、承受水體、排放量與申報濃度；時間粒度不足以單獨訓練逐時提前預報。</p><a href="https://data.moenv.gov.tw/dataset/detail/EMS_S_03" target="_blank" rel="noreferrer">查看資料集 ↗</a></article>
          <article><span>實廠資料入口</span><h2>化工廠訓練資料範本</h2><p>已定義進出水、流量、投藥、曝氣、污泥與品質旗標欄位。正式模型應以實廠時序資料重新訓練。</p><a href="public/data/templates/chemical_plant_training_template.csv">下載 CSV 範本 ↓</a></article>
        </div>
      </section>
    </main>
    <footer><span>放流前哨 · 化工業放流水預警研究系統</span><span id="artifact-time">模型產物載入中</span></footer>
  `;
}

function showPage(name) {
  const valid = ['overview', 'forecast', 'models', 'sources'];
  const page = valid.includes(name) ? name : 'overview';
  document.querySelectorAll('.page').forEach((node) => node.classList.toggle('active', node.dataset.page === page));
  document.querySelectorAll('[data-page-link]').forEach((node) => node.classList.toggle('active', node.dataset.pageLink === page));
  if (location.hash !== `#${page}`) history.replaceState(null, '', `#${page}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function statusClass(status) {
  return status === 'exceeds' ? 'danger' : status === 'near' ? 'warning' : status === 'below' ? 'safe' : 'muted';
}

function renderLimit(prefix, value, limit, assessment, deployment) {
  document.querySelector(`#${prefix}-value`).textContent = format(value);
  document.querySelector(`#${prefix}-limit`).textContent = `${format(limit)} mg/L`;
  document.querySelector(`#${prefix}-margin`).textContent = `${format(assessment.margin)} mg/L`;
  document.querySelector(`#${prefix}-state`).textContent = assessment.label;
  const card = document.querySelector(`#${prefix}-card`);
  card.classList.remove('safe', 'warning', 'danger', 'muted');
  card.classList.add(statusClass(assessment.status));
  document.querySelector(`#${prefix}-gauge`).style.height = `${Math.min(100, Math.max(5, assessment.ratio * 100))}%`;
  document.querySelector(`#${prefix}-model-state`).innerHTML = `<b>${deployment.label}</b> · ${deployment.detail}`;
}

function renderModelCards(artifact) {
  document.querySelector('#model-cards').innerHTML = Object.values(artifact.models).map((model) => {
    const deployment = modelDeploymentState(model);
    const m = model.metrics;
    return `<article class="${deployment.ready ? 'passed' : 'blocked'}"><div><span>${model.target}</span><b>${deployment.label}</b></div><strong>${format(m.mae, 2)}</strong><small>MAE mg/L</small><dl><div><dt>中位數基準</dt><dd>${format(m.medianBaselineMae, 2)}</dd></div><div><dt>改善幅度</dt><dd>${format(m.improvementPercent, 1)}%</dd></div><div><dt>R²</dt><dd>${format(m.r2, 3)}</dd></div><div><dt>測試筆數</dt><dd>${model.rows.test}</dd></div></dl><p>${deployment.detail}</p></article>`;
  }).join('');
}

function defaultInputs(models) {
  const model = models['DQO-S'];
  return Object.fromEntries(model.features.map((field, index) => [field, model.parameters.featureMedians[index]]));
}

function renderFields(models, inputs) {
  document.querySelector('#input-fields').innerHTML = models['DQO-S'].features.map((field) => {
    const meta = featureMeta[field];
    return `<label><span>${meta.label}<small>${field}</small></span><div><input name="${field}" value="${inputs[field]}" type="number" min="0" step="${meta.step}" required><b>${meta.unit}</b></div></label>`;
  }).join('');
}

function formInputs() {
  return Object.fromEntries(Object.keys(featureMeta).map((field) => [field, document.querySelector(`[name="${field}"]`).value]));
}

function calculate(models, profile, inputs) {
  const ss = Math.max(0, predictEffluent(models['SS-S'], inputs));
  const cod = Math.max(0, predictEffluent(models['DQO-S'], inputs));
  return {
    ss,
    cod,
    ssAssessment: assessMaximum(ss, profile.limits.ss.max),
    codAssessment: assessMaximum(cod, profile.limits.cod.max)
  };
}

function renderForecast(result) {
  document.querySelector('#forecast-ss').textContent = format(result.ss);
  document.querySelector('#forecast-cod').textContent = format(result.cod);
  const ssStatus = document.querySelector('#forecast-ss-status');
  const codStatus = document.querySelector('#forecast-cod-status');
  ssStatus.textContent = result.ssAssessment.label;
  codStatus.textContent = result.codAssessment.label;
  ssStatus.className = statusClass(result.ssAssessment.status);
  codStatus.className = statusClass(result.codAssessment.status);
  const worst = [result.ssAssessment, result.codAssessment].sort((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0))[0];
  document.querySelector('#forecast-note').textContent = worst.status === 'exceeds'
    ? '預測結果超出所選中央基準，應優先複測放流水並檢查處理單元。'
    : worst.status === 'near'
      ? '至少一項預測值進入 80% 操作警戒區，建議提前檢查製程與安排複測。'
      : '預測值低於所選中央基準；仍須依許可條件及實際檢驗結果判讀。';
}

async function boot() {
  shell();
  try {
    const [modelResponse, profileResponse] = await Promise.all([
      fetch('public/data/effluent-model-v4.json'),
      fetch('public/data/legal-profiles.json')
    ]);
    if (!modelResponse.ok || !profileResponse.ok) throw new Error('模型或法規設定檔無法載入');
    const artifact = await modelResponse.json();
    const profiles = await profileResponse.json();
    const profile = profiles.profiles[0];
    const inputs = defaultInputs(artifact.models);
    const result = calculate(artifact.models, profile, inputs);

    document.querySelector('#profile-industry').textContent = profile.industry;
    document.querySelector('#profile-date').textContent = profile.effectiveFrom;
    document.querySelector('#profile-caveat').textContent = profile.caveat;
    document.querySelector('#law-link').href = profile.source.lawUrl;
    document.querySelector('#source-law-link').href = profile.source.attachmentUrl;
    document.querySelector('#source-law-title').textContent = profile.source.title;
    document.querySelector('#ph-range').textContent = `${profile.limits.ph.min.toFixed(1)}–${profile.limits.ph.max.toFixed(1)}`;
    document.querySelector('#artifact-time').textContent = `模型產物：${new Date(artifact.createdAt).toLocaleString('zh-TW')}`;

    renderLimit('ss', result.ss, profile.limits.ss.max, result.ssAssessment, modelDeploymentState(artifact.models['SS-S']));
    renderLimit('cod', result.cod, profile.limits.cod.max, result.codAssessment, modelDeploymentState(artifact.models['DQO-S']));
    renderModelCards(artifact);
    renderFields(artifact.models, inputs);
    renderForecast(result);

    document.querySelector('#forecast-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const values = formInputs();
      const validation = validateEffluentInputs(values);
      const feedback = document.querySelector('#input-feedback');
      if (!validation.ok) {
        feedback.className = 'feedback error';
        feedback.textContent = [...validation.missing.map((v) => `缺少 ${v}`), ...validation.invalid.map((v) => `${v} 超出合理範圍`)].join('；');
        return;
      }
      feedback.className = 'feedback ok';
      feedback.textContent = '已使用目前四項進水數據重新計算。';
      const updated = calculate(artifact.models, profile, values);
      renderForecast(updated);
      renderLimit('ss', updated.ss, profile.limits.ss.max, updated.ssAssessment, modelDeploymentState(artifact.models['SS-S']));
      renderLimit('cod', updated.cod, profile.limits.cod.max, updated.codAssessment, modelDeploymentState(artifact.models['DQO-S']));
    });

    document.addEventListener('click', (event) => {
      const trigger = event.target.closest('[data-page-link]');
      if (trigger) showPage(trigger.dataset.pageLink);
    });
    window.addEventListener('hashchange', () => showPage(location.hash.slice(1)));
    showPage(location.hash.slice(1));
  } catch (error) {
    const fatal = document.querySelector('#fatal');
    fatal.hidden = false;
    fatal.textContent = `載入失敗：${error.message}`;
  }
}

if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', boot);
