// The map: raw plots underneath, strategy points and lines on top, all as known at time now.
import { S, $, table, compareEntry, trackLabel, fadeWindowMs, fmt, fmtMs, fmtN, runName, SOURCE_NAME, SOURCE_BY_ID, escapeHtml } from "./state.js";
import { rawColourFunction, strategyColourFunction, SOURCE_COLOR, GREY, FILTERED, ICONS, rgb, runColour } from "./palette.js";
import { hideFailed } from "./filters.js";
import { toggleTrack } from "./compare.js";
import { bus } from "./bus.js";

let map, overlay, baseLayers = [];
let shiftDown = false;   // shift held at the last mouse down on the map

// DO-260B: NACp -> 95 % position error radius, NIC -> containment radius, metres
export const NACP_M = { 11:3, 10:10, 9:30, 8:92.6, 7:185.2, 6:555.6, 5:926, 4:1852, 3:3704, 2:7408, 1:18520 };
export const NIC_M = { 11:7.5, 10:25, 9:75, 8:185.2, 7:370.4, 6:1111.2, 5:1852, 4:3704, 3:7408, 2:14816, 1:37040 };
const SIGMA_FACTOR = { s1:1, s2:2, s95:2.45 };

export function initMap(onReady) {
  const box = S.CASE.case.box;
  map = new maplibregl.Map({ container:"map", style:"https://tiles.openfreemap.org/styles/dark", center:[(box.lon_min + box.lon_max) / 2, (box.lat_min + box.lat_max) / 2], zoom:8.3, boxZoom:false, dragRotate:false, pitchWithRotate:false, touchPitch:false });
  $("mapwrap").addEventListener("contextmenu", e => e.preventDefault());
  map.addControl(new maplibregl.NavigationControl(), "top-right"); map.addControl(new maplibregl.ScaleControl({ unit:"metric" }));
  overlay = new deck.MapboxOverlay({ interleaved:false, layers:[], onClick:(info, event) => clickAt(info, event) });
  map.addControl(overlay);
  new ResizeObserver(() => map.resize()).observe($("mapwrap"));
  const placeDbg = () => { $("dbg").style.bottom = ($("ctl").offsetHeight + 12) + "px"; }; placeDbg(); new ResizeObserver(placeDbg).observe($("ctl"));
  map.on("load", dimBasemap);
  map.on("mousemove", e => { $("dbgLat").textContent = e.lngLat.lat.toFixed(4); $("dbgLon").textContent = e.lngLat.lng.toFixed(4); });
  map.on("move", () => { $("dbgZoom").textContent = map.getZoom().toFixed(2); }); $("dbgZoom").textContent = map.getZoom().toFixed(2);
  document.addEventListener("mousedown", e => { if (!$("pick").contains(e.target)) closePick(); });
  boxSelect();
  map.loaded() ? onReady() : map.once("idle", onReady);
}

// the OpenFreeMap dark style is too bright for plots on top; pull roads, fills and labels back
function dimBasemap() {
  for (const layer of map.getStyle().layers) {
    try {
      if (layer.type === "line") map.setPaintProperty(layer.id, "line-opacity", 0.28);
      else if (layer.type === "fill") map.setPaintProperty(layer.id, "fill-opacity", 0.55);
      else if (layer.type === "symbol") { map.setPaintProperty(layer.id, "text-opacity", 0.55); map.setPaintProperty(layer.id, "icon-opacity", 0.4); }
      else if (layer.type === "background") map.setPaintProperty(layer.id, "background-color", "#0a0a0a");
    } catch (err) { }
  }
}

// ---------- what is shown ----------

// opacity falls in a straight line from full at the plot's position time to zero at the end of the fade window
function fader() {
  const fadeMs = fadeWindowMs();
  return t => { if (!fadeMs) return 230; const age = S.now - t; return age >= fadeMs ? 0 : Math.round(230 * (1 - age / fadeMs)); };
}
// while comparing: everything, only the compared tracks, or everything else
function shownFilter() {
  const mode = S.compare.length ? $("mapShows").value : "all";
  return (kind, i) => mode === "all" ? true : mode === "only" ? !!compareEntry(kind, i) : !compareEntry(kind, i);
}
const inWindow = t => !S.win || (t >= S.win[0] && t <= S.win[1]);

export function draw() {
  if (!S.RAW || !map) return;
  const alpha = fader(), shown = shownFilter(), comparing = S.compare.length > 0;
  const layers = [boxLayer()];
  S.visible = { raw:[], runs:{} };
  if ($("rawOn").checked) layers.push(...rawLayers(alpha, shown, comparing));
  const pointLayers = [];
  for (const id of S.runShown) if (S.RUNS[id]) { const [lines, points] = strategyLayers(id, alpha, shown, comparing); if (lines) layers.push(lines); pointLayers.push(...points); }
  baseLayers = [...layers, ...pointLayers];
  drawHighlight();
}

function boxLayer() {
  const b = S.CASE.case.box;
  return new deck.PathLayer({ id:"box", data:[{ path:[[b.lon_min, b.lat_min], [b.lon_max, b.lat_min], [b.lon_max, b.lat_max], [b.lon_min, b.lat_max], [b.lon_min, b.lat_min]] }], getPath:d => d.path, getColor:[183, 192, 202, 90], getWidth:1, widthUnits:"pixels" });
}

function rawLayers(alpha, shown, comparing) {
  const R = S.RAW, pass = S.rawPass, hide = hideFailed(), mode = $("rawColour").value, sizeMode = $("rawSize").value, px = +$("rawPx").value;
  const colourOf = rawColourFunction(mode);
  // compared tracks take their own colour and everything else goes grey; a plot that fails the filters is darker still
  const colour = i => { if (!pass[i]) return FILTERED; if (comparing) { const c = compareEntry("raw", i); return c ? c.color : GREY; } return colourOf(i); };
  const idx = [];
  for (let i = 0; i < R.n && R.r[i] <= S.now; i++) if ((pass[i] || !hide) && inWindow(R.t[i]) && alpha(R.t[i]) > 0 && shown("raw", i)) idx.push(i);   // RAW is sorted by receipt time
  S.visible.raw = idx;
  const stamp = [S.now, mode, sizeMode, px, S.compare.length, S.compare.map(c => c.color).join(), pass, fadeWindowMs()];
  const common = { getPosition:i => [R.lon[i], R.lat[i]], pickable:true, onHover:info => mapHover(info, "raw") };
  if (sizeMode === "fixed") return [new deck.ScatterplotLayer({ id:"raw", data:idx, ...common, radiusUnits:"pixels", getRadius:px, getFillColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getFillColor:stamp } })];

  // sized by NACp or NIC: a circle of that radius in metres; no number gets a cross at the fixed size, a 0 gets a ring
  const value = i => sizeMode === "nacp" ? R.nacp[i] : R.nic[i];
  const radius = i => sizeMode === "nacp" ? NACP_M[R.nacp[i]] : (NIC_M[R.nic[i]] ?? (R.rc[i] || null));
  const sized = [], zero = [], missing = [];
  for (const i of idx) { const v = value(i); if (v == null) missing.push(i); else if (v === 0) zero.push(i); else if (radius(i)) sized.push(i); else missing.push(i); }
  const icon = (id, data, kind) => new deck.IconLayer({ id, data, ...common, getIcon:() => ({ url:ICONS[kind], id:kind, width:64, height:64, mask:true }), sizeUnits:"pixels", getSize:px * 2, getColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getColor:stamp, getSize:stamp } });
  return [
    new deck.ScatterplotLayer({ id:"raw-sized", data:sized, ...common, radiusUnits:"meters", getRadius:radius, filled:true, stroked:true, lineWidthUnits:"pixels", getLineWidth:1,
      getFillColor:i => [...colour(i), Math.round(alpha(R.t[i]) * 0.35)], getLineColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getFillColor:stamp, getLineColor:stamp, getRadius:[sizeMode] } }),
    icon("raw-zero", zero, "ring"),
    icon("raw-missing", missing, "cross"),
  ];
}

function strategyLayers(id, alpha, shown, comparing) {
  const run = S.RUNS[id], idx = [], paths = {};
  for (let i = 0; i < run.n && run.created[i] <= S.now; i++) {   // sorted by created
    const replaced = run.valid_to[i]; if (replaced != null && replaced <= S.now) continue;   // a later event replaced it
    if (!inWindow(run.t[i]) || alpha(run.t[i]) <= 0 || !shown(id, i)) continue;
    idx.push(i); (paths[run.track[i]] ||= []).push(i);
  }
  S.visible.runs[id] = idx;
  const pointColour = strategyColourFunction($("pointColour").value, id), lineColour = strategyColourFunction($("lineColour").value, id);
  const override = (i, base) => { if (!comparing) return base(i); const c = compareEntry(id, i); return c ? c.color : GREY; };
  const stamp = [S.now, $("pointColour").value, $("lineColour").value, $("pointSize").value, $("pointPx").value, $("lineWidth").value, S.compare.length, S.compare.map(c => c.color).join(), fadeWindowMs()];
  let lines = null;
  if ($("linesOn").checked) {
    const data = Object.values(paths).map(ids => { ids.sort((a, b) => run.t[a] - run.t[b]); return { first:ids[0], newest:run.t[ids[ids.length - 1]], path:ids.map(i => [run.lon[i], run.lat[i]]) }; });
    lines = new deck.PathLayer({ id:"lines-" + id, data, getPath:d => d.path, getColor:d => [...override(d.first, lineColour), Math.max(40, alpha(d.newest))], getWidth:+$("lineWidth").value, widthUnits:"pixels", updateTriggers:{ getColor:stamp, getWidth:stamp } });
  }
  const points = [];
  if ($("pointsOn").checked) {
    const common = { getPosition:i => [run.lon[i], run.lat[i]], pickable:true, onHover:info => mapHover(info, id), stroked:true, lineWidthUnits:"pixels" };
    const factor = SIGMA_FACTOR[$("pointSize").value], px = +$("pointPx").value;
    // the horizontal sigma from the strategy's recorded east and north sigmas, when it records them
    const sigma = run.sigma_east_m && run.sigma_north_m ? i => { const e = run.sigma_east_m[i], n = run.sigma_north_m[i]; return e == null || n == null ? null : Math.sqrt((e * e + n * n) / 2); } : () => null;
    const sized = factor ? idx.filter(i => sigma(i) != null) : [], fixed = factor ? idx.filter(i => sigma(i) == null) : idx;
    if (sized.length) points.push(new deck.ScatterplotLayer({ id:"pts-sized-" + id, data:sized, ...common, radiusUnits:"meters", getRadius:i => sigma(i) * factor, getLineWidth:1,
      getFillColor:i => [...override(i, pointColour), Math.round(alpha(run.t[i]) * 0.15)], getLineColor:i => [...override(i, pointColour), alpha(run.t[i])], updateTriggers:{ getFillColor:stamp, getLineColor:stamp, getRadius:stamp } }));
    // fixed size: a solid point with a thin black edge, so it stands out from the line through it
    if (fixed.length) points.push(new deck.ScatterplotLayer({ id:"pts-" + id, data:fixed, ...common, radiusUnits:"pixels", getRadius:px, getLineWidth:1,
      getFillColor:i => [...override(i, pointColour), alpha(run.t[i])], getLineColor:i => [0, 0, 0, alpha(run.t[i])], updateTriggers:{ getFillColor:stamp, getLineColor:stamp, getRadius:stamp } }));
  }
  return [lines, points];
}

// the hover ring, drawn on top without rebuilding everything else
export function drawHighlight() {
  const layers = [...baseLayers];
  if (S.hover && table(S.hover.kind)) {
    const d = table(S.hover.kind);
    layers.push(new deck.ScatterplotLayer({ id:"hover", data:[S.hover], getPosition:h => [d.lon[h.i], d.lat[h.i]], radiusUnits:"pixels", getRadius:9, filled:false, stroked:true, lineWidthUnits:"pixels", getLineWidth:2.5, getLineColor:[204, 255, 0] }));
  }
  overlay.setProps({ layers });
}

// ---------- hover, click, box ----------

function mapHover(info, kind) { setHover(info.object == null ? null : { kind, i:info.object }, info.x, info.y); }
export function setHover(hover, x, y, fromChart) {
  const same = (S.hover && hover && S.hover.kind === hover.kind && S.hover.i === hover.i) || (!S.hover && !hover);
  S.hover = hover;
  if (!same) { drawHighlight(); bus.redrawCharts(); }
  const tip = $("tip");
  if (!hover || x == null) { tip.style.display = "none"; return; }
  tip.innerHTML = describe(hover); tip.style.display = "block";
  tip.style.left = Math.min(x + 12, $("mapwrap").clientWidth - tip.offsetWidth - 8) + "px"; tip.style.top = (fromChart ? y : y + 12) + "px";
}

export function describe({ kind, i }) {
  const d = table(kind), raw = kind === "raw";
  const source = raw ? SOURCE_NAME[d.src[i]] + (d.kind[i] ? " " + d.kind[i] : "") : SOURCE_NAME[SOURCE_BY_ID[d.src[i]]] || "";
  const lines = [
    `<b>${escapeHtml(d.cs[i] || "no callsign")}</b> · hex ${d.hex[i] || "–"} · tail ${d.tail[i] || "–"}`,
    raw ? `raw plot · ${source} · source track ${escapeHtml(d.tid[i])}` : `${escapeHtml(runName(kind))} · track ${escapeHtml(d.track[i])} · ${d.quality[i]} · from ${source}`,
    `position ${fmtMs(d.t[i])} · received ${fmt(d.r[i])} (${((d.r[i] - d.t[i]) / 1000).toFixed(2)} s late)`,
    raw ? "" : `emitted ${fmt(d.created[i])}${d.valid_to[i] != null ? ` · replaced ${fmt(d.valid_to[i])}` : ""}`,
    `alt ${number(d.alt[i], 0)} ft · ${number(d.gs[i], 0)} kt · trk ${number(d.trk[i], 0)}`,
    raw ? accuracyLine(i) : stateLine(d, i),
    raw ? outcomeLine(i) : "",
  ];
  return lines.filter(Boolean).join("<br>");
}
const number = (v, digits) => typeof v === "number" ? v.toFixed(digits) : "–";
function accuracyLine(i) {
  const R = S.RAW, parts = [];
  if (R.nacp[i] != null) parts.push(`NACp ${R.nacp[i]}${NACP_M[R.nacp[i]] ? ` (< ${NACP_M[R.nacp[i]]} m)` : " (unknown)"}`);
  if (R.nic[i] != null) parts.push(`NIC ${R.nic[i]}${NIC_M[R.nic[i]] ? ` (Rc < ${NIC_M[R.nic[i]]} m)` : " (unknown)"}`);
  if (R.rc[i] != null) parts.push(`Rc ${R.rc[i]} m`);
  return `<span class="muted">${parts.length ? parts.join(" · ") : "no accuracy numbers on this plot"}</span>`;
}
function stateLine(run, i) {
  const parts = (run.state_columns || []).filter(c => run[c][i] != null).map(c => `${c} ${(+run[c][i]).toFixed(1)}`);
  return parts.length ? `<span class="muted">${parts.join(" · ")}</span>` : "";
}
function outcomeLine(i) {
  const parts = Object.entries(S.OUTCOMES).filter(([id]) => S.runActive.has(id)).map(([id, o]) => {
    const numbers = Object.entries(o.numbers || {}).filter(([, v]) => v[i] != null).map(([k, v]) => `${k} ${(+v[i]).toFixed(1)}`);
    return `${escapeHtml(runName(id))}: ${o.state[i]}${o.reason[i] ? " (" + escapeHtml(o.reason[i]) + ")" : o.track[i] ? " into " + escapeHtml(o.track[i]) : ""}${numbers.length ? ", " + numbers.join(", ") : ""}`;
  });
  return parts.length ? `<span class="muted">${parts.join("<br>")}</span>` : "";
}

// a click: every plot within a few pixels is picked, so overlapping plots can be told apart
function clickAt(info) {
  closePick();
  if (shiftDown) return;   // shift belongs to the box select
  const picks = overlay.pickMultipleObjects({ x:info.x, y:info.y, radius:7, depth:40 });
  const items = picks.filter(p => p.layer && (p.layer.id.startsWith("raw") || p.layer.id.startsWith("pts-"))).map(p => ({ kind:p.layer.id.startsWith("raw") ? "raw" : p.layer.id.replace(/^pts-(sized-)?/, ""), i:p.object }));
  const tracks = [], seen = new Set();
  for (const it of items) { const d = table(it.kind), key = it.kind === "raw" ? `raw|${d.src[it.i]}|${d.tid[it.i]}` : `${it.kind}|${d.track[it.i]}`; if (!seen.has(key)) { seen.add(key); tracks.push(it); } }
  if (!tracks.length) return;
  if (tracks.length === 1) return toggleTrack(tracks[0].kind, tracks[0].i);
  openPick(info.x, info.y, `${tracks.length} tracks here, which one?`, tracks.map(it => {
    const d = table(it.kind), entry = compareEntry(it.kind, it.i);
    const label = it.kind === "raw" ? trackLabel({ kind:"raw", src:d.src[it.i], tid:d.tid[it.i] }) : trackLabel({ kind:it.kind, track:d.track[it.i] });
    return { color: entry ? entry.color : it.kind === "raw" ? SOURCE_COLOR[d.src[it.i]] : runColour(it.kind), text: label + (d.cs[it.i] ? ` · ${d.cs[it.i]}` : ""), note: entry ? "remove" : "add", action: () => toggleTrack(it.kind, it.i) };
  }));
}
function openPick(x, y, title, items) {
  const el = $("pick");
  el.innerHTML = `<div class="head">${title}</div>` + items.map((it, k) => `<div class="item" data-k="${k}"><span class="sw" style="background:${rgb(it.color)}"></span>${escapeHtml(it.text)}<span class="muted">${it.note}</span></div>`).join("");
  el.querySelectorAll(".item").forEach(div => div.onclick = () => { closePick(); items[+div.dataset.k].action(); });
  el.style.display = "block";
  el.style.left = Math.min(x + 8, $("mapwrap").clientWidth - el.offsetWidth - 8) + "px"; el.style.top = Math.min(y + 8, $("mapwrap").clientHeight - el.offsetHeight - 8) + "px";
}
export function closePick() { $("pick").style.display = "none"; }

// shift and drag draws a box: the left button adds every track with a visible plot inside it, the right button removes them
function boxSelect() {
  const wrap = $("mapwrap"), box = $("selbox"); let start = null, removing = false;
  const rect = (a, b) => ({ x:Math.min(a[0], b[0]), y:Math.min(a[1], b[1]), w:Math.abs(a[0] - b[0]), h:Math.abs(a[1] - b[1]) });
  const pos = e => { const r = wrap.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  wrap.addEventListener("mousedown", e => {
    shiftDown = e.shiftKey;
    if (!e.shiftKey || (e.button !== 0 && e.button !== 2) || e.target.closest("#ctl, #pick, #runsPanel, .maplibregl-ctrl")) return;
    start = pos(e); removing = e.button === 2; box.classList.toggle("remove", removing); map.dragPan.disable();
  }, true);
  document.addEventListener("mousemove", e => { if (!start) return; const r = rect(start, pos(e)); Object.assign(box.style, { display:"block", left:r.x + "px", top:r.y + "px", width:r.w + "px", height:r.h + "px" }); });
  document.addEventListener("mouseup", e => {
    if (!start) return;
    const r = rect(start, pos(e)); start = null; box.style.display = "none"; map.dragPan.enable();
    if (r.w < 4 && r.h < 4) return;
    const nw = map.unproject([r.x, r.y]), se = map.unproject([r.x + r.w, r.y + r.h]);
    const latMin = Math.min(nw.lat, se.lat), latMax = Math.max(nw.lat, se.lat), lonMin = Math.min(nw.lng, se.lng), lonMax = Math.max(nw.lng, se.lng);
    const found = [], seen = new Set();
    const consider = (kind, idx) => { const d = table(kind); for (const i of idx) { if (d.lat[i] < latMin || d.lat[i] > latMax || d.lon[i] < lonMin || d.lon[i] > lonMax) continue; const key = kind === "raw" ? `raw|${d.src[i]}|${d.tid[i]}` : `${kind}|${d.track[i]}`; if (!seen.has(key)) { seen.add(key); found.push({ kind, i }); } } };
    consider("raw", S.visible.raw);
    for (const [id, idx] of Object.entries(S.visible.runs)) consider(id, idx);
    const work = found.filter(f => removing ? !!compareEntry(f.kind, f.i) : !compareEntry(f.kind, f.i));
    work.forEach((f, k) => toggleTrack(f.kind, f.i, k < work.length - 1));
    $("status").textContent = `${fmtN(S.RAW.n)} · ${work.length} ${removing ? "removed" : "added"}`;
  });
}

export const resizeMap = () => map && map.resize();
