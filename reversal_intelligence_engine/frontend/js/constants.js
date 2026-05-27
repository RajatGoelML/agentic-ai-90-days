// ============================================
// CONSTANTS — Reversal Intelligence Engine
// ============================================
const API_BASE = 'http://127.0.0.1:8000';
const DECISION_MAP = {
  STRONG_BUY: { label: 'Strong Buy', cssClass: 'status-badge--strong-buy', color: 'var(--status-strong-buy)' },
  EARLY_REVERSAL_CANDIDATE: { label: 'Early Reversal', cssClass: 'status-badge--early-reversal', color: 'var(--status-early-reversal)' },
  GOOD_COMPANY_BAD_PRICE: { label: 'Good Co / Bad Price', cssClass: 'status-badge--good-company', color: 'var(--status-good-company)' },
  HIGH_RISK_REVERSAL: { label: 'High Risk Reversal', cssClass: 'status-badge--high-risk', color: 'var(--status-high-risk)' },
  AVOID_STRUCTURALLY_WEAK: { label: 'Avoid — Weak', cssClass: 'status-badge--avoid', color: 'var(--status-avoid)' },
  WATCHLIST: { label: 'Watchlist', cssClass: 'status-badge--watchlist', color: 'var(--status-watchlist)' },
  WAIT_FOR_CONFIRMATION: { label: 'Wait for Confirmation', cssClass: 'status-badge--wait', color: 'var(--status-wait)' },
  MOMENTUM_NOT_CONFIRMED: { label: 'Momentum Unconfirmed', cssClass: 'status-badge--momentum', color: 'var(--status-momentum)' },
};
const PIPELINE_STAGES = [
  { id: 'INGEST', label: 'Ingestion', icon: '\u{1F4E1}', desc: 'Reversal screener detection' },
  { id: 'ENRICHMENT', label: 'Market Data', icon: '\u{1F4CA}', desc: 'Financial intelligence fetch' },
  { id: 'SIGNAL', label: 'Enrichment', icon: '\u{2699}\uFE0F', desc: 'AI context building' },
  { id: 'DEBATE', label: 'Agent Analysis', icon: '\u{2696}\uFE0F', desc: 'Multi-agent debate' },
  { id: 'WATCHLIST', label: 'Recommendation', icon: '\u{1F3AF}', desc: 'Final classification' },
];
const BULLISH_SIGNALS = ['STRONG_ROE','EARLY_REVERSAL_FORMING','HIGHER_LOWS','PRICE_STABILIZING','RS_IMPROVING','SECTOR_DISCOUNT','EARNINGS_GROWTH_NORMALIZING','ACCUMULATION_DETECTED','VOLUME_SPIKE','BREAKOUT_POTENTIAL'];
const BEARISH_SIGNALS = ['LOW_REVENUE_GROWTH','NEGATIVE_EPS','HIGH_DEBT','DECLINING_ROE','REVENUE_DECLINING','WEAK_MOMENTUM','NO_REVERSAL_SIGNS','STRUCTURAL_DECLINE'];
// ============================================
// UTILS
// ============================================
function safe(val, fallback) { return val != null && val !== '' ? val : (fallback || 'N/A'); }
function pct(val) { return val != null ? val.toFixed(1) + '%' : 'N/A'; }
function usd(val) { return val != null ? '\u0024' + val.toFixed(4) : 'N/A'; }
function formatMktCap(val) {
  if (!val) return 'N/A';
  if (val >= 1e12) return '\u20B9' + (val/1e12).toFixed(2) + 'T';
  if (val >= 1e9) return '\u20B9' + (val/1e9).toFixed(2) + 'B';
  if (val >= 1e6) return '\u20B9' + (val/1e6).toFixed(1) + 'M';
  return '\u20B9' + val.toLocaleString();
}
function formatNum(val, dec) { return val != null ? Number(val).toFixed(dec || 2) : 'N/A'; }
function getDecisionMeta(decision) { return DECISION_MAP[decision] || { label: decision, cssClass: 'status-badge--wait', color: 'var(--status-wait)' }; }
function getConfidenceColor(conf) {
  if (conf >= 0.8) return 'var(--accent-green)';
  if (conf >= 0.6) return 'var(--accent-blue)';
  if (conf >= 0.4) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}
function isSignalBullish(s) { return BULLISH_SIGNALS.includes(s) || s.includes('STRONG') || s.includes('IMPROVING') || s.includes('REVERSAL') || s.includes('HIGHER') || s.includes('STABILIZ'); }
function escHtml(str) { const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }
function formatTimestamp(ts) {
  if (!ts) return 'N/A';
  const d = new Date(ts);
  return d.toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' }) + ' ' + d.toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit' });
}
// ============================================
// API CLIENT
// ============================================
const api = {
  async loadLatest() {
    const res = await fetch(API_BASE + '/api/watchlist/latest');
    if (!res.ok) throw new Error('Failed to load latest watchlist');
    return res.json();
  },
  async loadHistory() {
    const res = await fetch(API_BASE + '/api/watchlist/history');
    if (!res.ok) throw new Error('Failed to load history');
    return res.json();
  },
  async loadFile(filename) {
    const res = await fetch(API_BASE + '/api/watchlist/' + encodeURIComponent(filename));
    if (!res.ok) throw new Error('Failed to load file');
    return res.json();
  },
  async runWorkflow() {
    const res = await fetch(API_BASE + '/run-workflow', { method: 'POST' });
    if (!res.ok) throw new Error('Workflow failed');
    return res.json();
  }
};
