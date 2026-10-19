# INSY

School projects for INSY, one folder per project.

| Project | Description | Live page |
|---|---|---|
| [NN](NN/) | Neural network from scratch that decodes a 4-bit BCD digit into a 7-segment display: Python, TensorFlow comparison, C inference, ESP32 | [open](https://freitagwiederwochentag.github.io/INSY/NN/) |

Start page: <https://freitagwiederwochentag.github.io/INSY/>

General (shared by all projects): design rules [DESIGN.md](DESIGN.md), repo rules [CLAUDE.md](CLAUDE.md),
the general prompt log [docs/PROMPT_LOG.md](docs/PROMPT_LOG.md) and the token tool [tools/token_usage.py](tools/token_usage.py).
Each project keeps its own prompt log in its own `docs/` folder.

The live pages are built and deployed by GitHub Actions (`.github/workflows/pages.yml`) on every push to `main`.
