# CLAUDE.md – NN project

## Project
School project (INSY): feedforward neural network written from scratch in Python that decodes a
**4-bit BCD input (digits 0–9)** into the **7 segments A–G** of a 7-segment display.
Full assignment: `docs/Aufgabenstellung.pdf` (Parts 1–6). All parts are implemented:
1/2 Python network + export/import, 3 TensorFlow comparison, 4/5 forward-only C library reading the
`.txt` and the `.h` export, 6 ESP32 sketch (with a host simulation, since no board is attached).

## Decisions
- Input is 4 bit as in the PDF (not 3 bit).
- NumPy is allowed; otherwise only the standard library (+ pytest for tests). TensorFlow only for Part 3
  (`requirements-tf.txt`, separate so the rest works without it; `tf_net.py` is not part of the `nn` package).
- Keep the class structure from the PDF: `Neuron` → `Layer` → `NeuralNetwork`. Do not replace it
  with whole-layer matrix math – the per-neuron structure is part of the assignment.
- Code, comments, console output and docs are in English.
- Hyperparameters from the PDF: XOR 2-2-1, 7-seg 4-16-7, 20000 epochs, learning rate 0.1, sigmoid.
- One folder per part (1+2, 3, 4+5, 6); shared things (docs, models, tools, web) are top-level folders of NN.

## Commands (run from the repo root, the folder above NN)
```
python3 -m venv .venv && .venv/bin/pip install -r NN/requirements.txt -e NN   # -e NN makes `nn` importable everywhere
.venv/bin/python NN/part1_2_python/train_xor.py     # train XOR, export models/xor.{json,txt} + xor_net.h
.venv/bin/python NN/part1_2_python/verify_xor.py    # re-import JSON and verify
.venv/bin/python NN/part1_2_python/train_7seg.py    # train 7-seg decoder, export models/7seg.{json,txt} + 7seg_net.h
.venv/bin/python NN/part1_2_python/verify_7seg.py   # re-import JSON and verify all 10 digits
.venv/bin/pip install --pre -r NN/requirements-tf.txt  # Part 3 only (Python 3.14 has only a TF release candidate)
.venv/bin/python NN/part3_tensorflow/compare_tf.py  # Part 3 -> models/tf_comparison.json, *_tf.keras, *_tf_weights.json
make -C NN/part4_5_c test                           # Parts 4/5: build C library + tests (.txt and .h), 10/10 digits
cd NN/part6_esp32 && pio run -t upload              # Part 6: build/flash the ESP32 sketch
NN/web/build.sh                                     # web page build: models + Python code + WebAssembly (needs emcc)
python3 -m http.server -d NN/web 8000               # preview the web page on http://localhost:8000
cd NN && ../.venv/bin/pytest                        # all tests (see pytest.ini; wasm tests need node + web build)
.venv/bin/python tools/token_usage.py               # token usage per prompt (repo tool, writes every prompt log)
```

## Layout
```
docs/              Aufgabenstellung.pdf, PROMPT_LOG.md (NN's prompt log), token_usage.json
models/            exported networks, shared by all parts (json, txt, .h, keras, TF weights, comparison)
part1_2_python/    nn/ (neural_network.py, datasets.py, paths.py), train_*/verify_* scripts, tests/
part3_tensorflow/  tf_net.py, compare_tf.py, tests/
part4_5_c/         lib/nn (nn.h, nn.c, nn_from_header.h), nn_cli.c, test_*.c, Makefile (native + `web` targets), tests/
part6_esp32/       platformio.ini, src/main.cpp, sim/ (Arduino mock: sim_main.cpp for the PC, web_main.cpp for wasm), tests/
web/               static site for GitHub Pages: index + one page per part, assets/, build.sh, tests/
conftest.py        shared fixture: small trained net compiled into all C programs
```
- Import the network as `from nn import NeuralNetwork`. Use paths via `nn.paths.MODELS` / `ROOT` (= NN folder),
  never relative to the working directory.
- Web page: everything shown is computed by the real code of the part, in the browser (the user asked for this explicitly,
  no forward-pass copy in JS): Parts 1+2 run `part1_2_python/nn` in Pyodide (`web/assets/py-worker.js`, `web_api.py`),
  Parts 4+5 and 6 run the C code / unchanged sketch as WebAssembly (`make -C part4_5_c web`). Part 3 is the exception:
  TensorFlow can't run in a browser, so the page loads the trained Keras weights into TensorFlow.js and must say clearly
  that this is for visualization only, linking the real Python files; its training curves are recorded by `compare_tf.py`.
- `web/build/` is generated (gitignored); the GitHub Actions workflow `.github/workflows/pages.yml` builds, tests and deploys it.

## Export formats
- JSON: `{"layer_sizes", "activation", "layers": [{"neurons": [{"weights", "bias"}]}]}`, full precision.
- TXT: line-oriented, parseable with `fscanf`: `layers N`, `sizes ...`, `activation ...`, then one line
  per neuron `layer L neuron N bias B weights W0 W1 ...`. Layer index 1 = first hidden layer.
- H: include guard, `NN_NUM_LAYERS`, `NN_LAYER_SIZES[]`, `NN_L<k>_WEIGHTS[n][m]`, `NN_L<k>_BIASES[n]`,
  must compile standalone (`cc -fsyntax-only -x c NN/models/7seg_net.h`).
- TF weights (`*_tf_weights.json`): `{"input_size", "layers": [{"units", "activation", "kernel", "bias"}]}`, Keras layout.

## Work log (mandatory)
The rule is in the repo root's CLAUDE.md. NN's entries go to `NN/docs/PROMPT_LOG.md`; work on the repo itself (design, rules,
start page, tools) goes to the general log `docs/PROMPT_LOG.md` in the repo root. Tokens: `.venv/bin/python tools/token_usage.py --write-log`.
