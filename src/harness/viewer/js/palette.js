// Colours, and the legends that say what they mean.
// Checked with the dataviz palette validator on the map background #0a0a0a: the three ADS-B sources pass every pair
// for colour-blind readers; the strategy colours sit brighter on purpose, so strategy output reads as a layer above the raw plots.
import { S, $, SOURCE_NAME, runName, strategyOf, escapeHtml, fmtN } from "./state.js";

const hex = h => [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16));
export const rgb = c => `rgb(${c})`;

// the documented categorical order for dark surfaces; a colour follows its source, never its rank
const CATEGORICAL = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"].map(hex);
export const SOURCE_COLOR = { adsbx:CATEGORICAL[0], uavionix:CATEGORICAL[1], planefinder:CATEGORICAL[2], tfms_ti:CATEGORICAL[3], stdds:CATEGORICAL[4], tfms_or:CATEGORICAL[5], ual:CATEGORICAL[6], asa:CATEGORICAL[7] };
const STRATEGY_COLORS = ["#ffffff", "#ccff00", "#e87ba4", "#9085e9"].map(hex);
export const COMPARE_COLORS = ["#3987e5", "#d95926", "#199e70", "#ffffff", "#ccff00", "#e87ba4", "#9085e9", "#c98500"].map(hex);
// what a strategy did with a raw plot is a state, so it takes the status colours
export const STATE_COLOR = { used:hex("#0ca30c"), dropped:hex("#fab219"), rejected:hex("#d03b3b"), skipped:hex("#6b6b6b"), unknown:hex("#3a3a3a") };
export const OTHER = hex("#6b6b6b");
export const GREY = [74, 74, 74];        // everything that is not compared, while the compare list has tracks
export const FILTERED = [44, 44, 44];    // a raw plot that fails the filters, when not hidden

// ---------- raw plots ----------

export function rawColourOptions() {
  const out = [["source", "source"], ["kind", "source and plot kind"], ["track", "source track id"], ["identity", "hex, else tail, else source track id"]];
  for (const id of [...S.runActive]) out.push(["outcome:" + id, `what ${runName(id)} did with it`]);
  return out;
}

// every source and kind with its count, most plots first; the first eight get a colour, the rest share "other"
let kindColours = null;
function kinds() {
  if (kindColours) return kindColours;
  const counts = new Map();
  for (let i = 0; i < S.RAW.n; i++) { const key = S.RAW.src[i] + "|" + S.RAW.kind[i]; counts.set(key, (counts.get(key) || 0) + 1); }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  kindColours = new Map(sorted.map(([key, n], k) => [key, { color: k < CATEGORICAL.length ? CATEGORICAL[k] : OTHER, n }]));
  return kindColours;
}
const kindLabel = key => { const [src, kind] = key.split("|"); return SOURCE_NAME[src] + (kind ? " " + kind : ""); };

export function rawColourFunction(mode) {
  const R = S.RAW;
  if (mode === "kind") { const k = kinds(); return i => k.get(R.src[i] + "|" + R.kind[i]).color; }
  if (mode === "track") return i => hashColor(R.src[i] + ":" + R.tid[i]);
  if (mode === "identity") return i => hashColor(R.hex[i] || R.tail[i] || R.src[i] + ":" + R.tid[i]);
  if (mode.startsWith("outcome:")) {
    const o = S.OUTCOMES[mode.slice(8)];
    if (!o) return () => OTHER;
    return i => STATE_COLOR[o.state[i]] || OTHER;
  }
  return i => SOURCE_COLOR[R.src[i]];
}

export function rawColourLegend(mode) {
  const R = S.RAW;
  if (mode === "source") {
    const counts = {}; for (let i = 0; i < R.n; i++) counts[R.src[i]] = (counts[R.src[i]] || 0) + 1;
    return legend(Object.keys(SOURCE_COLOR).filter(s => counts[s]).map(s => ({ color:SOURCE_COLOR[s], label:SOURCE_NAME[s], n:counts[s] })));
  }
  if (mode === "kind") {
    const items = [], other = { color:OTHER, label:"other", n:0 };
    for (const [key, v] of kinds()) if (v.color === OTHER) other.n += v.n; else items.push({ color:v.color, label:kindLabel(key), n:v.n });
    return legend(other.n ? [...items, other] : items);
  }
  if (mode.startsWith("outcome:")) {
    const o = S.OUTCOMES[mode.slice(8)];
    if (!o) return `<span class="item dim">loading…</span>`;
    const counts = {}; for (const st of o.state) counts[st] = (counts[st] || 0) + 1;
    return legend(Object.keys(STATE_COLOR).filter(st => counts[st]).map(st => ({ color:STATE_COLOR[st], label:st, n:counts[st] })));
  }
  return `<span class="item dim">one colour per track, too many for a legend</span>`;
}

// ---------- strategies ----------

// a run keeps its colour from its place in the case's run list, so it looks the same every time the case opens
const at = (list, key) => STRATEGY_COLORS[Math.max(0, list.indexOf(key)) % STRATEGY_COLORS.length];
export const runColour = id => at(S.CASE.runs.map(r => r.id), id);
export const strategyColour = strategy => at([...new Set(S.CASE.runs.map(r => strategyOf(r.id)))], strategy);

export function strategyColourFunction(mode, id) {
  if (mode === "track") { const run = S.RUNS[id]; return i => hashColor(id + ":" + run.track[i]); }
  const c = mode === "strategy" ? strategyColour(strategyOf(id)) : runColour(id);
  return () => c;
}

export function strategyLegend(mode, shape) {
  const shown = $("runsOn").checked ? [...S.runShown].filter(id => S.RUNS[id]) : [];
  if (!shown.length) return "";
  if (mode === "track") return `<span class="item dim">one colour per track, too many for a legend</span>`;
  if (mode === "strategy") { const names = [...new Set(shown.map(strategyOf))]; return legend(names.map(s => ({ color:strategyColour(s), label:s.replace(/_/g, " "), shape }))); }
  return legend(shown.map(id => ({ color:runColour(id), label:runName(id), shape })));
}

// ---------- shared ----------

export function legend(items) {
  return items.map(it => `<span class="item">${swatch(it.color, it.shape)}${escapeHtml(it.label)}${it.n != null ? ` <span class="n">${fmtN(it.n)}</span>` : ""}</span>`).join("");
}
export function swatch(color, shape = "dot") {
  if (shape === "line") return `<span class="sw line" style="background:${rgb(color)}"></span>`;
  if (shape === "point") return `<span class="sw outlined" style="background:${rgb(color)}"></span>`;
  if (shape === "cross" || shape === "ring") return `<img class="mark-icon" src="${ICONS[shape]}" alt="">`;
  return `<span class="sw" style="background:${rgb(color)}"></span>`;
}

export function hashColor(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
  return hsl((h >>> 0) % 360, 55 + ((h >>> 9) % 35), 45 + ((h >>> 17) % 25));
}
function hsl(h, s, l) {
  s /= 100; l /= 100;
  const k = n => (n + h / 30) % 12, a = s * Math.min(l, 1 - l), f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [255 * f(0), 255 * f(8), 255 * f(4)].map(Math.round);
}

// the two marks for a plot without a usable accuracy number, drawn white so deck.gl can tint them:
// a filled circle with a cross cut out (the plot has no NACp or NIC), and a ring (the plot says 0, accuracy unknown)
function icon(kind) {
  const size = 64, c = document.createElement("canvas"); c.width = c.height = size;
  const g = c.getContext("2d");
  g.fillStyle = g.strokeStyle = "#ffffff";
  if (kind === "cross") {
    g.beginPath(); g.arc(32, 32, 31, 0, Math.PI * 2); g.fill();
    g.globalCompositeOperation = "destination-out"; g.lineWidth = 11; g.lineCap = "butt";
    g.beginPath(); g.moveTo(16, 16); g.lineTo(48, 48); g.moveTo(48, 16); g.lineTo(16, 48); g.stroke();
  } else {
    g.lineWidth = 12; g.beginPath(); g.arc(32, 32, 25, 0, Math.PI * 2); g.stroke();
  }
  return c.toDataURL();
}
export const ICONS = { cross: icon("cross"), ring: icon("ring") };
