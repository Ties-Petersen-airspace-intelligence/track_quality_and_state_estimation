// Charts of the compared tracks against position time. Raw plot charts and strategy charts are kept apart, because
// the two have different fields: a raw chart picks fields of the source protos, a strategy chart fields of the fused
// plots or numbers the strategy recorded. Every chart starts from the field browser.
import { S, $, api, table, trackLabel, runName, SOURCE_NAME, fmt, escapeHtml, fmtN } from "./state.js";
import { SOURCE_COLOR, rgb, swatch } from "./palette.js";
import { loadOutcomes } from "./runs.js";
import { setHover } from "./mapview.js";
import { onZoom, resetZoom } from "./timeline.js";

let built = [];          // {spec, u, full, points, xs, labels}
let nextId = 1;
const hiddenSeries = {}; // chart id -> labels switched off in its legend

// ---------- values ----------

// a field's values as {kind, values, words}: kind is number, time (text read as a time) or text; words are the text
// found in a mostly numeric field, such as "ground" for an altitude
const OUTCOME_TEXT = { state:"state", track_id:"track", reason:"reason" };
async function rawValues(field) {
  if (field.run) {
    const o = await loadOutcomes(field.run);
    return OUTCOME_TEXT[field.column] ? { kind:"text", values:o[OUTCOME_TEXT[field.column]] } : { kind:"number", values:o.numbers[field.column] };
  }
  const key = `raw|${field.source}|${field.column}`;
  if (!S.FIELDS[key]) S.FIELDS[key] = await api("field", { source:field.source, column:field.column });
  return S.FIELDS[key];
}
async function runValues(id, column) {
  const run = S.RUNS[id];
  if (run[column]) return { kind:"number", values:run[column] };
  const key = `run|${id}|${column}`;
  if (!S.FIELDS[key]) S.FIELDS[key] = await api("field", { run:id, column });
  return S.FIELDS[key];
}
const MAX_LANES = 20;
const laneName = v => v == null ? "not set" : v === "" ? "empty" : String(v);

// ---------- building the charts ----------

export async function rebuildCharts() {
  for (const c of built) c.u.destroy();
  built = [];
  const token = ++rebuildToken;
  // load every field a chart needs before drawing any, so a slow field does not leave half the charts
  const values = new Map();
  for (const spec of S.charts) for (const f of spec.fields) {
    if (spec.group === "raw") values.set(fieldKey(f), await rawValues(f).catch(() => null));
    else for (const c of S.compare) if (!c.hidden && c.kind !== "raw" && S.RUNS[c.kind] && !values.has(c.kind + "|" + f.column)) values.set(c.kind + "|" + f.column, await runValues(c.kind, f.column).catch(() => null));
  }
  if (token !== rebuildToken) return;   // a newer rebuild started while this one waited
  for (const group of ["raw", "strategy"]) {
    const box = $(group + "Charts"); box.innerHTML = "";
    const specs = S.charts.filter(s => s.group === group);
    if (!specs.length) { box.innerHTML = `<div class="empty">No chart yet. Press + chart and pick one or more fields.</div>`; continue; }
    const points = comparedPoints(group);
    for (const spec of specs) built.push(makeChart(spec, points, values, box));
  }
  redrawCharts();
}
let rebuildToken = 0;
const fieldKey = f => f.run ? `out|${f.run}|${f.column}` : `raw|${f.source}|${f.column}`;

// every plot of every compared track of this group, sorted by position time
function comparedPoints(group) {
  const points = [];
  for (const c of S.compare) {
    if (c.hidden || (c.kind === "raw") !== (group === "raw")) continue;
    const d = table(c.kind); if (!d) continue;
    for (let i = 0; i < d.n; i++) {
      if (c.kind === "raw" ? d.src[i] !== c.src || d.tid[i] !== c.tid : d.track[i] !== c.track) continue;
      points.push({ kind:c.kind, i, t:d.t[i], track:c, known:c.kind === "raw" ? d.r[i] : d.created[i], until:c.kind === "raw" ? null : d.valid_to[i] });
    }
  }
  return points.sort((a, b) => a.t - b.t);
}

function makeChart(spec, points, values, box) {
  const xs = points.map(p => p.t / 1000), series = [{}], full = [], labels = [], legendItems = [];
  // every compared track and field that has values: its values per point (undefined where the point is another track's)
  const found = [];
  spec.fields.forEach(f => {
    for (const c of S.compare) {
      if (c.hidden || (c.kind === "raw") !== (spec.group === "raw")) continue;
      if (spec.group === "raw" && f.source && f.source !== c.src) continue;
      const v = spec.group === "raw" ? values.get(fieldKey(f)) : values.get(c.kind + "|" + f.column);
      if (!v || !v.values) continue;
      const raw = points.map(p => p.track === c ? v.values[p.i] : undefined), words = v.words ? points.map(p => p.track === c ? v.words[p.i] : undefined) : null;
      const kind = spec.kind || v.kind;
      if (kind !== "text" && !raw.some(y => y != null) && !(words && words.some(w => w != null))) continue;
      found.push({ f, c, raw, words, kind });
    }
  });
  const kind = spec.kind || (found[0] ? found[0].kind : "number");

  // text: one lane per value, in the order values first appear in time; each track gets a thin row inside every lane
  let lanes = null, wordLanes = null, tooMany = 0;
  if (kind === "text") {
    lanes = new Map();
    points.forEach((p, j) => { for (const s of found) if (s.raw[j] !== undefined) { const name = laneName(s.raw[j]); if (!lanes.has(name)) lanes.set(name, lanes.size); } });
    if (lanes.size > MAX_LANES) { tooMany = lanes.size; found.length = 0; }
  } else {
    // words mixed into numbers get lanes of their own below the numbers
    wordLanes = new Map();
    points.forEach((p, j) => { for (const s of found) if (s.words && s.words[j] != null && !wordLanes.has(s.words[j])) wordLanes.set(s.words[j], wordLanes.size); });
  }
  let low = Infinity, high = -Infinity;
  for (const s of found) if (kind !== "text") for (const y of s.raw) if (y != null) { if (y < low) low = y; if (y > high) high = y; }
  if (low === Infinity) { low = 0; high = 1; }
  const pad = (high - low) * 0.08 + (high === low ? 1 : 0);
  const band = (high - low + 2 * pad) * 0.12;   // the height of one word lane under a number chart
  const rows = Math.max(found.length, 1);
  const inLane = (lane, r) => lane + 0.1 + 0.8 * (r + 0.5) / rows;
  const wordY = (lane, r) => low - pad - band * inLane(lane, r);

  // one series per compared track and field; a second field of the same track is drawn hollow, or dashed for a line
  const fieldsSeen = new Map();   // compare entry -> how many of its fields are in the chart so far
  // the legend names the field only for a track with several fields here; one field per source needs just the track
  const fieldsOf = new Map(); for (const s of found) fieldsOf.set(s.c, (fieldsOf.get(s.c) || 0) + 1);
  found.forEach((s, r) => {
    const ys = kind === "text" ? s.raw.map(v => v === undefined ? null : inLane(lanes.get(laneName(v)), r))
                               : s.raw.map((y, j) => y != null ? y : (s.words && s.words[j] != null ? wordY(wordLanes.get(s.words[j]), r) : null));
    const k = fieldsSeen.get(s.c) || 0; fieldsSeen.set(s.c, k + 1);
    const label = trackLabel(s.c) + (fieldsOf.get(s.c) > 1 ? " · " + s.f.label : ""), line = spec.group === "strategy" && kind !== "text", color = rgb(s.c.color);
    series.push({ label, stroke:color, width:line ? 1.3 : 0, dash:line && k ? [5, 4] : undefined, paths:line ? uPlot.paths.linear() : () => null, spanGaps:kind !== "text",
                  points:{ show:true, size:line ? 3 : 4, width:1, stroke:color, fill:k ? "#0a0a0a" : color } });
    full.push(ys); labels.push(label);
    legendItems.push(`<span class="item${(hiddenSeries[spec.id] || new Set()).has(label) ? " off" : ""}" data-label="${escapeHtml(label)}" title="click to hide or show, shift click to show only this one">${swatch(s.c.color, line ? "line" : "dot")} ${escapeHtml(label)}</span>`);
  });
  const empty = tooMany ? `${tooMany} different values on the compared tracks, more than the ${MAX_LANES} a chart can show, so nothing is drawn`
    : S.compare.some(c => !c.hidden && (c.kind === "raw") === (spec.group === "raw")) ? "the compared tracks do not carry this field" : `compare a ${spec.group === "raw" ? "source" : "strategy"} track to fill this chart`;

  const el = document.createElement("div"); el.className = "chart";
  el.innerHTML = `<div class="chart-head"><b>${escapeHtml(spec.fields.map(f => f.label).join(", "))}</b><button class="icon-btn close" title="remove this chart">×</button></div>` +
    (kind === "time" ? `<div class="chart-note">Text read as times: the values are shown as times of day, UTC.</div>` : "") +
    `<div class="legend">${legendItems.join("") || `<span class="item ${tooMany ? "warn" : "dim"}">${empty}</span>`}</div>`;
  const holder = document.createElement("div"); holder.className = "holder"; const grip = document.createElement("div"); grip.className = "hgrip"; grip.title = "drag to change the height";
  el.append(holder, grip); box.appendChild(el);
  el.querySelector(".close").onclick = () => { S.charts = S.charts.filter(s => s !== spec); rebuildCharts(); };

  const axis = { stroke:"#888888", grid:{ stroke:"#1e1e1e", width:1, dash:[2, 4] }, ticks:{ stroke:"#333333", width:1, size:4 }, font:'10px "Simplon ASI Mono", "SF Mono", SFMono-Regular, Menlo, monospace' };
  // two ways to zoom: "timeline" drags a time window that every chart, the map and the timeline follow;
  // "box" drags a rectangle that zooms this chart alone, kept in spec.box until a double click
  const boxMode = S.chartZoom === "box";
  const yRange = kind === "text" ? [0, Math.max(lanes.size, 1)] : [low - pad - (wordLanes.size ? band * (wordLanes.size + 0.2) : 0), high + pad];
  const yAxis = yAxisFor(kind, lanes, wordLanes, low, high, pad, band);
  let chart = null;   // filled in once uPlot is built; its hooks can fire during construction
  const u = new uPlot({
    width:chartWidth(), height:spec.height || 220, legend:{ show:false },
    cursor:{ drag:{ x:true, y:boxMode }, focus:{ prox:16 }, points:{ show:false }, bind:{ dblclick:() => null } },
    scales:{
      x:{ time:false, range:(u, min, max) => u._byUser ? [min, max] : spec.box ? spec.box.x : u.scales.x.min == null ? [0, S.CASE.span_ms / 1000] : [min, max] },
      y:{ range:(u, min, max) => boxMode && u._byUser ? [min, max] : spec.box ? spec.box.y : yRange },
    },
    // time labels with seconds once the view is shorter than ten minutes, so zoomed ticks do not repeat
    axes:[{ ...axis, space:90, values:(u, vals) => vals.map(v => fmt(v * 1000).slice(0, u.scales.x.max - u.scales.x.min < 600 ? 8 : 5)) }, { ...axis, ...yAxis }],
    series,
    hooks:{
      // uPlot fires setScale once more after it is built; only a zoom made by the user counts
      setScale:[(u, key) => {
        if (!u._byUser || syncing) return;
        if (!boxMode) { if (key === "x") { u._byUser = false; onZoom(u.scales.x.min, u.scales.x.max); } return; }
        // uPlot sets x and then y in the same moment; keep both, and let the flag go once both are in
        spec.box = { x:[u.scales.x.min, u.scales.x.max], y:[u.scales.y.min, u.scales.y.max] };
      }],
      setCursor:[u => chartCursor(u, chart)],
      draw:[u => drawMarks(u, chart)],
    },
  }, [xs, ...full.map(() => xs.map(() => null))], holder);
  u.root.classList.toggle("box-zoom", boxMode);   // the drag rectangle gets all four edges, not only the two sides of a time band
  chart = { spec, u, full, points, xs, labels, values, kind, lanes, wordLanes, wordTop:low - pad };

  // legend: click hides or shows a series, shift click shows only that one, shift click again brings all back
  const items = [...el.querySelectorAll(".legend .item[data-label]")];
  items.forEach((item, k) => item.onclick = e => {
    const hidden = hiddenSeries[spec.id] ||= new Set();
    if (e.shiftKey) { const onlyThis = labels.every((l, j) => j === k ? !hidden.has(l) : hidden.has(l)); labels.forEach((l, j) => (onlyThis || j === k) ? hidden.delete(l) : hidden.add(l)); }
    else hidden.has(labels[k]) ? hidden.delete(labels[k]) : hidden.add(labels[k]);
    items.forEach((it, j) => it.classList.toggle("off", hidden.has(labels[j])));
    redrawCharts();
  });
  u.over.addEventListener("mousedown", () => { u._byUser = true; }, true);
  u.over.addEventListener("dblclick", () => {
    if (!boxMode) return resetZoom();
    // back to this chart's own full view; the other charts keep theirs
    spec.box = null; syncing = true;
    u.setScale("y", { min:yRange[0], max:yRange[1] });
    const [min, max] = S.win ? [S.win[0] / 1000, S.win[1] / 1000] : [0, S.CASE.span_ms / 1000];
    u.setScale("x", { min, max }); syncing = false;
  }, true);
  u.over.addEventListener("mouseleave", () => setHover(null));
  grip.onmousedown = e => {
    e.preventDefault(); const startY = e.clientY, startH = u.height;
    const move = ev => { spec.height = Math.max(80, Math.min(900, startH + ev.clientY - startY)); u.setSize({ width:u.width, height:spec.height }); };
    const up = () => { document.removeEventListener("mousemove", move); document.removeEventListener("mouseup", up); };
    document.addEventListener("mousemove", move); document.addEventListener("mouseup", up);
  };
  return chart;
}
// uPlot applies a drag's zoom while the mouse button goes up; after that, no scale change counts as the user's
document.addEventListener("mouseup", () => setTimeout(() => { for (const c of built) c.u._byUser = false; }));
// the chart card sits 1rem in from both panel edges; the plot fills the card less its own padding
// the value axis: numbers as they are, times as times of day, text as lane names; words under numbers get their names too
function yAxisFor(kind, lanes, wordLanes, low, high, pad, band) {
  const trim = t => t.length > 16 ? t.slice(0, 15) + "…" : t;
  if (kind === "text") {
    const names = [...lanes.keys()];
    const size = Math.min(140, 16 + 6.2 * Math.max(4, ...names.map(n => trim(n).length)));
    return { size, splits:() => names.map((_, k) => k + 0.5), values:(u, vals) => vals.map(v => trim(names[Math.floor(v)] ?? "")), grid:{ show:false } };
  }
  const number = v => kind === "time" ? new Date(v / 1000).toISOString().slice(11, 19) : fmtN(Math.round(v * 100) / 100);
  if (!wordLanes || !wordLanes.size) return { size:kind === "time" ? 70 : 56, values:(u, vals) => vals.map(number) };
  // numbers at nice steps above the words, one tick per word lane below them
  const words = [...wordLanes.keys()], step = niceStep((high - low + 2 * pad) / 4);
  const ticks = []; for (let v = Math.ceil((low - pad) / step) * step; v <= high + pad; v += step) ticks.push(v);
  const centres = words.map((_, k) => low - pad - band * (k + 0.5));
  return { size:Math.max(56, 16 + 6.2 * Math.max(...words.map(w => trim(w).length))), splits:() => [...ticks, ...centres],
           values:(u, vals) => vals.map(v => { const k = centres.findIndex(c => Math.abs(c - v) < 1e-9); return k >= 0 ? trim(words[k]) : number(v); }) };
}
function niceStep(raw) {
  const power = 10 ** Math.floor(Math.log10(raw || 1)), f = raw / power;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * power;
}

const chartWidth = () => $("rawCharts").clientWidth - 2 * parseFloat(getComputedStyle(document.documentElement).fontSize) - 10;
export function resizeCharts() { for (const c of built) c.u.setSize({ width:chartWidth(), height:c.u.height }); }

// ---------- keeping the charts in step with time now and the zoom ----------

// what was known at time now: raw plots we had received, strategy plots emitted and not yet replaced
const knownNow = p => p.known <= S.now && (p.until == null || p.until > S.now);
let syncing = false;
export function redrawCharts() {
  for (const c of built) {
    const hidden = hiddenSeries[c.spec.id] || new Set();
    const data = [c.xs, ...c.full.map((ys, k) => hidden.has(c.labels[k]) ? ys.map(() => null) : ys.map((y, j) => y != null && knownNow(c.points[j]) ? y : null))];
    // setData without resetting the scales keeps the zoom but does not repaint, so ask for the repaint, then move the axis
    c.u.setData(data, false);
    c.u.redraw(true, false);
    // a chart zoomed with a box keeps its box; the others follow the timeline window
    const [min, max] = c.spec.box ? c.spec.box.x : S.win ? [S.win[0] / 1000, S.win[1] / 1000] : [0, S.CASE.span_ms / 1000];
    if (Math.abs(c.u.scales.x.min - min) > 0.001 || Math.abs(c.u.scales.x.max - max) > 0.001) { syncing = true; c.u.setScale("x", { min, max }); syncing = false; }
  }
}

// the point closest to the cursor, in pixels
function nearest(u, chart) {
  const { left, top } = u.cursor; if (left == null || left < 0) return null;
  let best = null, bestDistance = 14;
  chart.full.forEach((ys, k) => {
    if ((hiddenSeries[chart.spec.id] || new Set()).has(chart.labels[k])) return;
    ys.forEach((y, j) => {
      if (y == null || !knownNow(chart.points[j])) return;
      const d = Math.hypot(u.valToPos(chart.xs[j], "x") - left, u.valToPos(y, "y") - top);
      if (d < bestDistance) { bestDistance = d; best = chart.points[j]; }
    });
  });
  return best;
}
function chartCursor(u, chart) {
  if (!chart || u.cursor.left == null || u.cursor.left < 0) return;
  const p = nearest(u, chart);
  if (!p) { setHover(null); return; }
  const rect = u.over.getBoundingClientRect(), map = $("mapwrap").getBoundingClientRect();
  setHover({ kind:p.kind, i:p.i }, map.width, Math.max(8, rect.top - map.top + u.cursor.top - 30), true);
}
// the now line and the hover ring, drawn on every chart
export function repaintCharts() { for (const c of built) c.u.redraw(false, false); }

function drawMarks(u, chart) {
  const ctx = u.ctx; ctx.save();
  // nothing drawn outside the plot area, so a point outside a zoomed view leaves no ring on the axes
  ctx.beginPath(); ctx.rect(u.bbox.left, u.bbox.top, u.bbox.width, u.bbox.height); ctx.clip();
  // lines between the lanes of a text chart, and above the word lanes of a number chart
  const hline = (y, dash) => { const py = u.valToPos(y, "y", true); ctx.strokeStyle = "#2a2d33"; ctx.lineWidth = 1; ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(u.bbox.left, py); ctx.lineTo(u.bbox.left + u.bbox.width, py); ctx.stroke(); ctx.setLineDash([]); };
  if (chart && chart.kind === "text") for (let k = 1; k < chart.lanes.size; k++) hline(k, []);
  if (chart && chart.wordLanes && chart.wordLanes.size) hline(chart.wordTop, [4, 3]);
  const x = u.valToPos(S.now / 1000, "x", true);
  if (x >= u.bbox.left && x <= u.bbox.left + u.bbox.width) { ctx.strokeStyle = "#ccff00"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, u.bbox.top); ctx.lineTo(x, u.bbox.top + u.bbox.height); ctx.stroke(); }
  if (chart && S.hover) {
    const j = chart.points.findIndex(p => p.kind === S.hover.kind && p.i === S.hover.i);
    if (j >= 0) for (const ys of chart.full) if (ys[j] != null) {
      ctx.strokeStyle = "#ccff00"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(u.valToPos(chart.xs[j], "x", true), u.valToPos(ys[j], "y", true), 7, 0, Math.PI * 2); ctx.stroke();
    }
  }
  ctx.restore();
}

// ---------- the field browser ----------

let browsing = null, picked = new Map();   // group being browsed; field key -> field

export function openFieldBrowser(group, button) {
  browsing = group; picked = new Map();
  $("fbTitle").textContent = group === "raw" ? "raw plot fields" : "strategy fields";
  $("fbSearch").value = ""; $("fbPicked").textContent = "pick one or more fields";
  renderFieldList();
  const r = button.getBoundingClientRect(), el = $("fieldBrowser");
  el.classList.add("open");
  el.style.left = Math.max(8, r.right - el.offsetWidth) + "px"; el.style.top = Math.max(8, Math.min(r.bottom + 4, window.innerHeight - el.offsetHeight - 8)) + "px";
  $("fbSearch").focus();
  // the sources' fields are read the first time the list opens, and what the strategies recorded per raw plot joins
  // the list once it has loaded; the list opens without waiting for either
  if (group !== "raw") return;
  if (!S.RAW.schema) loadRawSchema().then(() => { if (browsing === "raw") renderFieldList(); });
  const missing = [...S.runActive].filter(id => !id.startsWith("prod_fusion") && !S.OUTCOMES[id]);
  if (missing.length) Promise.allSettled(missing.map(loadOutcomes)).then(() => { if (browsing === "raw") renderFieldList(); });
}
// the sources' fields: the server builds them in the background once the case is open; asked for right after the page
// has loaded, so they are usually there by the time the field list opens
let rawSchema = null;
export const loadRawSchema = () => rawSchema ||= api("schema").then(fields => { S.RAW.schema = fields; }, () => { rawSchema = null; });
export function closeFieldBrowser() { $("fieldBrowser").classList.remove("open"); $("fbInfo").style.display = "none"; browsing = null; }

function groups() {
  if (browsing === "raw") {
    const out = Object.entries(S.RAW.schema).map(([src, fields]) => ({ title:SOURCE_NAME[src], color:SOURCE_COLOR[src], fields:fields.map(f => ({ ...f, source:src, label:`${src}.${f.name}` })) }));
    for (const id of S.runActive) {
      const o = S.OUTCOMES[id]; if (!o || !Object.keys(o.numbers || {}).length) continue;
      const texts = [["state", "What the strategy did with the plot: used, skipped, dropped, rejected or unknown."], ["track_id", "The strategy's track the plot went into, or was checked against."], ["reason", "The strategy's few words on why it skipped, dropped or rejected the plot."]]
        .map(([name, doc]) => { const v = o[OUTCOME_TEXT[name]]; return { name, kind:"text", count:v.filter(x => x != null && x !== "").length, distinct:new Set(v).size, run:id, label:`${runName(id)} ${name}`, note:S.CASE.notes?.[name] || doc, doc:`Recorded by ${runName(id)} in its raw_plots.parquet; not part of any proto.` }; });
      out.push({ title:`recorded per raw plot by ${runName(id)}`, fields:[...texts, ...Object.keys(o.numbers).map(name => {
        // a loop, not Math.min(...values): a big case has a million values, more than a call can take as arguments
        let count = 0, min = Infinity, max = -Infinity;
        for (const v of o.numbers[name]) if (v != null) { count++; if (v < min) min = v; if (v > max) max = v; }
        return { name, kind:"number", count, min, max, run:id, label:`${runName(id)} ${name}`, note:S.CASE.notes?.[name] || "",
                 doc:`Recorded by the strategy ${runName(id)} for each raw plot it handled, in its raw_plots.parquet. Not part of any proto.` };
      })] });
    }
    return out;
  }
  // the fields of every drawn strategy run, each field once
  const fused = new Map(), state = new Map();
  for (const id of S.runShown) for (const f of (S.RUNS[id] || {}).schema || []) {
    const target = f.table === "track_state" ? state : fused, seen = target.get(f.name);
    const doc = f.table === "track_state" ? "Recorded by the strategy about its track as of each plot, in its track_state.parquet. Not part of any proto." : f.doc;
    target.set(f.name, { name:f.name, kind:f.kind, words:f.words, distinct:f.distinct, note:f.note, count:(seen ? seen.count : 0) + f.count, runs:[...(seen ? seen.runs : []), runName(id)], column:f.name, label:f.name, doc:seen ? seen.doc : doc,
                         min:Math.min(seen?.min ?? Infinity, f.min ?? Infinity), max:Math.max(seen?.max ?? -Infinity, f.max ?? -Infinity) });
  }
  return [{ title:"fused plot fields", fields:[...fused.values()] }, { title:"recorded about the track by the strategy", fields:[...state.values()] }].filter(g => g.fields.length);
}

function renderFieldList() {
  const query = $("fbSearch").value.trim().toLowerCase(), list = $("fbList");
  if (browsing === "raw" && !S.RAW.schema) { list.innerHTML = `<div class="empty" style="padding:0.7rem">Reading the fields of every source…</div>`; return; }
  const all = groups();
  if (!all.length) { list.innerHTML = `<div class="empty" style="padding:0.7rem">${browsing === "raw" ? "This case has no raw plots." : "Tick a strategy run under Strategies first; its fields show here."}</div>`; return; }
  list.innerHTML = all.map((g, gi) => {
    const fields = g.fields.filter(f => !query || f.name.toLowerCase().includes(query)).sort((a, b) => a.name.localeCompare(b.name));
    if (!fields.length) return "";
    return `<div class="fb-group">${g.color ? swatch(g.color) : ""}${escapeHtml(g.title)}</div>` + fields.map((f, fi) => {
      const usable = f.count > 0, key = `${gi}|${f.name}`;
      return `<label class="${usable ? "" : "off"}"><input type="checkbox" data-key="${escapeHtml(key)}" ${usable ? "" : "disabled"} ${picked.has(key) ? "checked" : ""}><span class="name">${escapeHtml(f.name)}</span><span class="kind">${KIND_LABEL(f)} · ${fmtN(f.count)}</span><span class="info" data-key="${escapeHtml(key)}">i</span></label>`;
    }).join("");
  }).join("") || `<div class="empty" style="padding:0.7rem">No field matches.</div>`;
  // the i on each row: a card with what the field is, how it looks in this case, and why it is greyed out
  list.querySelectorAll(".info").forEach(info => {
    const [gi, name] = info.dataset.key.split("|"), g = all[+gi], f = g.fields.find(x => x.name === name);
    info.onclick = e => e.preventDefault();   // the i sits inside the row's label; it must not tick the field
    info.onmouseenter = () => showFieldInfo(info, f, g);
    info.onmouseleave = () => { $("fbInfo").style.display = "none"; };
  });
  list.querySelectorAll("input[data-key]").forEach(cb => cb.onchange = () => {
    const [gi, name] = cb.dataset.key.split("|"), f = all[+gi].fields.find(x => x.name === name);
    cb.checked ? picked.set(cb.dataset.key, f) : picked.delete(cb.dataset.key);
    $("fbPicked").textContent = picked.size ? [...picked.values()].map(p => p.label).join(", ") : "pick one or more fields";
  });
}

// what the list says a field is: text read as times keeps saying text
const KIND_LABEL = f => f.kind === "time" ? "text as time" : f.kind === "text" ? "text" : f.words && f.words.length ? "number + words" : "number";

function showFieldInfo(anchor, f, g) {
  // times are stored as microseconds since the epoch; show them as times of day
  const value = v => v > 1e14 ? new Date(v / 1000).toISOString().slice(11, 19) + " Z" : fmtN(Math.round(v * 1000) / 1000);
  const why = !f.count ? "No plot in this case carries a value, so there is nothing to chart." : "";
  const how = f.kind === "time" ? "Stored as text; read as a date and time and charted as times of day, UTC."
    : f.kind === "text" ? `Charted as lanes, one per value in the order they first appear; ${f.distinct != null ? fmtN(f.distinct) + " different values in this case, " : ""}up to ${MAX_LANES} fit on the compared tracks.`
    : f.words && f.words.length ? `Numbers, with some text mixed in (${f.words.slice(0, 4).map(w => `"${w}"`).join(", ")}), charted in lanes under the numbers.` : "";
  const where = f.source ? `${SOURCE_NAME[f.source]} raw plots` : f.runs ? f.runs.join(", ") : g.title;
  const card = $("fbInfo");
  card.innerHTML = `<div class="fi-name">${escapeHtml(f.name)}</div>` +
    (f.note ? `<div class="fi-note">${escapeHtml(f.note)}</div>` : "") +
    `<div class="fi-doc"><span class="fi-label">proto comment</span>${f.doc ? escapeHtml(f.doc) : `<span class="dim">none</span>`}</div>` +
    (how ? `<div class="fi-how">${escapeHtml(how)}</div>` : "") +
    `<div class="fi-meta"><span>${KIND_LABEL(f)}</span><span>${where}</span><span>set on ${fmtN(f.count)} ${f.count === 1 ? "row" : "rows"}</span>${f.kind !== "text" && f.count && Number.isFinite(f.min) ? `<span>${value(f.min)} – ${value(f.max)}</span>` : ""}</div>` +
    (why ? `<div class="fi-why">${why}</div>` : "");
  card.style.display = "block";
  // to the left of the field list, level with the row, kept on screen
  const r = anchor.getBoundingClientRect(), box = $("fieldBrowser").getBoundingClientRect();
  card.style.left = Math.max(8, box.left - card.offsetWidth - 8) + "px";
  card.style.top = Math.max(8, Math.min(r.top - 12, window.innerHeight - card.offsetHeight - 8)) + "px";
}

export function wireFieldBrowser() {
  $("fbSearch").oninput = renderFieldList;
  $("fbCancel").onclick = closeFieldBrowser;
  $("fbAdd").onclick = () => {
    if (!picked.size) return;
    // numbers, times and text cannot share an axis: one chart per kind picked
    const byKind = new Map();
    for (const f of picked.values()) (byKind.get(f.kind) || byKind.set(f.kind, []).get(f.kind)).push(f);
    for (const [kind, fields] of byKind) S.charts.push({ id:nextId++, group:browsing, kind, fields:fields.map(f => browsing === "raw" ? (f.run ? { run:f.run, column:f.name, label:f.label } : { source:f.source, column:f.name, label:f.label }) : { column:f.name, label:f.label }) });
    closeFieldBrowser(); rebuildCharts();
  };
  document.addEventListener("mousedown", e => { if (browsing && !e.target.closest("#fieldBrowser, #addRawChart, #addStrategyChart")) closeFieldBrowser(); });
}
