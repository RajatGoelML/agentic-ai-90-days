// ============================================
// APP — Reversal Intelligence Engine Frontend
// ============================================
const AppState = {
  theme: localStorage.getItem('rie-theme') || 'dark',
  view: 'watchlist',
  data: null,
  recommendations: [],
  executionLog: [],
  tokenUsage: null,
  generatedAt: null,
  selectedRec: null,
  detailOpen: false,
  isRunning: false,
  pipelineStep: -1,
  searchQuery: '',
  filterDecision: 'ALL',
  sortField: 'confidence',
  sortDir: 'desc',
  historyFiles: [],
};
// ============================================
// THEME
// ============================================
function applyTheme() {
  document.documentElement.setAttribute('data-theme', AppState.theme);
  localStorage.setItem('rie-theme', AppState.theme);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = AppState.theme === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
}
function toggleTheme() {
  AppState.theme = AppState.theme === 'dark' ? 'light' : 'dark';
  applyTheme();
}
// ============================================
// PIPELINE RENDERER
// ============================================
function renderPipeline() {
  const el = document.getElementById('pipelineBar');
  if (!el) return;
  let html = '';
  PIPELINE_STAGES.forEach((stage, i) => {
    const cls = AppState.pipelineStep > i ? 'completed' : AppState.pipelineStep === i ? 'active' : '';
    html += '<div class="pipeline-node ' + cls + '">' +
      '<div class="pipeline-node__icon">' + stage.icon + '</div>' +
      '<div class="pipeline-node__label">' + stage.label + '</div>' +
      '<div class="pipeline-node__status">' + (cls === 'completed' ? '\u2713 Done' : cls === 'active' ? 'Processing...' : 'Pending') + '</div></div>';
    if (i < PIPELINE_STAGES.length - 1) {
      const conCls = AppState.pipelineStep > i ? 'completed' : AppState.pipelineStep === i ? 'active' : '';
      html += '<div class="pipeline-connector ' + conCls + '"></div>';
    }
  });
  el.innerHTML = html;
}
// ============================================
// SUMMARY STATS
// ============================================
function renderSummaryStats() {
  const el = document.getElementById('summaryStats');
  if (!el || !AppState.recommendations.length) { if(el) el.innerHTML = ''; return; }
  const recs = AppState.recommendations;
  const counts = {};
  recs.forEach(r => { counts[r.decision] = (counts[r.decision]||0) + 1; });
  const avgConf = recs.reduce((s,r) => s + (r.confidence||0), 0) / recs.length;
  let html = '<div class="summary-stat"><div class="summary-stat__dot" style="background:var(--accent-blue)"></div><div class="summary-stat__label">Stocks Analyzed</div><div class="summary-stat__value">' + recs.length + '</div></div>';
  html += '<div class="summary-stat"><div class="summary-stat__dot" style="background:var(--accent-purple)"></div><div class="summary-stat__label">Avg Confidence</div><div class="summary-stat__value">' + (avgConf*100).toFixed(0) + '%</div></div>';
  Object.entries(counts).forEach(([d,c]) => {
    const meta = getDecisionMeta(d);
    html += '<div class="summary-stat"><div class="summary-stat__dot" style="background:' + meta.color + '"></div><div class="summary-stat__label">' + meta.label + '</div><div class="summary-stat__value">' + c + '</div></div>';
  });
  if (AppState.tokenUsage) {
    html += '<div class="summary-stat"><div class="summary-stat__dot" style="background:var(--accent-amber)"></div><div class="summary-stat__label">Model</div><div class="summary-stat__value" style="font-size:var(--fs-xs)">' + safe(AppState.tokenUsage.model) + '</div></div>';
    html += '<div class="summary-stat"><div class="summary-stat__dot" style="background:var(--accent-green)"></div><div class="summary-stat__label">Est. Cost</div><div class="summary-stat__value">' + usd(AppState.tokenUsage.estimated_cost_usd) + '</div></div>';
  }
  if (AppState.generatedAt) {
    html += '<div class="summary-stat"><div class="summary-stat__dot" style="background:var(--text-muted)"></div><div class="summary-stat__label">Generated</div><div class="summary-stat__value" style="font-size:var(--fs-xs)">' + formatTimestamp(AppState.generatedAt) + '</div></div>';
  }
  el.innerHTML = html;
}
// ============================================
// WATCHLIST TABLE
// ============================================
function getFilteredSortedRecs() {
  let recs = [...AppState.recommendations];
  if (AppState.searchQuery) {
    const q = AppState.searchQuery.toLowerCase();
    recs = recs.filter(r => (r.symbol||'').toLowerCase().includes(q) || (r.company_name||'').toLowerCase().includes(q) || (r.sector||'').toLowerCase().includes(q));
  }
  if (AppState.filterDecision !== 'ALL') {
    recs = recs.filter(r => r.decision === AppState.filterDecision);
  }
  const f = AppState.sortField;
  const dir = AppState.sortDir === 'asc' ? 1 : -1;
  recs.sort((a,b) => {
    let va = a[f], vb = b[f];
    if (typeof va === 'string') return dir * va.localeCompare(vb||'');
    return dir * ((va||0) - (vb||0));
  });
  return recs;
}
function renderWatchlistTable() {
  const el = document.getElementById('watchlistTableBody');
  const countEl = document.getElementById('watchlistCount');
  if (!el) return;
  const recs = getFilteredSortedRecs();
  if (countEl) countEl.textContent = recs.length + ' stocks';
  if (!recs.length) {
    el.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:48px;color:var(--text-muted)">No recommendations match your filters</td></tr>';
    return;
  }
  let html = '';
  recs.forEach(r => {
    const meta = getDecisionMeta(r.decision);
    const confColor = getConfidenceColor(r.confidence);
    const confPct = ((r.confidence||0)*100).toFixed(0);
    const rr = r.risk_reward || {};
    const rrView = rr.risk_reward_view || 'N/A';
    const rrClass = rrView === 'FAVORABLE' ? 'metric__value--positive' : rrView === 'UNFAVORABLE' ? 'metric__value--negative' : 'metric__value--neutral';
    const selClass = AppState.selectedRec && AppState.selectedRec.symbol === r.symbol ? 'selected' : '';
    html += '<tr class="' + selClass + '" onclick="openDetail(\'' + escHtml(r.symbol) + '\')">';
    html += '<td><div class="symbol-cell">' + escHtml(r.symbol) + '</div><div class="company-cell">' + escHtml(safe(r.company_name,'')) + '</div></td>';
    html += '<td class="sector-cell">' + escHtml(safe(r.sector,'')) + '</td>';
    html += '<td><span class="status-badge ' + meta.cssClass + '">' + meta.label + '</span></td>';
    html += '<td><div class="confidence-bar"><div class="confidence-bar__track"><div class="confidence-bar__fill" style="width:' + confPct + '%;background:' + confColor + '"></div></div><div class="confidence-bar__label">' + confPct + '%</div></div></td>';
    html += '<td class="summary-cell" title="' + escHtml(r.summary||'') + '">' + escHtml(safe(r.summary,'').substring(0,100)) + '</td>';
    html += '<td style="font-size:var(--fs-xs);color:var(--text-secondary)">' + escHtml(safe(r.reversal_quality,'').substring(0,60)) + '</td>';
    html += '<td><span class="' + rrClass + '" style="font-family:var(--font-mono);font-size:var(--fs-xs)">' + rrView + '</span></td>';
    html += '<td style="font-family:var(--font-mono);font-size:var(--fs-xs)">' + formatMktCap(r.metrics ? r.metrics.market_cap : null) + '</td>';
    html += '</tr>';
  });
  el.innerHTML = html;
}
function handleSort(field) {
  if (AppState.sortField === field) {
    AppState.sortDir = AppState.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    AppState.sortField = field;
    AppState.sortDir = 'desc';
  }
  renderWatchlistTable();
  updateSortIndicators();
}
function updateSortIndicators() {
  document.querySelectorAll('.watchlist-table th').forEach(th => {
    const f = th.getAttribute('data-sort');
    th.classList.toggle('sorted', f === AppState.sortField);
    const ind = th.querySelector('.sort-indicator');
    if (ind && f === AppState.sortField) ind.textContent = AppState.sortDir === 'asc' ? '\u25B2' : '\u25BC';
    else if (ind) ind.textContent = '\u25BC';
  });
}
function handleSearch(val) { AppState.searchQuery = val; renderWatchlistTable(); }
function handleFilter(val) { AppState.filterDecision = val; renderWatchlistTable(); }
// ============================================
// DETAIL PANEL
// ============================================
function openDetail(symbol) {
  const rec = AppState.recommendations.find(r => r.symbol === symbol);
  if (!rec) return;
  AppState.selectedRec = rec;
  AppState.detailOpen = true;
  renderDetailPanel(rec);
  document.getElementById('detailOverlay').classList.add('open');
  document.getElementById('detailBackdrop').classList.add('open');
  renderWatchlistTable();
}
function closeDetail() {
  AppState.detailOpen = false;
  AppState.selectedRec = null;
  document.getElementById('detailOverlay').classList.remove('open');
  document.getElementById('detailBackdrop').classList.remove('open');
  renderWatchlistTable();
}
function renderDetailPanel(r) {
  const el = document.getElementById('detailContent');
  if (!el) return;
  const meta = getDecisionMeta(r.decision);
  const m = r.metrics || {};
  const tc = r.technical_context || {};
  const rv = r.relative_valuation || {};
  const rr = r.risk_reward || {};
  const ns = r.news_sentiment || {};
  const sig = r.signals || {};
  let html = '<div class="detail-header"><div class="detail-header__info">';
  html += '<div class="detail-header__symbol">' + escHtml(r.symbol) + '</div>';
  html += '<div class="detail-header__meta"><span class="status-badge ' + meta.cssClass + '">' + meta.label + '</span>';
  html += '<span>' + escHtml(safe(r.company_name,'')) + '</span>';
  html += '<span>' + escHtml(safe(r.sector,'')) + '</span></div></div>';
  html += '<button class="btn-icon" onclick="closeDetail()" title="Close">\u2715</button></div>';
  html += '<div class="detail-body">';
  // Summary
  html += '<div class="detail-section"><div class="detail-section__title">AI Summary</div>';
  html += '<p style="font-size:var(--fs-sm);line-height:1.7;color:var(--text-secondary)">' + escHtml(safe(r.summary,'')) + '</p>';
  html += '<p style="font-size:var(--fs-xs);color:var(--text-tertiary);margin-top:4px"><strong>Reversal Quality:</strong> ' + escHtml(safe(r.reversal_quality,'')) + '</p></div>';
  // Confidence + Risk/Reward
  html += '<div class="detail-section"><div class="detail-section__title">Confidence & Risk/Reward</div>';
  html += '<div class="metrics-grid">';
  html += renderMetricCard('Confidence', ((r.confidence||0)*100).toFixed(0) + '%');
  html += renderMetricCard('Risk/Reward', safe(rr.risk_reward_view));
  html += renderMetricCard('Base Upside', pct(rr.base_case_upside_pct));
  html += renderMetricCard('Bear Downside', pct(rr.bear_case_downside_pct));
  html += renderMetricCard('Bull Upside', pct(rr.bull_case_upside_pct));
  html += '</div>';
  if (rr.bear_case_downside_pct != null || rr.bull_case_upside_pct != null) {
    const bw = Math.max(rr.bear_case_downside_pct||0, 5);
    const uw = Math.max(rr.bull_case_upside_pct||0, 5);
    const total = bw + (rr.base_case_upside_pct||10) + uw;
    html += '<div class="risk-reward-bar" style="margin-top:12px">';
    html += '<div class="risk-reward-bar__bear" style="flex:' + bw/total + '">-' + (rr.bear_case_downside_pct||0) + '%</div>';
    html += '<div class="risk-reward-bar__base" style="flex:' + (rr.base_case_upside_pct||10)/total + '">+' + (rr.base_case_upside_pct||0) + '%</div>';
    html += '<div class="risk-reward-bar__bull" style="flex:' + uw/total + '">+' + (rr.bull_case_upside_pct||0) + '%</div>';
    html += '</div>';
  }
  html += '</div>';
  // Agent Cards
  html += '<div class="detail-section"><div class="detail-section__title">Multi-Agent Analysis</div>';
  html += '<div class="agents-grid">';
  html += '<div class="agent-card agent-card--bull"><div class="agent-card__header">\uD83D\uDC02 Bull Agent</div><div class="agent-card__body">' + escHtml(safe(r.bull_case_summary,'No bull thesis available.')) + '</div></div>';
  html += '<div class="agent-card agent-card--bear"><div class="agent-card__header">\uD83D\uDC3B Bear Agent</div><div class="agent-card__body">' + escHtml(safe(r.bear_case_summary,'No bear thesis available.')) + '</div></div>';
  html += '</div>';
  html += '<div class="agents-grid agents-grid--full" style="margin-top:12px">';
  html += '<div class="agent-card agent-card--judge"><div class="agent-card__header">\u2696\uFE0F Judge Agent — Final Verdict</div><div class="agent-card__body">' + escHtml(safe(r.summary,'')) + '</div></div>';
  html += '</div></div>';
  // Financial Metrics
  html += '<div class="detail-section"><div class="detail-section__title">Financial Metrics</div><div class="metrics-grid">';
  html += renderMetricCard('PE Ratio', formatNum(m.pe_ratio));
  html += renderMetricCard('Forward PE', formatNum(m.forward_pe));
  html += renderMetricCard('ROE', m.roe != null ? m.roe.toFixed(2) + '%' : 'N/A');
  html += renderMetricCard('EPS', formatNum(m.eps));
  html += renderMetricCard('Revenue Growth', pct(m.revenue_growth));
  html += renderMetricCard('Market Cap', formatMktCap(m.market_cap));
  html += '</div></div>';
  // Relative Valuation
  if (rv && Object.keys(rv).length) {
    html += '<div class="detail-section"><div class="detail-section__title">Relative Valuation</div><div class="tech-grid">';
    html += renderTechItem('Company PE', formatNum(rv.company_pe));
    html += renderTechItem('Sector Median PE', formatNum(rv.sector_median_pe));
    html += renderTechItem('PE Band', safe(rv.sector_pe_band));
    html += renderTechItem('Peer Position', safe(rv.peer_position));
    html += renderTechItem('Fwd PE Compression', rv.forward_pe_compression ? 'Yes' : 'No');
    html += renderTechItem('Valuation View', safe(rv.valuation_view));
    html += '</div></div>';
  }
  // Technical Context
  if (tc && Object.keys(tc).length) {
    html += '<div class="detail-section"><div class="detail-section__title">Technical Structure</div><div class="tech-grid">';
    html += renderTechItem('Trend', safe(tc.trend));
    html += renderTechItem('Reversal Phase', safe(tc.reversal_phase));
    html += renderTechItem('Price Structure', safe(tc.price_structure));
    html += renderTechItem('Correction Depth', pct(tc.correction_depth_pct));
    html += renderTechItem('From 52W High', pct(tc.pct_from_52w_high));
    html += renderTechItem('From 52W Low', pct(tc.pct_from_52w_low));
    html += renderTechItem('Above 200 DMA', tc.above_200_dma ? 'Yes' : 'No');
    html += renderTechItem('Above 50 DMA', tc.above_50_dma ? 'Yes' : 'No');
    html += renderTechItem('Higher Lows', tc.higher_lows_forming ? 'Yes' : 'No');
    html += renderTechItem('Stabilizing', tc.price_stabilizing ? 'Yes' : 'No');
    html += renderTechItem('RS Improving', tc.rs_improving ? 'Yes' : 'No');
    html += renderTechItem('Volume', safe(tc.volume_signal));
    html += '</div></div>';
  }
  // Signals
  html += '<div class="detail-section"><div class="detail-section__title">Deterministic Signals</div><div class="tech-grid">';
  html += renderTechItem('Valuation', safe(sig.valuation));
  html += renderTechItem('Profitability', safe(sig.profitability));
  html += renderTechItem('Growth', safe(sig.growth));
  html += '</div>';
  if (r.supporting_signals && r.supporting_signals.length) {
    html += '<div style="margin-top:12px"><div style="font-size:var(--fs-xs);color:var(--text-tertiary);margin-bottom:6px">SUPPORTING SIGNALS</div><div class="signal-chips">';
    r.supporting_signals.forEach(s => { html += '<span class="signal-tag signal-tag--bullish">' + escHtml(s) + '</span>'; });
    html += '</div></div>';
  }
  if (r.risk_signals && r.risk_signals.length) {
    html += '<div style="margin-top:8px"><div style="font-size:var(--fs-xs);color:var(--text-tertiary);margin-bottom:6px">RISK SIGNALS</div><div class="signal-chips">';
    r.risk_signals.forEach(s => { html += '<span class="signal-tag signal-tag--bearish">' + escHtml(s) + '</span>'; });
    html += '</div></div>';
  }
  html += '</div>';
  // News Sentiment
  html += '<div class="detail-section"><div class="detail-section__title">News & Sentiment</div>';
  html += '<div style="font-size:var(--fs-xs);color:var(--text-tertiary);margin-bottom:8px">Net Sentiment: <strong style="color:var(--text-primary)">' + safe(ns.net_sentiment) + '</strong></div>';
  const bullNews = ns.bullish || [];
  const bearNews = ns.bearish || [];
  if (bullNews.length) {
    html += '<div style="display:flex;flex-direction:column;gap:4px">';
    bullNews.forEach(n => { html += '<div class="news-item news-item--bullish">' + escHtml(n) + '</div>'; });
    html += '</div>';
  }
  if (bearNews.length) {
    html += '<div style="display:flex;flex-direction:column;gap:4px;margin-top:8px">';
    bearNews.forEach(n => { html += '<div class="news-item news-item--bearish">' + escHtml(n) + '</div>'; });
    html += '</div>';
  }
  if (!bullNews.length && !bearNews.length) {
    html += '<div style="font-size:var(--fs-xs);color:var(--text-muted)">No classified news available for this stock.</div>';
  }
  html += '</div>';
  html += '</div>'; // detail-body
  el.innerHTML = html;
}
function renderMetricCard(label, value) {
  return '<div class="metric-card"><div class="metric-card__label">' + label + '</div><div class="metric-card__value">' + value + '</div></div>';
}
function renderTechItem(label, value) {
  return '<div class="tech-item"><span class="tech-item__label">' + label + '</span><span class="tech-item__value">' + value + '</span></div>';
}
// ============================================
// PIPELINE VIEW (detailed stage cards)
// ============================================
function renderPipelineView() {
  const el = document.getElementById('pipelineViewContent');
  if (!el) return;
  if (!AppState.recommendations.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-state__icon">\u{1F50D}</div><div class="empty-state__title">No Pipeline Data</div><div class="empty-state__desc">Run the workflow or load a watchlist file to see pipeline analysis.</div></div>';
    return;
  }
  const rec = AppState.recommendations[0];
  const m = rec.metrics || {};
  const tc = rec.technical_context || {};
  const rv = rec.relative_valuation || {};
  const sig = rec.signals || {};
  const ns = rec.news_sentiment || {};
  const meta = getDecisionMeta(rec.decision);
  let html = '';
  // Stage 1 — Ingestion
  html += '<div class="pipeline-stage-card" style="animation-delay:0s"><div class="pipeline-stage-card__header"><div class="pipeline-stage-card__number" style="background:var(--node-ingest)">1</div><div class="pipeline-stage-card__title">Ingestion — Reversal Screener Detection</div><div class="pipeline-stage-card__subtitle">' + AppState.recommendations.length + ' candidates</div></div>';
  html += '<div class="pipeline-stage-card__body"><div class="metrics-grid">';
  AppState.recommendations.forEach(r => {
    html += '<div class="metric-card"><div class="metric-card__label">Symbol</div><div class="metric-card__value">' + escHtml(r.symbol) + '</div></div>';
  });
  html += '</div><p style="margin-top:12px;font-size:var(--fs-xs);color:var(--text-tertiary)">Stocks detected by reversal screener as possible recovery opportunities. Source: Chartink reversal scan.</p></div></div>';
  // Stage 2 — Market Data
  html += '<div class="pipeline-stage-card" style="animation-delay:0.1s"><div class="pipeline-stage-card__header"><div class="pipeline-stage-card__number" style="background:var(--node-enrich)">2</div><div class="pipeline-stage-card__title">Market + Financial Data Fetch</div><div class="pipeline-stage-card__subtitle">yfinance + SearchAPI</div></div>';
  html += '<div class="pipeline-stage-card__body"><div class="metrics-grid">';
  html += renderMetricCard('PE Ratio', formatNum(m.pe_ratio));
  html += renderMetricCard('Forward PE', formatNum(m.forward_pe));
  html += renderMetricCard('ROE', m.roe != null ? m.roe.toFixed(2) + '%' : 'N/A');
  html += renderMetricCard('EPS', formatNum(m.eps));
  html += renderMetricCard('Revenue Growth', pct(m.revenue_growth));
  html += renderMetricCard('Market Cap', formatMktCap(m.market_cap));
  html += '</div></div></div>';
  // Stage 3 — Enrichment
  html += '<div class="pipeline-stage-card" style="animation-delay:0.2s"><div class="pipeline-stage-card__header"><div class="pipeline-stage-card__number" style="background:var(--node-signal)">3</div><div class="pipeline-stage-card__title">Enrichment + AI Context Building</div><div class="pipeline-stage-card__subtitle">Signal Generation</div></div>';
  html += '<div class="pipeline-stage-card__body"><div class="tech-grid">';
  html += renderTechItem('Valuation Signal', safe(sig.valuation));
  html += renderTechItem('Profitability', safe(sig.profitability));
  html += renderTechItem('Growth', safe(sig.growth));
  html += renderTechItem('Reversal Phase', safe(tc.reversal_phase));
  html += renderTechItem('Price Structure', safe(tc.price_structure));
  html += renderTechItem('Valuation View', safe(rv.valuation_view));
  html += renderTechItem('Net Sentiment', safe(ns.net_sentiment));
  html += renderTechItem('RS Improving', tc.rs_improving ? 'Yes' : 'No');
  html += '</div></div></div>';
  // Stage 4 — Multi-Agent Debate
  html += '<div class="pipeline-stage-card" style="animation-delay:0.3s"><div class="pipeline-stage-card__header"><div class="pipeline-stage-card__number" style="background:var(--node-debate)">4</div><div class="pipeline-stage-card__title">Multi-Agent Analysis</div><div class="pipeline-stage-card__subtitle">Bull \u00B7 Bear \u00B7 Judge</div></div>';
  html += '<div class="pipeline-stage-card__body"><div class="agents-grid">';
  html += '<div class="agent-card agent-card--bull"><div class="agent-card__header">\uD83D\uDC02 Bull Agent</div><div class="agent-card__body">' + escHtml(safe(rec.bull_case_summary,'')) + '</div></div>';
  html += '<div class="agent-card agent-card--bear"><div class="agent-card__header">\uD83D\uDC3B Bear Agent</div><div class="agent-card__body">' + escHtml(safe(rec.bear_case_summary,'')) + '</div></div>';
  html += '</div><div class="agents-grid agents-grid--full" style="margin-top:12px">';
  html += '<div class="agent-card agent-card--judge"><div class="agent-card__header">\u2696\uFE0F Judge Agent</div><div class="agent-card__body">' + escHtml(safe(rec.summary,'')) + '</div></div>';
  html += '</div></div></div>';
  // Stage 5 — Final Recommendation
  html += '<div class="pipeline-stage-card" style="animation-delay:0.4s"><div class="pipeline-stage-card__header"><div class="pipeline-stage-card__number" style="background:var(--node-watchlist)">5</div><div class="pipeline-stage-card__title">Final Recommendation</div><div class="pipeline-stage-card__subtitle">' + meta.label + '</div></div>';
  html += '<div class="pipeline-stage-card__body"><div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">';
  html += '<span class="status-badge ' + meta.cssClass + '" style="font-size:var(--fs-sm);padding:4px 12px">' + meta.label + '</span>';
  html += '<div class="confidence-bar"><div class="confidence-bar__track" style="max-width:120px"><div class="confidence-bar__fill" style="width:' + ((rec.confidence||0)*100) + '%;background:' + getConfidenceColor(rec.confidence) + '"></div></div><div class="confidence-bar__label">' + ((rec.confidence||0)*100).toFixed(0) + '%</div></div>';
  html += '</div><p style="font-size:var(--fs-sm);color:var(--text-secondary);line-height:1.7">' + escHtml(safe(rec.summary,'')) + '</p></div></div>';
  el.innerHTML = html;
}
// ============================================
// EXECUTION LOG VIEW
// ============================================
function renderExecutionLog() {
  const el = document.getElementById('executionLogContent');
  if (!el) return;
  if (!AppState.executionLog.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-state__icon">\u{23F1}\uFE0F</div><div class="empty-state__title">No Execution Log</div><div class="empty-state__desc">Run the workflow to see execution timeline.</div></div>';
    return;
  }
  let html = '<div class="execution-log">';
  AppState.executionLog.forEach(item => {
    const statusCls = item.status === 'SUCCESS' ? 'success' : 'failed';
    html += '<div class="execution-log-item">';
    html += '<div class="execution-log-item__node">' + escHtml(item.node) + '</div>';
    html += '<div class="execution-log-item__status ' + statusCls + '">' + item.status + '</div>';
    html += '<div class="execution-log-item__duration">' + (item.duration != null ? item.duration.toFixed(2) + 's' : '') + '</div>';
    html += '</div>';
  });
  html += '</div>';
  el.innerHTML = html;
}
// ============================================
// VIEW SWITCHING
// ============================================
function switchView(view) {
  AppState.view = view;
  document.querySelectorAll('.view-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-view') === view));
  document.querySelectorAll('.view-panel').forEach(p => p.classList.toggle('hidden', p.id !== 'view-' + view));
  if (view === 'pipeline') renderPipelineView();
  if (view === 'log') renderExecutionLog();
}
// ============================================
// DATA LOADING
// ============================================
function loadData(data) {
  AppState.data = data;
  AppState.recommendations = data.recommendations || [];
  AppState.executionLog = data.execution_log || [];
  AppState.tokenUsage = data.token_usage || null;
  AppState.generatedAt = data.generated_at || null;
  // Only mark pipeline complete if we actually have results
  AppState.pipelineStep = AppState.recommendations.length > 0 ? PIPELINE_STAGES.length : -1;
  renderPipeline();
  renderSummaryStats();
  renderWatchlistTable();
  updateSortIndicators();
  if (AppState.view === 'pipeline') renderPipelineView();
  if (AppState.view === 'log') renderExecutionLog();
  populateFilterDropdown();
}
function populateFilterDropdown() {
  const sel = document.getElementById('filterSelect');
  if (!sel) return;
  const decisions = [...new Set(AppState.recommendations.map(r => r.decision))];
  let html = '<option value="ALL">All Statuses</option>';
  decisions.forEach(d => {
    const meta = getDecisionMeta(d);
    html += '<option value="' + d + '">' + meta.label + '</option>';
  });
  sel.innerHTML = html;
}
// ============================================
// WORKFLOW RUNNER
// ============================================
async function runWorkflow() {
  if (AppState.isRunning) return;
  AppState.isRunning = true;
  const btn = document.getElementById('runBtn');
  const indicator = document.getElementById('runningIndicator');
  if (btn) btn.disabled = true;
  if (indicator) indicator.classList.remove('hidden');
  AppState.pipelineStep = 0;
  renderPipeline();
  // Step pipeline every ~15s — workflow typically takes 60-90s across 5 stages
  const stepInterval = setInterval(() => {
    if (AppState.pipelineStep < PIPELINE_STAGES.length - 1) {
      AppState.pipelineStep++;
      renderPipeline();
    }
  }, 15000);
  try {
    const data = await api.runWorkflow();
    clearInterval(stepInterval);
    loadData(data);
  } catch (err) {
    clearInterval(stepInterval);
    console.error('Workflow failed:', err);
    AppState.pipelineStep = -1;
    renderPipeline();
    alert('Workflow failed. Check console for details.');
  } finally {
    AppState.isRunning = false;
    if (btn) btn.disabled = false;
    if (indicator) indicator.classList.add('hidden');
  }
}
async function loadLatestWatchlist() {
  try {
    const data = await api.loadLatest();
    loadData(data);
  } catch (err) {
    console.error('Failed to load latest:', err);
  }
}
async function loadWatchlistHistory() {
  try {
    const data = await api.loadHistory();
    AppState.historyFiles = data.files || [];
    renderHistoryDropdown();
  } catch (err) {
    console.error('Failed to load history:', err);
  }
}
function renderHistoryDropdown() {
  const sel = document.getElementById('historySelect');
  if (!sel) return;
  let html = '<option value="">Load Previous Run...</option>';
  AppState.historyFiles.forEach(f => {
    // Format: "22_May_26_run_001.json" → "22 May 26 — Run 001"
    const display = f
      .replace('.json', '')
      .replace(/_run_(\d+)$/, ' — Run $1')
      .replace(/_/g, ' ');
    html += '<option value="' + escHtml(f) + '">' + escHtml(display) + '</option>';
  });
  sel.innerHTML = html;
}
async function handleHistorySelect(filename) {
  if (!filename) return;
  try {
    const data = await api.loadFile(filename);
    loadData(data);
  } catch (err) {
    console.error('Failed to load file:', err);
  }
}
// ============================================
// INIT
// ============================================
document.addEventListener('DOMContentLoaded', function() {
  applyTheme();
  renderPipeline();
  loadWatchlistHistory();

  // Auto-poll every 20 seconds to pick up runs triggered from the command line
  setInterval(async function() {
    if (AppState.isRunning) return;  // skip if a workflow is already running via UI
    try {
      const data = await api.loadLatest();
      // Only reload if the data is newer than what we currently have
      if (data && data.generated_at && data.generated_at !== AppState.generatedAt) {
        loadData(data);
      }
    } catch (_) {}
  }, 20000);

  // Keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && AppState.detailOpen) closeDetail();
  });
});
