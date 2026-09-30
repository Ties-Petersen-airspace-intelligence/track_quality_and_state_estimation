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
  compare: [],            // {kind:"raw", src, tid, color, hidden} or {kind:runId, track, color, hidden}
  compareOn: true,        // off: the map ignores the compare list, which stays as it is
  hover: null,            // {kind:"raw"|runId, i}
  rawPass: null,          // Uint8Array, 1 where a raw plot passes the filters
  visible: { raw: [], runs: {} },   // plot indices drawn right now, for the box select
  charts: [],             // {id, group:"raw"|"strategy", fields:[{source?, run?, column, label}], height, box}
  chartZoom: "timeline",  // "timeline": a drag zooms every chart, the map and the timeline; "box": a drag zooms one chart
};

export const $ = id => document.getElementById(id);
export const api = (what, params = {}) => fetch(`/api/${what}?` + new URLSearchParams({ case: S.CASE ? S.CASE.name : "", ...params })).then(r => r.json());
// the same, telling onProgress(bytes so far, bytes in all) as the answer arrives; the server sends its size up front
export async function apiProgress(what, params, onProgress) {
  const response = await fetch(`/api/${what}?` + new URLSearchParams({ case: S.CASE ? S.CASE.name : "", ...params }));
  const total = +response.headers.get("Content-Length") || 0, reader = response.body.getReader(), chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length; onProgress(got, total);
  }
  const bytes = new Uint8Array(got);
  let at = 0; for (const c of chunks) { bytes.set(c, at); at += c.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}
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
// the compare list shapes the map only while comparing is switched on and the list has tracks
export const comparing = () => S.compareOn && S.compare.length > 0;
export const trackLabel = c => c.kind === "raw" ? `${SOURCE_NAME[c.src]} ${c.tid}` : `${runName(c.kind)} ${c.track}`;

export function fadeWindowMs() {
  const v = $("fadeWin").value;
  if (v === "custom") return Math.max(1, +$("fadeCustom").value || 120) * 1000;
  return +v * 1000;
}
// a metre slider's position (0 to 100) to metres, 10 to 1,000 m on a square curve: halfway is about 260 m
export const sliderMetres = id => { const m = 10 + 990 * (+$(id).value / 100) ** 2; return m < 100 ? Math.round(m) : Math.round(m / 10) * 10; };
export const metresSlider = m => Math.round(Math.sqrt((m - 10) / 990) * 100);
export const clampNow = v => S.win ? Math.max(S.win[0], Math.min(S.win[1], v)) : Math.max(0, Math.min(S.CASE.span_ms, v));
