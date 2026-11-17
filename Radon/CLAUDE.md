# CLAUDE.md – Radon project

## Project
School project (INSY): analyse the radon sensor export `data/radon_sample_data.csv` (2026-03-24 → 2026-10-13, Vienna)
and show **data-backed** conclusions in a dashboard. No assignment PDF; the goal given by the user: find correlations and
show meaningful findings (e.g. night vs. day, closed windows – and more), each one backed by the data.

Data: radon (Bq/m³) + sensor uptime for 7 rooms (Büro, Küche, Küche-Sockel, Schlafzimmer, Technikraum, Werkstatt,
Wohnzimmer), indoor climate (pressure, temperature, CO₂, humidity) in Küche + Schlafzimmer, weather (temperature, pressure,
wind, soil temperature at 0/6/54 cm). One row per sensor message, ~10 min per radon sensor, hourly weather.

## Decisions
- Python with pandas + SciPy does all the analysis; the dashboard only draws the JSON it writes (no statistics in JS).
  The 20 MB CSV is committed so CI can rebuild everything.
- Cleaning: readings in the first 60 min after a sensor restart (uptime) are dropped; a 0 is a dropout only if its
  neighbours are > 30 Bq/m³ (zeros in low-radon rooms are real). Everything is averaged onto one hourly grid.
- "Nobody at home" = days where neither CO₂ sensor varies by more than 100 ppm (found: 1–5 Aug 2026). These days are
  excluded from the weather/driver links so one event does not dominate them.
- Tests use **one value per day** (or per airing event), never thousands of autocorrelated hours. A finding holds when
  p < 0.01 **and** the effect matters (|Spearman ρ| ≥ 0.2 or ≥ 10 % difference). Findings that don't hold are shown too,
  in "Not supported by the data". Statements are generated from the numbers, never hard-coded.
- Zones (rooms whose radon moves together) are found by clustering, not assumed.
- Reference levels: 300 Bq/m³ (Austrian radon ordinance / EU 2013/59/Euratom), 100 Bq/m³ (WHO).
- Charts: plain SVG, design tokens from DESIGN.md; series `--s1`, `--s2`; positive ρ = s1, negative = s2;
  yellow only for the selected room.

## Commands (run from the repo root)
```
.venv/bin/pip install -r Radon/requirements.txt -e Radon   # -e makes `radon` importable
.venv/bin/python Radon/analysis/run_analysis.py           # CSV -> web/build/data/*.json, prints every finding + stats
cd Radon && ../.venv/bin/pytest -q                         # tests (cleaning rules, statistics on synthetic data, real run)
Radon/web/build.sh                                         # dashboard build: analysis JSON + prompt log
python3 -m http.server -d Radon/web 8001                   # preview on http://localhost:8001
.venv/bin/python tools/token_usage.py --write-log          # token usage per prompt (repo tool, writes every prompt log)
```

## Layout
```
data/              radon_sample_data.csv (raw export, German column names)
docs/              PROMPT_LOG.md (Radon's prompt log), token_usage.json
analysis/radon/    load.py (CSV -> English column names, Vienna time), clean.py (cleaning, hourly/daily grid),
                   findings.py (overview, correlations, one function per finding), export.py (JSON), paths.py
analysis/          run_analysis.py, tests/
web/               index.html (dashboard), log.html, assets/ (style.css, common.js, dashboard.js), build.sh
```
- `web/build/` is generated (gitignored); `.github/workflows/pages.yml` builds, tests and deploys it to `/INSY/Radon/`.
- A new finding = a function `f_<name>(h)` in `findings.py` returning `{id, title, statement, held, stat, method, chart}`
  (chart types: `bars`, `lines`, `matrix`), added to `all_findings`, plus a test on synthetic data with a known answer.

## Work log (mandatory)
The rule is in the repo root's CLAUDE.md. Radon's entries go to `Radon/docs/PROMPT_LOG.md`; work on the repo itself goes to the
general log `docs/PROMPT_LOG.md`. Tokens: `.venv/bin/python tools/token_usage.py --write-log`.
