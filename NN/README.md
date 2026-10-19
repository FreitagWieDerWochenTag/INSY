# NN – BCD → 7-segment decoder network

A feedforward neural network written from scratch in Python (`Neuron` → `Layer` → `NeuralNetwork`) that turns a
4-bit BCD digit (0–9) into the seven segments A–G of a display. Assignment: [docs/Aufgabenstellung.pdf](docs/Aufgabenstellung.pdf).

**Interactive page: <https://freitagwiederwochentag.github.io/INSY/NN/>**. Each part runs its real code in the browser:
Python via Pyodide, C and the ESP32 sketch via WebAssembly, and the Keras weights via TensorFlow.js (Part 3, visualization only).

| Part | Folder | What | Result |
|---|---|---|---|
| 1 + 2 | [part1_2_python](part1_2_python/) | network, backprop, JSON/TXT/.h export + import; XOR 2-2-1 and 7-seg 4-16-7 | 4/4, 10/10 |
| 3 | [part3_tensorflow](part3_tensorflow/) | same nets in TensorFlow/Keras, same start weights and sample order | TF with our loss = ours to 1e-5 |
| 4 + 5 | [part4_5_c](part4_5_c/) | forward-only C library: weights from `.txt` (Part 4) or compiled in from `.h` (Part 5) | 10/10, Δ < 1e-7 to Python |
| 6 | [part6_esp32](part6_esp32/) | Arduino sketch for an ESP32: serial digit → network → 7 GPIOs → display | builds with PlatformIO |

Shared folders: `models/` (all exported networks), `docs/` (assignment, [prompt log](docs/PROMPT_LOG.md)),
`tools/` (token usage of the Claude Code sessions), `web/` (the interactive page).

## Run it
From the repository root:
```
python3 -m venv .venv && .venv/bin/pip install -r NN/requirements.txt -e NN
.venv/bin/python NN/part1_2_python/train_7seg.py      # train + export (Part 2)
.venv/bin/python NN/part1_2_python/verify_7seg.py     # re-import + check 10/10
.venv/bin/pip install --pre -r NN/requirements-tf.txt && .venv/bin/python NN/part3_tensorflow/compare_tf.py   # Part 3
make -C NN/part4_5_c test                             # Parts 4/5
cd NN/part6_esp32 && pio run -t upload                # Part 6 on a real ESP32
cd NN && ../.venv/bin/pytest                          # all tests
```
Web page locally (needs Emscripten, `brew install emscripten`): `NN/web/build.sh && python3 -m http.server -d NN/web 8000`.

### ESP32 wiring (from the assignment)
| Segment | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| GPIO | 0 | 4 | 16 | 17 | 5 | 18 | 19 |

Each segment goes through a ~330 Ω resistor. The common cathode goes to GND (build with `-DCOMMON_ANODE` for a common-anode display).
