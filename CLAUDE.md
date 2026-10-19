# CLAUDE.md – INSY repository

Repository for INSY school projects, one folder per project. Each project has its own `CLAUDE.md`
with its decisions, commands and work-log rule – read it before working on that project.

| Folder | Project |
|---|---|
| `NN/` | Neural network from scratch: 4-bit BCD → 7-segment decoder, Parts 1–6 (see `NN/CLAUDE.md`) |

## Conventions for all projects
- Design: follow `DESIGN.md` (Apple-like, navy + white, yellow accent only for active states). Its visual reference is the
  "INSY Design System" in Claude Design (link in DESIGN.md). Keep both in sync when the design changes.
- Code, comments, console output and docs are in English.
- Shared Python venv at the repo root: `.venv` (gitignored). Run commands from the repo root.
- Inside a project: general folders (`docs/`, `models/`, `tools/`, `web/`) + one folder per assignment part.
- GitHub Pages: `.github/workflows/pages.yml` builds the general site `web/` (start page with the sections General: design,
  rules, general prompt log, and Projects) into `https://<owner>.github.io/INSY/` and every project's `web/` folder into
  `https://<owner>.github.io/INSY/<project>/`. Add a new project to `web/index.html`, `web/assets/site.js` (PROJECTS), the workflow
  and `LOGS` in `tools/token_usage.py`.
- Commits go to `main`; the workflow tests and deploys on every push.

## Work log (mandatory)
Every project has its own prompt log (`<project>/docs/PROMPT_LOG.md`); work on the repository itself (structure, rules,
design, start page, tools) goes to the general log `docs/PROMPT_LOG.md`. After **every** user prompt, append an entry
`## #N – YYYY-MM-DD – <prompt summary>` to each log the prompt worked in (N = the shared prompt number), with what was done,
files changed and decisions. The token numbers are measured, never estimated: run
`.venv/bin/python tools/token_usage.py --write-log`, which regenerates the cost block at the top of every log (+ `token_usage.json`
for the Log pages). It splits a prompt's API calls by the paths they touched; calls without a path follow `PROMPT_PROJECT`
(default NN). Never edit the block between `<!-- COSTS:START/END -->` by hand. Prices live in `PRICES` in `tools/token_usage.py`.
