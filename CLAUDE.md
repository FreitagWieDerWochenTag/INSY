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
- GitHub Pages: `.github/workflows/pages.yml` builds every project's `web/` folder into `https://<owner>.github.io/INSY/<project>/`;
  the landing page is `index.html` in the repo root. Add new projects to it and to the workflow.
- Commits go to `main`; the workflow tests and deploys on every push.
