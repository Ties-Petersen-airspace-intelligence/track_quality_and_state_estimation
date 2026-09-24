// Small interface pieces: brand dropdowns, a two-thumb range slider, and the panel grips.
import { $ } from "./state.js";

// ---------- dropdowns in the brand style ----------
// Every select keeps working for the code (value, options, change); a button and a list drawn next to it are what the page shows.
export function asiSelects(root = document) {
  for (const sel of root.querySelectorAll("select:not(.asel-native)")) {
    sel.classList.add("asel-native");
    const wrap = document.createElement("div"); wrap.className = "asel";
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "asel-btn"; btn.innerHTML = '<span></span><svg viewBox="0 0 10 10"><path d="M1.5 3.2 5 6.7 8.5 3.2" fill="none" stroke="#c3c8cf" stroke-width="1.2"/></svg>';
    const list = document.createElement("div"); list.className = "asel-list";
    wrap.append(btn, list); sel.after(wrap); wrap._sel = sel; sel._wrap = wrap;
    // the list is fixed to the page, so a scrolling side panel cannot clip it; it opens upward near the bottom edge
    btn.onclick = e => {
      e.stopPropagation();
      const open = !wrap.classList.contains("open"); closeSelects(); if (!open) return;
      renderSelectList(wrap);
      const r = btn.getBoundingClientRect(), up = window.innerHeight - r.bottom < 260;
      Object.assign(list.style, { left:r.left + "px", minWidth:r.width + "px", top:up ? "auto" : (r.bottom + 4) + "px", bottom:up ? (window.innerHeight - r.top + 4) + "px" : "auto" });
      wrap.classList.add("open");
    };
    refreshSelect(sel);
  }
}
export function closeSelects() { document.querySelectorAll(".asel.open").forEach(w => w.classList.remove("open")); }
export function refreshSelect(sel) {
  const wrap = sel._wrap; if (!wrap) return;
  const o = sel.options[sel.selectedIndex];
  wrap.querySelector(".asel-btn span").textContent = o ? o.textContent : "";
  wrap.style.display = sel.style.display === "none" ? "none" : "";
}
export function setOptions(sel, options, keep) {
  sel.innerHTML = options.map(([value, text]) => `<option value="${value}">${text}</option>`).join("");
  if (options.some(([value]) => value === keep)) sel.value = keep;
  refreshSelect(sel);
}
function renderSelectList(wrap) {
  const sel = wrap._sel, label = sel.closest(".field")?.querySelector(".label"), title = sel.title || (label ? label.textContent : "select option");
  const list = wrap.querySelector(".asel-list");
  list.innerHTML = `<div class="asel-head">${title}</div>` + [...sel.options].map((o, i) => `<div class="asel-item ${i === sel.selectedIndex ? "on" : ""} ${o.disabled ? "off" : ""}" data-i="${i}">${o.textContent}<i>›</i></div>`).join("");
  list.querySelectorAll(".asel-item").forEach(it => it.onclick = () => {
    const i = +it.dataset.i; if (sel.options[i].disabled) return;
    sel.selectedIndex = i; refreshSelect(sel); closeSelects();
    sel.dispatchEvent(new Event("change"));
  });
}
document.addEventListener("mousedown", e => { if (!e.target.closest(".asel")) closeSelects(); });

// ---------- a range with two thumbs, and number boxes to type the ends ----------
// onChange gets [low, high]; the thumbs cannot cross
export function rangeSlider(container, { min, max, step, low, high, onChange }) {
  container.innerHTML = `<div class="range2"><div class="track"></div><div class="fill"></div><input type="range"><input type="range"></div><input type="number"><input type="number">`;
  const [a, b] = container.querySelectorAll(".range2 input"), [boxA, boxB] = container.querySelectorAll('input[type="number"]'), fill = container.querySelector(".fill");
  for (const el of [a, b, boxA, boxB]) { el.min = min; el.max = max; el.step = step; }
  a.value = boxA.value = low; b.value = boxB.value = high;
  const paint = () => { const span = max - min || 1; fill.style.left = ((+a.value - min) / span * 100) + "%"; fill.style.width = ((+b.value - +a.value) / span * 100) + "%"; };
  const emit = () => { paint(); onChange([+a.value, +b.value]); };
  a.oninput = () => { if (+a.value > +b.value) a.value = b.value; boxA.value = a.value; emit(); };
  b.oninput = () => { if (+b.value < +a.value) b.value = a.value; boxB.value = b.value; emit(); };
  boxA.onchange = () => { a.value = Math.min(+boxA.value, +b.value); boxA.value = a.value; emit(); };
  boxB.onchange = () => { b.value = Math.max(+boxB.value, +a.value); boxB.value = b.value; emit(); };
  paint();
}

// ---------- the side panels and the runs panel can be dragged wider or narrower ----------
export function grips(onResized) {
  let drag = null;
  const start = (id, name) => $(id).onmousedown = e => { drag = name; e.preventDefault(); document.body.classList.add("dragging"); $(id).classList.add("on"); };
  start("gripRight", "right"); start("gripLeft", "left"); start("gripRuns", "runs");
  document.addEventListener("mousemove", e => {
    if (!drag) return;
    const style = document.documentElement.style;
    if (drag === "right") style.setProperty("--right", Math.max(320, Math.min(window.innerWidth * 0.6, window.innerWidth - e.clientX)) + "px");
    else if (drag === "left") style.setProperty("--left", Math.max(260, Math.min(window.innerWidth * 0.4, e.clientX)) + "px");
    else style.setProperty("--runs", Math.max(360, e.clientX - $("mapwrap").getBoundingClientRect().left) + "px");
  });
  document.addEventListener("mouseup", () => {
    if (!drag) return;
    drag = null; document.body.classList.remove("dragging");
    document.querySelectorAll(".grip.on").forEach(g => g.classList.remove("on"));
    onResized();
  });
}
