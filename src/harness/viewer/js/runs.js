// Strategy runs: loading them, the list under Strategies, and the panel with every run of the case.
import { S, $, api, runById, runName, strategyOf, fmtN, escapeHtml } from "./state.js";
import { bus } from "./bus.js";
import { runColour, swatch } from "./palette.js";

const pending = {};   // "run|id" or "outcomes|id" -> the request still on its way
function once(key, request) {
  pending[key] ||= request().finally(() => { delete pending[key]; });
  return pending[key];
}
async function answer(what, id) {
  const data = await api(what, { run:id });
  if (data.error) throw new Error(data.error);
  return data;
}
export async function loadRun(id) {
  if (S.RUNS[id]) return S.RUNS[id];
  $("status").textContent = `loading ${runName(id)}…`;
  return once("run|" + id, async () => {
    const run = await answer("run", id);
    run.n = run.t.length;
    S.RUNS[id] = run;
    $("status").textContent = fmtN(S.RAW.n);
    return run;
  });
}
export async function loadOutcomes(id) {
  if (S.OUTCOMES[id]) return S.OUTCOMES[id];
  return once("outcomes|" + id, async () => (S.OUTCOMES[id] = await answer("outcomes", id)));
}

// the newest run of every strategy, and production, are listed when a case opens; none is drawn yet
export function defaultActive() {
  const newest = {};
  for (const r of S.CASE.runs) newest[strategyOf(r.id)] = r.id;   // list_runs gives labels in order
  S.runActive = new Set(Object.values(newest));
}

export function setActive(id, on) {
  if (on) S.runActive.add(id);
  else { S.runActive.delete(id); S.runShown.delete(id); }   // its compared tracks stay in the list; only × removes one
  bus.renderStrategies(); bus.renderCompare(); renderRunsPanel(); bus.rebuildCharts(); bus.draw();
}
export async function setShown(id, on) {
  if (on) {
    S.runShown.add(id);
    try { await loadRun(id); } catch (error) { S.runShown.delete(id); $("status").textContent = `${runName(id)} did not load: ${error.message}`; }
  } else S.runShown.delete(id);   // its compared tracks stay in the list; only × removes one
  bus.renderStrategies(); bus.renderCompare(); renderRunsPanel(); bus.rebuildCharts(); bus.draw();
}

// ---------- the list under Strategies ----------
export function renderRunList() {
  const ids = S.CASE.runs.map(r => r.id).filter(id => S.runActive.has(id));
  $("runList").innerHTML = ids.length ? ids.map(id => {
    const run = S.RUNS[id], count = run ? `${fmtN(run.n)} plots` : (runById(id).counts ? `${fmtN(runById(id).counts.fused_plots)} plots` : "");
    return `<label><input type="checkbox" data-id="${id}" ${S.runShown.has(id) ? "checked" : ""}>${S.runShown.has(id) ? swatch(runColour(id), "line") : `<span class="sw line" style="background:var(--line-strong)"></span>`}${escapeHtml(runName(id))}<span class="n">${count}</span></label>`;
  }).join("") : `<div class="empty">No run is active. Open "all runs…" and tick one.</div>`;
  $("runList").querySelectorAll("input").forEach(cb => cb.onchange = () => setShown(cb.dataset.id, cb.checked));
}

// ---------- the panel with every run ----------
let sort = { key:"created", asc:true }, openRow = null, diff = [];
const COLUMNS = [
  { key:"on", title:"active", val:r => S.runActive.has(r.id) ? 1 : 0, cell:r => `<input type="checkbox" class="rp-on" data-id="${r.id}" ${S.runActive.has(r.id) ? "checked" : ""}>` },
  { key:"diff", title:"diff", cell:r => r.production ? "" : `<input type="checkbox" class="rp-diff" data-id="${r.id}" ${diff.includes(r.id) ? "checked" : ""}>` },
  { key:"strategy", title:"strategy", val:r => strategyOf(r.id), cell:r => strategyOf(r.id).replace(/_/g, " ") },
  { key:"label", title:"label", cls:"lab", cell:r => r.label || "" },
  { key:"created", title:"when", cls:"dim", cell:r => r.created ? r.created.slice(5, 16).replace("T", " ") : "" },
  { key:"batch", title:"batch", cls:"dim", cell:r => r.batch ? r.batch.slice(4, 8) + " " + r.batch.slice(9, 13) : "" },
  { key:"commit", title:"commit", cls:"dim", val:r => (r.git || {}).commit || "", cell:r => r.git && r.git.commit ? r.git.commit.slice(0, 7) + (r.git.dirty ? `<span class="dirty" title="the working tree had uncommitted changes">*</span>` : "") : "" },
  { key:"fused", title:"plots", cls:"num", val:r => (r.counts || {}).fused_plots, cell:r => fmtN((r.counts || {}).fused_plots) },
  { key:"tracks", title:"tracks", cls:"num", val:r => (r.counts || {}).tracks, cell:r => fmtN((r.counts || {}).tracks) },
  { key:"rewritten", title:"rewritten", cls:"num", val:r => (r.counts || {}).rewritten, cell:r => fmtN((r.counts || {}).rewritten) },
  { key:"duration", title:"took", cls:"num dim", val:r => r.duration_s, cell:r => r.duration_s == null ? "" : r.duration_s + " s" },
  { key:"note", title:"note", cls:"note", cell:r => escapeHtml(r.note || "") },
];

export function openRunsPanel(open) { $("runsPanel").classList.toggle("open", open); if (open) renderRunsPanel(); }

export function renderRunsPanel() {
  if (!$("runsPanel").classList.contains("open")) return;
  const col = COLUMNS.find(c => c.key === sort.key), val = r => col.val ? col.val(r) : r[col.key];
  const rows = [...S.CASE.runs].sort((a, b) => { const x = val(a), y = val(b); const c = x == null ? 1 : y == null ? -1 : (typeof x === "number" ? x - y : String(x).localeCompare(String(y))); return sort.asc ? c : -c; });
  $("runsCount").textContent = `${S.CASE.runs.length} runs`;
  let body = "<thead><tr>" + COLUMNS.map(c => `<th data-key="${c.key}" class="${c.key === sort.key ? "sorted" + (sort.asc ? " asc" : "") : ""}">${c.title}</th>`).join("") + "</tr></thead><tbody>";
  for (const r of rows) {
    // a production entry has no run.json, so its note is fixed
    const editable = c => c.key === "note" && !r.production;
    body += `<tr class="run" data-id="${r.id}">` + COLUMNS.map(c => `<td class="${c.cls || ""} ${editable(c) && !r.note ? "empty" : ""}" ${editable(c) ? `contenteditable="plaintext-only" data-id="${r.id}"` : ""}>${c.cell(r)}</td>`).join("") + "</tr>";
    if (openRow === r.id) body += `<tr class="detail"><td colspan="${COLUMNS.length}">${detail(r)}</td></tr>`;
  }
  $("runsTable").innerHTML = body + "</tbody>";
  $("runsTable").querySelectorAll("th").forEach(th => th.onclick = () => { const k = th.dataset.key; sort = sort.key === k ? { key:k, asc:!sort.asc } : { key:k, asc:true }; renderRunsPanel(); });
  $("runsTable").querySelectorAll("tr.run").forEach(tr => tr.onclick = e => { if (e.target.closest("input, td[contenteditable]")) return; openRow = openRow === tr.dataset.id ? null : tr.dataset.id; renderRunsPanel(); });
  $("runsTable").querySelectorAll(".rp-on").forEach(cb => cb.onchange = () => setActive(cb.dataset.id, cb.checked));
  $("runsTable").querySelectorAll(".rp-diff").forEach(cb => cb.onchange = () => { diff = cb.checked ? [...diff.filter(x => x !== cb.dataset.id), cb.dataset.id].slice(-2) : diff.filter(x => x !== cb.dataset.id); renderRunsPanel(); });
  $("runsTable").querySelectorAll("td[contenteditable]").forEach(td => {
    td.onkeydown = e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); td.blur(); } if (e.key === "Escape") { td.textContent = runById(td.dataset.id).note || ""; td.blur(); } };
    td.onblur = () => saveNote(td.dataset.id, td.textContent.trim());
    td.onfocus = () => td.classList.remove("empty");
  });
  renderDiff();
}

async function saveNote(id, note) {
  const r = runById(id);
  if ((r.note || "") === note) { renderRunsPanel(); return; }
  const res = await fetch(`/api/note?` + new URLSearchParams({ case:S.CASE.name, run:id }), { method:"POST", headers:{ "Content-Type":"application/json" }, body:JSON.stringify({ note }) });
  if (res.ok) r.note = note;
  renderRunsPanel();
}

// the manifest laid out for reading: run, code, what came out, then the strategy's parameters
function detail(r) {
  const g = r.git || {}, c = r.counts || {}, params = Object.entries(r.params || {});
  const row = (k, v) => v == null || v === "" ? "" : `<span class="k">${k}</span><span class="v">${escapeHtml(String(v))}</span>`;
  const head = t => `<span class="h">${t}</span>`;
  if (r.production) return `<div class="det">${head("production")}${row("what", r.note)}${row("replayed as", "created_at and valid_to as the table holds them; raw plots used where a fused plot of the same source has the same position time and the same source track id (append) or hex (final)")}</div>`;
  const outcomes = Object.entries(c.outcomes || {}).map(([k, v]) => `${k} ${fmtN(v)}`).join(", ");
  const reasons = Object.entries(c.reasons || {}).map(([k, v]) => `${k} ${fmtN(v)}`).join(", ");
  return `<div class="det">` +
    head("run") + row("run", `${r.strategy} ${r.label}`) + row("when", (r.created || "").replace("T", " ").replace("+00:00", " UTC")) + row("took", r.duration_s == null ? "" : r.duration_s + " s") + row("batch", r.batch) + row("command", r.command) + row("note", r.note) +
    head("code") + row("commit", g.commit) + row("branch", g.branch) + row("uncommitted changes", g.dirty == null ? "" : g.dirty ? "yes, the working tree was dirty" : "no") +
    head("what came out") + row("raw plots fed in", fmtN(c.raw_plots)) + row("events emitted", fmtN(c.events)) + row("fused plots", fmtN(c.fused_plots)) + row("tracks", fmtN(c.tracks)) + row("plots later rewritten", fmtN(c.rewritten)) + row("raw plots", outcomes) + row("reasons", reasons) +
    head("parameters") + (params.length ? params.map(([k, v]) => row(k, typeof v === "object" ? JSON.stringify(v) : v)).join("") : row("none", "this strategy declares no parameters")) +
    `</div>`;
}

// every manifest field as key -> value, nested ones flattened with a dot, for the diff
function flat(r) { const out = {}; const walk = (o, pre) => { for (const [k, v] of Object.entries(o)) { if (k === "id") continue; if (v && typeof v === "object" && !Array.isArray(v)) walk(v, pre + k + "."); else out[pre + k] = v; } }; walk(r, ""); return out; }
function renderDiff() {
  const el = $("runsDiff");
  if (diff.length < 2) { el.innerHTML = diff.length === 1 ? `<div class="help">tick one more run to compare</div>` : ""; return; }
  const [a, b] = diff.map(runById), fa = flat(a), fb = flat(b), keys = [...new Set([...Object.keys(fa), ...Object.keys(fb)])];
  el.innerHTML = `<table><thead><tr><th>field</th><th>${runName(a.id)}</th><th>${runName(b.id)}</th></tr></thead><tbody>` + keys.map(k => { const same = String(fa[k] ?? "") === String(fb[k] ?? ""); return `<tr class="${same ? "same" : ""}"><td class="dim">${k}</td><td class="${same ? "" : "changed"}">${escapeHtml(String(fa[k] ?? ""))}</td><td class="${same ? "" : "changed"}">${escapeHtml(String(fb[k] ?? ""))}</td></tr>`; }).join("") + "</tbody></table>";
}
