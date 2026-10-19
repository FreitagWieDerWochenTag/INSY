// The implementations the pages run. Each forward() returns {inputs, layers: [[{z, a}]], output, compute_ms}
// computed by the real code; the pages only draw it.
//   PyEngine   Parts 1+2  part1_2_python/nn, unchanged, in Pyodide (CPython + NumPy as WebAssembly)
//   CEngine    Parts 4+5  part4_5_c/nn_cli.c + lib/nn, compiled to WebAssembly with Emscripten
//   EspEngine  Part 6     part6_esp32/src/main.cpp (unchanged sketch) + Arduino mock, WebAssembly
//   TFEngine   Part 3     the trained Keras weights in TensorFlow.js (visualization only, see part3.html)

const scripts = {};
function loadScript(src) {
  scripts[src] ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src; s.onload = resolve; s.onerror = () => reject(new Error("could not load " + src));
    document.head.appendChild(s);
  });
  return scripts[src];
}

// ---------- Python in Pyodide (web worker) ----------
let pyWorker = null;
export class PyEngine {
  constructor() {
    if (!pyWorker) {
      pyWorker = { worker: new Worker("assets/py-worker.js"), next: 0, pending: new Map() };
      pyWorker.worker.onmessage = ({ data }) => {
        const p = pyWorker.pending.get(data.id);
        if (!p) return;
        if (data.stdout !== undefined) return p.onStdout?.(data.stdout);
        pyWorker.pending.delete(data.id);
        data.error !== undefined ? p.reject(new Error(data.error)) : p.resolve(data.result);
      };
    }
  }
  call(fn, args = [], onStdout) {
    return new Promise((resolve, reject) => {
      const id = pyWorker.next++;
      pyWorker.pending.set(id, { resolve, reject, onStdout });
      pyWorker.worker.postMessage({ id, fn, args });
    });
  }
  init() { return (this.version ??= this.call("init")); }
  load(name, url) { return this.call("load", [name, url]); }     // -> network dict (JSON export format)
  async forward(name, bits) {
    const r = await this.call("forward", [name, JSON.stringify(bits)]);
    return { inputs: bits, ...r };
  }
  predictAll(name, inputs) { return this.call("predict_all", [name, JSON.stringify(inputs)]); }
  // onProgress(epoch, mse) from the "epoch N  mse X" lines that NeuralNetwork.train(log_every) prints
  train(name, { dataset, epochs, learningRate, seed, logEvery, compareTo }, onProgress) {
    return this.call("train", [name, dataset, epochs, learningRate, seed, logEvery, compareTo || ""], (line) => {
      const m = line.match(/epoch\s+(\d+)\s+mse\s+([\d.eE+-]+)/);
      if (m) onProgress(+m[1], +m[2]);
    });
  }
}

// ---------- C (Parts 4/5) in WebAssembly ----------
// kind "txt": main(MODEL.txt, BITS) reads the .txt export from the virtual file system (Part 4)
// kind "h":   main(BITS) with the weights compiled in from models/7seg_net.h (Part 5)
export class CEngine {
  constructor(kind) { this.kind = kind; }
  init() {
    return (this.ready ??= (async () => {
      await loadScript(`build/wasm/nn_${this.kind}.js`);
      const factory = this.kind === "txt" ? window.createNnTxt : window.createNnH;
      this.mod = await factory({ print: (l) => { this.stdout += l + "\n"; }, printErr: (l) => { this.stderr += l + "\n"; } });
      if (this.kind === "txt") {
        const res = await fetch("build/models/7seg.txt");
        if (!res.ok) throw new Error("build/models/7seg.txt: " + res.status);
        this.mod.FS.writeFile("/7seg.txt", new Uint8Array(await res.arrayBuffer()));
      }
    })());
  }
  command(bits) {
    return this.kind === "txt" ? `nn_cli_txt 7seg.txt ${bits.join("")}` : `nn_cli_h ${bits.join("")}`;
  }
  async forward(bits) {
    await this.init();
    this.stdout = ""; this.stderr = "";
    const args = this.kind === "txt" ? ["/7seg.txt", bits.join("")] : [bits.join("")];
    const t0 = performance.now();
    const code = this.mod.callMain(args);
    const compute_ms = performance.now() - t0;
    if (code) throw new Error(`exit code ${code}: ${this.stderr.trim()}`);
    return { inputs: bits, ...JSON.parse(this.stdout), compute_ms, stdout: this.stdout, command: this.command(bits) };
  }
}

// ---------- ESP32 sketch (Part 6) in WebAssembly ----------
export class EspEngine {
  constructor(onSerial) { this.onSerial = onSerial; }
  init() {
    return (this.ready ??= (async () => {
      await loadScript("build/wasm/esp32.js");
      this.mod = await window.createEsp32({ print: (l) => this.onSerial(l), printErr: (l) => this.onSerial("[stderr] " + l) });
      this.mod._sim_start();
    })());
  }
  send(ch) { this.mod._sim_send(ch.charCodeAt(0)); }
  pinMode(p) { return this.mod._sim_pin_mode(p); }
  pinLevel(p) { return this.mod._sim_pin_level(p); }
}

// ---------- TensorFlow.js (Part 3, visualization only) ----------
export class TFEngine {
  constructor(weightsUrl) { this.url = weightsUrl; }
  init() {
    return (this.ready ??= (async () => {
      await loadScript("https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js");
      const res = await fetch(this.url);
      if (!res.ok) throw new Error(this.url + ": " + res.status);
      this.data = await res.json();
      const tf = window.tf;
      this.model = tf.sequential();
      this.data.layers.forEach((l, i) => this.model.add(tf.layers.dense({
        units: l.units, activation: l.activation, ...(i === 0 ? { inputShape: [this.data.input_size] } : {}),
      })));
      this.model.layers.forEach((dense, i) =>
        dense.setWeights([tf.tensor2d(this.data.layers[i].kernel), tf.tensor1d(this.data.layers[i].bias)]));
      this.backend = tf.getBackend();
    })());
  }
  // Weights in the JSON export layout, only to draw the graph (Keras kernel is inputs x neurons)
  network() {
    const sizes = [this.data.input_size, ...this.data.layers.map((l) => l.units)];
    return {
      layer_sizes: sizes, activation: this.data.layers[0].activation,
      layers: this.data.layers.map((l) => ({
        neurons: l.bias.map((b, j) => ({ weights: l.kernel.map((row) => row[j]), bias: b })),
      })),
    };
  }
  // Same as layer_values() in part3_tensorflow/tf_net.py: z = values·kernel + bias, a = dense(values)
  async forward(bits) {
    await this.init();
    const tf = window.tf;
    const t0 = performance.now();
    const tensors = tf.tidy(() => {
      let values = tf.tensor2d([bits], [1, bits.length]);
      return this.model.layers.map((dense) => {
        const [kernel, bias] = dense.getWeights();
        const z = values.matMul(kernel).add(bias);
        values = dense.apply(values);
        return [z, values];
      });
    });
    const arrays = await Promise.all(tensors.map(([z, a]) => Promise.all([z.data(), a.data()])));
    tensors.flat().forEach((t) => t.dispose());
    const compute_ms = performance.now() - t0;
    const layers = arrays.map(([z, a]) => Array.from(z, (zi, i) => ({ z: zi, a: a[i] })));
    return { inputs: bits, layers, output: layers.at(-1).map((n) => n.a), compute_ms };
  }
}
