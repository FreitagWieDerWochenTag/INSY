// Shared drawing code for all pages. It only draws results that a real implementation computed
// (Python via Pyodide, C via WebAssembly, TensorFlow.js); there is no forward pass in this file.

export const SEGMENTS = "ABCDEFG";
// Standard 7-segment patterns, only used to name the pattern the net produced (not for computing it)
export const PATTERNS = { "1111110": 0, "0110000": 1, "1101101": 2, "1111001": 3, "0110011": 4,
                          "1011011": 5, "1011111": 6, "1110000": 7, "1111111": 8, "1111011": 9 };
export const THRESHOLD = 0.5;
const SVGNS = "http://www.w3.org/2000/svg";
export const $ = (id) => document.getElementById(id);
export const fmt = (v) => (v >= 0 ? " " : "") + v.toFixed(4);
export const toBits = (d, n = 4) => Array.from({ length: n }, (_, i) => (d >> (n - 1 - i)) & 1);
export const toValue = (bits) => bits.reduce((acc, b) => acc * 2 + b, 0);
export const segmentsOf = (output) => output.map((v) => (v >= THRESHOLD ? 1 : 0));

export function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

// ---------- source links ----------
// On GitHub Pages (<owner>.github.io/<repo>/NN/...) the repo is derived from the URL.
const FALLBACK_REPO = "https://github.com/187hahaxd/INSY";
export function sourceUrl(path) {
  const host = location.hostname;
  let repo = FALLBACK_REPO;
  if (host.endsWith(".github.io")) {
    const name = location.pathname.split("/").filter(Boolean)[0];
    if (name) repo = `https://github.com/${host.split(".")[0]}/${name}`;
  }
  return `${repo}/blob/main/NN/${path}`;
}
export function sourceLink(path, label) {
  return `<a href="${sourceUrl(path)}" target="_blank" rel="noopener"><code>${label || path}</code></a>`;
}

// ---------- page frame ----------
const PAGES = [
  ["index.html", "Overview", ""],
  ["part1-2.html", "Parts 1+2", "Python"],
  ["part3.html", "Part 3", "TensorFlow"],
  ["part4-5.html", "Parts 4+5", "C"],
  ["part6.html", "Part 6", "ESP32"],
];
export function frame() {
  const here = location.pathname.split("/").pop() || "index.html";
  const bar = document.createElement("nav");
  bar.className = "topbar";
  bar.setAttribute("aria-label", "Parts");
  bar.innerHTML = `<div class="topbar-inner">
      <a class="brand" href="index.html"><svg viewBox="0 0 120 200" aria-hidden="true">${
        Object.entries(SEG_SHAPES).map(([s, p]) => `<polygon points="${p}" fill="${"BCFG".includes(s) ? "var(--led)" : "var(--line)"}"/>`).join("")
      }</svg>BCD Decoder Net</a>
      <div class="tabs">${PAGES.map(([href, label, tech]) =>
        `<a class="tab" href="${href}"${href === here ? ' aria-current="page"' : ""}>${label}${tech ? `<small>${tech}</small>` : ""}</a>`).join("")}</div>
    </div>`;
  document.body.prepend(bar);
  if (!$("tip")) {
    const t = document.createElement("div");
    t.id = "tip"; t.hidden = true;
    document.body.appendChild(t);
  }
}

export function setStatus(id, state, text) {
  const s = $(id);
  s.classList.remove("ready", "error");
  if (state) s.classList.add(state);
  s.querySelector(".status-text").textContent = text;
}

// ---------- tooltip ----------
export function showTip(e, text) {
  const t = $("tip");
  t.textContent = text; t.hidden = false;
  const x = Math.min(e.clientX + 14, innerWidth - t.offsetWidth - 8);
  const y = Math.min(e.clientY + 14, innerHeight - t.offsetHeight - 8);
  t.style.left = x + "px"; t.style.top = y + "px";
}
export function hideTip() { $("tip").hidden = true; }

// ---------- input controls: bit switches + digit keys ----------
export class InputPanel {
  constructor({ bitsBox, keysBox, codeBox, nBits = 4, maxKey = 15, trained = 9, start = 5, onChange }) {
    this.n = nBits; this.onChange = onChange; this.trained = trained;
    this.bits = toBits(start, nBits);
    this.bitsBox = bitsBox; this.keysBox = keysBox; this.codeBox = codeBox;
    bitsBox.innerHTML = ""; keysBox.innerHTML = "";
    bitsBox.classList.toggle("two", nBits === 2);
    const weights = Array.from({ length: nBits }, (_, i) => 2 ** (nBits - 1 - i));
    this.bitButtons = weights.map((w, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "bit";
      b.innerHTML = `<span class="weight">${nBits === 4 ? w : "x" + i}</span><span class="track"></span><span class="value">0</span>`;
      b.addEventListener("click", () => { this.bits[i] ^= 1; this.changed(); });
      bitsBox.appendChild(b);
      return b;
    });
    this.keys = [];
    for (let d = 0; d <= maxKey; d++) {
      const k = document.createElement("button");
      k.type = "button"; k.className = "key" + (d > trained ? " untrained" : "");
      k.textContent = nBits === 4 ? d : toBits(d, nBits).join("");
      k.title = d > trained ? "not in the training data" : "input " + d;
      k.addEventListener("click", () => { this.bits = toBits(d, nBits); this.changed(); });
      keysBox.appendChild(k);
      this.keys.push(k);
    }
    this.render();
  }
  get value() { return toValue(this.bits); }
  changed() { this.render(); this.onChange(this.bits.slice()); }
  render() {
    this.bits.forEach((b, i) => {
      this.bitButtons[i].setAttribute("aria-pressed", b ? "true" : "false");
      this.bitButtons[i].querySelector(".value").textContent = b;
    });
    this.keys.forEach((k, d) => k.classList.toggle("current", d === this.value));
    if (this.codeBox) this.codeBox.innerHTML = `input <strong>[${this.bits.join(", ")}]</strong>` +
      (this.n === 4 ? ` = <strong>${this.value}</strong>` : "") +
      (this.value > this.trained ? ` <span class="warn">· not trained</span>` : "");
  }
}

// ---------- network graph ----------
// net: {layer_sizes, activation, layers: [{neurons: [{weights, bias}]}]} (the JSON export format)
// result: {inputs, layers: [[{z, a}]], output} as returned by an engine
export class NetView {
  constructor(svg, { inputLabels, outputLabels } = {}) {
    this.svg = svg; this.inputLabels = inputLabels; this.outputLabels = outputLabels;
    this.net = null; this.last = null;
  }
  layout(sizes) {
    const H = 470, top = 38, bottom = 20, xs = [70, 320, 560];
    return sizes.map((n, l) => {
      const step = (H - top - bottom) / n;
      return Array.from({ length: n }, (_, i) => ({ x: xs[l], y: top + step * (i + 0.5) }));
    });
  }
  build(net) {
    this.net = net; this.last = null;
    const svg = this.svg;
    svg.innerHTML = "";
    const pos = this.layout(net.layer_sizes);
    const names = ["input", "hidden", "output"];
    pos.forEach((col, l) => el("text", { x: col[0].x, y: 16, "text-anchor": "middle", class: "layer" }, svg).textContent =
      `${names[l] || "layer " + l} · ${col.length}`);
    const edgeGroups = [], nodeGroups = [];
    this.edges = []; this.nodes = [];
    net.layers.forEach((layer, l) => {
      const g = el("g", { "data-stage": l + 1 }, svg);
      edgeGroups.push(g);
      const maxW = Math.max(...layer.neurons.flatMap((n) => n.weights.map(Math.abs)));
      this.edges[l] = layer.neurons.map((n, j) => n.weights.map((w, i) => {
        const a = pos[l][i], b = pos[l + 1][j];
        const p = el("path", {
          d: `M${a.x},${a.y} C${(a.x + b.x) / 2},${a.y} ${(a.x + b.x) / 2},${b.y} ${b.x},${b.y}`,
          class: "edge " + (w >= 0 ? "pos" : "neg"),
          "stroke-width": (0.4 + 3.2 * Math.abs(w) / maxW).toFixed(2), "stroke-opacity": 0.15,
        }, g);
        p.addEventListener("pointermove", (e) => this.last && showTip(e, this.edgeTip(l, j, i)));
        p.addEventListener("pointerleave", hideTip);
        return p;
      }));
    });
    const r = [13, 11, 13];
    pos.forEach((col, l) => {
      const g = el("g", { "data-stage": l }, svg);
      nodeGroups.push(g);
      this.nodes[l] = col.map((p, i) => {
        const node = el("g", { class: "node", tabindex: 0 }, g);
        el("circle", { cx: p.x, cy: p.y, r: r[l] ?? 11, class: "ring" }, node);
        const fill = el("circle", { cx: p.x, cy: p.y, r: (r[l] ?? 11) - 3, class: "fill", "fill-opacity": 0 }, node);
        if (l === 0) el("text", { x: p.x - 22, y: p.y + 4, "text-anchor": "end" }, g).textContent = this.inputLabel(i);
        if (l === pos.length - 1) el("text", { x: p.x + 22, y: p.y + 5, class: "seg" }, g).textContent = this.outputLabel(i);
        node.addEventListener("pointermove", (e) => this.last && showTip(e, this.nodeTip(l, i)));
        node.addEventListener("pointerleave", hideTip);
        node.addEventListener("focus", () => {
          if (!this.last) return;
          const b = node.getBoundingClientRect();
          showTip({ clientX: b.right, clientY: b.top }, this.nodeTip(l, i));
        });
        node.addEventListener("blur", hideTip);
        return fill;
      });
    });
    this.stages = nodeGroups.flatMap((g, i) => (edgeGroups[i] ? [g, edgeGroups[i]] : [g]));
  }
  inputLabel(i) {
    if (this.inputLabels) return this.inputLabels[i];
    return this.net.layer_sizes[0] === 4 ? `x${i} (${[8, 4, 2, 1][i]})` : "x" + i;
  }
  outputLabel(i) {
    if (this.outputLabels) return this.outputLabels[i];
    return this.net.layer_sizes.at(-1) === 7 ? SEGMENTS[i] : "y" + i;
  }
  activation(l, i) { return l === 0 ? this.last.inputs[i] : this.last.layers[l - 1][i].a; }
  render(result) {
    this.last = result;
    this.nodes.forEach((col, l) => col.forEach((fill, i) => fill.setAttribute("fill-opacity", this.activation(l, i).toFixed(3))));
    this.net.layers.forEach((layer, l) => {
      const flows = layer.neurons.map((n) => n.weights.map((w, i) => Math.abs(w * this.activation(l, i))));
      const maxFlow = Math.max(1e-9, ...flows.flat());
      this.edges[l].forEach((row, j) => row.forEach((p, i) =>
        p.setAttribute("stroke-opacity", (0.05 + 0.9 * flows[j][i] / maxFlow).toFixed(3))));
    });
  }
  nodeTip(l, i) {
    if (l === 0) return `input ${this.inputLabel(i)}\nvalue  ${this.last.inputs[i]}`;
    const n = this.net.layers[l - 1].neurons[i], s = this.last.layers[l - 1][i];
    const name = l === this.net.layers.length ? `output ${this.outputLabel(i)}` : `hidden h${i}`;
    return `${name}\nbias        ${fmt(n.bias)}\nz = Σw·a+b  ${fmt(s.z)}\n${(this.net.activation || "sigmoid").padEnd(12)}${fmt(s.a)}`;
  }
  edgeTip(l, j, i) {
    const w = this.net.layers[l].neurons[j].weights[i], a = this.activation(l, i);
    const from = l === 0 ? `x${i}` : `h${i}`, to = l === this.net.layers.length - 1 ? this.outputLabel(j) : `h${j}`;
    return `${from} → ${to}\nweight w    ${fmt(w)}\ninput a     ${fmt(a)}\nw · a       ${fmt(w * a)}`;
  }
  async animate() {
    if (!this.stages || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    this.stages.forEach((g) => g.classList.add("stage-hidden"));
    for (const g of this.stages) {
      g.classList.remove("stage-hidden");
      await new Promise((r) => setTimeout(r, 380));
    }
  }
}

// ---------- 7-segment display ----------
export const SEG_SHAPES = {   // viewBox 0 0 120 200
  A: "22,10 98,10 88,22 32,22",
  B: "100,13 110,23 110,92 100,98 90,90 90,25",
  C: "100,102 110,108 110,177 100,187 90,175 90,110",
  D: "32,178 88,178 98,190 22,190",
  E: "20,102 30,110 30,175 20,187 10,177 10,108",
  F: "20,13 30,25 30,90 20,98 10,92 10,23",
  G: "30,94 90,94 98,100 90,106 30,106 22,100",
};
export class SegDisplay {
  constructor(svg, readout, table) {
    this.readout = readout; this.table = table;
    this.segs = [...SEGMENTS].map((s) => el("polygon", { points: SEG_SHAPES[s], fill: "var(--led)", "fill-opacity": 0.08 }, svg));
    if (table) {
      table.innerHTML = [...SEGMENTS].map((s) =>
        `<tr><td>${s}</td><td class="bar-cell"><div class="bar"><b style="width:0"></b></div></td><td>–</td></tr>`).join("");
      this.rows = [...table.querySelectorAll("tr")];
    }
  }
  render(output) {
    output.forEach((v, i) => {
      this.segs[i].setAttribute("fill-opacity", (0.07 + 0.93 * v).toFixed(3));
      if (this.rows) {
        this.rows[i].querySelector("b").style.width = (v * 100).toFixed(1) + "%";
        this.rows[i].lastElementChild.textContent = v.toFixed(2);
      }
    });
    const pattern = segmentsOf(output).join("");
    const digit = PATTERNS[pattern];
    if (this.readout) this.readout.innerHTML = `segments ≥ 0.5: ${pattern}<br>` +
      (digit !== undefined ? `shows <strong>${digit}</strong>` : `<strong>no valid digit</strong>`);
  }
}

// ---------- loss chart (log scale) ----------
// series: [{key, label, short, epochs: [...], values: [...]}]
export function lossChart(svg, series, { maxEpoch, onHover = true } = {}) {
  svg.innerHTML = "";
  const L = 52, R = 150, T = 12, B = 30, W = 560, H = 260;
  const all = series.flatMap((s) => s.values).filter((v) => v > 0);
  if (!all.length) return;
  const lo = Math.floor(Math.log10(Math.min(...all))), hi = Math.max(lo + 1, Math.ceil(Math.log10(Math.max(...all))));
  const last = maxEpoch || Math.max(...series.flatMap((s) => s.epochs));
  const x = (e) => L + (W - L - R) * (e - 1) / Math.max(1, last - 1);
  const y = (v) => T + (H - T - B) * (hi - Math.log10(Math.max(v, 10 ** lo))) / (hi - lo);
  for (let p = lo; p <= hi; p++) {
    el("line", { x1: L, x2: W - R, y1: y(10 ** p), y2: y(10 ** p), class: "grid" }, svg);
    el("text", { x: L - 6, y: y(10 ** p) + 3, "text-anchor": "end" }, svg).textContent = "1e" + p;
  }
  [0, 0.25, 0.5, 0.75, 1].map((f) => Math.max(1, Math.round(last * f))).forEach((e) =>
    el("text", { x: x(e), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = e >= 1000 ? e / 1000 + "k" : e);
  el("text", { x: (L + W - R) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "epoch";
  const ends = [];
  series.forEach((s) => {
    if (!s.values.length) return;
    el("path", { class: "series s-" + s.key, d: s.values.map((v, i) => (i ? "L" : "M") + x(s.epochs[i]).toFixed(1) + "," + y(v).toFixed(1)).join("") }, svg);
    ends.push({ s, y: y(s.values.at(-1)) });
  });
  // direct labels at the line ends, nudged apart so they don't overlap
  ends.sort((a, b) => a.y - b.y).forEach((e, i, arr) => { if (i && e.y - arr[i - 1].y < 12) e.y = arr[i - 1].y + 12; });
  ends.forEach((e) => el("text", { x: W - R + 6, y: e.y + 3, class: "lbl" }, svg).textContent = e.s.short);
  if (!onHover) return;
  const cross = el("line", { y1: T, y2: H - B, class: "cross", visibility: "hidden" }, svg);
  const hit = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: "transparent" }, svg);
  hit.addEventListener("pointermove", (evt) => {
    const box = svg.getBoundingClientRect();
    const sx = (evt.clientX - box.left) * W / box.width;
    const ep = series[0].epochs;
    let i = 0;
    while (i < ep.length - 1 && x(ep[i + 1]) <= sx) i++;
    cross.setAttribute("x1", x(ep[i])); cross.setAttribute("x2", x(ep[i])); cross.setAttribute("visibility", "visible");
    showTip(evt, `epoch ${ep[i]}\n` + series.filter((s) => s.values[i] !== undefined)
      .map((s) => `${s.short.padEnd(14)}${s.values[i].toExponential(2)}`).join("\n"));
  });
  hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
}

export async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status} ${res.statusText}`);
  return res.json();
}
export async function getText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status} ${res.statusText}`);
  return res.text();
}
