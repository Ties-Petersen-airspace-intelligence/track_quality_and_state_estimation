// Raw plot filters: every filter starts switched off and greyed; switched on filters combine with AND, or with OR.
// The result is one pass or fail per raw plot in S.rawPass, worked out when a filter changes, not on every frame.
import { S, $, SOURCE_NAME, runName, fmtN, escapeHtml } from "./state.js";
import { asiSelects, rangeSlider, setOptions } from "./controls.js";
import { loadOutcomes } from "./runs.js";
import { bus } from "./bus.js";
import { STATE_COLOR, OTHER, swatch } from "./palette.js";

const R = () => S.RAW;
// numeric fields: a range, or whether the field is set at all, or is 0
const NUMERIC = [
  { id:"alt", name:"altitude", unit:"ft", value:i => R().alt[i], step:100 },
  { id:"nacp", name:"NACp", unit:"", value:i => R().nacp[i], step:1 },
  { id:"nic", name:"NIC", unit:"", value:i => R().nic[i], step:1 },
  { id:"late", name:"lateness", unit:"s", note:"Received minus position time. ", value:i => (R().r[i] - R().t[i]) / 1000, step:0.1 },
  { id:"gs", name:"ground speed", unit:"kt", value:i => R().gs[i], step:1 },
];
const TEXT = [
  { id:"hex", name:"hex", value:i => R().hex[i] },
  { id:"cs", name:"callsign", value:i => R().cs[i] },
  { id:"tail", name:"tail", value:i => R().tail[i] },
];
const state = {};       // filter id -> its settings, including on
const summaries = {};   // filter id -> the few words its header shows while it is on

export function buildFilters() {
  const box = $("filters");
  box.innerHTML = "";
  box.append(sourceFilter());
  for (const f of NUMERIC) box.append(numericFilter(f));
  box.append(groundFilter());
  for (const f of TEXT) box.append(textFilter(f));
  box.append(outcomeFilter());
  asiSelects(box);
  document.querySelectorAll('input[name="fail"], input[name="combine"]').forEach(r => r.onchange = changed);
  computePass();
}

// a filter block, folded until it is switched on: ticking opens it, unticking folds it, the arrow or the name
// folds and unfolds it; a switched on filter says in its header what it keeps
function block(id, name, body, summary) {
  const el = document.createElement("div"); el.className = "filter"; el.dataset.id = id;
  el.innerHTML = `<div class="fhead"><input type="checkbox" title="switch this filter on or off"><span class="name">${name}</span><span class="summary"></span><span class="arrow" title="fold or unfold"></span></div><div class="fbody"></div>`;
  el.querySelector(".fbody").append(...[].concat(body));
  summaries[id] = summary;
  const cb = el.querySelector(".fhead input");
  cb.onchange = () => { state[id].on = cb.checked; el.classList.toggle("on", cb.checked); fold(el, cb.checked); changed(); };
  for (const part of el.querySelectorAll(".arrow, .name")) part.onclick = () => fold(el, !el.classList.contains("open"));
  return el;
}
function fold(el, open) { el.classList.toggle("open", open); }
const units = (v, unit) => fmtN(v) + (unit ? " " + unit : "");
function renderSummaries() {
  for (const el of document.querySelectorAll("#filters .filter")) {
    const id = el.dataset.id;
    el.querySelector(".summary").textContent = state[id].on ? "· " + summaries[id]() : "";
  }
}
const html = text => { const t = document.createElement("template"); t.innerHTML = text.trim(); return [...t.content.childNodes]; };

function sourceFilter() {
  // one tick per source, and under a source with several kinds of plot one tick per kind
  const counts = new Map(), kinds = new Map();
  for (let i = 0; i < R().n; i++) {
    const src = R().src[i], kind = R().kind[i];
    counts.set(src, (counts.get(src) || 0) + 1);
    if (kind) { const k = src + "|" + kind; kinds.set(k, (kinds.get(k) || 0) + 1); }
  }
  state.source = { on:false, off:new Set() };   // ticked off: "src" or "src|kind"
  let body = `<div class="opts">`;
  for (const [src, n] of counts) {
    body += `<label><input type="checkbox" data-key="${src}" checked> ${SOURCE_NAME[src]} <span class="n">${fmtN(n)}</span></label>`;
    for (const [k, m] of [...kinds].filter(([k]) => k.startsWith(src + "|")).sort((a, b) => b[1] - a[1])) body += `<label class="sub"><input type="checkbox" data-key="${escapeHtml(k)}" checked> ${escapeHtml(k.split("|")[1])} <span class="n">${fmtN(m)}</span></label>`;
  }
  const el = block("source", "source and plot kind", html(body + "</div>"), () => state.source.off.size ? `${state.source.off.size} ticked off` : "all ticked");
  el.querySelectorAll(".opts input").forEach(cb => cb.onchange = () => { cb.checked ? state.source.off.delete(cb.dataset.key) : state.source.off.add(cb.dataset.key); changed(); });
  return el;
}

function numericFilter(f) {
  const values = []; for (let i = 0; i < R().n; i++) { const v = f.value(i); if (v != null) values.push(v); }
  let min = Infinity, max = -Infinity; for (const v of values) { if (v < min) min = v; if (v > max) max = v; }
  if (!values.length) { min = 0; max = 0; }
  min = Math.floor(min / f.step) * f.step; max = Math.ceil(max / f.step) * f.step;
  state[f.id] = { on:false, mode:"range", low:min, high:max };
  const nodes = html(`<div class="field"><span class="label">keep plots that</span><select><option value="range">fall in the range</option><option value="set">have it set</option><option value="unset">do not have it set</option><option value="zero">have it 0</option></select></div><div class="field range-row"></div><div class="note">${f.note || ""}${fmtN(values.length)} of ${fmtN(R().n)} plots carry it${f.unit ? `, in ${f.unit}` : ""}.</div>`);
  const el = block(f.id, f.name, nodes, () => { const st = state[f.id]; return st.mode === "set" ? "set" : st.mode === "unset" ? "not set" : st.mode === "zero" ? "is 0" : `${units(st.low, "")} – ${units(st.high, f.unit)}`; });
  const sel = el.querySelector("select"), row = el.querySelector(".range-row");
  rangeSlider(row, { min, max, step:f.step, low:min, high:max, onChange:([low, high]) => { state[f.id].low = low; state[f.id].high = high; changed(); } });
  sel.onchange = () => { state[f.id].mode = sel.value; row.style.display = sel.value === "range" ? "" : "none"; changed(); };
  return el;
}

function groundFilter() {
  state.ground = { on:false, mode:"air" };
  const el = block("ground", "on the ground", html(`<div class="field"><span class="label">keep plots</span><select><option value="air">in the air</option><option value="ground">on the ground</option></select></div><div class="note">As the source says it: ADS-B Exchange writes "ground" as its altitude, uAvionix sets the ground bit. Other sources never say, so their plots count as in the air.</div>`), () => state.ground.mode === "air" ? "in the air" : "on the ground");
  el.querySelector("select").onchange = e => { state.ground.mode = e.target.value; changed(); };
  return el;
}

function textFilter(f) {
  state[f.id] = { on:false, mode:"set" };
  const el = block(f.id, f.name, html(`<div class="field"><span class="label">keep plots that</span><select><option value="set">have it set</option><option value="unset">do not have it set</option></select></div>`), () => state[f.id].mode === "set" ? "set" : "not set");
  el.querySelector("select").onchange = e => { state[f.id].mode = e.target.value; changed(); };
  return el;
}

function outcomeFilter() {
  state.outcome = { on:false, run:"", statesOff:new Set(), reasonsOff:new Set() };
  const el = block("outcome", "what a strategy did with it", html(`<div class="field"><span class="label">strategy run</span><select class="outcome-run"></select></div><div class="opts outcome-states" style="margin-top:0.35rem"></div><div class="opts outcome-reasons" style="margin-top:0.35rem"></div>`), () => { const o = state.outcome; if (!o.run) return "pick a run"; const off = o.statesOff.size + o.reasonsOff.size; return runName(o.run) + (off ? `, ${off} ticked off` : ""); });
  el.querySelector(".outcome-run").onchange = async e => { state.outcome.run = e.target.value; state.outcome.statesOff.clear(); state.outcome.reasonsOff.clear(); if (e.target.value) await loadOutcomes(e.target.value); renderOutcomeOptions(); changed(); };
  return el;
}
// the run menu lists the active runs; called when the active runs change
export function syncOutcomeRuns() {
  const sel = document.querySelector("#filters .outcome-run"); if (!sel) return;
  const keep = state.outcome.run;
  setOptions(sel, [["", "pick a run"], ...[...S.runActive].map(id => [id, runName(id)])], keep);
  if (keep && !S.runActive.has(keep)) { state.outcome.run = ""; renderOutcomeOptions(); changed(); }
}
function renderOutcomeOptions() {
  const el = document.querySelector('.filter[data-id="outcome"]'), o = S.OUTCOMES[state.outcome.run];
  const statesBox = el.querySelector(".outcome-states"), reasonsBox = el.querySelector(".outcome-reasons");
  if (!o) { statesBox.innerHTML = reasonsBox.innerHTML = ""; return; }
  const states = {}, reasons = {};
  for (let i = 0; i < R().n; i++) { states[o.state[i]] = (states[o.state[i]] || 0) + 1; if (o.reason[i]) { const k = o.state[i] + ": " + o.reason[i]; reasons[k] = (reasons[k] || 0) + 1; } }
  statesBox.innerHTML = Object.entries(states).map(([st, n]) => `<label><input type="checkbox" data-state="${st}" ${state.outcome.statesOff.has(st) ? "" : "checked"}>${swatch(STATE_COLOR[st] || OTHER)} ${st} <span class="n">${fmtN(n)}</span></label>`).join("");
  reasonsBox.innerHTML = Object.entries(reasons).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<label class="sub"><input type="checkbox" data-reason="${escapeHtml(k)}" ${state.outcome.reasonsOff.has(k) ? "" : "checked"}> ${escapeHtml(k)} <span class="n">${fmtN(n)}</span></label>`).join("");
  statesBox.querySelectorAll("input").forEach(cb => cb.onchange = () => { cb.checked ? state.outcome.statesOff.delete(cb.dataset.state) : state.outcome.statesOff.add(cb.dataset.state); changed(); });
  reasonsBox.querySelectorAll("input").forEach(cb => cb.onchange = () => { cb.checked ? state.outcome.reasonsOff.delete(cb.dataset.reason) : state.outcome.reasonsOff.add(cb.dataset.reason); changed(); });
}

// ---------- the pass or fail per raw plot ----------

function predicates() {
  const out = [], raw = R();
  if (state.source.on) { const off = state.source.off; out.push(i => !off.has(raw.src[i]) && !(raw.kind[i] && off.has(raw.src[i] + "|" + raw.kind[i]))); }
  for (const f of NUMERIC) {
    const s = state[f.id]; if (!s.on) continue;
    if (s.mode === "set") out.push(i => f.value(i) != null);
    else if (s.mode === "unset") out.push(i => f.value(i) == null);
    else if (s.mode === "zero") out.push(i => f.value(i) === 0);
    else out.push(i => { const v = f.value(i); return v != null && v >= s.low && v <= s.high; });
  }
  if (state.ground.on) out.push(state.ground.mode === "ground" ? i => raw.ground[i] === 1 : i => raw.ground[i] !== 1);
  for (const f of TEXT) { const s = state[f.id]; if (s.on) out.push(s.mode === "set" ? i => !!f.value(i) : i => !f.value(i)); }
  const o = state.outcome.on && S.OUTCOMES[state.outcome.run];
  if (o) out.push(i => !state.outcome.statesOff.has(o.state[i]) && !(o.reason[i] && state.outcome.reasonsOff.has(o.state[i] + ": " + o.reason[i])));
  return out;
}

export function computePass() {
  const tests = predicates(), all = document.querySelector('input[name="combine"]:checked').value === "and", n = R().n;
  const pass = new Uint8Array(n);
  let failed = 0;
  for (let i = 0; i < n; i++) {
    const ok = !tests.length || (all ? tests.every(t => t(i)) : tests.some(t => t(i)));
    pass[i] = ok ? 1 : 0; if (!ok) failed++;
  }
  S.rawPass = pass;
  const hide = hideFailed();
  $("filterCount").textContent = tests.length ? `${tests.length} on · ${fmtN(failed)} ${hide ? "hidden" : "shown grey"}` : "";
  $("dbgFiltered").textContent = fmtN(failed);
}
export const hideFailed = () => document.querySelector('input[name="fail"]:checked').value === "hide";

function changed() { renderSummaries(); computePass(); bus.draw(); }
