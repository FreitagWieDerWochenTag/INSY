# Radon – what drives it in this house

Seven months (Mar–Oct 2026) of radon readings from seven rooms, plus indoor climate and local weather, analysed in Python
(pandas, SciPy) and shown in an interactive dashboard: **<https://freitagwiederwochentag.github.io/INSY/Radon/>**

Every finding is tested on one value per day (or per airing event) and shown as "holds" only if p < 0.01 and the effect
is large enough to matter; the ones that don't hold are shown too.

```
.venv/bin/pip install -r Radon/requirements.txt -e Radon
.venv/bin/python Radon/analysis/run_analysis.py     # prints every finding with its statistic
cd Radon && ../.venv/bin/pytest -q
Radon/web/build.sh && python3 -m http.server -d Radon/web 8001
```

Details, decisions and layout: [CLAUDE.md](CLAUDE.md). Prompt log: [docs/PROMPT_LOG.md](docs/PROMPT_LOG.md).
