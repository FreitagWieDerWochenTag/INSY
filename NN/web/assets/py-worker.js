// Module web worker that runs the real Python network (part1_2_python/nn) in Pyodide, CPython compiled to
// WebAssembly. It runs off the main thread, so training 20000 epochs does not freeze the page.
// Pyodide is served from our own site (build/pyodide, see build.sh): Safari refuses to load it from a CDN here.
// Messages to the page: {progress} while starting, {id, result | error | stdout} for calls.
import { loadPyodide } from "../build/pyodide/pyodide.mjs";

let current = null;   // id of the request whose stdout is streamed (training progress)
const progress = (text) => postMessage({ progress: text });

const ready = (async () => {
  progress("downloading Python (Pyodide, about 12 MB the first time)…");
  const py = await loadPyodide({ indexURL: new URL("../build/pyodide/", import.meta.url).href });
  progress("loading NumPy…");
  await py.loadPackage("numpy");
  progress("loading the nn package…");
  const fetchText = async (url) => {
    const res = await fetch(new URL(url, import.meta.url));
    if (!res.ok) throw new Error(`${url}: ${res.status}`);
    return res.text();
  };
  const files = JSON.parse(await fetchText("../build/py/files.json"));
  py.FS.mkdirTree("/home/pyodide/nn");
  py.FS.mkdirTree("/home/pyodide/models");
  for (const f of files) py.FS.writeFile(`/home/pyodide/nn/${f}`, await fetchText(`../build/py/nn/${f}`));
  py.setStdout({ batched: (line) => current !== null && postMessage({ id: current, stdout: line }) });
  py.runPython(await fetchText("web_api.py"));
  return { py, version: py.runPython("import sys, numpy; f'Python {sys.version.split()[0]} · NumPy {numpy.__version__}'") };
})();
ready.catch((err) => postMessage({ fatal: String(err?.message || err) }));

onmessage = async ({ data: { id, fn, args } }) => {
  try {
    const { py, version } = await ready;
    if (fn === "init") return postMessage({ id, result: version });
    if (fn === "load") {   // args: [name, url of the exported JSON, relative to the page]
      const res = await fetch(new URL(args[1], new URL("../", import.meta.url)));
      if (!res.ok) throw new Error(`${args[1]}: ${res.status}`);
      const path = `/home/pyodide/models/${args[0]}.json`;
      py.FS.writeFile(path, await res.text());
      args = [args[0], path];
    }
    current = id;
    const result = py.globals.get(fn)(...args);
    current = null;
    postMessage({ id, result: JSON.parse(result) });
  } catch (err) {
    current = null;
    postMessage({ id, error: String(err?.message || err) });
  }
};
