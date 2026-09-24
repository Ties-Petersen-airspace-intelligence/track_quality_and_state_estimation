// Time: the timeline at the bottom, playback, and the zoom window the charts set.
import { S, $, fmt, clampNow } from "./state.js";
import { bus } from "./bus.js";

export function initTimeline() {
  const c = S.CASE.case;
  $("ctlDay").textContent = new Date(S.CASE.t0_us / 1000).toUTCString().slice(5, 11).toUpperCase();
  $("ctlSpan").textContent = `${c.t_start.slice(11, 16)} – ${c.t_end.slice(11, 16)} Z`;
  $("time").max = S.CASE.span_ms;
  for (const f of [0, 0.25, 0.5, 0.75, 1]) {
    const tick = document.createElement("div");
    tick.className = "tick" + (f === 0 ? " first" : f === 1 ? " last" : ""); tick.style.left = (f * 100) + "%"; tick.textContent = fmt(f * S.CASE.span_ms).slice(0, 5);
    $("timeline").appendChild(tick);
  }
  $("time").oninput = () => setNow(+$("time").value);
  $("play").onclick = togglePlay;
  $("resetZoom").onclick = resetZoom;
  document.addEventListener("keydown", e => {
    if (e.target.closest("input, [contenteditable]")) return;
    if (e.key === " ") { e.preventDefault(); togglePlay(); }
    else if (e.key === "ArrowRight") setNow(S.now + (e.shiftKey ? 10000 : 1000));
    else if (e.key === "ArrowLeft") setNow(S.now - (e.shiftKey ? 10000 : 1000));
  });
}

export function setNow(ms) { S.now = clampNow(ms); $("time").value = S.now; bus.draw(); }

// the header clock, the played bar and the now chip
export function paintTimeline() {
  const pct = (S.now / S.CASE.span_ms * 100) + "%";
  $("now").textContent = fmt(S.now); $("dbgNow").textContent = fmt(S.now);
  $("nowMark").style.left = pct; $("played").style.width = pct;
  $("nowChip").style.left = `clamp(1.2rem, ${pct}, calc(100% - 1.2rem))`; $("nowChip").textContent = fmt(S.now).slice(0, 5);
}

function togglePlay() {
  S.playing = !S.playing; $("play").textContent = S.playing ? "❚❚" : "▶";
  if (!S.playing) return;
  let last = performance.now();
  const tick = ts => {
    if (!S.playing) return;
    const end = S.win ? S.win[1] : S.CASE.span_ms;
    setNow(Math.min(end, S.now + (ts - last) * +$("speed").value)); last = ts;
    if (S.now >= end) { S.playing = false; $("play").textContent = "▶"; return; }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// a zoom in any chart: every chart follows, the map shows only that window, the timeline highlights it
export function onZoom(minS, maxS) {
  const whole = minS <= 0.001 && maxS >= S.CASE.span_ms / 1000 - 0.001;
  const next = whole ? null : [minS * 1000, maxS * 1000];
  if ((next == null && S.win == null) || (next && S.win && Math.abs(next[0] - S.win[0]) < 1 && Math.abs(next[1] - S.win[1]) < 1)) return;
  S.win = next; applyWindow();
}
export function resetZoom() { S.win = null; applyWindow(); }
function applyWindow() {
  const hl = $("winHL");
  $("resetZoom").style.display = S.win ? "inline-block" : "none"; $("resetZoom").className = S.win ? "accent" : "";
  if (S.win) { hl.style.display = "block"; hl.style.left = (S.win[0] / S.CASE.span_ms * 100) + "%"; hl.style.width = ((S.win[1] - S.win[0]) / S.CASE.span_ms * 100) + "%"; hl.title = `${fmt(S.win[0])} to ${fmt(S.win[1])}`; }
  else hl.style.display = "none";
  setNow(S.now);
}
