// Everything the page knows, in one place, so every module reads and writes the same state.
export const S = {
  CASE: null,          // the case manifest from /api/case plus its name
  RAW: null,           // base columns of every raw plot, sorted by receipt time
  RUNS: {},            // run id -> base columns of its fused plots, sorted by emission time
  OUTCOMES: {},        // run id -> state, track, reason and recorded numbers per raw plot
  FIELDS: {},          // "raw|source|column" or "run|id|column" -> values, loaded when a chart asks
  now: 0,              // ms after the case start
  win: null,           // zoomed time window [ms, ms], or null
  playing: false,
  runActive: new Set(),   // runs listed under Strategies
  runShown: new Set(),    // runs drawn on the map
  compare: [],            // {kind:"raw", src, tid, color} or {kind:runId, track, color}
  hover: null,            // {kind:"raw"|runId, i}
  rawPass: null,          // Uint8Array, 1 where a raw plot passes the filters
  visible: { raw: [], runs: {} },   // plot indices drawn right now, for the box select
  charts: [],             // {id, group:"raw"|"strategy", fields:[{source?, run?, column, label}], height}
};

export const $ = id => document.getElementById(id);
export const api = (what, params = {}) => fetch(`/api/${what}?` + new URLSearchParams({ case: S.CASE ? S.CASE.name : "", ...params })).then(r => r.json());
export const fmt = ms => new Date(S.CASE.t0_us / 1000 + ms).toISOString().slice(11, 19);
export const fmtMs = ms => fmt(ms) + "." + String(Math.round(((ms % 1000) + 1000) % 1000)).padStart(3, "0");
export const fmtN = v => v == null ? "" : Number(v).toLocaleString();
export const escapeHtml = t => String(t).replace(/[&<>"]/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[ch]));

export const SOURCE_NAME = { adsbx:"ADS-B Exchange", planefinder:"PlaneFinder", uavionix:"uAvionix", stdds:"STDDS", tfms_ti:"TFMS TI", tfms_or:"TFMS OR", ual:"United", asa:"Alaska" };
export const SOURCE_BY_ID = { 4:"adsbx", 3:"planefinder", 11:"uavionix", 10:"stdds", 1:"tfms_ti", 2:"tfms_or", 6:"ual", 5:"asa" };

// a run id is "strategy/label", production is "prod_fusion_append" or "prod_fusion_regular"
export const strategyOf = id => id.split("/")[0];
export const runById = id => S.CASE.runs.find(r => r.id === id);
export function runName(id) {
  const [strategy, label] = id.split("/");
  const several = S.CASE.runs.filter(r => strategyOf(r.id) === strategy).length > 1;
  return strategy.replace(/_/g, " ") + (label && several ? " " + label : "");
}
export const table = kind => kind === "raw" ? S.RAW : S.RUNS[kind];

// which compare entry a plot belongs to, if any
export function compareEntry(kind, i) {
  const d = table(kind);
  return kind === "raw" ? S.compare.find(c => c.kind === "raw" && c.src === d.src[i] && c.tid === d.tid[i]) : S.compare.find(c => c.kind === kind && c.track === d.track[i]);
}
export const trackLabel = c => c.kind === "raw" ? `${SOURCE_NAME[c.src]} ${c.tid}` : `${runName(c.kind)} ${c.track}`;

export function fadeWindowMs() {
  const v = $("fadeWin").value;
  if (v === "custom") return Math.max(1, +$("fadeCustom").value || 120) * 1000;
  return +v * 1000;
}
export const clampNow = v => S.win ? Math.max(S.win[0], Math.min(S.win[1], v)) : Math.max(0, Math.min(S.CASE.span_ms, v));
