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

async function rawValues(field) {
  if (field.run) return (await loadOutcomes(field.run)).numbers[field.column];
  const key = `raw|${field.source}|${field.column}`;
  if (!S.FIELDS[key]) S.FIELDS[key] = (await api("field", { source:field.source, column:field.column })).values;
  return S.FIELDS[key];
}
async function runValues(id, column) {
  const run = S.RUNS[id];
  if (run[column]) return run[column];
  const key = `run|${id}|${column}`;
  if (!S.FIELDS[key]) S.FIELDS[key] = (await api("field", { run:id, column })).values;
  return S.FIELDS[key];
}

// ---------- building the charts ----------

export async function rebuildCharts() {
  for (const c of built) c.u.destroy();
  built = [];
  const token = ++rebuildToken;
  // load every field a chart needs before drawing any, so a slow field does not leave half the charts
  const values = new Map();
  for (const spec of S.charts) for (const f of spec.fields) {
    if (spec.group === "raw") values.set(fieldKey(f), await rawValues(f).catch(() => null));
    else for (const c of S.compare) if (c.kind !== "raw" && S.RUNS[c.kind] && !values.has(c.kind + "|" + f.column)) values.set(c.kind + "|" + f.column, await runValues(c.kind, f.column).catch(() => null));
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
    if ((c.kind === "raw") !== (group === "raw")) continue;
    const d = table(c.kind); if (!d) continue;
    for (let i = 0; i < d.n; i++) {
      if (c.kind === "raw" ? d.src[i] !== c.src || d.tid[i] !== c.tid : d.track[i] !== c.track) continue;
      points.push({ kind:c.kind, i, t:d.t[i], track:c, known:c.kind === "raw" ? d.r[i] : d.created[i], until:c.kind === "raw" ? null : d.valid_to[i] });
    }
  }
  return points.sort((a, b) => a.t - b.t);
}

function makeChart(spec, points, values, box) {
  const xs = points.map(p => p.t / 1000), series = [{}], full = [], labels = [], legendItems = [], all = [];
  // one series per compared track and field; a second field of the same track is drawn hollow, or dashed for a line
  const fieldsSeen = new Map();   // compare entry -> how many of its fields are in the chart so far
  spec.fields.forEach(f => {
    for (const c of S.compare) {
      if ((c.kind === "raw") !== (spec.group === "raw")) continue;
      if (spec.group === "raw" && f.source && f.source !== c.src) continue;
      const v = spec.group === "raw" ? values.get(fieldKey(f)) : values.get(c.kind + "|" + f.column);
      if (!v) continue;
      const ys = points.map(p => p.track === c ? (v[p.i] ?? null) : null);
      if (!ys.some(y => y != null)) continue;
      for (const y of ys) if (y != null) all.push(y);
      const k = fieldsSeen.get(c) || 0; fieldsSeen.set(c, k + 1);
      const label = trackLabel(c) + (spec.fields.length > 1 ? " · " + f.label : ""), line = spec.group === "strategy", color = rgb(c.color);
      series.push({ label, stroke:color, width:line ? 1.3 : 0, dash:line && k ? [5, 4] : undefined, paths:line ? uPlot.paths.linear() : () => null, spanGaps:true,
                    points:{ show:true, size:line ? 3 : 4, width:1, stroke:color, fill:k ? "#0a0a0a" : color } });
      full.push(ys); labels.push(label);
      legendItems.push(`<span class="item${(hiddenSeries[spec.id] || new Set()).has(label) ? " off" : ""}" data-label="${escapeHtml(label)}" title="click to hide or show, shift click to show only this one">${swatch(c.color, line ? "line" : "dot")} ${escapeHtml(label)}</span>`);
    }
  });
  let low = Infinity, high = -Infinity; for (const y of all) { if (y < low) low = y; if (y > high) high = y; }
  if (!all.length) { low = 0; high = 1; }

  const el = document.createElement("div"); el.className = "chart";
  el.innerHTML = `<div class="chart-head"><b>${escapeHtml(spec.fields.map(f => f.label).join(", "))}</b><span class="close" title="remove this chart">×</span></div>` +
    `<div class="legend">${legendItems.join("") || `<span class="item dim">${S.compare.some(c => (c.kind === "raw") === (spec.group === "raw")) ? "the compared tracks do not carry this field" : `compare a ${spec.group === "raw" ? "source" : "strategy"} track to fill this chart`}</span>`}</div>`;
  const holder = document.createElement("div"), grip = document.createElement("div"); grip.className = "hgrip"; grip.title = "drag to change the height";
  el.append(holder, grip); box.appendChild(el);
  el.querySelector(".close").onclick = () => { S.charts = S.charts.filter(s => s !== spec); rebuildCharts(); };

  const axis = { stroke:"#888888", grid:{ stroke:"#1e1e1e", width:1, dash:[2, 4] }, ticks:{ stroke:"#333333", width:1, size:4 }, font:'10px "Simplon ASI Mono", "SF Mono", SFMono-Regular, Menlo, monospace' };
  const pad = (high - low) * 0.08 + (high === low ? 1 : 0);
  let chart = null;   // filled in once uPlot is built; its hooks can fire during construction
  const u = new uPlot({
    width:chartWidth(), height:spec.height || 220, legend:{ show:false },
    cursor:{ drag:{ x:true, y:false }, focus:{ prox:16 }, points:{ show:false }, bind:{ dblclick:() => null } },
    scales:{ x:{ time:false, range:(u, min, max) => u.scales.x.min == null ? [0, S.CASE.span_ms / 1000] : [min, max] }, y:{ range:() => [low - pad, high + pad] } },
    axes:[{ ...axis, space:90, values:(u, vals) => vals.map(v => fmt(v * 1000).slice(0, 5)) }, { ...axis, size:56 }],
    series,
    hooks:{
      // uPlot fires setScale once more after it is built; only a zoom made by the user counts
      setScale:[(u, key) => { if (key === "x" && u._byUser && !syncing) { u._byUser = false; onZoom(u.scales.x.min, u.scales.x.max); } }],
      setCursor:[u => chartCursor(u, chart)],
      draw:[u => drawMarks(u, chart)],
    },
  }, [xs, ...full.map(() => xs.map(() => null))], holder);
  chart = { spec, u, full, points, xs, labels, values };

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
  u.over.addEventListener("dblclick", () => resetZoom(), true);
  u.over.addEventListener("mouseleave", () => setHover(null));
  grip.onmousedown = e => {
    e.preventDefault(); const startY = e.clientY, startH = u.height;
    const move = ev => { spec.height = Math.max(80, Math.min(900, startH + ev.clientY - startY)); u.setSize({ width:u.width, height:spec.height }); };
    const up = () => { document.removeEventListener("mousemove", move); document.removeEventListener("mouseup", up); };
    document.addEventListener("mousemove", move); document.addEventListener("mouseup", up);
  };
  return chart;
}
const chartWidth = () => $("rawCharts").clientWidth - 30;
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
    const [min, max] = S.win ? [S.win[0] / 1000, S.win[1] / 1000] : [0, S.CASE.span_ms / 1000];
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
function drawMarks(u, chart) {
  const ctx = u.ctx; ctx.save();
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

export async function openFieldBrowser(group, button) {
  browsing = group; picked = new Map();
  $("fbTitle").textContent = group === "raw" ? "raw plot fields" : "strategy fields";
  $("fbSearch").value = ""; $("fbPicked").textContent = "pick one or more fields";
  if (group === "raw") for (const id of S.runActive) if (!id.startsWith("prod_fusion")) await loadOutcomes(id);
  renderFieldList();
  const r = button.getBoundingClientRect(), el = $("fieldBrowser");
  el.classList.add("open");
  el.style.left = Math.max(8, r.right - el.offsetWidth) + "px"; el.style.top = Math.min(r.bottom + 4, window.innerHeight - el.offsetHeight - 8) + "px";
  $("fbSearch").focus();
}
export function closeFieldBrowser() { $("fieldBrowser").classList.remove("open"); browsing = null; }

function groups() {
  if (browsing === "raw") {
    const out = Object.entries(S.RAW.schema).map(([src, fields]) => ({ title:SOURCE_NAME[src], color:SOURCE_COLOR[src], fields:fields.map(f => ({ ...f, source:src, label:`${src}.${f.name}` })) }));
    for (const id of S.runActive) { const o = S.OUTCOMES[id]; if (o && Object.keys(o.numbers || {}).length) out.push({ title:`recorded per raw plot by ${runName(id)}`, fields:Object.keys(o.numbers).map(name => ({ name, kind:"number", count:o.numbers[name].filter(v => v != null).length, run:id, label:`${runName(id)} ${name}` })) }); }
    return out;
  }
  // the fields of every drawn strategy run, each field once
  const fused = new Map(), state = new Map();
  for (const id of S.runShown) for (const f of (S.RUNS[id] || {}).schema || []) {
    const target = f.table === "track_state" ? state : fused, seen = target.get(f.name);
    target.set(f.name, { name:f.name, kind:f.kind, count:(seen ? seen.count : 0) + f.count, runs:[...(seen ? seen.runs : []), runName(id)], column:f.name, label:f.name });
  }
  return [{ title:"fused plot fields", fields:[...fused.values()] }, { title:"recorded about the track by the strategy", fields:[...state.values()] }].filter(g => g.fields.length);
}

function renderFieldList() {
  const query = $("fbSearch").value.trim().toLowerCase(), list = $("fbList");
  const all = groups();
  if (!all.length) { list.innerHTML = `<div class="empty" style="padding:0.7rem">${browsing === "raw" ? "This case has no raw plots." : "Tick a strategy run under Strategies first; its fields show here."}</div>`; return; }
  list.innerHTML = all.map((g, gi) => {
    const fields = g.fields.filter(f => !query || f.name.toLowerCase().includes(query)).sort((a, b) => a.name.localeCompare(b.name));
    if (!fields.length) return "";
    return `<div class="fb-group">${g.color ? swatch(g.color) : ""}${escapeHtml(g.title)}</div>` + fields.map((f, fi) => {
      const usable = f.kind === "number" && f.count > 0, key = `${gi}|${f.name}`;
      return `<label class="${usable ? "" : "off"}" title="${usable ? "" : f.kind === "text" ? "text, cannot be charted" : "never set in this case"}${f.runs ? " · in " + escapeHtml(f.runs.join(", ")) : ""}"><input type="checkbox" data-key="${escapeHtml(key)}" ${usable ? "" : "disabled"} ${picked.has(key) ? "checked" : ""}><span class="name">${escapeHtml(f.name)}</span><span class="kind">${f.kind === "number" ? fmtN(f.count) : f.kind}</span></label>`;
    }).join("");
  }).join("") || `<div class="empty" style="padding:0.7rem">No field matches.</div>`;
  list.querySelectorAll("input[data-key]").forEach(cb => cb.onchange = () => {
    const [gi, name] = cb.dataset.key.split("|"), f = all[+gi].fields.find(x => x.name === name);
    cb.checked ? picked.set(cb.dataset.key, f) : picked.delete(cb.dataset.key);
    $("fbPicked").textContent = picked.size ? [...picked.values()].map(p => p.label).join(", ") : "pick one or more fields";
  });
}

export function wireFieldBrowser() {
  $("fbSearch").oninput = renderFieldList;
  $("fbCancel").onclick = closeFieldBrowser;
  $("fbAdd").onclick = () => {
    if (!picked.size) return;
    S.charts.push({ id:nextId++, group:browsing, fields:[...picked.values()].map(f => browsing === "raw" ? (f.run ? { run:f.run, column:f.name, label:f.label } : { source:f.source, column:f.name, label:f.label }) : { column:f.name, label:f.label }) });
    closeFieldBrowser(); rebuildCharts();
  };
  document.addEventListener("mousedown", e => { if (browsing && !e.target.closest("#fieldBrowser, #addRawChart, #addStrategyChart")) closeFieldBrowser(); });
}
