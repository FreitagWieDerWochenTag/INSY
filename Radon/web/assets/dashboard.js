// Radon dashboard. Draws the JSON written by Radon/analysis/run_analysis.py (build/data/*.json);
// the statistics and the finding texts all come from Python, this file only scales and draws them.
import { $, el, frame, tip, hideTip, sourceLink, getJSON } from "./common.js";

frame();
const num = (v, d = 0) => (v == null ? "–" : v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }));
const fmtP = (p) => (p == null ? "" : p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(p < 0.01 ? 3 : 2)}`);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmtDate = (s) => { const [y, m, d] = s.split("-"); return `${+d} ${MONTHS[+m - 1]} ${y}`; };

function niceMax(v, ticks = 4) {   // a round axis top with `ticks` steps
  const raw = Math.max(v, 1e-9) / ticks;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((f) => f * mag).find((s) => s >= raw);
  return { top: step * ticks, step };
}
function yAxis(svg, { L, R, W, y, top, step, unit }) {
  for (let v = 0; v <= top + 1e-9; v += step) {
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid" }, svg);
    el("text", { x: L - 6, y: y(v) + 3, "text-anchor": "end" }, svg).textContent = num(v);
  }
  if (unit) el("text", { x: L - 6, y: y(top) - 10, "text-anchor": "end" }, svg).textContent = unit;
}
const clear = (svg) => { while (svg.firstChild) svg.removeChild(svg.firstChild); };

// ---------------------------------------------------------------- load
let D;
try {
  const names = ["overview", "daily", "hourly_profile", "correlations", "findings"];
  const all = await Promise.all(names.map((n) => getJSON(`build/data/${n}.json`)));
  D = Object.fromEntries(names.map((n, i) => [n, all[i]]));
} catch (err) {
  const s = $("status");
  s.classList.add("error");
  s.querySelector(".status-text").innerHTML = `Could not load the analysis (${err.message}). Run <code>Radon/web/build.sh</code> first. ` +
    `<button class="tool retry" onclick="location.reload()">Reload</button>`;
  throw err;
}
const ov = D.overview;
const rooms = ov.rooms;
const label = Object.fromEntries(rooms.map((r) => [r.room, r.label]));
const emptySet = new Set(ov.empty_days);
let current = rooms.reduce((a, b) => (b.mean > a.mean ? b : a)).room;

$("status").classList.add("ready");
$("status").querySelector(".status-text").innerHTML =
  `computed by Python (pandas, SciPy) from ${sourceLink("data/radon_sample_data.csv", "radon_sample_data.csv")} · ` +
  `${fmtDate(ov.start)} – ${fmtDate(ov.end)}`;

// ---------------------------------------------------------------- KPIs
{
  const typical = rooms.reduce((s, r) => s + r.mean_occupied, 0) / rooms.length;
  const above = rooms.reduce((s, r) => s + r.hours_above_ref, 0);
  const aboveEmpty = rooms.reduce((s, r) => s + r.hours_above_ref_empty, 0);
  const empty = D.findings.find((f) => f.id === "empty");
  $("kpis").innerHTML = [
    [num(typical), "Bq/m³", `typical level with somebody at home (mean of all rooms); reference level ${ov.reference}`],
    [empty ? `${num(empty.ratio_range[0], 1)}–${num(empty.ratio_range[1], 0)}×` : "–", "", `the usual radon level in every room while nobody was home (${ov.empty_days.length} days)`],
    [num(above), "room-hours", `above ${ov.reference} Bq/m³ – ${num(100 * aboveEmpty / Math.max(above, 1))} % of them while nobody was at home`],
    [`${D.findings.filter((f) => f.held).length}`, `of ${D.findings.length}`, "suspected effects hold up in the tests below"],
  ].map(([b, u, s]) => `<div class="kpi"><b>${b}${u ? `<small>${u}</small>` : ""}</b><span>${s}</span></div>`).join("");
}

// ---------------------------------------------------------------- room picker
function renderPicker() {
  $("rooms").innerHTML = rooms.map((r) =>
    `<button class="seg-btn" data-room="${r.room}" aria-pressed="${r.room === current}">${r.label}</button>`).join("");
}
$("rooms").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-room]");
  if (b) select(b.dataset.room);
});
function select(room) {
  current = room;
  renderPicker(); drawSeries(); drawProfile(); drawCompare(); drawTable();
}

// ---------------------------------------------------------------- daily time series
function drawSeries() {
  const svg = $("ts"); clear(svg);
  const W = 900, H = 300, L = 46, R = 16, T = 18, B = 26;
  const dates = D.daily.dates, s = D.daily.rooms[current];
  const n = dates.length;
  const x = (i) => L + (W - L - R) * i / (n - 1);
  const { top, step } = niceMax(Math.max(ov.reference * 1.1, ...s.max.filter((v) => v != null)), 5);
  const y = (v) => T + (H - T - B) * (1 - v / top);
  $("ts-title").textContent = `Daily radon · ${label[current]}`;
  const r = rooms.find((q) => q.room === current);
  $("ts-note").textContent = `${num(r.hours)} hours of data · max ${num(r.max)} Bq/m³`;

  dates.forEach((d, i) => {   // nobody at home: shaded days
    if (emptySet.has(d)) el("rect", { x: x(i) - (W - L - R) / (n - 1) / 2, y: T, width: (W - L - R) / (n - 1), height: H - T - B, class: "empty" }, svg);
  });
  yAxis(svg, { L, R, W, y, top, step, unit: "Bq/m³" });
  dates.forEach((d, i) => {   // month ticks
    if (d.endsWith("-01")) {
      el("line", { x1: x(i), x2: x(i), y1: H - B, y2: H - B + 4, class: "axis" }, svg);
      el("text", { x: x(i) + 3, y: H - B + 16 }, svg).textContent = MONTHS[+d.slice(5, 7) - 1];
    }
  });
  // min-max band and mean line, broken where a day has no data
  const runs = []; let cur = [];
  s.mean.forEach((v, i) => { if (v == null) { if (cur.length) runs.push(cur); cur = []; } else cur.push(i); });
  if (cur.length) runs.push(cur);
  for (const run of runs) {
    const up = run.map((i) => `${x(i)},${y(s.max[i])}`), down = run.slice().reverse().map((i) => `${x(i)},${y(s.min[i])}`);
    el("polygon", { points: up.concat(down).join(" "), class: "band" }, svg);
    el("polyline", { points: run.map((i) => `${x(i)},${y(s.mean[i])}`).join(" "), class: "series c1" }, svg);
  }
  for (const [v, cls, txt] of [[ov.reference, "ref", `${ov.reference} reference level`], [ov.who, "ref2", `${ov.who} WHO`]]) {
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: cls }, svg);
    el("text", { x: W - R - 4, y: y(v) - 5, "text-anchor": "end", class: cls === "ref" ? "reflbl" : "" }, svg).textContent = txt;
  }
  crosshair(svg, { L, R, T, B, W, H, n, x, onIndex: (i) => {
    if (s.mean[i] == null) return null;
    const temp = D.daily.out_temp[i];
    return { y: y(s.mean[i]), text: `${fmtDate(dates[i])}${emptySet.has(dates[i]) ? " · nobody home" : ""}\n` +
      `mean ${num(s.mean[i])} Bq/m³\nrange ${num(s.min[i])} – ${num(s.max[i])}` + (temp != null ? `\noutdoor ${num(temp, 1)} °C` : "") };
  } });
}

function crosshair(svg, { L, R, T, B, W, H, n, x, onIndex }) {
  const line = el("line", { y1: T, y2: H - B, class: "cross", visibility: "hidden" }, svg);
  const dot = el("circle", { r: 4.5, class: "dot1", visibility: "hidden" }, svg);
  const hit = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, class: "hit", style: "cursor:crosshair" }, svg);
  const tipEl = $("tip");
  hit.addEventListener("pointermove", (e) => {
    const box = svg.getBoundingClientRect();
    const px = (e.clientX - box.left) * W / box.width;
    const i = Math.max(0, Math.min(n - 1, Math.round((px - L) / (W - L - R) * (n - 1))));
    const info = onIndex(i);
    if (!info) { hideTip(); dot.setAttribute("visibility", "hidden"); return; }
    line.setAttribute("x1", x(i)); line.setAttribute("x2", x(i)); line.setAttribute("visibility", "visible");
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", info.y); dot.setAttribute("visibility", "visible");
    tipEl.textContent = info.text; tipEl.hidden = false;
    tipEl.style.left = Math.min(e.clientX + 14, innerWidth - tipEl.offsetWidth - 8) + "px";
    tipEl.style.top = Math.min(e.clientY + 14, innerHeight - tipEl.offsetHeight - 8) + "px";
  });
  hit.addEventListener("pointerleave", () => { line.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); hideTip(); });
}

// ---------------------------------------------------------------- hourly profile
function drawProfile() {
  const svg = $("hp"); clear(svg);
  const W = 560, H = 240, L = 40, R = 12, T = 18, B = 24;
  const v = D.hourly_profile[current];
  const { top, step } = niceMax(Math.max(...v) * 1.05, 4);
  const x = (i) => L + (W - L - R) * i / 23, y = (q) => T + (H - T - B) * (1 - q / top);
  $("hp-title").textContent = `Over the day · ${label[current]}`;
  yAxis(svg, { L, R, W, y, top, step, unit: "Bq/m³" });
  for (let i = 0; i < 24; i += 3) el("text", { x: x(i), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = `${String(i).padStart(2, "0")}:00`;
  el("polyline", { points: v.map((q, i) => `${x(i)},${y(q)}`).join(" "), class: "series c1" }, svg);
  const hi = v.indexOf(Math.max(...v)), lo = v.indexOf(Math.min(...v));
  for (const [i, t] of [[hi, "peak"], [lo, "low"]]) {
    el("circle", { cx: x(i), cy: y(v[i]), r: 4, class: "dot1" }, svg);
    el("text", { x: x(i), y: y(v[i]) + (t === "peak" ? -9 : 16), "text-anchor": "middle", class: "lbl" }, svg)
      .textContent = `${t} ${num(v[i])} at ${String(i).padStart(2, "0")}:00`;
  }
  crosshair(svg, { L, R, T, B, W, H, n: 24, x, onIndex: (i) => ({ y: y(v[i]), text: `${String(i).padStart(2, "0")}:00 – ${String(i + 1).padStart(2, "0")}:00\nmean ${num(v[i], 1)} Bq/m³` }) });
}

// ---------------------------------------------------------------- rooms compared
function drawCompare() {
  const svg = $("cmp"); clear(svg);
  const W = 560, L = 150, R = 70, rowH = 30, T = 4;
  const rows = rooms.slice().sort((a, b) => b.mean - a.mean);
  const H = T + rows.length * rowH + 4;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const max = Math.max(...rows.map((r) => r.mean));
  rows.forEach((r, i) => {
    const y0 = T + i * rowH, w = Math.max(2, (W - L - R) * r.mean / max);
    el("text", { x: L - 10, y: y0 + 19, "text-anchor": "end", class: "rowlbl" }, svg).textContent = r.label;
    el("rect", { x: L, y: y0 + 7, width: w, height: 16, rx: 4, class: r.room === current ? "sel" : "f1" }, svg);
    el("text", { x: L + w + 6, y: y0 + 19, class: "lbl" }, svg).textContent = `${num(r.mean)} Bq/m³`;
    const hit = el("rect", { x: 0, y: y0, width: W, height: rowH, class: "hit" }, svg);
    tip(hit, `${r.label}\nmean ${num(r.mean, 1)} · median ${num(r.median, 1)}\n95th percentile ${num(r.p95)} · max ${num(r.max)}\n` +
      `${num(r.hours_above_ref)} h above ${ov.reference} (${num(r.hours_above_ref_empty)} while nobody was home)`);
    hit.addEventListener("click", () => select(r.room));
  });
}

// ---------------------------------------------------------------- finding cards and their small charts
function legendHtml(series) {
  return series.length < 2 ? "" :
    `<div class="legend">${series.map((s, k) => `<span><i class="k${k + 1}"></i>${s.name}</span>`).join("")}</div>`;
}

function hbars(svg, chart) {   // grouped horizontal bars, labels on the left (room names are long)
  const W = 400, L = 128, R = 52, T = 2, n = chart.series.length;
  const barH = 10, gap = 2, rowH = n * (barH + gap) + 10;
  const H = T + chart.labels.length * rowH;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const max = Math.max(...chart.series.flatMap((s) => s.values.filter((v) => v != null)), 1e-9);
  chart.labels.forEach((lab, i) => {
    const y0 = T + i * rowH;
    el("text", { x: L - 8, y: y0 + rowH / 2 - 1, "text-anchor": "end", class: "rowlbl" }, svg).textContent = lab;
    chart.series.forEach((s, k) => {
      const v = s.values[i]; if (v == null) return;
      const w = Math.max(2, (W - L - R) * v / max), y = y0 + 4 + k * (barH + gap);
      const bar = el("rect", { x: L, y, width: w, height: barH, rx: 3, class: `f${k + 1}` }, svg);
      el("text", { x: L + w + 5, y: y + barH - 1, class: "lbl" }, svg).textContent = num(v);
      tip(bar, `${lab}\n${s.name}: ${num(v, 1)} ${chart.unit || ""}`);
    });
  });
}

function lines(svg, chart) {
  const W = 400, H = 200, L = 36, R = 14, T = 14, B = 22;
  const n = chart.labels.length;
  const { top, step } = niceMax(Math.max(...chart.series.flatMap((s) => s.values.filter((v) => v != null))) * 1.05, 4);
  const x = (i) => L + (W - L - R) * i / (n - 1), y = (v) => T + (H - T - B) * (1 - v / top);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  yAxis(svg, { L, R, W, y, top, step });
  chart.labels.forEach((lab, i) => { el("text", { x: x(i), y: H - B + 15, "text-anchor": "middle" }, svg).textContent = lab; });
  chart.series.forEach((s, k) => {
    const pts = s.values.map((v, i) => (v == null ? null : [x(i), y(v)])).filter(Boolean);
    el("polyline", { points: pts.map((p) => p.join(",")).join(" "), class: `series c${k + 1}` }, svg);
    s.values.forEach((v, i) => {
      if (v == null) return;
      const c = el("circle", { cx: x(i), cy: y(v), r: 4, class: "dot1", style: `fill: var(--s${k + 1})` }, svg);
      tip(c, `${chart.labels[i]} · ${s.name}\n${num(v, 1)} ${chart.unit || ""}`);
    });
  });
}

function matrix(svg, chart, { rowLabels = chart.labels, colLabels = chart.labels, values = chart.values, faint = () => false,
  W = 400, L = 128, T = 34, cell = null, tipText } = {}) {
  const nC = colLabels.length, cw = cell || (W - L) / nC, ch = Math.min(30, cw * 0.62);
  const H = T + rowLabels.length * ch + 2;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  colLabels.forEach((lab, j) => {
    const parts = lab.replace(" (", "\n(").split("\n");
    parts.forEach((p, k) => el("text", { x: L + j * cw + cw / 2, y: T - 6 - (parts.length - 1 - k) * 11, "text-anchor": "middle" }, svg).textContent = p);
  });
  rowLabels.forEach((lab, i) => {
    el("text", { x: L - 8, y: T + i * ch + ch / 2 + 4, "text-anchor": "end", class: "rowlbl" }, svg).textContent = lab;
    colLabels.forEach((_, j) => {
      const v = values[i][j];
      const weak = faint(i, j);
      const share = v == null ? 0 : Math.round(Math.min(1, Math.abs(v)) * (weak ? 30 : 85));
      const color = v != null && v < 0 ? "var(--s2)" : "var(--s1)";
      const r = el("rect", { x: L + j * cw + 1, y: T + i * ch + 1, width: cw - 2, height: ch - 2, rx: 4,
        style: `fill: color-mix(in srgb, ${color} ${share}%, var(--bg-2))` }, svg);
      const t = el("text", { x: L + j * cw + cw / 2, y: T + i * ch + ch / 2 + 3.5, "text-anchor": "middle",
        class: `cell${weak ? " faint" : ""}`, style: !weak && Math.abs(v) > 0.55 ? "fill: var(--surface)" : "" }, svg);
      t.textContent = v == null ? "–" : v.toFixed(2).replace("-", "−");
      if (tipText) tip(r, tipText(i, j));
    });
  });
}

function findingCard(f) {
  const card = document.createElement("article");
  card.className = `panel finding${f.held ? "" : " weak"}`;
  const s = f.stat;
  const statParts = [`${s.name}: <b>${s.value == null ? "–" : num(s.value, 2)}</b>`, fmtP(s.p), `n = ${num(s.n)} ${s.unit}`].filter(Boolean);
  card.innerHTML = `<span class="badge${f.held ? " held" : ""}">${f.held ? "holds" : "not supported"}</span>
    <h3>${f.title}</h3><p>${f.statement}</p>
    ${f.chart ? `<svg class="chart" role="img" aria-label="${f.title}"></svg>${f.chart.type === "matrix" ? "" : legendHtml(f.chart.series)}` : ""}
    <div class="stat-line">${statParts.join(" · ")}</div>
    <details><summary>How it was tested</summary><p>${f.method}</p></details>`;
  if (f.chart) {
    const svg = card.querySelector("svg");
    if (f.chart.type === "bars") hbars(svg, f.chart);
    else if (f.chart.type === "lines") lines(svg, f.chart);
    else if (f.chart.type === "matrix") matrix(svg, f.chart, {
      faint: (i, j) => i === j, tipText: (i, j) => `${f.chart.labels[i]} × ${f.chart.labels[j]}\nρ = ${f.chart.values[i][j]}`,
    });
  }
  return card;
}
const isStrong = (f) => f.held && !f.negative;
D.findings.filter(isStrong).forEach((f) => $("findings").appendChild(findingCard(f)));
D.findings.filter((f) => !isStrong(f)).forEach((f) => $("weak").appendChild(findingCard(f)));

// ---------------------------------------------------------------- driver correlation heat map
{
  const C = D.correlations;
  const cell = Object.fromEntries(C.cells.map((c) => [`${c.driver}|${c.room}`, c]));
  const values = C.drivers.map((d) => C.rooms.map((r) => cell[`${d.key}|${r.key}`]?.rho ?? null));
  matrix($("heat"), null, {
    rowLabels: C.drivers.map((d) => d.label), colLabels: C.rooms.map((r) => r.label), values,
    W: 900, L: 210, T: 40, faint: (i, j) => !cell[`${C.drivers[i].key}|${C.rooms[j].key}`]?.held,
    tipText: (i, j) => {
      const c = cell[`${C.drivers[i].key}|${C.rooms[j].key}`];
      return `${C.drivers[i].label} × ${C.rooms[j].label}\nρ = ${c.rho ?? "–"} · ${fmtP(c.p)}\nn = ${c.n} days\n${c.held ? "clear link" : "no clear link"}`;
    },
  });
}

// ---------------------------------------------------------------- table + method
function drawTable() {
  $("table").innerHTML = `<tr><th>Room</th><th>Mean</th><th>Median</th><th>95th pct.</th><th>Max</th>` +
    `<th>h &gt; ${ov.who}</th><th>h &gt; ${ov.reference}</th><th>of them nobody home</th><th>Data from</th></tr>` +
    rooms.map((r) => `<tr class="${r.room === current ? "sel" : ""}"><td>${r.label}</td><td>${num(r.mean, 1)}</td><td>${num(r.median, 1)}</td>` +
      `<td>${num(r.p95)}</td><td>${num(r.max)}</td><td>${num(r.hours_above_who)}</td><td>${num(r.hours_above_ref)}</td>` +
      `<td>${num(r.hours_above_ref_empty)}</td><td>${r.first}</td></tr>`).join("");
}
$("table-note").textContent = `Bq/m³, hourly means. ${ov.reference} Bq/m³ is the reference level of the Austrian radon ordinance ` +
  `(EU directive 2013/59/Euratom); the WHO recommends ${ov.who} Bq/m³.`;
{
  const warm = rooms.reduce((s, r) => s + (r.cleaning.warmup || 0), 0), drop = rooms.reduce((s, r) => s + (r.cleaning.dropouts || 0), 0);
  const total = rooms.reduce((s, r) => s + (r.cleaning.readings || 0), 0);
  $("method").innerHTML = [
    `${num(total)} radon readings (about one per sensor every 10 min); ${num(warm)} taken in the first hour after a sensor restart were dropped, ` +
      `as were ${num(drop)} 0-dropouts between high readings. Zeros in low-radon rooms are kept: they are real.`,
    "All sensors and the hourly weather are averaged onto one hourly grid; a day counts if it has at least 18 hours of data.",
    `“Nobody at home” = days on which neither CO₂ sensor varies by more than 100 ppm (people always move CO₂): ${ov.empty_days.map(fmtDate).join(", ")}. ` +
      "These days are left out of the weather links so the one event does not dominate them.",
    `Zones are found by clustering the rooms by how strongly their radon moves together: ${ov.zones.map((z) => `${z.name} (${z.rooms.map((r) => label[r]).join(", ")})`).join("; ")}.`,
    `Code: ${sourceLink("analysis/radon/findings.py", "analysis/radon/findings.py")} (tests, findings) · ${sourceLink("analysis/radon/clean.py", "clean.py")} · ` +
      `${sourceLink("analysis/run_analysis.py", "run_analysis.py")}.`,
  ].map((t) => `<li>${t}</li>`).join("");
}

renderPicker(); drawSeries(); drawProfile(); drawCompare(); drawTable();
