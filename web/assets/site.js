// General site of the INSY repo (landing page, design, general prompt log). Projects have their own sites.
export const $ = (id) => document.getElementById(id);
const SVGNS = "http://www.w3.org/2000/svg";
export function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

// On GitHub Pages (<owner>.github.io/<repo>/) the repo is derived from the URL.
export function repoUrl(path) {
  let repo = "https://github.com/FreitagWieDerWochenTag/INSY";
  if (location.hostname.endsWith(".github.io")) {
    const name = location.pathname.split("/").filter(Boolean)[0];
    if (name) repo = `https://github.com/${location.hostname.split(".")[0]}/${name}`;
  }
  return `${repo}/blob/main/${path}`;
}
export const sourceLink = (path, label) =>
  `<a href="${repoUrl(path)}" target="_blank" rel="noopener"><code>${label || path}</code></a>`;

const PAGES = [["index.html", "Home"], ["design.html", "Design"], ["log.html", "Prompt log"]];
const PROJECTS = [["NN/", "NN", "neural network"]];
export function frame() {
  const here = location.pathname.split("/").pop() || "index.html";
  const bar = document.createElement("nav");
  bar.className = "topbar";
  bar.setAttribute("aria-label", "INSY");
  bar.innerHTML = `<div class="topbar-inner">
      <a class="brand" href="index.html">INSY</a>
      <div class="tabs">${PAGES.map(([href, label]) =>
        `<a class="tab" href="${href}"${href === here ? ' aria-current="page"' : ""}>${label}</a>`).join("")}
        <span class="tab-sep" aria-hidden="true"></span>
        ${PROJECTS.map(([href, label, sub]) => `<a class="tab" href="${href}">${label}<small>${sub}</small></a>`).join("")}</div>
    </div>`;
  document.body.prepend(bar);
  if (!$("tip")) {
    const t = document.createElement("div");
    t.id = "tip"; t.hidden = true;
    document.body.appendChild(t);
  }
}

export function showTip(e, text) {
  const t = $("tip");
  t.textContent = text; t.hidden = false;
  t.style.left = Math.min(e.clientX + 14, innerWidth - t.offsetWidth - 8) + "px";
  t.style.top = Math.min(e.clientY + 14, innerHeight - t.offsetHeight - 8) + "px";
}
export function hideTip() { $("tip").hidden = true; }

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
export const esc = (t) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
