"""Cleaning rules and the common hourly grid that all findings use."""
import numpy as np
import pandas as pd

from .load import ROOMS

WARMUP_MIN = 60          # a radon monitor needs about an hour after a (re)start before its value means anything
GLITCH_NEIGHBOURS = 30   # a 0 Bq/m³ reading is a dropout if the readings around it are clearly above this


def clean_radon(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Radon readings per room with warm-up readings and 0-dropouts removed.

    Returns the cleaned frame (one column per room key) and how many readings each rule removed.
    Zeros are real in rooms with very little radon, so a 0 is only dropped when its neighbours are high.
    """
    out, removed = {}, {}
    for key in ROOMS:
        col, up = f"{key}_radon", f"{key}_uptime"
        if col not in raw:
            continue
        s = raw[col].dropna()
        s = s[~s.index.duplicated(keep="last")]
        n0 = len(s)
        if up in raw:
            uptime = raw[up].reindex(s.index)
            s = s[~(uptime < WARMUP_MIN)]
        n_warm = n0 - len(s)
        s = s.clip(lower=0)  # -0.0 in the export
        around = s.rolling(7, center=True, min_periods=3).median()
        glitch = (s == 0) & (around > GLITCH_NEIGHBOURS)
        s = s[~glitch]
        out[key] = s
        removed[key] = {"readings": n0, "warmup": int(n_warm), "dropouts": int(glitch.sum()), "kept": len(s)}
    return pd.DataFrame(out), removed


def hourly(raw: pd.DataFrame) -> pd.DataFrame:
    """Everything on one hourly grid (mean of the readings in each hour): radon per room + climate + weather."""
    radon, _ = clean_radon(raw)
    radon_h = radon.resample("1h").mean()
    other = raw[[c for c in raw.columns if not c.endswith(("_radon", "_uptime"))]]
    other_h = other.resample("1h").mean()
    h = radon_h.join(other_h, how="outer")
    # outdoor values are hourly but not on the full hour: fill single gaps so they line up with the radon hours
    for c in ("out_temp", "out_pressure", "wind", "soil_temp_0", "soil_temp_6", "soil_temp_54"):
        if c in h:
            h[c] = h[c].interpolate(limit=2, limit_area="inside")
    return h


def daily(h: pd.DataFrame, min_hours: int = 18) -> pd.DataFrame:
    """Daily means; a day counts for a column only if at least `min_hours` hours have data."""
    count = h.resample("1D").count()
    mean = h.resample("1D").mean()
    return mean.where(count >= min_hours)
