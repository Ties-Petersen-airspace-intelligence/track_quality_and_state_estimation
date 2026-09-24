// The compare list: tracks picked on the map or by hex, callsign or tail. Each gets its own colour, and while the
// list has tracks those colours replace every colouring option.
import { S, $, table, compareEntry, trackLabel, fmt, escapeHtml } from "./state.js";
import { COMPARE_COLORS, rgb } from "./palette.js";
import { bus } from "./bus.js";

// the first colour no compared track uses yet, so a colour stays with its track when others leave
function freeColour() {
  const used = new Set(S.compare.map(c => String(c.color)));
  return COMPARE_COLORS.find(c => !used.has(String(c))) || COMPARE_COLORS[S.compare.length % COMPARE_COLORS.length];
}

export function toggleTrack(kind, i, quiet) {
  const d = table(kind), existing = compareEntry(kind, i);
  if (existing) S.compare = S.compare.filter(c => c !== existing);
  else S.compare.push(kind === "raw" ? { kind, src:d.src[i], tid:d.tid[i], color:freeColour() } : { kind, track:d.track[i], color:freeColour() });
  if (!quiet) changed();
}

// every source track and drawn strategy track whose plots carry this hex, callsign or tail
export function findTracks(query) {
  if (!query) return;
  const matches = d => i => (d.hex[i] || "").toUpperCase() === query || (d.cs[i] || "").toUpperCase() === query || (d.tail[i] || "").toUpperCase() === query;
  const add = kind => {
    const d = table(kind), hit = matches(d), seen = new Set();
    for (let i = 0; i < d.n; i++) {
      if (!hit(i)) continue;
      const key = kind === "raw" ? d.src[i] + "|" + d.tid[i] : d.track[i];
      if (seen.has(key)) continue;
      seen.add(key);
      if (!compareEntry(kind, i)) toggleTrack(kind, i, true);
    }
    return seen.size;
  };
  let found = add("raw");
  for (const id of S.runShown) if (S.RUNS[id]) found += add(id);
  $("status").textContent = found ? `${found} tracks for ${query}` : `nothing carries ${query}`;
  changed();
}

export function clearCompare() { S.compare = []; changed(); }

export function renderCompare() {
  document.body.classList.toggle("comparing", S.compare.length > 0);
  $("rawColourGroup").classList.toggle("overridden", S.compare.length > 0);
  $("stratColourGroup").classList.toggle("overridden", S.compare.length > 0);
  if (!S.compare.length) { $("sel").innerHTML = `<p class="help" style="margin:0.6rem 0 0">Nothing to compare yet. Click plots on the map, or type a hex, callsign or tail above.</p>`; return; }
  const chips = S.compare.map((c, k) => {
    const d = table(c.kind); if (!d) return "";
    let n = 0, t0 = Infinity, t1 = -Infinity; const callsigns = new Set();
    for (let i = 0; i < d.n; i++) {
      if (c.kind === "raw" ? d.src[i] !== c.src || d.tid[i] !== c.tid : d.track[i] !== c.track) continue;
      n++; if (d.cs[i]) callsigns.add(d.cs[i]); t0 = Math.min(t0, d.t[i]); t1 = Math.max(t1, d.t[i]);
    }
    return `<span class="chip" data-k="${k}" style="border-left-color:${rgb(c.color)}" title="click to remove">${escapeHtml(trackLabel(c))} <span class="muted">${n} · ${fmt(t0).slice(0, 5)}–${fmt(t1).slice(0, 5)}${callsigns.size ? " · " + escapeHtml([...callsigns].join(", ")) : ""}</span><span class="x">×</span></span>`;
  }).join("");
  $("sel").innerHTML = `<div class="label" style="margin-top:0.7rem">${S.compare.length} track${S.compare.length > 1 ? "s" : ""} · click one to remove</div><div class="chips">${chips}</div>`;
  $("sel").querySelectorAll(".chip").forEach(chip => chip.onclick = () => { S.compare.splice(+chip.dataset.k, 1); changed(); });
}

function changed() { renderCompare(); bus.rebuildCharts(); bus.draw(); }
