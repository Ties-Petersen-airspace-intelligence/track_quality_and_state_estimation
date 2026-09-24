// The page: load the case, build the panels, wire every control to a redraw.
import { S, $, api, apiProgress, fmtN, escapeHtml, sliderMetres } from "./state.js";
import { bus } from "./bus.js";
import { asiSelects, setOptions, grips, closeSelects } from "./controls.js";
import { rawColourOptions, rawColourLegend, strategyLegend, legend } from "./palette.js";
import { buildFilters, syncOutcomeRuns } from "./filters.js";
import { defaultActive, renderRunList, openRunsPanel, loadOutcomes } from "./runs.js";
import { renderCompare, findTracks, clearCompare } from "./compare.js";
import { initMap, draw, resizeMap, closePick } from "./mapview.js";
import { rebuildCharts, redrawCharts, repaintCharts, resizeCharts, openFieldBrowser, closeFieldBrowser, wireFieldBrowser, loadRawSchema } from "./charts.js";
import { initTimeline, paintTimeline } from "./timeline.js";

bus.draw = () => { paintTimeline(); draw(); redrawCharts(); };
bus.rebuildCharts = rebuildCharts;
bus.redrawCharts = redrawCharts;
bus.repaintCharts = repaintCharts;
bus.renderCompare = renderCompare;
bus.renderStrategies = renderStrategies;

// the Controls cheat sheet is open for a new visitor; once closed it stays closed
function rememberControls() {
  const box = $("controlsRef");
  try { box.open = localStorage.getItem("controlsOpen") !== "0"; } catch (err) { }
  box.ontoggle = () => { try { localStorage.setItem("controlsOpen", box.open ? "1" : "0"); } catch (err) { } };
}

async function init() {
  rememberControls();
  // the case: from the address, else the first case with raw plots; the address holds nothing else
  const cases = (await api("cases")).cases, wanted = new URLSearchParams(location.search).get("case");
  const name = cases.some(c => c.name === wanted && c.complete) ? wanted : (cases.find(c => c.complete) || {}).name;
  $("caseSel").innerHTML = cases.map(c => `<option value="${c.name}" ${c.name === name ? "selected" : ""} ${c.complete ? "" : "disabled"}>${c.name}${c.complete ? "" : " (no raw plots)"}</option>`).join("");
  $("caseSel").onchange = () => { location.search = "?case=" + encodeURIComponent($("caseSel").value); };
  $("resetView").onclick = () => { location.search = "?case=" + encodeURIComponent(S.CASE.name); };
  if (!name) { $("splashWhat").textContent = "no case with raw plots in the cases folder"; return; }
  history.replaceState(null, "", "?case=" + encodeURIComponent(name));
  S.CASE = { name };
  S.CASE = { ...(await api("case")), name };
  caseHeader();

  // the raw plots, then everything that depends on them
  // the server first reads every source file, then sends the plots; the dashes fill as they arrive
  $("splashWhat").textContent = "the server is reading the raw plots";
  const mb = bytes => (bytes / 1e6).toFixed(bytes < 1e7 ? 1 : 0) + " MB";
  S.RAW = await apiProgress("raw", {}, (got, total) => {
    const share = total ? Math.min(1, got / total) : 0;
    $("splashFill").style.width = (share * 100) + "%";
    $("splashWhat").textContent = total ? `loading raw plots · ${Math.floor(share * 100)}% of ${mb(total)}` : `loading raw plots · ${mb(got)}`;
    if (got >= total && total) $("splashWhat").textContent = `reading ${mb(total)} of raw plots`;
  });
  S.RAW.n = S.RAW.t.length;
  $("status").textContent = fmtN(S.RAW.n);
  $("splashWhat").textContent = `${fmtN(S.RAW.n)} raw plots · drawing`;
  defaultActive();
  S.now = Math.min(S.CASE.span_ms, 12 * 60000);
  initTimeline();
  buildFilters();
  renderStrategies();
  renderCompare();
  asiSelects();
  wire();
  grips(() => { resizeMap(); resizeCharts(); });
  const done = () => { const el = $("splash"); if (!el) return; el.classList.add("gone"); setTimeout(() => el.remove(), 400); };
  initMap(done); setTimeout(done, 4000);
  await rebuildCharts();
  bus.draw();
  loadRawSchema();
}

function caseHeader() {
  const c = S.CASE.case, box = c.box, suspect = c.suspect || {};
  $("topDay").textContent = new Date(c.t_start.slice(0, 10) + "T00:00:00Z").toUTCString().slice(5, 16).toUpperCase();
  $("topWindow").textContent = `${c.t_start.slice(11, 16)} – ${c.t_end.slice(11, 16)}`;
  // the case as the panel's title, like a Flyways flight header: the suspect aircraft, then the case and its window
  $("caseTitle").textContent = [suspect.callsign, suspect.hex].filter(Boolean).join(" / ") || S.CASE.name;
  $("caseSub").textContent = `${S.CASE.name} · ${c.t_start.slice(11, 16)} – ${c.t_end.slice(11, 16)} Z`;
  $("caseKv").innerHTML = [["day", c.day], ["window", `${c.t_start.slice(11, 16)} – ${c.t_end.slice(11, 16)} Z`], ["box lat", `${box.lat_min} … ${box.lat_max}`], ["box lon", `${box.lon_min} … ${box.lon_max}`], ["found by", (c.found_by || "").split(",")[0].replace("case finder rule ", "") || "–"]]
    .map(([k, v]) => `<div class="kvrow"><span class="k">${k}</span><span class="v">${escapeHtml(v)}</span></div>`).join("");
}

// the parts that follow the active and shown runs: the run list, the colour menus, the legends
function renderStrategies() {
  renderRunList();
  setOptions($("rawColour"), rawColourOptions(), $("rawColour").value || "source");
  syncOutcomeRuns();
  legends();
}

function legends() {
  const mode = $("rawColour").value;
  if (mode.startsWith("outcome:") && !S.OUTCOMES[mode.slice(8)]) loadOutcomes(mode.slice(8)).then(() => { legends(); bus.draw(); });
  $("rawColourLegend").innerHTML = rawColourLegend(mode);
  const size = $("rawSize").value, label = { nacp:"NACp", nic:"NIC" }[size];
  // pixels in the fixed mode; in the NACp and NIC modes every plot has a size in metres, the ones without the number too
  $("rawPxRow").style.display = size === "fixed" ? "" : "none"; $("rawMetresRow").style.display = size === "fixed" ? "none" : "";
  $("rawMetresLabel").textContent = `size without ${label || "NACp"}`;
  $("rawPxValue").textContent = $("rawPx").value + " px"; $("rawMetresValue").textContent = sliderMetres("rawMetres") + " m";
  $("rawSizeLegend").innerHTML = size === "fixed" ? "" : legend([{ shape:"dot", color:[170, 170, 170], label:`circle: the ${label} radius in metres` }, { shape:"cross", label:`no ${label} on the plot` }, { shape:"ring", label:`${label} 0, accuracy unknown` }]);
  $("pointLegend").innerHTML = strategyLegend($("pointColour").value, "point");
  $("lineLegend").innerHTML = strategyLegend($("lineColour").value, "line");
  const sized = $("pointSize").value !== "fixed";
  $("pointPxRow").style.display = sized ? "none" : ""; $("pointMetresRow").style.display = sized ? "" : "none";
  $("pointPxValue").textContent = $("pointPx").value + " px"; $("pointMetresValue").textContent = sliderMetres("pointMetres") + " m";
  $("lineWidthValue").textContent = $("lineWidth").value + " px";
  $("pointSizeNote").textContent = sized ? "A circle in metres from the sigma east and north the strategy recorded in track_state. Points without a sigma get the size in metres below." : "";
}

function wire() {
  const redraw = () => { legends(); bus.draw(); };
  for (const id of ["rawOn", "rawColour", "rawSize", "rawPx", "rawMetres", "pointsOn", "linesOn", "pointColour", "lineColour", "pointSize", "pointPx", "pointMetres", "lineWidth", "mapShows"]) {
    $(id).addEventListener($(id).type === "range" ? "input" : "change", redraw);
  }
  $("fadeWin").onchange = () => { $("fadeCustom").style.display = $("fadeWin").value === "custom" ? "" : "none"; bus.draw(); };
  $("fadeCustom").oninput = bus.draw;
  $("runsMore").onclick = () => openRunsPanel(!$("runsPanel").classList.contains("open"));
  $("runsClose").onclick = () => openRunsPanel(false);
  $("find").onkeydown = e => { if (e.key === "Enter") { findTracks($("find").value.trim().toUpperCase()); $("find").value = ""; } };
  $("clear").onclick = clearCompare;
  $("compareOn").onchange = () => { S.compareOn = $("compareOn").checked; renderCompare(); bus.draw(); };
  $("addRawChart").onclick = e => openFieldBrowser("raw", e.currentTarget);
  $("addStrategyChart").onclick = e => openFieldBrowser("strategy", e.currentTarget);
  wireFieldBrowser();
  document.querySelectorAll('input[name="chartZoom"]').forEach(r => r.onchange = () => { S.chartZoom = r.value; for (const spec of S.charts) spec.box = null; rebuildCharts(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") { closeSelects(); closePick(); closeFieldBrowser(); } });
}

init();
