#!/bin/sh
# Builds the general site (landing page, design, general prompt log) into web/build/ (also used by pages.yml).
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/web/build"
mkdir -p "$OUT"
cp "$REPO/DESIGN.md" "$REPO/docs/PROMPT_LOG.md" "$REPO/docs/token_usage.json" "$OUT/"
echo "general site build ready: $OUT"
