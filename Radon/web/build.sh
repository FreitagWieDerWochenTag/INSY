#!/bin/sh
# Builds everything the dashboard needs into web/build/ (also used by .github/workflows/pages.yml):
#   build/data/  the JSON written by the Python analysis (analysis/run_analysis.py) from data/radon_sample_data.csv
#   build/docs/  the prompt log + token usage (tools/token_usage.py --write-log) for the Log page
# Preview: python3 -m http.server -d Radon/web 8001
set -e
RADON="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
[ -x "$RADON/../.venv/bin/python" ] && [ -z "$PYTHON" ] && PY="$RADON/../.venv/bin/python"
"$PY" "$RADON/analysis/run_analysis.py" > /dev/null
mkdir -p "$RADON/web/build/docs"
cp "$RADON/docs/PROMPT_LOG.md" "$RADON/docs/token_usage.json" "$RADON/web/build/docs/"
echo "Radon web build ready: $RADON/web/build"
