// Web worker that runs the real Python network (part1_2_python/nn) in Pyodide, CPython compiled to
// WebAssembly. It runs off the main thread, so training 20000 epochs does not freeze the page.
importScripts("https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js");

let current = null;   // id of the request whose stdout is streamed (training progress)

const ready = (async () => {
  const py = await loadPyodide();
  await py.loadPackage("numpy");
  const fetchText = async (url) => {
    const res = await fetch(url);
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

onmessage = async ({ data: { id, fn, args } }) => {
  try {
    const { py, version } = await ready;
    if (fn === "init") return postMessage({ id, result: version });
    if (fn === "load") {   // args: [name, url of the exported JSON]
      const res = await fetch(args[1]);
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
    postMessage({ id, error: String(err.message || err) });
  }
};
