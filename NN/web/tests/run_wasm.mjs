// Runs the WebAssembly builds in Node exactly like the web page does and prints one JSON object.
// Used by web/tests/test_wasm.py:  node run_wasm.mjs WASM_DIR MODEL.txt
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const [wasmDir, modelTxt] = process.argv.slice(2);
const require = createRequire(import.meta.url);
const load = (name) => require(path.resolve(wasmDir, name + ".js"));
const codes = Array.from({ length: 16 }, (_, d) => [3, 2, 1, 0].map((s) => (d >> s) & 1).join(""));

async function cli(factory, args) {
  let out = "";
  const mod = await factory({ print: (line) => { out += line + "\n"; }, printErr: () => {} });
  if (args.txt) mod.FS.writeFile("/7seg.txt", readFileSync(modelTxt));
  return codes.map((bits) => {
    out = "";
    mod.callMain(args.txt ? ["/7seg.txt", bits] : [bits]);
    return JSON.parse(out);
  });
}

const result = {
  nn_txt: await cli(load("nn_txt"), { txt: true }),
  nn_h: await cli(load("nn_h"), {}),
};
let serial = "";
const esp = await load("esp32")({ print: (line) => { serial += line + "\n"; } });
esp._sim_start();
const pins = [0, 4, 16, 17, 5, 18, 19];
result.esp32 = { setup: pins.map((p) => esp._sim_pin_level(p)), digits: [] };
for (const ch of "0123456789x") {
  serial = "";
  esp._sim_send(ch.charCodeAt(0));
  result.esp32.digits.push({ ch, pins: pins.map((p) => esp._sim_pin_level(p)), serial });
}
console.log(JSON.stringify(result));
