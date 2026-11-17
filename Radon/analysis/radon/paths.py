"""Paths of the Radon project, independent of the working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # the Radon folder
DATA = ROOT / "data" / "radon_sample_data.csv"       # raw export of the sensors
WEB_DATA = ROOT / "web" / "build" / "data"           # JSON for the dashboard (generated, gitignored)
