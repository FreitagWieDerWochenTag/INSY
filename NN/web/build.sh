#!/bin/sh
# Builds everything the web page needs into web/build/ (also used by .github/workflows/pages.yml):
#   build/models/  the exported networks (JSON/TXT/.h, TF weights, TF comparison)
#   build/py/nn/   the unchanged Python package of Parts 1+2, run in the browser by Pyodide
#   build/docs/    the prompt log + token usage (tools/token_usage.py --write-log) for the Log page
#   build/wasm/    the C code (Parts 4/5) and the ESP32 sketch (Part 6) compiled to WebAssembly
#   build/pyodide/ Pyodide (CPython + NumPy as WebAssembly), served from our own site: Safari refuses
#                  to load it into a web worker from the CDN (importScripts across origins)
# Needs Emscripten (brew install emscripten). Preview: python3 -m http.server -d NN/web 8000
set -e
NN="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$NN/web/build"
mkdir -p "$OUT/models" "$OUT/py/nn"
cp "$NN"/models/*.json "$NN"/models/*.txt "$NN"/models/*.h "$OUT/models/"
cp "$NN"/part1_2_python/nn/*.py "$OUT/py/nn/"
mkdir -p "$OUT/docs" && cp "$NN/docs/PROMPT_LOG.md" "$NN/docs/token_usage.json" "$OUT/docs/"   # Log page
(cd "$OUT/py/nn" && printf '[%s]\n' "$(ls *.py | sed 's/.*/"&"/' | paste -sd, -)") > "$OUT/py/files.json"
make -s -C "$NN/part4_5_c" web

PYODIDE_VERSION=314.0.7
PYODIDE_URL="https://cdn.jsdelivr.net/pyodide/v$PYODIDE_VERSION/full"
NUMPY_WHEEL=numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl   # from pyodide-lock.json of that version
mkdir -p "$OUT/pyodide"
for f in pyodide.mjs pyodide.asm.mjs pyodide.asm.wasm python_stdlib.zip pyodide-lock.json "$NUMPY_WHEEL"; do
  [ -s "$OUT/pyodide/$f" ] || curl -fsSL -o "$OUT/pyodide/$f" "$PYODIDE_URL/$f"
done
echo "web build ready: $OUT"
