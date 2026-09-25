// The map: raw plots underneath, strategy points and lines on top, all as known at time now.
import { S, $, api, runById, table, compareEntry, comparing, trackLabel, fadeWindowMs, fmt, fmtMs, fmtN, runName, SOURCE_NAME, SOURCE_BY_ID, escapeHtml, sliderMetres } from "./state.js";
import { rawColourFunction, strategyColourFunction, SOURCE_COLOR, GREY, FILTERED, rgb, runColour } from "./palette.js";
import { hideFailed } from "./filters.js";
import { toggleTrack } from "./compare.js";
import { bus } from "./bus.js";

let map, overlay, baseLayers = [];
let shiftDown = false;   // shift held at the last mouse down on the map

// DO-260B: NACp -> 95 % position error radius, NIC -> containment radius, metres
export const NACP_M = { 11:3, 10:10, 9:30, 8:92.6, 7:185.2, 6:555.6, 5:926, 4:1852, 3:3704, 2:7408, 1:18520 };
export const NIC_M = { 11:7.5, 10:25, 9:75, 8:185.2, 7:370.4, 6:1111.2, 5:1852, 4:3704, 3:7408, 2:14816, 1:37040 };
const SIGMA_FACTOR = { s1:1, s2:2, s95:2.45 };
// the measurement sigma a strategy run recorded for a raw plot it used, in metres, from a "sigma:<run>" size mode
const runSigma = (mode, i) => { const v = S.OUTCOMES[mode.slice(6)]?.numbers?.measurement_sigma_m?.[i]; return v == null ? null : +v; };

// how big a plot is drawn: { units:"pixels"|"meters", radius }, for the layers and for the hover ring
function rawRadius(i) {
  const R = S.RAW, mode = $("rawSize").value;
  if (mode === "fixed") return { units:"pixels", radius:+$("rawPx").value };
  if (mode.startsWith("sigma:")) { const sigma = runSigma(mode, i); return { units:"meters", radius:sigma ? sigma * SIGMA_FACTOR.s95 : sliderMetres("rawMetres") }; }
  const metres = mode === "nacp" ? NACP_M[R.nacp[i]] : (NIC_M[R.nic[i]] ?? (R.rc[i] || null));
  return { units:"meters", radius:metres || sliderMetres("rawMetres") };
}
// the horizontal uncertainty ellipse from the strategy's recorded east and north sigmas and their covariance, in metres:
// the long and short axis at one sigma and the angle of the long axis from east. Without a covariance the axes run east and north.
function ellipse(run, i) {
  if (!run.sigma_east_m || !run.sigma_north_m) return null;
  const e = run.sigma_east_m[i], n = run.sigma_north_m[i];
  return e == null || n == null ? null : ellipseOf(e, n, (run.cov_east_north_m2 && run.cov_east_north_m2[i]) || 0);
}
function ellipseOf(e, n, c) {
  const mid = (e * e + n * n) / 2, half = Math.sqrt(((e * e - n * n) / 2) ** 2 + c * c);
  return { major:Math.sqrt(mid + half), minor:Math.sqrt(Math.max(0, mid - half)), angle:0.5 * Math.atan2(2 * c, e * e - n * n) };
}
// a point's size: pixels, or in the uncertainty modes the ellipse scaled by the chosen factor; radius is the circle of the same
// area, which is what sorts the points and decides which one is smallest under the mouse
function pointRadius(id, i) {
  const factor = SIGMA_FACTOR[$("pointSize").value];
  if (!factor) return { units:"pixels", radius:+$("pointPx").value };
  const el = ellipse(S.RUNS[id], i);
  if (!el) return { units:"meters", radius:sliderMetres("pointMetres") };
  return { units:"meters", radius:Math.sqrt(el.major * el.minor) * factor, ellipse:el, factor };
}
// the outline of an ellipse around a point, as longitude and latitude, scale times its one sigma size
function ellipsePath(lon, lat, el, scale) {
  const east = 111320 * Math.cos(lat * Math.PI / 180), north = 110540, cos = Math.cos(el.angle), sin = Math.sin(el.angle), path = [];
  for (let k = 0; k <= 32; k++) {
    const t = k / 32 * 2 * Math.PI, x = el.major * scale * Math.cos(t), y = el.minor * scale * Math.sin(t);
    path.push([lon + (x * cos - y * sin) / east, lat + (x * sin + y * cos) / north]);
  }
  return path;
}

export function initMap(onReady) {
  const box = S.CASE.case.box;
  map = new maplibregl.Map({ container:"map", style:"https://tiles.openfreemap.org/styles/dark", center:[(box.lon_min + box.lon_max) / 2, (box.lat_min + box.lat_max) / 2], zoom:8.3, boxZoom:false, dragRotate:false, pitchWithRotate:false, touchPitch:false });
  $("mapwrap").addEventListener("contextmenu", e => e.preventDefault());
  map.addControl(new maplibregl.NavigationControl(), "top-right"); map.addControl(new maplibregl.ScaleControl({ unit:"metric" }));
  overlay = new deck.MapboxOverlay({ interleaved:false, layers:[], onClick:(info, event) => clickAt(info, event), onHover:info => hoverAt(info.x, info.y) });
  map.addControl(overlay);
  new ResizeObserver(() => map.resize()).observe($("mapwrap"));
  const placeDbg = () => { $("dbg").style.bottom = ($("ctl").offsetHeight + 12) + "px"; }; placeDbg(); new ResizeObserver(placeDbg).observe($("ctl"));
  map.on("load", dimBasemap);
  map.on("mousemove", e => { $("dbgLat").textContent = e.lngLat.lat.toFixed(4); $("dbgLon").textContent = e.lngLat.lng.toFixed(4); });
  map.on("move", () => { $("dbgZoom").textContent = map.getZoom().toFixed(2); });
  map.on("moveend", () => { if (lastPointer) hoverAt(...lastPointer); });
  $("dbgZoom").textContent = map.getZoom().toFixed(2);
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
  // a compared track switched off with its eye is never drawn; the rest follows "while comparing"
  const mode = comparing() ? $("mapShows").value : "all";
  return (kind, i) => { const e = compareEntry(kind, i); if (e && e.hidden) return false; return mode === "all" ? true : mode === "only" ? !!e : !e; };
}
const inWindow = t => !S.win || (t >= S.win[0] && t <= S.win[1]);

export function draw() {
  if (!S.RAW || !map) return;
  const alpha = fader(), shown = shownFilter(), isComparing = comparing();
  const layers = [boxLayer()];
  S.visible = { raw:[], runs:{} };
  if ($("rawOn").checked) layers.push(...rawLayers(alpha, shown, isComparing));
  const pointLayers = [];
  // the show box on the Strategies heading hides every run at once and keeps which ones are ticked
  if ($("runsOn").checked) for (const id of S.runShown) if (S.RUNS[id]) { const [lines, points] = strategyLayers(id, alpha, shown, isComparing); if (lines) layers.push(lines); pointLayers.push(...points); }
  baseLayers = [...layers, ...pointLayers];
  drawHighlight();
}

function boxLayer() {
  const b = S.CASE.case.box;
  return new deck.PathLayer({ id:"box", data:[{ path:[[b.lon_min, b.lat_min], [b.lon_max, b.lat_min], [b.lon_max, b.lat_max], [b.lon_min, b.lat_max], [b.lon_min, b.lat_min]] }], getPath:d => d.path, getColor:[183, 192, 202, 90], getWidth:1, widthUnits:"pixels" });
}

function rawLayers(alpha, shown, isComparing) {
  const R = S.RAW, pass = S.rawPass, hide = hideFailed(), mode = $("rawColour").value, sizeMode = $("rawSize").value, px = +$("rawPx").value;
  const colourOf = rawColourFunction(mode);
  // compared tracks take their own colour and everything else goes grey; a plot that fails the filters is darker still
  const colour = i => { if (!pass[i]) return FILTERED; if (isComparing) { const c = compareEntry("raw", i); return c ? c.color : GREY; } return colourOf(i); };
  const idx = [];
  for (let i = 0; i < R.n && R.r[i] <= S.now; i++) if ((pass[i] || !hide) && inWindow(R.t[i]) && alpha(R.t[i]) > 0 && shown("raw", i)) idx.push(i);   // RAW is sorted by receipt time
  S.visible.raw = idx;
  const stamp = [S.now, mode, sizeMode, px, sliderMetres("rawMetres"), comparing(), S.compare.map(c => c.color + c.hidden).join(), pass, fadeWindowMs()];
  const common = { getPosition:i => [R.lon[i], R.lat[i]], pickable:true };
  if (sizeMode === "fixed") return [new deck.ScatterplotLayer({ id:"raw", data:idx, ...common, radiusUnits:"pixels", getRadius:px, getFillColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getFillColor:stamp } })];

  // sized by NACp, NIC or a strategy run's sigma: a circle of that radius in metres (for the sigma the 95 % circle, 2.45 sigma);
  // no number gets a solid circle with a cross cut out, a 0 gets a ring, both of the size in metres from the slider;
  // all drawn as shapes, so they stay sharp at any zoom
  const sigmaMode = sizeMode.startsWith("sigma:");
  const value = i => sigmaMode ? runSigma(sizeMode, i) : sizeMode === "nacp" ? R.nacp[i] : R.nic[i];
  const radius = i => rawRadius(i).radius;
  const sized = [], zero = [], missing = [];
  for (const i of idx) { const v = value(i); if (v == null) missing.push(i); else if (v === 0) zero.push(i); else if (sigmaMode || (sizeMode === "nacp" ? NACP_M[v] : (NIC_M[v] ?? R.rc[i]))) sized.push(i); else missing.push(i); }
  const bigFirst = list => list.sort((a, b) => radius(b) - radius(a));
  const shape = { getPosition:common.getPosition, radiusUnits:"meters", getRadius:radius, pickable:false };
  const metres = sliderMetres("rawMetres");
  return [
    new deck.ScatterplotLayer({ id:"raw-missing", data:missing, ...shape, getFillColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getFillColor:stamp, getRadius:stamp } }),
    new deck.PathLayer({ id:"raw-cross", data:missing.flatMap(i => [[i, 0], [i, 1]]), pickable:false, getPath:([i, stroke]) => cross(R.lon[i], R.lat[i], metres, stroke), widthUnits:"meters", getWidth:metres * 0.24, capRounded:false,
      getColor:([i]) => [10, 10, 10, alpha(R.t[i])], updateTriggers:{ getPath:stamp, getWidth:stamp, getColor:stamp } }),
    new deck.ScatterplotLayer({ id:"raw-zero", data:zero, ...shape, getRadius:metres * 0.88, filled:false, stroked:true, lineWidthUnits:"meters", getLineWidth:metres * 0.24,
      getLineColor:i => [...colour(i), alpha(R.t[i])], updateTriggers:{ getLineColor:stamp, getRadius:stamp, getLineWidth:stamp } }),
    new deck.ScatterplotLayer({ id:"raw-sized", data:bigFirst(sized), ...shape, filled:true, stroked:false,
      getFillColor:i => [...colour(i), Math.round(alpha(R.t[i]) * 0.55)], updateTriggers:{ getFillColor:stamp, getRadius:stamp } }),
    // what the mouse finds: one invisible circle per plot, the whole disc, biggest first so the smallest under the mouse is on top
    new deck.ScatterplotLayer({ id:"raw", data:bigFirst([...idx]), ...common, radiusUnits:"meters", getRadius:radius, getFillColor:[0, 0, 0, 0], updateTriggers:{ getRadius:stamp } }),
  ];
}

// one of the two strokes of a cross inside a circle of radius metres, as a lon/lat path
function cross(lon, lat, metres, stroke) {
  const arm = metres * 0.5, dLat = arm / 111320, dLon = arm / (111320 * Math.cos(lat * Math.PI / 180));
  return stroke === 0 ? [[lon - dLon, lat - dLat], [lon + dLon, lat + dLat]] : [[lon + dLon, lat - dLat], [lon - dLon, lat + dLat]];
}

function strategyLayers(id, alpha, shown, isComparing) {
  const run = S.RUNS[id], idx = [], paths = {};
  for (let i = 0; i < run.n && run.created[i] <= S.now; i++) {   // sorted by created
    const replaced = run.valid_to[i]; if (replaced != null && replaced <= S.now) continue;   // a later event replaced it
    if (!inWindow(run.t[i]) || alpha(run.t[i]) <= 0 || !shown(id, i)) continue;
    idx.push(i); (paths[run.track[i]] ||= []).push(i);
  }
  S.visible.runs[id] = idx;
  const pointColour = strategyColourFunction($("pointColour").value, id), lineColour = strategyColourFunction($("lineColour").value, id);
  const override = (i, base) => { if (!isComparing) return base(i); const c = compareEntry(id, i); return c ? c.color : GREY; };
  const stamp = [S.now, $("pointColour").value, $("lineColour").value, $("pointSize").value, $("pointPx").value, sliderMetres("pointMetres"), $("lineWidth").value, comparing(), S.compare.map(c => c.color + c.hidden).join(), fadeWindowMs()];
  let lines = null;
  if ($("linesOn").checked) {
    const data = Object.values(paths).map(ids => { ids.sort((a, b) => run.t[a] - run.t[b]); return { first:ids[0], newest:run.t[ids[ids.length - 1]], path:ids.map(i => [run.lon[i], run.lat[i]]) }; });
    lines = new deck.PathLayer({ id:"lines-" + id, data, getPath:d => d.path, getColor:d => [...override(d.first, lineColour), Math.max(40, alpha(d.newest))], getWidth:+$("lineWidth").value, widthUnits:"pixels", updateTriggers:{ getColor:stamp, getWidth:stamp } });
  }
  const points = [];
  if ($("pointsOn").checked) {
    const common = { getPosition:i => [run.lon[i], run.lat[i]], pickable:false, stroked:true, lineWidthUnits:"pixels" };
    const factor = SIGMA_FACTOR[$("pointSize").value], radius = i => pointRadius(id, i).radius, bigFirst = list => list.sort((a, b) => radius(b) - radius(a));
    const sized = factor ? bigFirst(idx.filter(i => ellipse(run, i))) : [], fixed = factor ? bigFirst(idx.filter(i => !ellipse(run, i))) : idx;
    // the uncertainty ellipses, each outline worked out once per run and factor
    const outlines = (run.outlines ||= {})[factor] ||= [], outline = i => outlines[i] ||= ellipsePath(run.lon[i], run.lat[i], ellipse(run, i), factor);
    const shape = { data:sized, getPolygon:outline, filled:true, stroked:true, lineWidthUnits:"pixels", getLineWidth:1 };
    if (sized.length) points.push(new deck.PolygonLayer({ id:"vpts-sized-" + id, ...shape, pickable:false,
      getFillColor:i => [...override(i, pointColour), Math.round(alpha(run.t[i]) * 0.15)], getLineColor:i => [...override(i, pointColour), alpha(run.t[i])], updateTriggers:{ getFillColor:stamp, getLineColor:stamp, getPolygon:factor } }));
    // a solid point with a thin black edge, so it stands out from the line through it: pixels in the fixed mode,
    // the size in metres from the slider for points without a sigma in the uncertainty modes
    if (fixed.length) points.push(new deck.ScatterplotLayer({ id:"vpts-" + id, data:fixed, ...common, radiusUnits:factor ? "meters" : "pixels", getRadius:i => pointRadius(id, i).radius, getLineWidth:1,
      getFillColor:i => [...override(i, pointColour), alpha(run.t[i])], getLineColor:i => [0, 0, 0, alpha(run.t[i])], updateTriggers:{ getFillColor:stamp, getLineColor:stamp, getRadius:stamp } }));
    // what the mouse finds: every point once, biggest first, so the smallest under the mouse wins; an ellipse is found by its own shape
    points.push(new deck.ScatterplotLayer({ id:"pts-" + id, data:fixed, getPosition:common.getPosition, pickable:true,
      radiusUnits:factor ? "meters" : "pixels", getRadius:radius, getFillColor:[0, 0, 0, 0], updateTriggers:{ getRadius:stamp } }));
    if (sized.length) points.push(new deck.PolygonLayer({ id:"pts-" + id + "#ellipse", ...shape, pickable:true, stroked:false, getFillColor:[0, 0, 0, 0], updateTriggers:{ getPolygon:factor } }));
  }
  return [lines, points];
}

// the hover ring, drawn on top without rebuilding everything else
export function drawHighlight() {
  const layers = [...baseLayers];
  if (S.hover && table(S.hover.kind)) {
    // the ring outlines the plot just outside its edge, in the plot's own units, so it fits at any zoom
    const d = table(S.hover.kind), { i } = S.hover;
    const size = S.hover.kind === "raw" ? rawRadius(i) : $("pointsOn").checked ? pointRadius(S.hover.kind, i) : { units:"pixels", radius:3 };
    // a layer cannot change its kind under one id, so the ellipse ring and the round ring each have their own
    if (size.ellipse) layers.push(new deck.PathLayer({ id:"hover-ellipse", data:[S.hover], getPath:h => ellipsePath(d.lon[h.i], d.lat[h.i], size.ellipse, size.factor * 1.12), widthUnits:"pixels", getWidth:2, getColor:[204, 255, 0] }));
    else {
      const ring = size.units === "pixels" ? { radiusUnits:"pixels", getRadius:size.radius + 4 } : { radiusUnits:"meters", getRadius:size.radius * 1.12, radiusMinPixels:6 };
      layers.push(new deck.ScatterplotLayer({ id:"hover-ring", data:[S.hover], getPosition:h => [d.lon[h.i], d.lat[h.i]], ...ring, filled:false, stroked:true, lineWidthUnits:"pixels", getLineWidth:2, getLineColor:[204, 255, 0] }));
    }
  }
  layers.push(...lookAhead());
  overlay.setProps({ layers });
}

// ---------- looking ahead from the hovered strategy point ----------
// the server asks the strategy's own predict() where the aircraft goes next; each answer is kept, so moving back over a
// point draws at once, and an answer that arrives after the mouse moved on is kept but not drawn
const AHEAD_S = [5, 10, 20, 30, 60], ahead = {};
// the switch shows, and counts, only with an uncertainty size
const lookingAhead = () => $("predictOn").checked && !!SIGMA_FACTOR[$("pointSize").value];
function lookAhead() {
  const h = S.hover;
  const factor = SIGMA_FACTOR[$("pointSize").value];
  if (!lookingAhead() || !h || h.kind === "raw") return [];
  if (!(runById(h.kind) || {}).predicts) { $("status").textContent = `${runName(h.kind)} cannot look ahead: its strategy has no predict()`; return []; }
  const key = h.kind + "|" + h.i, got = ahead[key];
  if (!got) {
    ahead[key] = "asking";
    api("predict", { run:h.kind, i:h.i, seconds:AHEAD_S.join(",") })
      .then(answer => {
        ahead[key] = answer.ellipses || [];
        if (!ahead[key].length) $("status").textContent = `${runName(h.kind)} recorded no state at this point, nothing to look ahead from; rerun it to record one`;
        if (S.hover && S.hover.kind + "|" + S.hover.i === key) drawHighlight();
      })
      .catch(() => { delete ahead[key]; });
    return [];
  }
  if (got === "asking" || !got.length) return [];
  const d = table(h.kind);
  const shapes = got.map(e => ({ seconds:e.seconds, path:ellipsePath(e.longitude, e.latitude, ellipseOf(e.sigma_east_m, e.sigma_north_m, e.cov_east_north_m2), factor) }));
  // the label sits at the northernmost point of its ellipse; a dashed line joins the point to the predicted centres
  const north = path => path.reduce((a, b) => b[1] > a[1] ? b : a);
  const dashed = { widthUnits:"pixels", getWidth:1.5, getColor:[255, 255, 255, 220], getDashArray:[5, 4], dashJustified:true, extensions:[new deck.PathStyleExtension({ dash:true })] };
  return [
    new deck.PathLayer({ id:"ahead", data:[{ path:[[d.lon[h.i], d.lat[h.i]], ...got.map(e => [e.longitude, e.latitude])] }, ...shapes], getPath:s => s.path, ...dashed }),
    new deck.TextLayer({ id:"ahead-labels", data:shapes, getPosition:s => north(s.path), getText:s => `+${s.seconds} s`, getSize:11, getColor:[255, 255, 255, 230],
      fontFamily:getComputedStyle(document.documentElement).getPropertyValue("--mono"), getTextAnchor:"middle", getAlignmentBaseline:"bottom", getPixelOffset:[0, -3] }),
  ];
}

// ---------- hover, click, box ----------

// everything under the mouse, from every layer, and the one drawn smallest on screen wins: a small raw plot inside a
// strategy's big uncertainty circle, or a small circle inside a big one of the same layer, can always be hovered
// while the map pans or zooms nothing is looked up: finding everything under the mouse redraws the picking buffer once
// per plot found, which on a big case takes most of a frame; the lookup runs once when the map stops
let lastPointer = null;
function hoverAt(x, y) {
  lastPointer = x == null || x < 0 ? null : [x, y];
  if (map.isMoving()) return;
  if (!lastPointer) return setHover(null);
  let candidates = pickables(overlay.pickMultipleObjects({ x, y, radius:1, depth:24 }));
  if (!candidates.length) return setHover(null);
  // while looking ahead, a strategy point under the mouse wins over raw plots, which are nearly always smaller
  if (lookingAhead() && candidates.some(c => c.kind !== "raw")) candidates = candidates.filter(c => c.kind !== "raw");
  const pixels = c => { const size = c.kind === "raw" ? rawRadius(c.i) : pointRadius(c.kind, c.i); return size.units === "pixels" ? size.radius : size.radius / metresPerPixel(table(c.kind).lat[c.i]); };
  const best = candidates.reduce((a, b) => pixels(b) < pixels(a) ? b : a);
  setHover(best, x, y);
}
// the raw plots and strategy points among picks, as {kind, i}
function pickables(picks) {
  return picks.filter(p => p.layer && (p.layer.id === "raw" || p.layer.id.startsWith("pts-"))).map(p => ({ kind:p.layer.id === "raw" ? "raw" : p.layer.id.slice("pts-".length).split("#")[0], i:p.object }));
}
// metres per screen pixel at a latitude, for MapLibre's 512 pixel tiles
const metresPerPixel = lat => 40075016.686 * Math.cos(lat * Math.PI / 180) / (512 * 2 ** map.getZoom());
export function setHover(hover, x, y, fromChart) {
  const same = (S.hover && hover && S.hover.kind === hover.kind && S.hover.i === hover.i) || (!S.hover && !hover);
  S.hover = hover;
  if (!same) { drawHighlight(); bus.repaintCharts(); }
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
  const items = pickables(picks);
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
