"""Project paths, so scripts work no matter which directory they are started from."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # the NN project folder
MODELS = ROOT / "models"
