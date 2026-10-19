#!/bin/sh
# Builds everything the web page needs into web/build/ (also used by .github/workflows/pages.yml):
#   build/models/  the exported networks (JSON/TXT/.h, TF weights, TF comparison)
#   build/py/nn/   the unchanged Python package of Parts 1+2, run in the browser by Pyodide
#   build/wasm/    the C code (Parts 4/5) and the ESP32 sketch (Part 6) compiled to WebAssembly
# Needs Emscripten (brew install emscripten). Preview: python3 -m http.server -d NN/web 8000
set -e
NN="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$NN/web/build"
mkdir -p "$OUT/models" "$OUT/py/nn"
cp "$NN"/models/*.json "$NN"/models/*.txt "$NN"/models/*.h "$OUT/models/"
cp "$NN"/part1_2_python/nn/*.py "$OUT/py/nn/"
(cd "$OUT/py/nn" && printf '[%s]\n' "$(ls *.py | sed 's/.*/"&"/' | paste -sd, -)") > "$OUT/py/files.json"
make -s -C "$NN/part4_5_c" web
echo "web build ready: $OUT"
