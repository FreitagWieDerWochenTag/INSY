// Shared helpers of the Radon pages: page frame, source links, tooltip, SVG elements, fetching.
// Every number drawn comes from the JSON written by the Python analysis (Radon/analysis); nothing is computed here
// except scaling for the charts.

const SVGNS = "http://www.w3.org/2000/svg";
export const $ = (id) => document.getElementById(id);

export function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

// ---------- source links ----------
// On GitHub Pages (<owner>.github.io/<repo>/Radon/...) the repo is derived from the URL.
const FALLBACK_REPO = "https://github.com/FreitagWieDerWochenTag/INSY";
export function sourceUrl(path) {
  const host = location.hostname;
  let repo = FALLBACK_REPO;
  if (host.endsWith(".github.io")) {
    const name = location.pathname.split("/").filter(Boolean)[0];
    if (name) repo = `https://github.com/${host.split(".")[0]}/${name}`;
  }
  return `${repo}/blob/main/Radon/${path}`;
}
export function sourceLink(path, label) {
  return `<a href="${sourceUrl(path)}" target="_blank" rel="noopener"><code>${label || path}</code></a>`;
}

// ---------- page frame ----------
const PAGES = [
  ["index.html", "Dashboard", ""],
  ["log.html", "Log", "tokens & cost"],
];
export function frame() {
  const here = location.pathname.split("/").pop() || "index.html";
  const bar = document.createElement("nav");
  bar.className = "topbar";
  bar.setAttribute("aria-label", "Pages");
  // On GitHub Pages the project sits below the INSY start page
  const up = location.hostname.endsWith(".github.io") ? `<a class="tab up" href="../">INSY</a>` : "";
  bar.innerHTML = `<div class="topbar-inner">
      ${up}<a class="brand" href="index.html">Radon</a>
      <div class="tabs">${PAGES.map(([href, label, sub]) =>
        `<a class="tab" href="${href}"${href === here ? ' aria-current="page"' : ""}>${label}${sub ? `<small>${sub}</small>` : ""}</a>`).join("")}</div>
    </div>`;
  document.body.prepend(bar);
  if (!$("tip")) {
    const t = document.createElement("div");
    t.id = "tip"; t.hidden = true;
    document.body.appendChild(t);
  }
}

// ---------- tooltip ----------
export function showTip(e, text) {
  const t = $("tip");
  t.textContent = text; t.hidden = false;
  t.style.left = Math.min(e.clientX + 14, innerWidth - t.offsetWidth - 8) + "px";
  t.style.top = Math.min(e.clientY + 14, innerHeight - t.offsetHeight - 8) + "px";
}
export function hideTip() { $("tip").hidden = true; }
export function tip(node, text) {
  node.addEventListener("pointermove", (e) => showTip(e, typeof text === "function" ? text() : text));
  node.addEventListener("pointerleave", hideTip);
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
